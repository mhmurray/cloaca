from game import Game
from player import Player
from game_record import GameRecord
from message import GameAction, Command
import message
from error import GTRError

import uuid

import json
import pickle
import logging

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
             'started': <is_started>,
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

    def __init__(self, backup_file=None, load_backup_file=None):
        self.games = [] # Games database
        self._users = {} # User database
        self._backup_file = backup_file
        self._load_backup_file = load_backup_file

        if self._load_backup_file:
            self._load_backup()

        self.send_command = lambda _ : None

    def handle_command(self, user, command):
        """Muliplexes the action to helper functions.
        """
        game_id = command.game
        action = command.action.action
        args = command.action.args

        lg.debug('Handling command: {0!s}, {1!s}, {2!s}, {3!s}'
                .format(user, game_id, action, args))

        if action == message.REQGAMESTATE:
            self._send_gamestate(user, game_id)

        elif action == message.REQGAMELIST:
            gl = self._get_game_list()
            json_list = json.dumps(gl, sort_keys=True, default=lambda o:o.__dict__)
            resp = Command(game_id, GameAction(message.GAMELIST, json_list))
            self.send_command(user, resp)

        elif action == message.REQJOINGAME:
            # Game id is the argument here, not the game part of the request
            try:
                id_ = self._join_game(user, game_id)
            except GTRError as e:
                # I want to filter out the case where we're re-joining. Presumably
                # the user wants the game state and a join acknowledgement.
                # They can get this with a GAMESTATE request, though.
                self._send_error(user, e.message)
            else:
                resp = Command(id_, GameAction(message.JOINGAME))
                self.send_command(user, resp)
                
                # If the game is started, we need the game state
                gs = self._get_game_state(user, id_)
                if gs is not None and self.games[id_].is_started:
                    self._send_gamestate(user, id_)

        elif action == message.REQSTARTGAME:
            try:
                self._start_game(user, game_id)
            except GTRError as e:
                self._send_error(user, e.message)
            else:
                gs = self._get_game_state(user, game_id)
                for u in [p.uid for p in gs.players]:
                    resp = Command(game_id, GameAction(message.STARTGAME))
                    self.send_command(u, resp)

                    self._send_gamestate(u, game_id)

        elif action == message.REQCREATEGAME:
            game_id = self._create_game(user)
            resp = Command(game_id, GameAction(message.JOINGAME))
            self.send_command(user, resp)

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

            if i_active_p == player_index:
                try:
                    game.handle(command.action)
                except GTRError as e:
                    lg.warning(e.message)
                    self._send_error(user, e.message)

                self._save_backup()

            else:
                msg = ('Received action for player {0!s}, '
                    'but waiting on player {1!s}'
                    ).format(player_index, i_active_p)

                lg.warning(msg)
                self._send_error(user, msg)

            for u in [p.uid for p in game.players]:
                gs = self._get_game_state(u, game_id)
                self._send_gamestate(u, game_id)

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

    def _get_game_state(self, user, game_id):
        try:
            game = self.games[game_id]
        except IndexError as e:
            lg.warning(e.message)
            return None

        username = self._userinfo(user)['name']
        player_index = game.find_player_index(username)
        if player_index is None:
            lg.warning('User {0:s} is not part of game {1:d}'.format(username, game_id))
            return None

        if game.is_started:
            username = self._userinfo(user)['name']

            gs_privatized = game.privatized_game_state_copy(username)

            return gs_privatized
        else:
            return None


    def _send_gamestate(self, user, game):
        """Sends the game state from the specified game to the user as a
        GAMESTATE command.
        """
        gs = self._get_game_state(user, game)
        gs_json = json.dumps(gs, sort_keys=True, default=lambda o:o.__dict__)
        resp = Command(game, GameAction(message.GAMESTATE, gs_json))
        self.send_command(user, resp)

    def _send_error(self, user, msg):
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

    def _create_game(self, user):
        """Create a new game."""
        game = Game()
        self.games.append(game)
        game_id = len(self.games)-1
        lg.info('Creating new game {0:d}'.format(game_id))
        game.game_id = game_id
        game.host = user

        username = self._userinfo(user)['name']
        player_index = game.add_player(user, username)

        return game_id
        
    def _get_game_list(self):
        """Return list of games"""
        game_list = []
        for i, game in enumerate(self.games):
            players = [p.name for p in game.players]
            started = game.is_started
            host = game.host
            game_list.append(GameRecord(i, players, started, host))
        
        return game_list

    def _start_game(self, user, game_id):
        """Request that specified game starts"""

        try:
            game = self.games[game_id]
        except IndexError:
            raise GTRError('Tried to start non-existent game {0:d}'.format(game))

        if game.is_started:
            raise GTRError('Game already started')

        name = self._userinfo(user)['name']
        p = game.find_player_index(name)
        if p is None:
            raise GTRError('Player {0} cannot start game {1} that they haven\'t joined.'
                    .format(name, game_id))

        if user != game.host:
            raise GTRError('Player {0} cannot start game {1} if they are not the host ({2}).'
                    .format(name, game_id, game.host))

        game.start()
        self._save_backup()
        
        return None

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

