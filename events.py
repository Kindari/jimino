import functions
import re

event_listener_regex = re.compile("^on(?P<command>[A-Z][a-z]*$)")

class EventError(Exception): pass

class EventListener:
    def __init__(self, dispatcher):
        methods = [method for method in dir(self) if event_listener_regex.match(method)]
        for method in methods:
            command = event_listener_regex.match(method).group('command')
            dispatcher.listen( getattr(self, 'on%s' % command), command.lower())

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

class EventPing(Event):
    def init(self):
        self.server.pong( *self.arguments )

class EventMessage(Event):
    def init(self):
        self.source = self.server.entity(self.prefix)
        self.target = self.server.entity(self.arguments[0])
        print self.source, self.target

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
        Event.handle(self, listeners)

class EventNotice(Event):
    def init(self):
        self.source = self.server.entity(self.prefix)
        self.target = self.server.entity(self.arguments[0])

        self.message = message

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
        Event.handle(self, listeners)

class EventJoin(Event):
    def init(self):
        self.source = self.server.entity(self.prefix)
        self.target = self.server.entity(self.arguments[0])
        print "* %s has joined %s" % (self.source, self.target)

class EventMotd(Event):
    def init(self):
        self.message = self.arguments[1]
        print self.message

mapping = {
    'ping'      : EventPing,
    'privmsg'   : EventMessage,
    'join'      : EventJoin,
    'notice'    : EventNotice,
    'motd'      : EventMotd,
    'motdstart' : EventMotd,
    'endofmotd' : EventMotd,
}



