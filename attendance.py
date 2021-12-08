from twitchAPI.twitch import Twitch
from sheet_manager import SheetManager
import socket
from emoji import demojize
import re
import urllib.request
import ujson as json
import signal
import time


class TwitchAttendance:
    twitch = Twitch(app_id='', app_secret='')
    channel_name = ''
    channel_id = ''
    live_status = None
    sm = None
    lurker_list = []


    def start(self, name):
        self.channel_name = name
        self.sm = SheetManager(self.channel_name)
        self.channel_id = self.twitch.get_users(logins=self.channel_name)['data'][0]['id']
        self.update_live_status()


    def get_followers(self):
        followers_list = []
        followers = self.twitch.get_users_follows(first = 100, to_id=self.channel_id)
        for f in followers['data']:
            followers_list.append(f['from_name'])
        self.sm.write_list(followers_list)

        total_followers = int(followers['total'])
        if self.sm.need_update():
            while(True):
                try:
                    followers_list = []
                    cursor = followers['pagination']['cursor']
                    followers = self.twitch.get_users_follows(first=100, to_id=23211159, after=cursor)

                    for f in followers['data']:
                        followers_list.append(str(f['from_name']))

                    if(len(followers_list) >= total_followers or len(followers['data']) < 100):
                        break

                    self.sm.write_list(followers_list)
                except Exception:
                    continue


    def update_live_status(self):
        try:
            self.live_status = self.twitch.get_streams(user_id=self.channel_id)['data'][0]['type']
        except:
            self.live_status = None


    def live_update(self):
        server = 'irc.chat.twitch.tv'
        port = 6667
        nickname = ''
        token = ''
        channel = f'#{self.channel_name}'

        sock = socket.socket()
        sock.connect((server, port))
        sock.send(f'PASS {token}\n'.encode('utf-8'))
        sock.send(f'NICK {nickname}\n'.encode('utf-8'))
        sock.send(f'JOIN {channel}\n'.encode('utf-8'))
        all_followers = self.sm.get_followers()
        all_followers = set(all_followers)
        lurker_list=[]
        starttime = time.time()
        try:
            while self.live_status is  None:
                if (time.time() - starttime) % 60 == 0:
                    try:
                        with urllib.request.urlopen(f'https://tmi.twitch.tv/group/user/{self.channel_name}/chatters') as url:
                            url_data = url.read().decode('utf-8')
                            lurker_list.append(json.loads(url_data)['chatters']['viewers'])
                            print(lurker_list[0])
                            # self.sm.update_attendance(lurker, 'Lurking')

                            # data = json.loads(url.read().decode('utf-8'))
                            # self.lurker_list = data['chatters']['viewers']
                    except OSError:
                        print('Error')
                        pass

                resp = sock.recv(2048).decode('utf-8')

                if resp.startswith('PING'):
                    sock.send('PONG\n'.encode('utf-8'))

                try:
                    username, channel, message = re.search(':(.*)\!.*@.*\.tmi\.twitch\.tv PRIVMSG #(.*) :(.*)', resp).groups()
                    print(f'{username}: {message}')

                    if username in all_followers:
                        self.sm.update_attendance(username, 'Present')
                        all_followers.remove(username)

                except AttributeError:
                    print(demojize(resp))
        except Exception as e:
            print(e)
        finally:
            lurker_list = set(lurker_list[0])
            for lurker in lurker_list:
                self.sm.update_attendance(lurker, 'Lurking')
            sock.close()
            self.sm.close()
            exit(0)


if __name__ == '__main__':
    tm = TwitchAttendance()
    def signal_handler(sig, frame):
        tm.sm.close()
        print('Exiting...')
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    tm.start('atrioc')
    tm.get_followers()
    tm.live_update()
