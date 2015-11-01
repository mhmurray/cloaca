#!/usr/bin/env python

""" A simple command line interface to a NetstringReceiver.
"""

from twisted.internet.protocol import ClientFactory, Protocol
from twisted.protocols.basic import NetstringReceiver, LineReceiver
from twisted.internet import stdio

from os import linesep
import argparse

import message
from gamestate import GameState
from gtr import Game
import client3 as client

import pickle

import logging 
import sys
 
lg = logging.getLogger('gtr') 
formatter = logging.Formatter('%(message)s') 
ch = logging.StreamHandler(sys.stdout) 
ch.setLevel(logging.DEBUG) 
ch.setFormatter(formatter) 
lg.addHandler(ch) 
lg.setLevel(logging.DEBUG) 
lg.propagate = False 

class StdIOCommandProtocol(LineReceiver):
    delimiter = '\n' # unix terminal style newlines.

    def __init__(self, factory):
        """ This protocol takes a GTRClientfactory argument that manages the
        network connection to the server.
        """
        self.f = factory

    def lineReceived(self, line):
        # Ignore blank lines
        if not line:
            return

        self.f.handle_client_command(line)

class GameProtocol(NetstringReceiver):

    def connectionMade(self):
        if self.factory.p:
            sys.stderr.write("Already connected, losing connection\n")
            self.transport.loseConnection()

        else:
            self.factory.p = self
            sys.stderr.write( "Successfully connected.\n")

            print 'Requesting game state'
            self.factory.send_command(message.GameAction(
                    message.REQGAMESTATE))

            return

            sys.stderr.write('Logging in user ' + self.factory.username + '\n')
            self.factory.send_command(message.GameAction(
                    message.LOGIN, self.factory.username))

            self.factory.send_command(message.GameAction(
                    message.JOINGAME, self.factory.game_id))

            if self.factory.start_game:
                self.factory.send_command(message.GameAction(
                        message.STARTGAME))

    def loseConnection(self):
        if self.factory.p == self:
            self.factory.p = None
        sys.stderr.write('Disconnected\n')

    def stringReceived(self, s):
        print 'Received message:'
        print repr(pickle.loads(s))
        #self.factory.handle_server_msg(s)

class GameClientFactory(ClientFactory):
    protocol = GameProtocol

    def __init__(self, username, start_game=False, game_id=0):
        self.p = None
        self.game_state = None
        self.client = client.Client()
        self.player_index = None
        self.username = username
        self.start_game = start_game
        self.game_id = game_id

    def startedConnecting(self, connector):
        sys.stderr.write('Connecting...\n')

    def handle_server_msg(self, s):
        try:
            a = message.parse_action(s)
        except message.BadGameActionError as e:
            print e.message
            print 'Message was not a valid action: ' + s
            return

        if a.action == message.SETPLAYERID:
            self.handle_set_player_id(a)

        if a.action == message.GAMESTATE:
            self.handle_gamestate(a)

    def handle_gamestate(self, a):
        gs = pickle.loads(a.args[0])
        self.client.update_game_state(gs)

    def handle_set_player_id(self, a):
        index = a.args[0]
        if index is None:
            raise Exception('Not allowed to join game')

        if self.player_index is None:
            self.player_index = int(index)
            self.client.player_id = self.player_index
        else:
            raise Exception('Received second SETPLAYERID message')

    def print_help(self):
        sys.stderr.write(
            ('Enter an integer choice or one of the following:\n'
             '    restart : restarts the current action from the beginning\n'
             '    quit    : exit the client.\n'))


    def handle_client_command(self, command):
        """ Handles input from the client.
        """
        if command in ['help', 'h', '?']:
            self.print_help()
            return

        elif command in ['restart', 'r']:
            self.client.restart_command()
            return

        elif command in ['quit', 'q']:
            self.p.loseConnection()
            from twisted.internet import reactor
            reactor.stop()
            return


        b = self.client.builder
        if not b:
            sys.stderr.write('It\'s not your turn.\n')
            return

        try:
            choice = int(command)
        except ValueError:
            sys.stderr.write('Invalid choice: {0}\n'.format(command))
            self.print_help()
            return

        action = self.client.make_choice(choice)

        if action is not None:
            print 'doing action ' + repr(action)
            self.send_command(action)


    def send_command(self, game_action):
        """ Sends the command game_action to the server.
        It is of type message.GameAction.
        """
        self.p.sendString(','.join([self.username,'0', str(game_action.action)] + map(str, game_action.args)))

    def _fatal_error(self):
        """ Un-recoverable error. Close the connection.
        """
        print 'FATAL ERROR. Disconnecting...'
        self.p.loseConnection()


def main():
    parser = argparse.ArgumentParser(description='Connect to a GtR server.')
    parser.add_argument('--port', type=int, default=10000)
    parser.add_argument('--address', type=str, default='localhost')
    parser.add_argument('username')
    parser.add_argument('--start', action='store_true', default=False)
    parser.add_argument('--game-id', type=int, default=0)

    args = parser.parse_args()

    from twisted.internet import reactor

    factory = GameClientFactory(args.username, args.start, args.game_id)
    reactor.connectTCP(args.address, args.port, factory)

    stdio.StandardIO(StdIOCommandProtocol(factory))

    reactor.run()


if __name__ == '__main__':
    main()



