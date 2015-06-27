
from gtr import Game
from gamestate import GameState
from player import Player

import message
import argparse

from twisted.internet.protocol import ServerFactory, Protocol
from twisted.protocols.basic import NetstringReceiver

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
        game, action = request.split(',', 1)

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
            self.factory.handle_game_action(self.user, a)


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

    def handle_game_action(self, user, action):
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

