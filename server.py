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

from tornado import gen
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

    def __init__(self, database):
        self.games = []
        self._users = {} # User database

        self.db = database
        self.send_command = lambda _ : None


    def _send_game_list(self, user, game_list_future):
        game_list = game_list_future.result()
        json_list = json.dumps(game_list, sort_keys=True,
                default=lambda o:o.__dict__)
        resp = Command(game_id, GameAction(message.GAMELIST, json_list))
        self.send_command(user, resp)


    def _start_game_callback(self, user, future):
        e = future.exception()
        if e is not None:
            pass


    def handle_command(self, user, command):
        """Muliplexes the action to helper functions.
        """
        game_id = command.game
        action = command.action.action
        args = command.action.args

        lg.debug('Handling command: {0!s}, {1!s}, {2!s}, {3!s}'
                .format(user, game_id, action, args))

        if action == message.REQGAMESTATE:
            self._retrieve_and_send_game(user, game_id)


        elif action == message.REQGAMELIST:
            gl_future = self._get_game_list()
            cb = functools.partial(self._send_game_list, user)

            ioloop = tornado.ioloop.IOLoop.current()
            ioloop.add_future(gl_future, cb)


        elif action == message.REQCREATEGAME:
            res = self._handle_create(user)


        elif action == message.REQJOINGAME:
            self._handle_join(self, user, game_id)


        elif action == message.REQSTARTGAME:
            future = self._start_game(user, game_id)
            cb = functools.partial(self._start_game_callback, user)
            
            ioloop = tornado.ioloop.IOLoop.current()
            ioloop.add_future(future, cb)

            #except GTRError as e:
            #    self._send_error(user, e.message)
            #else:
            #    self.db.store_game(game_id, self.games[game_id])
            #    gs = self._get_game(user, game_id)
            #    for u in [p.uid for p in gs.players]:
            #        resp = Command(game_id, GameAction(message.STARTGAME))
            #        self.send_command(u, resp)

            #        self._retrieve_and_send_game(u, game_id)

        elif action in (message.CREATEGAME, message.JOINGAME,
                        message.GAMESTATE, message.GAMELIST,
                        message.STARTGAME, message.LOGIN):
            # Todo: send error to client.
            # It would be better to check if the action is a GameAction
            # command and return an error otherwise
            self._send_error(user, 'Invalid server command: '+str(command.action))

        else: # Game commands
            try:
                game = self.games[game_id]
            except IndexError as e:
                msg = ("Couldn't find game {0:d} in {1!s}"
                        ).format(game_id, self.games[:10])

                lg.warning(msg)
                self._send_error(user, msg)

            name = self._userinfo(user)['name']
            player_index = game.find_player_index(name)
            if player_index is None:
                msg = ('User {0} is not part of game {1:d}, players: {2!s}'
                        ).format(name, game_id,
                            [p.name for p in game.players])

                lg.warning(msg)
                self._send_error(user, msg)

            lg.debug('Expected action: {0}'.format(str(game.expected_action)))
            lg.debug('Got action: {0}'.format(repr(action)))
            lg.debug('Handling action: {0}'.format(repr(action)))

            i_active_p = game.active_player_index

            if game.finished:
                self._send_error(user, 'Game {0} has finished.'.format(game_id))

            if i_active_p == player_index:
                try:
                    game.handle(command.action)
                except GTRError as e:
                    lg.warning(e.message)
                    self._send_error(user, e.message)
                except GameOver:
                    lg.info('Game {0} has ended.'.format(game_id))

                self.db.store_game(game_id, self.games[game_id])

            else:
                msg = ('Received action for player {0!s}, '
                    'but waiting on player {1!s}'
                    ).format(player_index, i_active_p)

                lg.warning(msg)
                self._send_error(user, msg)

            for u in [p.uid for p in game.players]:
                self._retrieve_and_send_game(u, game_id)


    def _handle_create(self, user):
        game_id_future = self._create_game(user)
        cb = lambda gid: self.send_command(user,
                Command(gid.result(), GameAction(message.JOINGAME)))

        ioloop = tornado.ioloop.IOLoop.current()
        ioloop.add_future(game_id_future, cb)


    @gen.coroutine
    def _handle_join(self, user, game_id):
        """Joins an existing game"""
        userdict = yield self.db.retrieve_user(user)
        game_json = yield self.db.retrieve_game(game_id)

        username = userdict['username']

        if game is None:
            msg = 'Invalid game id: ' + str(game_id)
            lg.warning(msg)
            self._send_error(user, msg)
            return

        game = encode.json_to_game(game_json)

        try:
            player_index = game.add_player(user, username)
        except GTRError as e:
            lg.warning(e.message)
            self._send_error(user, e.message)
            return
        else:
            self.db.store_game(game_id, game)

            resp = Command(id_, GameAction(message.JOINGAME))
            self.send_command(user, resp)
            
            if game.started:
                self._send_game(user, game)


    def register_user(self, uid, userinfo):
        """Register the dictionary <userinfo> with the unique
        id <uid>. For instance, the player's display name should
        be included under the "name" key in <userinfo>.

        If the uid is already registered, the userinfo is replaced.
        """
        try:
            name = userinfo['name']
        except KeyError:
            lg.warning('Cannot register user without "name" key in dictionary.')
            lg.warning('  userinfo dict: ' +str(userinfo))
            return

        self._users[uid] = userinfo

    def unregister_user(self, uid):
        """Remove the user identified by uid from the the registry.

        If the user doesn't exist, this does nothing.
        """
        try:
            del self._users[uid]
        except KeyError:
            pass

    @gen.coroutine
    def _get_game(self, user, game_id):
        userdict = yield self.db.retrieve_user(user)
        game_json = yield self.db.retrieve_game(game_id)

        username = userdict['username']

        if game_json is None:
            msg = 'Invalid game id: ' + str(game_id)
            lg.warning(msg)
            self._send_error(user, msg)
            return
            
        game = encode.json_to_game(game_json)
        username = userdict['username']

        player_index = game.find_player_index(username)
        if player_index is None:
            msg = 'User {0:s} is not part of game {1:d}'.format(username, game_id)
            lg.warning(msg)
            self._send_error(user, msg)
            return

        if game.started:
            gs_privatized = game.privatized_game_state_copy(username)

            raise gen.Return(gs_privatized)


    def _send_game(self, user, game):
        """Sends the game to the user as a GAMESTATE command."""
        if game is None:
            gs_json = ''
        else:
            gs_json = encode.game_to_json(gs)

        resp = Command(game, GameAction(message.GAMESTATE, gs_json))
        self.send_command(user, resp)
        

    @gen.coroutine
    def _retrieve_and_send_game(self, user, game_id):
        """Retrieves the game from the database using game_id and 
        sends the game to the user in a GAMESTATE command.
        """
        gs = yield self._get_game(user, game)
        self._send_game(user, game)


    def _send_error(self, user, msg):
        """Send error message to user."""
        resp = Command(None, GameAction(message.SERVERERROR, msg))
        self.send_command(user, resp)
        

    def _userinfo(self, uid):
        """Get the userinfo dict associated with uid.

        Raise KeyError if the uid isn't registered.
        """
        try:
            return self._users[uid]
        except KeyError:
            raise

    def _join_game(self, user, game_id):
        """Joins an existing game"""
        try:
            game = self.games[game_id]
        except IndexError:
            raise GTRError()

        username = self._userinfo(user)['name']

        try:
            player_index = game.add_player(user, username)
        except GTRError:
            # Send error to client.
            raise

        return game_id

    @gen.coroutine
    def _join_game(self, user_id, game_id):
        """Join an existing game.

        Raise GTRError if the user or game cannot be found.
        """
        userdict = yield self.db.retrieve_user(user_id)
        game_json = yield self.db.retrieve_game(game_id)

        if game_json is None:
            msg = 'Invalid game id: ' + str(game_id)
            lg.warning(msg)
            self._send_error(user_id, msg)
            return

        game = encode.json_to_game(game_json)
        username = userdict['username']

        player_index = game.add_player(user, username)


    @gen.coroutine
    def _create_game(self, user):
        """Create a new game."""
        userdict = yield self.db.retrieve_user(user)
        id = yield self.db.retrieve_game_id()
        username = userdict['username']

        lg.info('Creating new game {0:d} with host {1}'.format(
            game_id, username))

        game = Game()
        game.game_id = id
        game.host = user

        player_index = game.add_player(user, username)

        self.db.store_game(id, game)

        raise gen.Return(game_id)
        

    @gen.coroutine
    def _get_game_list(self):
        """Get list of GameRecord objects.

        WARNING: This method loads all games
        into memory. That's probably bad.
        """
        game_ids = yield self.db.retrieve_all_games()
        games = yield self.db.retrieve_games(game_ids)

        game_list = []
        for i, game in enumerate(games):
            players = [p.name for p in game.players]
            started = game.started
            host = game.host
            game_list.append(GameRecord(i, players, started, host))

        raise gen.Return(game_list)


    @gen.coroutine
    def _start_game(self, user, game_id):
        userdict = yield self.db.retrieve_user(user)
        game_json = yield self.db.retrieve_game(game_id)

        if game_json is None:
            msg = 'Invalid game id: ' + str(game_id)
            lg.warning(msg)
            self._send_error(user, msg)
            return

        game = encode.json_to_game(game_json)

        if game.started:
            raise GTRError('Game already started')

        p = game.find_player_index(name)
        if p is None:
            raise GTRError('Player {0} cannot start game {1} '
                    'that they haven\'t joined.'
                    .format(name, game_id))

        if user != game.host:
            raise GTRError('Player {0} cannot start game {1} '
                    'if they are not the host ({2}).'
                    .format(name, game_id, game.host))

        game.start()
        self.db.store_game(game_id, game)


    def _load_backup(self):
        """ Loads backup from JSON-encoded constructed file.
        """
        if self.games:
            lg.warning('Error! Can\'t load backup file if games already exist')
            return

        try:
            f = open(self._load_backup_file, 'r')
        except IOError:
            lg.warning('Can\'t open backup file: ' + self._load_backup_file)
            return

        with f:
            try:
                game_states = pickle.load(f)
            except pickle.PickleError:
                lg.warning('Error! Couldn\'t load games from backup file: ' + self._load_backup_file)
                return

            self.games = [gs for gs in game_states]

    def _save_backup(self):
        """ Writes pickled list of game states to backup file.
        """
        if self._backup_file:

            game_states = [g for g in self.games]

            try:
                f = open(self._backup_file, 'w')
            except IOError:
                lg.warning('Can\'t write to file ' + self._backup_file)
                return
            
            with f:
                try:
                    pickle.dump(game_states, f)
                except pickle.PickleError:
                    lg.warning('Error writing backup: ' + self._backup_file)
                    return

