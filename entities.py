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
    def __str__(self):
        return self.nickname

class Channel(Entity):
    def init(self):
        self.type = 'channel'

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