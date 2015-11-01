from gtr import Game
from gamestate import GameState
from player import Player
from game_record import GameRecord
from interfaces import IGTRService

import message
import argparse
import uuid

from twisted.internet.protocol import ServerFactory, Protocol
from twisted.protocols.basic import NetstringReceiver
from twisted.internet import defer
from twisted.application import service

from zope.interface import implements

import pickle

import logging

class User(object):
    def __init__(self, name, game=None, player_index=None, protocol=None):
        self.name = name
        self.game = game
        self.player_index = player_index
        self.protocol = protocol

class GameActionProtocol(NetstringReceiver):
    def __init__(self):
        self.user = None

    def stringReceived(self, request):
        user, game, action = request.split(',', 2)

        try:
            a = message.parse_action(action)
        except message.BadGameActionError as e:
            print e.message
            return

        if a.action == message.LOGIN:
            username = a.args[0]
            self.handle_login(username)

        elif a.action == message.JOINGAME:
            game = a.args[0]
            self.factory.join_game(self.user, game)

        elif a.action == message.STARTGAME:
            game = self.user.game
            self.factory.start_game(game)

        else:
            self.factory.handle_game_action(self.user, game, a)


    def handle_login(self, username):
         self.user = self.factory.get_user(username)
         self.factory.associate(self, self.user)

class GameActionFactory(ServerFactory):
    protocol = GameActionProtocol

    def __init__(self, backup_file=None, load_backup_file=None):
        self.games = []
        self.proto_by_user = {}
        self.users_by_name = {}
        self.backup_file = backup_file
        self.load_backup_file = load_backup_file

        if self.load_backup_file:
            self.load_backup()

    def join_game(self, user, game_id=None):
        try:
            game = self.games[game_id]
        except IndexError:
            game = Game()
            self.games.append(game)
            game_id = self.games.index(game)
            print 'Creating new game {0:d}'.format(game_id)

        #if user.game == game_id and game.game_state.players[user.player_index] == user.name:
        #    print 'User already in this game'
        #    return

        if game.game_state.is_started:
            i = game.game_state.find_player_index(user.name)

            self.proto_by_user[user].sendString(
                    str(message.SETPLAYERID) + ',' + str(i))
            self.proto_by_user[user].sendString(
                    str(message.GAMESTATE) + ',' + pickle.dumps(game.game_state))

        else:
            i = game.game_state.find_or_add_player(user.name)

        user.game = game_id
        user.player_index = i

        return game_id


    def associate(self, protocol, user):
        try:
            p_old = self.proto_by_user[user]
        except KeyError:
            p_old = None

        # Close the existing connection
        if p_old:
            p_old.transport.lose_connection()

        self.proto_by_user[user] = protocol


    def get_user(self, name):
        try:
            user = self.users_by_name[name]
        except KeyError:
            user = User(name)

        return user


    def start_game(self, game_id):
        try:
            game = self.games[game_id]
        except IndexError:
            print 'Tried to start non-existent game {0:d}'.format(user, game)
            return

        if game.game_state.is_started:
            print 'Game already started'
            return

        self.init_and_start_game(game)

        for u, p in self.proto_by_user.items():
            if u.game == game_id:
                p.sendString(str(message.SETPLAYERID) + ',' + str(u.player_index))
                p.sendString(str(message.GAMESTATE) + ',' + pickle.dumps(game.game_state))


    def init_and_start_game(self, game):
        game.start_game()
        self.save_backup()

    def handle_game_action(self, user, game_id, action):
        try:
            game = self.games[int(game_id)]
        except IndexError as e:
            print e.message
            return

        try:
            a = message.parse_action(action)
        except message.BadGameActionError as e:
            print e.message
            return

        player_index = game.game_state.find_player_index(user)
        if player_index is None:
            print 'User {0:s} is not part of game {1:d}'.format(user, game_id)

        print 'handle_game_action(), Expected action: ' + str(game.expected_action())
        print str(message._action_args_dict[game.expected_action()])
        print 'handle_game_action(), Got action: ' + repr(action)

        print 'Handling action:'
        print '  ' + repr(action)

        i_active_p = game.game_state.get_active_player_index()

        if i_active_p == player_index:
            game.handle(action)
            self.save_backup()

            ##for u, p in self.proto_by_user.items():
            ##    if u.game == user.game:
            ##        p.sendString(str(message.GAMESTATE) + ',' + pickle.dumps(game.game_state))

        else:
            print 'Received action for player {0!s}, but waiting on player {1!s}'.format(
                    player, i_active_p)


    #def handle_game_action(self, user, action):
    def _handle_game_action(self, user, action):
        try:
            game = self.games[user.game]
        except IndexError:
            print 'User has not joined a game!'
            return

        print 'handle_game_action(), Expected action: ' + str(game.expected_action())
        print str(message._action_args_dict[game.expected_action()])
        print 'handle_game_action(), Got action: ' + repr(action)

        print 'Handling action:'
        print '  ' + repr(action)

        i_active_p = game.game_state.get_active_player_index()
        if i_active_p == user.player_index:
            game.handle(action)
            self.save_backup()

            for u, p in self.proto_by_user.items():
                if u.game == user.game:
                    p.sendString(str(message.GAMESTATE) + ',' + pickle.dumps(game.game_state))

        else:
            print 'Received action for player {0!s}, but waiting on player {1!s}'.format(
                    player, i_active_p)


class User(object):
    """Represents an authenticated user that can be used by the
    GTRServer to link players in games to users.
    """
    def __init__(self, name=None, uid=None, proto=None):
        self.name = name
        self.uid = uid # UUID
        self.proto = proto
        self.logged_in = False


class GTRServer(service.Service):
    """Contains a list of multiple Game objects and manages all the
    non-game actions related to e.g. connecting players and starting games.
    """

    implements(IGTRService)

    def __init__(self, backup_file=None, load_backup_file=None):
        self.games = [] # Games database
        self.users = [] # User database
        self.backup_file = backup_file
        self.load_backup_file = load_backup_file

        if self.load_backup_file:
            self.load_backup()


        g = Game()
        g.game_state.find_or_add_player('a')
        g.game_state.find_or_add_player('b')
        self.games.append(g)


    def get_game_state(self, user, game_id):
        try:
            game = self.games[game_id]
        except IndexError as e:
            print e.message
            return None

        player_index = game.game_state.find_player_index(user)
        if player_index is None:
            print 'User {0:s} is not part of game {1:d}'.format(user, game_id)
            return None

        if game.game_state.is_started:
            return defer.succeed(game.game_state)
        else:
            return defer.succeed(None)



    def submit_action(self, user, game_id, action):
        try:
            game = self.games[game_id]
        except IndexError as e:
            print e.message
            return

        try:
            a = message.parse_action(action)
        except message.BadGameActionError as e:
            print e.message
            return

        player_index = game.game_state.find_player_index(user)
        if player_index is None:
            print 'User {0:s} is not part of game {1:d}'.format(user, game_id)
            return

        print 'submit_action(), Expected action: ' + str(game.expected_action())
        print str(message._action_args_dict[game.expected_action()])
        print 'submit_action(), Got action: ' + repr(a)

        print 'Handling action:'
        print '  ' + repr(a)

        i_active_p = game.game_state.get_active_player_index()

        if i_active_p == player_index:
            print 'Game handling action: ' + str(action)
            game.handle(a)
            self.save_backup()

        else:
            print 'Received action for player {0!s}, but waiting on player {1!s}'.format(
                    player, i_active_p)


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
            print 'Creating new game {0:d}'.format(game_id)

        player_index = game.game_state.find_or_add_player(user)
        #if user.game == game_id and game.game_state.players[user.player_index] == user.name:
        #    print 'User already in this game'
        #    return

        return defer.succeed(game_id)

    def create_game(self, user):
        """Create a new game."""
        return self.join_game(user, len(self.games))
        

    def get_game_list(self):
        """Return list of games"""
        game_list = []
        for i, game in enumerate(self.games):
            players = [p.name for p in game.game_state.players]
            game_list.append(GameRecord(i,players))
        
        return defer.succeed(game_list)


    def start_game(self, user, game_id):
        """Request that specified game starts"""

        try:
            game = self.games[game_id]
        except IndexError:
            print 'Tried to start non-existent game {0:d}'.format(game)
            return defer.succeed(None)

        if game.game_state.is_started:
            print 'Game already started'
            return defer.succeed(None)

        game.start_game()
        self.save_backup()
        
        return defer.succeed(None)


    def load_backup(self):
        """ Loads backup from JSON-encoded constructed file.
        """
        if self.games:
            print 'Error! Can\'t load backup file if games already exist'
            return

        try:
            f = open(self.load_backup_file, 'r')
        except IOError:
            print 'Can\'t open backup file: ' + self.load_backup_file
            return

        with f:
            try:
                game_states = pickle.load(f)
            except pickle.PickleError:
                print 'Error! Couldn\'t load games from backup file: ' + self.load_backup_file
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
                print 'Can\'t write to file ' + self.backup_file
                return
            
            with f:
                try:
                    pickle.dump(game_states, f)
                except pickle.PickleError:
                    print 'Error writing backup: ' + self.backup_file
                    return

