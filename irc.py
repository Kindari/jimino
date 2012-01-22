import select
import re
import socket, ssl
import os, sys
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

    def nick(self, nickname):
        self.raw("NICK %s" % nickname )

    def user(self, username, realname):
        self.raw("USER %s 0 * :%s" % (username, realname))

    def password(self, password):
        self.raw("PASS %s" % password)

    def quit(self, message = None):
        if message is None:
            self.raw("QUIT")
        else:
            self.raw("QUIT :%s" % message)

    def privmsg(self, target, message):
        self.raw("PRIVMSG %s :%s" % (target, message))

    def pong(self, *args):
        self.raw("PONG %s" % ' '.join(args))

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
    servers = config.servers()
    for network in servers:
        options = servers[ network ]
        server = irc.server()
        server.connect( **options )
    irc.run( float(settings['timeout']) )
    for server in irc.servers:
        server.quit()
