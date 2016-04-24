from gtr import Game
from gamestate import GameState
from player import Player
from game_record import GameRecord
from message import GameAction
import message
from gtrutils import GTRError

import uuid
import copy

import json
import pickle
import logging

lg = logging.getLogger('server')
#logging.basicConfig()
lg.setLevel(logging.INFO)
#lg.setLevel(logging.DEBUG)

class GTRServer(object):
    """Contains a list of multiple Game objects and manages all the
    non-game actions related to e.g. connecting players and starting games.

    The send_action(user, action) method must be assigned to an appropriate
    handle when this object is used.
    """
    def __init__(self, backup_file=None, load_backup_file=None):
        self.games = [] # Games database
        self.users = [] # User database
        self.backup_file = backup_file
        self.load_backup_file = load_backup_file

        if self.load_backup_file:
            self.load_backup()

        self.send_action = lambda _ : None

    def get_game_state(self, user, game_id):
        try:
            game = self.games[game_id]
        except IndexError as e:
            lg.warning(e.message)
            return None

        player_index = game.game_state.find_player_index(user)
        if player_index is None:
            lg.warning('User {0:s} is not part of game {1:d}'.format(user, game_id))
            return None

        if game.game_state.is_started:
            # privatize modifies the object, so make a copy
            gs = copy.deepcopy(game.game_state)
            gs.privatize(user)
            return gs
        else:
            return None

    def handle_action(self, user, game_id, a):
        """Muliplexes the action to helper functions.
        """

        if a.action == message.REQGAMESTATE:
            gs = self.get_game_state(user, game_id)
            #resp = GameAction(message.GAMESTATE, pickle.dumps(gs))
            lg.info('Sending GameState');
            lg.info(str(gs));
            resp = GameAction(message.GAMESTATE, json.dumps(gs, default=lambda o:o.__dict__))
            self.send_action(user, resp)

        elif a.action == message.REQGAMELIST:
            gl = self.get_game_list()
            #self.send_action(user, GameAction(message.GAMELIST, pickle.dumps(gl)))
            json_list = json.dumps(gl, default=lambda o:o.__dict__)
            self.send_action(user, GameAction(message.GAMELIST, json_list))

        elif a.action == message.REQJOINGAME:
            # Game id is the argument here, not the game part of the request
            # Yes this is stupid.
            g_id = a.args[0]
            game_id = self.join_game(user, g_id)
            self.send_action(user, GameAction(message.JOINGAME, game_id))
                
            # If the game is started, we need the game state
            gs = self.get_game_state(user, game_id)
            if gs is not None and gs.is_started:
                #self.send_action(user, GameAction(message.GAMESTATE, pickle.dumps(gs)))
                self.send_action(user, GameAction(message.GAMESTATE, json.dumps(gs, default=lambda o:o.__dict__)))

        elif a.action == message.REQSTARTGAME:
            self.start_game(user, game_id)

            gs = self.get_game_state(user, game_id)
            for u in [p.name for p in gs.players]:
                gs = self.get_game_state(u, game_id)
                #self.send_action(u, GameAction(message.GAMESTATE, pickle.dumps(gs)))
                self.send_action(u, GameAction(message.GAMESTATE, json.dumps(gs, default=lambda o:o.__dict__)))

        elif a.action == message.REQCREATEGAME:
            game_id = self.create_game(user)
            self.send_action(user, GameAction(message.JOINGAME, game_id))

        else: # Game commands
            try:
                game = self.games[game_id]
            except IndexError as e:
                lg.warning(e.message)
                return

            player_index = game.game_state.find_player_index(user)
            if player_index is None:
                lg.warning('User {0:s} is not part of game {1:d}'.format(user, game_id))
                return

            lg.debug('Expected action: {0}'.format(str(game.expected_action())))
            lg.debug('Got action: {0}'.format(repr(a)))
            lg.debug('Handling action: {0}'.format(repr(a)))

            i_active_p = game.game_state.active_player_index

            if i_active_p == player_index:
                try:
                    game.handle(a)
                except GTRError, e:
                    lg.warning('Error handling action.\n' + e.message)
                    return

                self.save_backup()

            else:
                lg.warning('Received action for player {0!s}, but waiting on player {1!s}'
                    .format(player_index, i_active_p))

            for u in [p.name for p in game.game_state.players]:
                gs = self.get_game_state(u, game_id)
                #self.send_action(u, GameAction(message.GAMESTATE, pickle.dumps(gs)))
                self.send_action(u, GameAction(message.GAMESTATE, json.dumps(gs, default=lambda o:o.__dict__)))


    def find_or_add_user(self, username):
        """Finds a user by username, returning the User object
        that contains the UID.
        """
        matches = [u for u in self.users if u.name == username]
        if len(matches) == 0:
            uid = uuid.uuid4()
            u = User(username, uid, None)
            self.users.append(u)
        else:
            if len(matches) > 1:
                sys.stderr.write('Multiple users in database with name ' + username + '\n')
            u = matches[0]

        return u

    def join_game(self, user, game_id):
        """Joins an existing game"""
        try:
            game = self.games[game_id]
        except IndexError:
            game = Game()
            self.games.append(game)
            game_id = self.games.index(game)
            lg.info('Creating new game {0:d}'.format(game_id))
            game.game_state.game_id = game_id

        player_index = game.add_player(user)

        return game_id

    def create_game(self, user):
        """Create a new game."""
        return self.join_game(user, len(self.games))
        
    def get_game_list(self):
        """Return list of games"""
        game_list = []
        for i, game in enumerate(self.games):
            players = [p.name for p in game.game_state.players]
            game_list.append(GameRecord(i,players))
        
        return game_list

    def start_game(self, user, game_id):
        """Request that specified game starts"""

        try:
            game = self.games[game_id]
        except IndexError:
            lg.warning('Tried to start non-existent game {0:d}'.format(game))
            return None

        if game.game_state.is_started:
            lg.warning('Game already started')
            return None

        game.start_game()
        self.save_backup()
        
        return None

    def load_backup(self):
        """ Loads backup from JSON-encoded constructed file.
        """
        if self.games:
            lg.warning('Error! Can\'t load backup file if games already exist')
            return

        try:
            f = open(self.load_backup_file, 'r')
        except IOError:
            lg.warning('Can\'t open backup file: ' + self.load_backup_file)
            return

        with f:
            try:
                game_states = pickle.load(f)
            except pickle.PickleError:
                lg.warning('Error! Couldn\'t load games from backup file: ' + self.load_backup_file)
                return

            self.games = [Game(gs) for gs in game_states]

    def save_backup(self):
        """ Writes pickled list of game states to backup file.
        """
        if self.backup_file:

            game_states = [g.game_state for g in self.games]

            try:
                f = open(self.backup_file, 'w')
            except IOError:
                lg.warning('Can\'t write to file ' + self.backup_file)
                return
            
            with f:
                try:
                    pickle.dump(game_states, f)
                except pickle.PickleError:
                    lg.warning('Error writing backup: ' + self.backup_file)
                    return

