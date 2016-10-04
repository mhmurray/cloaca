from cloaca.game import Game
from cloaca.player import Player
from cloaca.game_record import GameRecord
from cloaca.message import GameAction, Command
import cloaca.message as message
from cloaca.error import GTRError, GameOver
import cloaca.encode as encode

import uuid
import functools

import json
import pickle
import logging
import datetime

from tornado import gen, locks
import tornado.ioloop

lg = logging.getLogger(__name__)
lg.addHandler(logging.NullHandler())

class GTRServer(object):
    """Manages multiple Game objects including non-game actions related to
    connecting players and starting games.

    The send_command(user, command) method must be assigned to an appropriate
    handle when this object is created.

    GTRServer doesn't handle any user authentication. It assumes
    the <user> parameter to any GameAction commands is uniquely
    defined and trusts the arguments to handle_command.

    Basic usage: Start a server, request the (empty) game list, create
    a new game which is assigned game_id=0. Request starting the game,
    which results in the game state being transmitted to all players.
    Submit a ThinkerOrLead action that again results in the new game
    state being sent to all players.

        uid = get_uid('p1')

        s = GTRServer()
        s.register_user(uid, {'name': 'p1'})

        s.send_command = lambda u, c: print 'User:', u, 'Command:', c
        s.handle_command(uid, Command(None, GameAction(REQGAMELIST)))
        # prints 'User: <uid> Command(None, GAMELIST, <list>)'
        
        s.handle_command(<uid>, Command(None, GameAction(REQCREATEGAME)))
        # prints 'User: <uid> Command(0, JOINGAME)'
        
        s.handle_command(<uid>, Command(0, GameAction(REQSTARTGAME)))
        # prints 'User: <uid> Command(0, STARTGAME)'
        # prints 'User: <uid> Command(0, GAMESTATE, <game_state>)'
        
        s.handle_command(<uid>, Command(0, GameAction(THINKERORLEAD, [True])))
        # prints 'User: <uid> Command(0, GAMESTATE, <game_state>)'
        
        ...


    Command responses

    Each command is listed here with a description of parameters and the
    reponse expected from the server. All commands are passed with a user id
    (uid) in the handle_command() function. The Command objects have a game ID
    parameter, but this is not always required.

    REQGAMELIST: Get the list of GameRecord objects
        No parameters, game ID not required

        Response:
        GAMELIST: The list of GameRecord objects is send to the client as a
        list of JSON objects with the format:
            {'game_id': <id>,
             'players': <player_list>,
             'started': <started>,
             'host' : <host_uid>}

        Errors
        None


    REQGAMESTATE: Get the game state dict for a specified game ID.
        No parameters, game ID required

        Response
        GAMESTATE: The GameState object is serialized to JSON using each
        object's __dict__. Thus, an object Card(ident=20) is
        represented as {'ident': 20}.

        Errors
        Game ID isn't a valid game.


    REQCREATEGAME: Create a new game with unspecified game ID.
        No Parameters, game ID not required

        Response
        JOINGAME: The game id is sent to confirm that the user joined the
        nely-created game.

        Errors
        None


    REQJOINGAME: Join a game with the game ID.
        No Parameters, game ID required

        Response
        JOINGAME: The game id is sent to confirm that the user joined the
        existing game.
        GAMESTATE: The GameState of the joined game. See REQGAMESTATE.

        Errors
        Game is full.
        Game is already started.
        You have already joined this game.


    REQSTARTGAME: Start a game.
        No Parameters, game ID required

        Repsonse
        STARTGAME: Confirm that the game has started.
        GAMESTATE: GameState object of the started game. See REQGAMESTATE.

        Errors
        You are not the host of the game.
        Game is already started.


    [GameAction]: Any other commands are considered GameAction commands.
            These are passed to the specified game to handle.
        GameAction parameters, game ID required

        Response
        GAMESTATE: If the action is successfully handled, an updated
            GameState is sent to all players.

        Errors
        You aren't playing in this game.
        This game is not started.
        This game has already finished.
        You don't have priority in this game.
        The action is invalid.
        The action is not the expected action for this game.
        There was a GameRulesError while processing the action.
        
    """

    GAME_WAIT_TIMEOUT = datetime.timedelta(seconds=1)


    def __init__(self, database):
        self.games = []
        self._users = {} # User database
        self._game_locks = {}

        self.db = database
        self.send_command = lambda _ : None


    @gen.coroutine
    def handle_game_actions(self, game_id, user_id, actions):
        """Process a list of game actions. The actions argument
        is of the form 
        [[action_number_1, GameAction1], [action_number_2, GameAction2]]

        The game is retrieved once and all GameActions are applied in 
        sequence.

        If there is an error processing one of the actions, the rest
        are ignored, but as long as one action was successfully processed,
        the game is stored and distributed to all players.

        The action number(s) must be equal to Game.action_number. If the
        provided action number is too low, that action is skipped, in case
        this is just a re-submission of a previous action list.
        If the provided action number is larger than Game.action_number or
        if the last (largest) action number in the list of actions is smaller
        than Game.action_number, an error is sent to the client and the game
        is not altered.

        The ability to process multiple actions at once avoids the overhead
        of acquiring a lock on the game and retrieving it from the database.
        No yield of program flow occurs while actions are being processed.
        """
        userdict = yield self.db.retrieve_user(user_id)

        # Check the lock to see if the game is in use.
        try:
            lock = self._game_locks[game_id]
        except KeyError:
            lock = locks.Lock()
            self._game_locks[game_id] = lock
        
        with (yield lock.acquire(GTRServer.GAME_WAIT_TIMEOUT)):
            game_json = yield self.db.retrieve_game(game_id)

            username = userdict['username']

            if game_json is None:
                msg = 'Invalid game id: ' + str(game_id)
                lg.warning(msg)
                return

            game = encode.json_to_game(game_json)

            player_index = game.find_player_index(username)
            if player_index is None:
                msg = ('User {0} is not part of game {1:d}, players: {2!s}'
                        ).format(name, game_id,
                            [p.name for p in game.players])
                lg.warning(msg)
                self._send_error(user_id, msg)
                return

            # Ignore actions if they're old, with too-low action_number.
            # It's probably the client re-sending a list of actions.
            # However, if no actions are applicable, send an error.
            if(game.action_number > actions[-1][0]):
                msg = ('Received latest action_number {0:d}, but require {1:d}.'
                        ).format(actions[-1][0], game.action_number)
                self._send_error(user_id, msg)
                return

            did_one = False
            for action_number, action in actions:
                if action_number > game.action_number:
                    msg = ('Received action_number {0:d}, but require {1:d}.'
                            ).format(action_number, game.action_number)
                    lg.warning(msg)
                    self._send_error(user_id, msg)
                    return
                elif action_number < game.action_number:
                    lg.debug('Skipping action {0:d}, {1}. (Game.action_number'
                            ' = {2}): '.format(action_number, repr(action),
                                    game.action_number))
                    continue

                lg.debug('Handling action: {0}'.format(repr(action)))

                if game.finished:
                    msg = 'Game {0} has finished.'.format(game_id)
                    lg.debug(msg)
                    self._send_error(user_id, msg)

                i_active_p = game.active_player_index

                if i_active_p != player_index:
                    msg = ('Received action for player {0!s} ({1}), '
                        'but waiting on player {2!s} ({3}).'
                        ).format(player_index, game.players[player_index].name,
                                i_active_p, game.players[i_active_p].name)

                    lg.warning(msg)
                    self._send_error(user_id, msg)
                    break

                try:
                    game.handle(action)
                except GTRError as e:
                    lg.warning(e.message)
                    self._send_error(user_id, e.message)
                    break
                except GameOver:
                    lg.info('Game {0} has ended.'.format(game_id))
                    did_one = True
                else:
                    did_one = True

            if did_one:
                yield self.store_game(game)

                for u in [p.uid for p in game.players]:
                    yield self._retrieve_and_send_game(u, game_id)



    @gen.coroutine
    def join_game(self, user_id, game_id):
        """Joins an existing game"""
        userdict = yield self.db.retrieve_user(user_id)
        game_json = yield self.db.retrieve_game(game_id)

        username = userdict['username']

        if game_json is None:
            msg = 'Invalid game id: ' + str(game_id)
            lg.warning(msg)
            return

        game = encode.json_to_game(game_json)

        player_index = game.add_player(user_id, username)
        yield self.store_game(game)


    @gen.coroutine
    def get_game(self, user_id, game_id):
        userdict = yield self.db.retrieve_user(user_id)
        game_json = yield self.db.retrieve_game(game_id)

        username = userdict['username']

        if game_json is None:
            msg = 'Invalid game id: ' + str(game_id)
            lg.warning(msg)
            raise GTRError(msg)
            
        game = encode.json_to_game(game_json)

        player_index = game.find_player_index(username)
        if player_index is None:
            msg = 'User {0:s} is not part of game {1:d}'.format(username, game_id)
            lg.warning(msg)
            raise GTRError(msg)

        if game.started:
            game_privatized = game.privatized_game_state_copy(username)

            raise gen.Return(game_privatized)

        else:
            raise gen.Return(None)


    @gen.coroutine
    def get_game_json(self, user_id, game_id):
        lg.debug('User {0!s} requests game {1!s}'.format(user_id, game_id))
        game = yield self.get_game(user_id, game_id)
        if game is None:
            game_json = ''
        else:
            game_json = encode.game_to_json(game)

        raise gen.Return(game_json)


    def _send_game(self, user_id, game):
        """Sends the game to the user as a GAMESTATE command."""
        if game is None:
            gs_json = ''
        else:
            gs_json = encode.game_to_json(game)

        resp = Command(game.game_id, None, GameAction(message.GAMESTATE, gs_json))
        self.send_command(user_id, resp)
        

    @gen.coroutine
    def _retrieve_and_send_game(self, user, game_id):
        """Retrieves the game from the database using game_id and 
        sends the game to the user in a GAMESTATE command.
        """
        try:
            game = yield self.get_game(user, game_id)
        except GTRError as e:
            self._send_error(user, e.message)
        else:
            self._send_game(user, game)


    def _send_error(self, user, msg):
        """Send error message to user."""
        resp = Command(None, None, GameAction(message.SERVERERROR, msg))
        self.send_command(user, resp)
        

    @gen.coroutine
    def create_game(self, user_id):
        """Create a new game, return the new game ID."""

        game_id = yield self.db.create_game_with_host(user_id)

        userdict = yield self.db.retrieve_user(user_id)
        username = userdict['username']

        lg.info('Creating new game {0:d} with host {1}'.format(
            game_id, username))

        game = Game()
        game.game_id = game_id
        game.host = username

        player_index = game.add_player(user_id, username)

        yield self.store_game(game)

        raise gen.Return(game_id)
        

    @gen.coroutine
    def store_game(self, game):
        """Convert a Game object to JSON and store in the database
        via self.db.store_game().
        """
        game_id = game.game_id
        game_json = encode.game_to_json(game)
        yield self.db.store_game(game_id, game_json)
    

    @gen.coroutine
    def start_game(self, user_id, game_id):
        userdict = yield self.db.retrieve_user(user_id)
        game_json = yield self.db.retrieve_game(game_id)

        username = userdict['username']

        if game_json is None:
            msg = 'Invalid game id: ' + str(game_id)
            lg.warning(msg)
            return

        game = encode.json_to_game(game_json)

        if game.started:
            raise GTRError('Game already started.')

        p = game.find_player_index(username)
        if p is None:
            raise GTRError('Player {0} cannot start game {1} '
                    'that they haven\'t joined.'
                    .format(username, game_id))

        if username != game.host:
            raise GTRError('Player {0} cannot start game {1} '
                    'if they are not the host ({2}).'
                    .format(username, game_id, game.host))

        game.start()
        self.store_game(game)

        raise gen.Return(game)
