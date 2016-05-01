from twisted.application import internet, service
from twisted.internet import protocol
from twisted.web import resource, server, static
from twisted.protocols.basic import NetstringReceiver
from twisted.python import components
from zope.interface import Interface, implements

from twisted.internet.protocol import ServerFactory, Protocol

from gamestate import GameState
from message import GameAction
import message
from server import GTRServer
from pickle import dumps

from interfaces import IGTRService, IGTRFactory

# For websocket test
import sys
sys.path.append("sockjs-twisted")
from txsockjs.factory import SockJSFactory

import json

class GTRProtocol(NetstringReceiver):

    @staticmethod
    def game_action_to_json(user, game_id, action):
        """Convert a username, game_id, and GameAction to a JSON string."""

        d = {'user': user, 'game': game_id,
            'action': action.action, 'args': action.args}

        return json.dumps(d)

    @staticmethod
    def game_action_from_json(j):
        """Convert json string and return (user, game_id, game_action).

        Returns:
        user -- string, username
        game_id -- int
        game_action -- list [<action>, <args>]
        """
        try:
            d = json.loads(j)
        except ValueError:
            print 'Failed to parse JSON: ' + str(j)
            return None

        try:
            user, game = d['user'], d['game']
            action, args = d['action'], d['args']
        except KeyError:
            print 'JSON object does not represent a GameAction: ', d
            return None

        return user, game, action, args


    def connectionMade(self):
        print 'client connected'

    def connectionLost(self, reason):
        print 'client disconnected'
        print reason

    def stringReceived(self, request):
        """Receives actions of the form "user, game_id, action".
        Converts the game_id to an integer and tries to parse the
        action.
        """
        print 'string received ', request
        user, game, action, args = self.game_action_from_json(request)

        try:
            a = message.parse_action(action, args)
        except message.BadGameActionError as e:
            print e.message
            return

        self.factory.register(self, user)
        self.factory.handle_action(user, game, a)

    def send_action(self, action):
        """Send a GameAction to the client."""
        #self.sendString(','.join(
        #        [str(action.action)] + map(str, action.args)))
        self.sendString(json.dumps(action, default = lambda o: o.__dict__))


class GTRService(service.Service):
    """Service to handle one instance of a GTRServer.
    """
    implements(IGTRService)

    def __init__(self, backup_file=None, load_backup_file=None):
        self.server = GTRServer(backup_file, load_backup_file)

        self.factory = None
        self.server.send_action = lambda user, action : self.send_action(user, action)

    def send_action(self, user, action):
        """Sends a message to the user if the user exists.
        """
        if self.factory is not None:
            self.factory.send_action(user, action)

    def handle_action(self, user, game_id, a):
        return self.server.handle_action(user, game_id, a)


class GTRFactoryFromService(protocol.ServerFactory):
    """Handles the connections to clients via GTRProtocol intances.

    Keeps a reference to a factory object that implements IGTRFactory.
    This object is used to communicate with the clients via the method
    GTRFactory.send_action(user, action).
    """

    implements(IGTRFactory)

    protocol = GTRProtocol

    def __init__(self, service):
        self.service = service
        self.service.factory = self
        self.users = {} # User-to-protocol dictionary. Filled when the first command is received.

    def register(self, protocol, user):
        """Register protocol as associated with the specified user.
        This replaces the old protocol silently.
        """
        self.users[user] = protocol

    def send_action(self, user, action):
        """Sends an action to the specified user.
        """
        try:
            protocol = self.users[user]
        except KeyError:
            print 'Error. Server tried to send a command to ' + user + \
                    ' but the user is not connected.'
            return
        
        protocol.send_action(action)

    def handle_action(self, user, game, action):
        self.service.handle_action(user, game, action)


components.registerAdapter(GTRFactoryFromService, IGTRService, IGTRFactory)


application = service.Application('gtr')
#s = GTRService('tmp/twistd_backup.dat', 'tmp/test_backup2.dat')
s = GTRService('tmp/twistd_backup.dat', None)
serviceCollection = service.IServiceCollection(application)

root = resource.Resource()

class FormPage(static.File):
    #def render_GET(self, request):
    #    return static.File('./index.html')
    
    def render_POST(self, request):
        return '<html><body>You submitted: %s</body></html>' % (cgi.escape(str(request.args)),)

class DisableCache(static.File):
    """Static file resource that sets the header to disable caching.
    """

    def render_GET(self, request):
        print request.responseHeaders
        request.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate')
        request.setHeader('Pragma', 'no-cache')
        request.setHeader('Expires', '0')
        print request.responseHeaders
        size = self.getFileSize()
        return static.File.render_GET(self, request)

class Test(resource.Resource):
    def render_GET(self, request):
        print request
        print 'TEstint'
        return 'stuff'

root.putChild('hello', SockJSFactory(IGTRFactory(s)))
root.putChild("index", static.File('site/index.html'))
root.putChild("style.css", static.File('site/style.css'))
root.putChild("favicon.ico", static.File('site/favicon.ico'))
root.putChild("js", static.File('site/js'))
site = server.Site(root)

#reactor.listenTCP(5050, site)
#reactor.run()


internet.TCPServer(5000, site).setServiceParent(serviceCollection)
#internet.TCPServer(5000, SockJSFactory(IGTRFactory(s))).setServiceParent(serviceCollection)
#internet.TCPServer(5000, IGTRFactory(s)).setServiceParent(serviceCollection)


# vim: set filetype=python:
