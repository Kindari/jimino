import re
from events import RelevantEventListener

class Entity(RelevantEventListener):
    def __init__(self, manager, irc, server, identifier):
        self.manager = manager
        self.irc = irc
        self.server = server
        self.identifier = identifier
        self.type = 'entity'
        self.init()
        RelevantEventListener.__init__(self, irc.dispatcher)
    def __repr__(self):
        return '<%s "%s">' % ( self.__class__, self.identifier )
    def __str__(self):
        return self.identifier
    def init(self):
        pass

class User(Entity):
    def init(self):
        self.type = 'user'
        self.nickname = self.identifier.group('nickname')
        self.username = self.identifier.group('username')
        self.host = self.identifier.group('host')
        self.identifier = "%s!%s@%s" % (self.nickname, self.username, self.host)
        self.channels = []
    def __iter__(self):
        return self.channels
    def __str__(self):
        return self.nickname
    def invite(self, channel):
        return self.server.invite(self, channel)
    def kick(self, channel, message = None):
        return self.server.kick(channel, self, message)
    def notice(self, message):
        return self.server.notice(self, message)
    def who(self, op = False ):
        return self.server.who( self, op )
    def whois(self):
        return self.server.whois(self)
    def whowas(self, max, server):
        return self.server.whowas(self, max, server)
    def privmsg(self, message):
        return self.server.privmsg(self, message)
    say = privmsg
    def action(self, message):
        return self.server.action(self, message)
    do = action
    def ctcp(self, command, message = None):
        return self.server.ctcp( self, command, message )
    def ctcp_reply(self, parameter):
        return self.server.ctcp_reply( self, parameter )
    def onJoin(self, event):
        if not event.target in self.channels:
            self.channels.append( event.target )
    def onPart(self, event):
        if event.target in self.channels:
            self.channels.remove( event.target )
    def onWhoReply(self, event):
        if not event.source in self.channels:
            self.channels.append(event.source)
    def onQuit(self, event):
        del self.manager.users[ self.nickname.lower() ]
    def onNick(self, event):
        del self.manager.users[ self.nickname.lower() ]
        self.nickname = event.target
        self.manager.users[ self.nickname.lower() ] = self
    

class Channel(Entity):
    def init(self):
        self.type = 'channel'
        self.topic = ''
        self.users = []

    def __iter__(self):
        return self.users

    def invite(self, nick):
        return self.server.invite(nick, self)
    def kick(self, nick, message = None):
        return self.server.kick(self, nick, message)
    def list(self):
        return self.server.list(self)
    def names(self):
        return self.server.names(self)
    def notice(self, message):
        return self.server.notice(self, message)
    def part(self, message):
        return self.server.part(self, message)
    def topic(self, topic = None):
        return self.server.topic( self, topic )
    def privmsg(self, message):
        return self.server.privmsg(self, message)
    say = privmsg
    def action(self, message):
        return self.server.action(self, message)
    do = action
    def ctcp(self, command, message = None):
        return self.server.ctcp(self, command, message)
    def ctcp_reply(self, parameter):
        return self.server.ctcp_reply( self, parameter )
    def who(self):
        return self.server.who(self)

    def onCurrentTopic(self, event):
        self.topic = event.message
    def onEndOfNames(self, event):
        self.who()
    def onWhoReply(self, event):
        if not event.target in self.users:
            self.users.append(event.target)
    def onEndOfWho(self, event):
        print self.users
    def onJoin(self, event):
        if not event.source in self.users:
            self.users.append( event.source )
    def onPart(self, event):
        if event.source in self.users:
            self.users.remove( event.source )
    def onQuit(self, event):
        if event.source in self.users:
            self.users.remove( event.source )

class EntityManager:
    def __init__(self, irc, server):
        self.irc = irc
        self.server = server
        self.users = {}
        self.channels = {}
    
    def __call__(self, identifier):
        user_match = irc_user_regex.match(identifier)
        if user_match:
            nick = user_match.group('nickname').lower()
            if nick in self.users:
                return self.users[ nick ]
            user = User(self, self.irc, self.server, user_match)
            self.users[ nick ] = user
            return user
        elif identifier[0] in self.server.chan_prefix:
            if identifier.lower() in self.channels:
                return self.channels[ identifier.lower() ]
            channel = Channel(self, self.irc, self.server, identifier)
            self.channels[identifier.lower()] = channel
            return channel
        elif identifier.lower() in self.users:
            return self.users[ identifier.lower() ]
        else:
            return Entity(self, self.irc, self.server, identifier)
        

irc_user_regex = re.compile("^(?P<nickname>.*)!(?P<username>.*)@(?P<host>.*)$")