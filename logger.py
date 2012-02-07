import ConfigParser
import os, sys
import copy

from events import EventListener

class Logger(EventListener):

    defaults = {
        'write' : 'stdout',
        'path'  : '.',
    }

    def __init__(self, dispatcher = None):
        print "logger"
        self.events = {}
        self.formats = {}
        self.files = {
            'stdout' : sys.stdout,
            'stderr' : sys.stderr,
        }

        self.read_config()
        if dispatcher: EventListener.__init__(self, dispatcher)

    def register_mapping(self):
        for event in self.events.keys():
            self.dispatcher.listen(self, event)
            print "Logger register", event

    def __call__(self, event):
        if event.command in self.events:
            for file in self.events[ event.command ][ 'write' ]:
                file = self.files[file]
                print >>file, self.format(event)
    
    def read_config(self):
        p = ConfigParser.RawConfigParser( self.defaults )
        p.read( 'log.conf' )

        for section in p.sections():
            
            if section[0]=='@':
                if len(section) > 1 and p.has_option(section, 'filename'):
                    path = os.path.realpath( p.get(section, 'path') )
                    filename = path + os.sep + p.get( section, 'filename' )
                    self.files[ section[1:] ] = open( filename , 'a')
            else:
                opts = copy.copy( self.defaults )
                opts.update( p.items( section ) )
                self.formats[section] = opts['format']
                del opts['format']
                del opts['path']

                opts['write'] = [ item.strip() for item in opts['write'].split(',') ]

                self.events[ section ] = opts
    def format(self, event):
        return self.formats[ event.command ] % event.__dict__

def load_module(irc):
    l = Logger( irc.dispatcher )
