from twisted.application import internet, service
from twisted.internet import protocol
from twisted.web import resource, server
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

class GTRProtocol(NetstringReceiver):

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
        user, game, action = request.split(',', 2)

        game_id = int(game)

        try:
            a = message.parse_action(action)
        except message.BadGameActionError as e:
            print e.message
            return

        self.factory.register(self, user)
        self.factory.handle_action(user, game_id, a)

    def send_action(self, action):
        """Sends a GameAction to the client"""
        self.sendString(','.join(
                [str(action.action)] + map(str, action.args)))


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
internet.TCPServer(5000, IGTRFactory(s)).setServiceParent(serviceCollection)


# vim: set filetype=python:
