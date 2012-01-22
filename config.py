import ConfigParser

def reader( filenames, defaults ):
    p = ConfigParser.SafeConfigParser( defaults )
    p.read( filenames )
    data = {}
    for section in p.sections():
        data[ section ] = dict( p.items( section ) )
    return data


def servers( filenames=['servers.conf'] ):
    defaults = {
        'server'   : '',
        'port'          : '6667',
        'nickname'      : 'Jimino',
        'username'      : '%(nickname)s',
        'realname'      : '%(nickname)s',
        'password'      : '',
        'ipv6'          : '0',
        'use_ssl'       : '0',
        'localaddress'  : '',
        'localport'     : '0'
    }

    return reader( filenames, defaults )

def channels( filenames=['channels.conf'] ):
    defaults = {
        'autojoin'      : '0',
        'password'      : '',
    }
    data = reader( filenames, defaults )
    networks = {}
    for section in data:
        network, channel = section.split(':', 1)
        if not network in networks:
            networks[ network ] = {}
        networks[ channel ] = data[section]
    return networks

def settings( filenames=['irc.conf'] ):
    defaults = {
        'debug'         : '0',
        'timeout'       : '0',
    }
    data = reader( filenames, defaults )
    if 'irc' in data:
        return data['irc']
    return defaults