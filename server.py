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

