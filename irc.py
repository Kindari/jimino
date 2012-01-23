import select
import re
import socket, ssl
import os, sys, signal
import time

from events import EventListener, EventDispatcher
from entities import EntityManager
import config

class IRCError(Exception): pass

class IRC:
    def __init__(self):
        self.servers = []
        self.dispatcher = EventDispatcher()
        self.running = True
        self.debug = False

    def server(self):
        server = Server( self )
        self.servers.append( server )
        return server
    def connected(self):
        return [server for server in self.servers if server.connected]
    def disconnected(self):
        return [server for server in self.servers if not server.connected]
    def run(self, timeout = 0):
        while self.running:
            mapping = {}
            for server in self.servers:
                if server.socket:
                    mapping[ server.socket ] = server
            i, o, e = select.select( mapping.keys(), [], [] )
            if i:
                for socket in i:
                    mapping[ socket ].process()
            else:
                time.sleep( timeout )
    def shutdown(self, *args):
        self.running = False
        print "Shutdown complete"
        os.remove('irc.pid')
        sys.exit(0)

class ServerError(IRCError): pass




class Server(EventListener):
    def __init__(self, irc):
        self.server_name = ''
        self.irc = irc
        self.connected = False
        self.socket = None
        self.ssl = None
        self.entity = EntityManager(self.irc, self)
        self.chan_prefix = "#"
        EventListener.__init__(self, irc.dispatcher)

    def __repr__(self):
        return self.server_name

    def connect(self, server, port = 6667, nickname="Jimino", password=None, username="Jimino",
            realname="Jimino", localaddress="", localport=0, use_ssl=False, ipv6=False, **options):
        if self.connected:
            self.disconnect()
        self.buffer = ""
        self.server_name = server
        self.nickname = nickname
        self.port = int(port)
        self.username = username or nickname
        self.realname = realname or nickname
        self.server_password = password
        self._local_address = localaddress
        self._local_port = int(localport)
        self._localhost = socket.gethostname()

        if bool(int(ipv6)):
            self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.socket.bind( (self._local_address, self._local_port) )
            self.socket.connect( (self.server_name, self.port) )
            if use_ssl:
                self.ssl = ssl.wrap_socket(self.socket)

        except socket.error, x:
            self.socket.close()
            self.socket = None
            raise ServerError, "Couldn't connect to socket: %s" % x

        self.connected = True
        if self.server_password:
            self.password( self.server_password )

        self.nick( self.nickname )
        self.user( self.username , self.realname )

        return self

    def disconnect(self, message="Goodbye"):
        if not self.connected:
            return
        self.quit(message)
        self.connected = False
        try:
            self.socket.close()
        except socket.error, x:
            pass
        self.socket = None

    def admin(self, server=None):
        if server:
            return self.raw("ADMIN %s" % server)
        return self.raw("ADMIN")
    def globops(self, text):
        return self.raw("GLOBOPS :%s" % text)
    def info(self, server=None):
        if server:
            return self.raw("INFO %s" % server)
        return self.raw("INFO")
    def invite(self, nickname, channel):
        return self.raw("INVITE %s %s" % (nickname, channel))
    def ison(self, nicks):
        return self.raw("ISON %s" % ' '.join(nicks))
    def join(self, channel, key=None):
        if key:
            return self.raw("JOIN %s %s" % (channel, key))
        return self.raw("JOIN %s" % channel)
    def kick(self, channel, nickname, comment = None):
        if comment:
            return self.raw("KICK %s %s :%s" % (channel, nickname, comment))
        return self.raw("KICK %s %s" % (channel, nickname))
    def links(self, server = None, mask = None):
        raw = "LINKS"
        if server:
            raw += " %s" % server
        if mask:
            raw += " %s" % mask
        return self.raw( raw )
    def list(self, channels = None, server = None):
        raw = "LIST"
        if channels:
            raw += ' '
            raw += ' '.join(channels)
        if server:
            raw += ' %s' % server
        return self.raw( raw )
    def lusers(self, server = None):
        if server:
            return self.raw( "LUSERS %s" % server )
        return self.raw("LUSERS")
    def mode(self, target, command):
        #@todo add smart logic here
        return self.raw("MODE %s %s" % (target, command))
    def motd(self, server = None):
        if server:
            return self.raw("MOTD %s" % server)
        return self.raw("MOTD")
    def names(self, channels = None):
        if channels:
            return self.raw("NAMES %s" % ' '.join(channels))
        return self.raw("NAMES")
    def notice(self, target, text):
        return self.raw("NOTICE %s :%s" % (target, text))
    def oper(self, nick, password):
        return self.raw("OPER %s %s" % (nick, password))
    def part(self, channels, message = None):
        if type(channels)==list:
            channels = ' '.join(channels)
        if message:
            return self.raw("PART %s :%s" % (channels, message))
        return self.raw("PART %s" % channels)
    


    def nick(self, nickname):
        return self.raw("NICK %s" % nickname )

    def user(self, username, realname):
        return self.raw("USER %s 0 * :%s" % (username, realname))

    def password(self, password):
        return self.raw("PASS %s" % password)

    def quit(self, message = None):
        if message:
            return self.raw("QUIT :%s" % message)
        return self.raw("QUIT")
    def squit(self, server, message = None):
        if message:
            return self.raw("SQUIT %s :%s" % (server, message))
        return self.raw("SQUIT %s" % server)
    def stats(self, command, server = None):
        if server:
            return self.raw("STATS %s %s" % (command, server))
        return self.raw("STATS %s" % command)
    def time(self, server=None):
        if server:
            return self.raw("TIME %s" % server)
        return self.raw("TIME")
    def topic(self, channel, topic = None):
        if topic:
            return self.raw("TOPIC %s :%s" % (channel, topic))
        return self.raw("TOPIC %s" % channel)
    def trace(self, target = None):
        if target:
            return self.raw("TRACE %s" % target)
        return self.raw("TRACE")
    def userhost(self, nickname):
        if type(nickname)==list:
            nickname = ','.join(nickname)
        return self.raw("USERHOST %s" % nickname)
    def users(self, server = None):
        if server:
            return self.raw("USERS %s" % server)
        return self.raw("USERS")
    def version(self, server = None):
        if server:
            return self.raw("VERSION %s" % server)
        return self.raw("VERSION")
    def wallops(self, text):
        return self.raw("WALLOPS :%s" % text)
    def who(self, target = None, op = False):
        raw = "WHO"
        if target:
            raw += " %s" % target
        if op:
            raw += " o"
        return self.raw( raw )
    def whois(self, target):
        if (type(target)==list):
            target = ','.join(target)
        return self.raw("WHOIS %s" % target)
    def whowas(self, target, max = None, server = None):
        raw = "WHOWAS %s" % target
        if max:
            raw += " %s" % max
        if server:
            raw += " %s" % server
        return self.raw( raw )
    

    def privmsg(self, target, message):
        if (type(target)==list):
            target = ','.join(target)
        return self.raw("PRIVMSG %s :%s" % (target, message))

    def ping(self, *args):
        return self.raw("PING %s" % ' '.join(args))
    def pong(self, *args):
        return self.raw("PONG %s" % ' '.join(args))
    def ctcp(self, target, command, message = None):
        if message:
            return self.privmsg( target, "\001%s %s\001" % (command.upper(), message) )
        return self.privmsg(target, "\001%s\001" % command.upper())
    def ctcp_reply(self, target, parameter):
        return self.notice( target, "\001%s\001" % parameter )
    def action(self, target, message):
        return self.ctcp(target, 'action', message)

    def raw(self, s):
        if not self.connected:
            raise ServerError, "Not Connected"
        try:
            if self.ssl:
                self.ssl.write(s + "\r\n")
            else:
                self.socket.send(s + "\r\n")
            if self.irc.debug:
                print "-->", s
        except socket.error, x:
            self.disconnect("Connection reset by peer")

    def readlines(self, bitrate=2**14):
        if not self.connected:
            raise ServerError, "Not Connected"
        try:
            if self.ssl: #@todo Non blocking reads using select
                new_data = self.ssl.read(bitrate)
            else:
                new_data = self.socket.recv(bitrate)
        except socket.error, x:
            self.disconnect("Connection reset by peer")
            return []
        if not new_data:
            self.disconnect("Connection reset by peer")
            return []
        lines = irc_linesep_regex.split( self.buffer + new_data)
        self.buffer = lines.pop()
        
        return lines

    def parseline(self, line):
        match = irc_1459_line_regex.match(line)
        
        prefix = match.group('prefix')
        command = match.group('command').lower()
        arguments = match.group('arguments')

        if arguments:
            args = arguments.split(' :', 1)
            arguments = args[0].split()
            if len(args) == 2:
                arguments.append(args[1])

        self.irc.dispatcher.dispatch(self.irc, self, prefix, command, arguments)

    def process(self):
        if not self.connected:
            raise ServerError, "Not Connected"
        for line in self.readlines():
            self.parseline( line )
            

irc_linesep_regex = re.compile("\r?\n")
irc_1459_line_regex = re.compile("^(:(?P<prefix>[^ ]+) +)?(?P<command>[^ ]+)( *(?P<arguments> .+))?")


if __name__=="__main__":
    settings = config.settings()
    irc = IRC()
    irc.debug = bool( int( settings['debug'] ))

    signal.signal( signal.SIGTERM, irc.shutdown )
    if irc.debug:
        print "Registered SIGTERM handler"
    
    with open('irc.pid', 'w') as f:
        f.write( str(os.getpid()) )
        if irc.debug:
            print "irc.pid wrote [%s]" % os.getpid()

    servers = config.servers()
    for network in servers:
        options = servers[ network ]
        server = irc.server()
        server.connect( **options )
    irc.run( float(settings['timeout']) )
    for server in irc.servers:
        server.quit()
