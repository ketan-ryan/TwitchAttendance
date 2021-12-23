from sheet_manager import SheetManager
from twitchAPI.twitch import Twitch
from emoji import demojize
from tqdm import tqdm
import urllib.request
import ujson as json
import traceback
import socket
import signal
import time
import re


class TwitchAttendance:
    token = ''
    app_id = ''
    app_secret = ''
    twitch = None
    channel_name = ''
    channel_id = ''
    live_status = None
    sm = None
    lurker_list = []
    start_time = time.time()


    def start(self, name):
        """Setup and initialize values for a desired streamer"""
        self.channel_name = name

        # Load sensitive values from local file
        with open('secrets.txt', 'r') as fp:
            lines = fp.readlines()
            self.token = lines[0].strip()
            self.app_id = lines[1].strip()
            self.app_secret = lines[2].strip()

        self.twitch = Twitch(app_id=self.app_id, app_secret=self.app_secret)

        self.sm = SheetManager(self.channel_name)
        self.channel_id = self.twitch.get_users(logins=self.channel_name)['data'][0]['id']
        self.update_live_status()


    def get_followers(self):
        """
        Get all followers for the desired streamer
        Should only be called once per month when setting up new excel sheet
        """
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
                    followers = self.twitch.get_users_follows(first=100, to_id=self.channel_id, after=cursor)

                    for f in followers['data']:
                        followers_list.append(str(f['from_name']))

                    if(len(followers_list) >= total_followers or len(followers['data']) < 100):
                        break

                    self.sm.write_list(followers_list)
                except Exception:
                    continue


    def update_live_status(self):
        """
        Determine whether the streamer is live
        Doesn't matter if the request times out, only an IndexError indicates the streamer is offline
        """
        try:
            self.live_status = self.twitch.get_streams(user_id=self.channel_id)['data'][0]['type']
        except IndexError:
            self.live_status = None
        except:
            return


    def second_elapsed(self):
        """
        Helper method to only run the update check once a second
        Does not need to run exactly once a second, we just don't need to run it every tick
        """
        return (round(time.time(), 1) - round(self.start_time, 1)).is_integer()


    def live_update(self):
        """
        Handles most of the logic of updating attendance
        Will occasionally update the list of lurking chatters
        Calls the Twitch IRC endpoint to get all chat messages and the user who sent it,
            marking them as present in the spreadsheet
        On exit, will convert the followers list to a set to remove duplicates and update them in the spreadsheet,
        closes the socket, and saves the spreadsheet
        """
        server = 'irc.chat.twitch.tv'
        port = 6667
        nickname = 'hazey'
        channel = f'#{self.channel_name}'

        sock = socket.socket()
        sock.connect((server, port))
        sock.send(f'PASS {self.token}\n'.encode('utf-8'))
        sock.send(f'NICK {nickname}\n'.encode('utf-8'))
        sock.send(f'JOIN {channel}\n'.encode('utf-8'))

        all_followers = self.sm.get_followers()
        all_followers = set(all_followers)

        lurker_list=[]
        try:
            while self.live_status is not None:
                if self.second_elapsed():
                    """Update the viewer list"""
                    try:
                        with urllib.request.urlopen(f'https://tmi.twitch.tv/group/user/{self.channel_name}/chatters') as url:
                            url_data = url.read().decode('utf-8')
                            for item in json.loads(url_data)['chatters']['viewers']:
                                lurker_list.append(item)
                    except Exception:
                        traceback.print_exc()
                        pass

                resp = sock.recv(2048).decode('utf-8')

                if resp.startswith('PING'):
                    sock.send("PONG\n".encode('utf-8'))

                try:
                    # Split IRC response
                    username, channel, message = re.search(':(.*)\!.*@.*\.tmi\.twitch\.tv PRIVMSG #(.*) :(.*)', resp).groups()
                    print(f'{username}: {message}')

                    # Update in spreadsheet
                    if username in all_followers:
                        self.sm.update_attendance(username, 'Present')
                        all_followers.remove(username)

                # Purely visual - print emojis in terminal
                except AttributeError:
                    print(demojize(resp))

                self.update_live_status()
        except Exception:
            traceback.print_exc()
        finally:
            lurker_list = set(lurker_list)
            print(len(lurker_list))
            for lurker in tqdm(lurker_list):
                self.sm.update_attendance(lurker, 'Lurking')
            sock.close()
            self.sm.close()
            exit(0)


if __name__ == '__main__':
    tm = TwitchAttendance()
    def signal_handler(sig, frame):
        tm.sm.close()
        print('\nExiting...')
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    tm.start('atrioc')
    tm.get_followers()
    tm.live_update()
