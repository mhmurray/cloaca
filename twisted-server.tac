from twisted.application import internet, service
from twisted.internet import protocol
from twisted.web import resource, server
from twisted.protocols.basic import NetstringReceiver
from twisted.python import components
from zope.interface import Interface, implements

from twisted.internet import defer

from gamestate import GameState
from message import GameAction
import message
from server import GTRServer
from pickle import dumps

from interfaces import IGTRService, IGTRFactory

def catch_error(err):
    return "Internal error in server"

class GTRProtocol(NetstringReceiver):

    def connectionMade(self):
        print 'client connected'

    def connectionLost(self, reason):
        print 'client disconnected'
        print reason

    def stringReceived(self, request):
        print 'string received ', request
        user, game, action = request.split(',', 2)

        game_id = int(game)

        try:
            a = message.parse_action(action)
        except message.BadGameActionError as e:
            print e.message
            return

        if a.action == message.REQGAMESTATE:
            d = self.factory.get_game_state(user, game_id)
            def ackGameState(gs):
                a = GameAction(message.GAMESTATE, dumps(gs))

                self.send_action(a)

            d.addCallbacks(ackGameState, catch_error)

        elif a.action == message.REQGAMELIST:
            d = self.factory.get_game_list()
            def ackGameList(game_list):
                gl = dumps(game_list)
                self.send_action(GameAction(message.GAMELIST, gl))

            d.addCallback(ackGameList)

        elif a.action == message.REQJOINGAME:
            # Game id is the argument here.
            g_id = a.args[0]
            d = self.factory.join_game(user, g_id)
            d.addErrback(catch_error)
            def ackJoinGame(game_id):
                self.send_action(GameAction(message.JOINGAME, game_id))

                # If the game is started, we need the game state
                dgs = self.factory.get_game_state(user, game_id)
                def ackGameState(gs):
                    if gs is not None:
                        self.send_action(GameAction(message.GAMESTATE, dumps(gs)))

                dgs.addCallbacks(ackGameState, catch_error)

            d.addCallback(ackJoinGame)
                

        elif a.action == message.REQSTARTGAME:
            d = self.factory.start_game(user, game_id)

            def ackStartGame(_):
                self.send_action(GameAction(message.STARTGAME))

                dgs = self.factory.get_game_state(user, game_id)
                def ackGameState(gs):
                    self.send_action(GameAction(message.GAMESTATE, dumps(gs)))

                dgs.addCallbacks(ackGameState, catch_error)

            d.addCallbacks(ackStartGame, catch_error)


        elif a.action == message.REQCREATEGAME:
            d = self.factory.create_game(user)
            d.addErrback(catch_error)
            def ackCreateGame(game_id):
                self.send_action(GameAction(message.JOINGAME, game_id))
            d.addCallback(ackCreateGame)

        else:
            self.factory.submit_action(user, game_id, action)

            dgs = self.factory.get_game_state(user, game_id)
            def ackGameState(gs):
                self.send_action(GameAction(message.GAMESTATE, dumps(gs)))
            dgs.addCallbacks(ackGameState, catch_error)


    def send_action(self, action):
        """Sends a GameAction to the client"""
        self.sendString(','.join(
                [str(action.action)] + map(str, action.args)))



class GTRFactoryFromService(protocol.ServerFactory):

    implements(IGTRFactory)

    protocol = GTRProtocol

    def __init__(self, service):
        self.service = service

    def submit_action(self, user, game, action):
        self.service.submit_action(user, game, action)

    def get_game_state(self, user, game):
        return self.service.get_game_state(user, game)

    def join_game(self, user, game):
        return self.service.join_game(user, game)

    def start_game(self, user, game):
        return self.service.start_game(user, game)

    def create_game(self, user):
        return self.service.create_game(user)

    def get_game_list(self):
        return self.service.get_game_list()
        


components.registerAdapter(GTRFactoryFromService,
                           IGTRService,
                           IGTRFactory)

class GTRService(service.Service):

    implements(IGTRService)

    def __init__(self, backup_file=None, load_backup_file=None):
        self.server = GTRServer(backup_file, load_backup_file)

    def submit_action(self, user, game, action):
        self.server.handle_game_action(user, game, action) 

    def get_game_state(self, user, game):
        return self.server.get_game_state(user, game)

    def join_game(self, user, game_id):
        return self.server.join_game(user, game_id)

    def create_game(self, user):
        return self.server.create_game(user)

    def start_game(self, user, game):
        return self.server.start_game(user, game)

    def get_game_list(self):
        return self.server.get_game_list()


application = service.Application('gtr')
#s = GTRService('tmp/twistd_backup.dat', 'tmp/test_backup.dat')
s = GTRServer('tmp/twistd_backup.dat', None)
serviceCollection = service.IServiceCollection(application)
internet.TCPServer(5000, IGTRFactory(s)).setServiceParent(serviceCollection)


# vim: set filetype=python
