import functions
import re

event_listener_regex = re.compile("^on(?P<command>[a-zA-Z0-9]*$)")

class EventError(Exception): pass

class EventListener:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.register_mapping()

    def register_mapping(self):
        mapping = self.find_event_listeners()
        for command, method in mapping.items():
            self.dispatcher.listen( method, command )
    def find_event_listeners(self):
        mapping = {}
        matches = [event_listener_regex.match(prop)
                    for prop in dir(self) if event_listener_regex.match(prop)]
        for match in matches:
            method = getattr(self, match.group())
            if callable(method):
                mapping[ match.group('command').lower() ] = method
        return mapping


class RelevantEventListener(EventListener):
    def register_mapping(self):
        self._event_mapping = self.find_event_listeners()
    def __call__(self, event):
        if event.command in self._event_mapping:
            self._event_mapping[ event.command ]( event )
    


class EventDispatcher:
    def __init__(self):
        self.listeners = {}
        self.global_listeners = []
        self.handles = {}
        self.register_mapping( mapping )
    
    def dispatch(self, irc, server, prefix, command, arguments):
        if command.isdigit() and command in functions.numeric_events:
            command = functions.numeric_events[ command ]
        
        if command in self.handles:
            klass = self.handles[command]
        else:
            klass = Event
        event = klass(irc, server, prefix, command, arguments)
        listeners = []
        listeners.extend(self.global_listeners)
        if command in self.listeners:
            listeners.extend( self.listeners[command] )
        event.handle( listeners )

    def listen(self, callable, command=None):
        if command:
            if not command in self.listeners:
                self.listeners[ command ] = []
            self.listeners[ command ].append( callable )
        else:
            self.global_listeners.append( callable )

    def handle(self, command, klass):
        self.handles[command] = klass

    def register_mapping(self, mapping):
        for command in mapping:
            self.handle( command, mapping[ command ] )

class Event:
    def __init__(self, irc, server, prefix, command, arguments ):
        self.irc = irc
        self.server = server
        self.prefix = prefix
        self.command = command
        self.arguments = arguments

        self.init()

    def handle(self, listeners):
        for listener in listeners:
            listener(self)
    def init(self):
        if self.irc.debug:
            print self.prefix, self.command, self.arguments

class EntityEvent(Event):
    def __init__(self, *arguments ):
        self.entities = []
        Event.__init__( self, *arguments )
    def handle(self, listeners):
        listeners.extend( self.entities )
        Event.handle(self, listeners)

class EventPing(Event):
    def init(self):
        self.server.pong( *self.arguments )

class EventMessage(EntityEvent):
    def init(self):
        self.source = self.server.entity(self.prefix)
        self.target = self.server.entity(self.arguments[0])
        self.entities = [ self.source, self.target ]

        action = False

        message = functions.ctcp_dequote(self.arguments[1])[0]

        if (type(message)==tuple):
            message = message[1]
            action = True

        self.message = message

        if self.target.type=='channel':
            if action:
                self.command = "pubaction"
            else: 
                self.command = 'pubmsg'
        elif action:
            self.command = 'privaction'
        
        print "%s:[%s] <%s> %s" % (self.command, self.target, self.source, self.message)
    
    def handle(self, listeners):
        if not self.command == 'privmsg':
            listeners = []
            listeners.extend(self.irc.dispatcher.global_listeners)
            if self.command in self.irc.dispatcher.listeners:
                listeners.extend( self.irc.dispatcher.listeners[ self.command ] )
        if 'message' in self.irc.dispatcher.listeners:
            listeners.extend( self.irc.dispatcher.listeners['message'] )
        EntityEvent.handle(self, listeners)

class EventNotice(EntityEvent):
    def init(self):
        self.source = self.server.entity(self.prefix)
        self.target = self.server.entity(self.arguments[0])
        self.entities = [self.source, self.target]

        self.message = self.arguments[1]

        if self.target.type=='channel':
            self.command = 'pubnotice'
        else:
            self.command = 'privnotice'
        print "%s:[%s] <%s> %s" % (self.command, self.target, self.source, self.message)
    
    def handle(self, listeners):
        listeners = []
        listeners.extend(self.irc.dispatcher.global_listeners)
        if self.command in self.irc.dispatcher.listeners:
            listeners.extend( self.irc.dispatcher.listeners[ command ] )
        if 'notice' in self.irc.dispatcher.listeners:
            listeners.extend( self.irc.dispatcher.listeners['message'] )
        EntityEvent.handle(self, listeners)

class EventJoin(EntityEvent):
    def init(self):
        self.source = self.server.entity(self.prefix)
        self.target = self.server.entity(self.arguments[0])
        self.entities = [self.source, self.target]
        print "* %s has joined %s" % (self.source, self.target)
class EventPart(EntityEvent):
    def init(self):
        self.source = self.server.entity( self.prefix )
        self.target = self.server.entity( self.arguments[0] )
        self.entities = [self.source, self.target]


class EventMotd(Event):
    def init(self):
        self.message = self.arguments[1]
        print self.message

class EventCurrentTopic(EntityEvent):
    def init(self):
        self.target = self.server.entity( self.arguments[1] )
        self.message = self.arguments[2]
        self.entities = [self.target]

nick_with_mode_regex = re.compile('^(?P<mode>[+%@!&~])?(?P<nickname>.*)')

class EventNamReply(EntityEvent):
    def init(self):
        self.source = self.server.entity( self.arguments[2] )
        self.entities = [self.source]
        self.arguments = self.arguments[3].split()
        self.users = {}
        for mode, nickname in [nick_with_mode_regex.match(name).groups() for name in self.arguments]:
            self.users[nickname] = mode
class EventEndOf(EntityEvent):
    def init(self):
        self.source = self.server.entity( self.arguments[1] )
        self.entities = [self.source]

class EventWhoReply(EntityEvent):
    def init(self):
        #arguments
        # self channel username hostname server nickname mode? 0-realname
        self.source = self.server.entity( self.arguments[1] )
        self.nickname = self.arguments[5]
        self.username = self.arguments[2]
        self.hostname = self.arguments[3]
        self.target = self.server.entity( "%s!%s@%s" % (self.nickname, self.username, self.hostname ))
        self.entities = [self.source, self.target]

class EventQuit(EntityEvent):
    def init(self):
        self.source = self.server.entity( self.prefix )
        self.entities = [self.source]
        if self.source.type=='user' and self.source.channels:
            self.entities.extend(self.source.channels)
        self.message =  self.arguments[0]

class EventNick(EntityEvent):
    def init(self):
        self.source = self.server.entity( self.prefix )
        self.entities = [ self.source ]
        self.target = self.arguments[0]

mapping = {
    'ping'      : EventPing,
    'privmsg'   : EventMessage,
    'join'      : EventJoin,
    'nick'      : EventNick,
    'part'      : EventPart,
    'quit'      : EventQuit,
    'notice'    : EventNotice,
    'motd'      : EventMotd,
    'motdstart' : EventMotd,
    'endofmotd' : EventEndOf,
    'currenttopic' : EventCurrentTopic,
    'namreply'  : EventNamReply,
    'endofnames': EventEndOf,
    'endofwho'  : EventEndOf,
    'whoreply'  : EventWhoReply,
}



