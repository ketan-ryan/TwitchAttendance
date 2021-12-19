import socket


class TwitchIRC:
    server = 'irc.chat.twitch.tv'
    port = 6667
    nickname = 'hazey'
    token = ''
    channel = ''
    sock = socket.socket()

    def __init__(self, name) -> None:
        """
        Setup socket to Twitch IRC server
        Request tags, commands, membership capabilities to be able to execute Twitch commands
        Load oauth token from local file
        """
        self.channel = name

        with open('secrets.txt', 'r') as fp:
            self.token = fp.readline().strip()

        self.sock.connect((self.server, self.port))
        self.sock.send('CAP REQ :twitch.tv/commands twitch.tv/membership\r\n'.encode('utf-8'))
        self.sock.send(f'PASS {self.token}\r\n'.encode('utf-8'))
        self.sock.send(f'NICK {self.nickname}\r\n'.encode('utf-8'))
        self.sock.send(f'JOIN #{self.channel}\r\n'.encode('utf-8'))


    def get_mods(self):
        """Use the /mods command to get all mods in a Twitch chat"""
        mods_substr = f'NOTICE #{self.channel} :The moderators of this channel are: '
        substr_idx = -999
        self.sock.send(f'PRIVMSG #{self.channel} :/mods\r\n'.encode('utf-8'))

        # We need a loop to get the full response from recv
        while True:
            resp = self.sock.recv(2048).decode('utf-8')
            for m in resp.split('\r\n'):
                if m.find(mods_substr) != -1:
                    substr_idx = m.find(mods_substr)
            if substr_idx != -999:
                break

        # Return list of moderators, stripped of whitespace
        return [x.strip() for x in resp[resp.find(mods_substr) + len(mods_substr):].split()]


    def get_vips(self):
        """Use the /vips command to get all vips in a Twitch chat"""
        vips_substr = f'NOTICE #{self.channel} :The VIPs of this channel are: '
        substr_idx = -999
        self.sock.send(f'PRIVMSG #{self.channel} :/vips\r\n'.encode('utf-8'))

        # We need a loop to get the full response from recv
        while True:
            resp = self.sock.recv(2048).decode('utf-8')
            for m in resp.split('\r\n'):
                if m.find(vips_substr) != -1:
                    substr_idx = m.find(vips_substr)
            if substr_idx != -999:
                break

        # Return list of vips, stripped of whitespace
        return [x.strip() for x in resp[resp.find(vips_substr) + len(vips_substr):].split()]


    def close(self):
        """Close connection"""
        self.sock.close()
