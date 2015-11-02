#!/usr/bin/env python

""" A simple command line interface to a NetstringReceiver.
"""

from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.protocols.basic import NetstringReceiver, LineReceiver
from twisted.internet import stdio

from os import linesep
import argparse
import re

import message
from message import GameAction
from gamestate import GameState
from gtr import Game
import client3 as client
from client3 import Choice

from fsm import StateMachine

from interfaces import IGTRService, IGTRFactory
from zope.interface import Interface, implements

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


class TerminalGUI(object):
    """The GUI is actually a LineReceiver protocol, which is used to connect
    to Standard IO. The lineReceived method is the input for client commands.
    """
    delimiter = '\n' # unix terminal style newlines
    
    def __init__(self, username):
        self.username = username
        self._server_protocol = None
        self._print_buffer = ''
        self._game_list = []
        self._waiting_for_list = False
        self._waiting_for_join = False
        self._waiting_for_start = False
        self._in_game = False
        self.client = client.Client()
        self.game_id = None
        self._update_interval = 15
        self.pump_return = None


        self.fsm = StateMachine()

        self.fsm.add_state('START', None, lambda _ : 'MAINMENU')
        self.fsm.add_state('MAINMENU',
                self._main_menu_arrival, self._main_menu_transition)
        self.fsm.add_state('SELECTGAME',
                self._select_game_arrival, self._select_game_transition)
        self.fsm.add_state('END', None, None, True)

        self.fsm.set_start('START')
        self.fsm.pump(None)

    def set_server_protocol(self, p):
        """Set the protocol interface to the server. This should be a 
        NetstringReceiver object.
        """
        self._server_protocol = p

    def _input_choice(self, choice):
        """Provides an input for the state machine. This function
        potentially returns a GameAction object, which is a command
        to be sent to the server.
        """
        # Convert from 1-indexed in the UI to the 0-indexed choices_list
        self.fsm.pump(int(choice)-1)
        return self.pump_return

    def handle_client_input(self, command):
        """Handle input from client.
        """
        if command in ['help', 'h', '?']:
            self.print_help()
            return

        elif command in ['restart', 'r']:
            self.client.restart_command()
            return

        elif command in ['refresh', 'f']:
            self.send_command(GameAction(message.REQGAMESTATE))
            return

        elif command in ['quit', 'q']:
            lg.info('Quitting game')
            self._server_protocol.loseConnection()
            from twisted.internet import reactor
            reactor.stop()
            return

        if self._in_game and not self.client.builder:
            lg.info("It's not your turn")
            return

        try:
            choice = int(command)
        except ValueError:
            sys.stderr.write('Invalid choice: {0}\n'.format(command))
            self.print_help()
            return

        if self._in_game:
            action = self.client.make_choice(choice)

            if action is not None:
                print 'doing action ' + repr(action)
                self.send_command(action)

        else:
            game_action = self._input_choice(choice)
            if game_action:
                self.send_command(game_action)

    
    def _main_menu_arrival(self):
        choices = ['List games', 'Join game', 'Create game', 'Start game']
        self.choices = [Choice(desc, desc) for desc in choices]

    def _main_menu_transition(self, choice):
        choice = self.choices[choice].item
        if choice == 'List games':
            self.pump_return = GameAction(message.REQGAMELIST)
            self._waiting_for_list = True
            return 'MAINMENU'

        elif choice == 'Join game':
            if len(self._game_list) == 0:
                lg.info('No games listed. Getting game list first.')
                self.pump_return = GameAction(message.REQGAMELIST)
                self._waiting_for_list = True
                return 'MAINMENU'
            else:
                return 'SELECTGAME'

        elif choice == 'Create game':
            lg.info('Creating new game...')
            self.pump_return = GameAction(message.REQCREATEGAME)
            self._waiting_for_join = True
            return 'MAINMENU'

        elif choice == 'Start game':
            lg.info('Requesting game start...')
            self.pump_return = GameAction(message.REQSTARTGAME)
            self._waiting_for_start = True
            return 'MAINMENU'

        else:
            return 'END'

    def _select_game_arrival(self):
        # we only get here if the game list is populated
        self.choices = [Choice(i, str(game)) for i, game in enumerate(self._game_list)]
        self._show_choices()

    def _select_game_transition(self, choice):
        game_id = self.choices[choice].item
        self._waiting_for_join = True
        self.pump_return = GameAction(message.REQJOINGAME, game_id)
        return 'MAINMENU'
        

    def _show_choices(self, prompt=None):
        """Returns the index in the choices_list selected by the user or
        raises a StartOverException or a CancelDialogExeption.

        The choices_list is a list of Choices.
        """
        i_choice = 1
        for c in self.choices:
            if c.selectable:
                lg.info('  [{0:2d}] {1}'.format(i_choice, c.description))
                i_choice+=1
            else:
                lg.info('       {0}'.format(c.description))

        if prompt is not None:
            lg.info(prompt)
        else:
            lg.info('Please make a selection:')

    def send_command(self, game_action):
        self._server_protocol.send_command(self.username, self.game_id, game_action)

    def update_game_list(self, game_list):
        self._game_list = game_list

        if self._waiting_for_list:
            self._waiting_for_list = False

            print 'List of games:'
            for record in self._game_list:
                print '  ' + str(record)
            print

            self._show_choices()

    def update_game_state(self, game_state):
        if game_state is None:
            return

        for p in game_state.players:
            if p.name == self.username:
                player_index = game_state.players.index(p)
                self.client.player_id = player_index

        if self._waiting_for_start:
            lg.info('Starting game ...')
            self._waiting_for_start = False
            self._in_game = True

        old_gs = self.client.game.game_state
        old_game_id = old_gs.game_id if old_gs else None
        new_game_id = game_state.game_id

        if old_game_id is None or old_game_id != new_game_id:
            self.client.update_game_state(game_state)



    def set_player_id(self, i):
        self.client.player_id = i

    def join_game(self, game_id):
        lg.info('Joined game {0:d}, waiting to start...'.format(game_id))
        self.game_id = game_id
        self._waiting_for_join = False
        self._show_choices()
        #self.routine_update()

    def routine_update(self):
        """Updates the game state routinely.
        """
        self.send_command(GameAction(message.REQGAMESTATE))

        from twisted.internet import reactor
        reactor.callLater(self._update_interval, self.routine_update)


class StdIOCommandProtocol(LineReceiver):
    delimiter = '\n' # unix terminal style newlines

    def __init__(self, gui):
        """ This protocol takes a TerminalGUI argument used to talk to the
        server.
        """
        self._gui = gui

    def lineReceived(self, line):
        # Ignore blank lines
        if not line:
            return

        self._gui.handle_client_input(line)

class ServerProtocol(NetstringReceiver):

    def __init__(self, ui):
        """Initialize the protocol with a given user interface.
        This also sets this object as the protocol using
        ui.set_server_protocol().
        """
        self._ui = ui
        self._ui.set_server_protocol(self)

    def connectionMade(self):
        """When connected, update game list.
        """
        lg.info('Connected! Request game list')
        self._ui._waiting_for_list = True
        self.send_command(self._ui.username, None, GameAction(message.REQGAMELIST))

    def send_command(self, user, game_id, game_action):
        """ Sends the command game_action to the server.
        It is of type message.GameAction.
        """
        if game_id is None:
            game_id = 0

        self.sendString(','.join([user, str(game_id), str(game_action.action)] + map(str, game_action.args)))

    def stringReceived(self, s):
        try:
            a = message.parse_action(s)
        except message.BadGameActionError as e:
            print e.message
            return

        lg.info("Action: " + repr(a)[0:50])
        action = a.action

        if action == message.GAMESTATE:
            if a.args[0] is None:
                game_state = None
            else:
                game_state = pickle.loads(a.args[0])

            self._ui.update_game_state(game_state)

        elif action == message.JOINGAME:
            game_id = int(a.args[0])
            self._ui.join_game(game_id)

        elif action == message.SETPLAYERID:
            player_id = a.args[0]
            self._ui.set_player_id(player_id)

        elif action == message.GAMELIST:
            game_list = pickle.loads(a.args[0])

            self._ui.update_game_list(game_list)

        else:
            lg.warn('Unknown command')
            lg.info(str(a))



class ServerProtocolFactory(Factory):
    """A light interface for Server connection to the twisted endpoint.connect
    """
        
    def __init__(self, username):
        self.username = username

    def buildProtocol(self, addr):
        return ServerProtocol(self.username)


def main():
    parser = argparse.ArgumentParser(description='Connect to a GtR server.')
    parser.add_argument('--port', type=int, default=10000)
    parser.add_argument('--address', type=str, default='localhost')
    parser.add_argument('username')
    parser.add_argument('--start', action='store_true', default=False)
    parser.add_argument('--game-id', type=int, default=0)

    args = parser.parse_args()

    from twisted.internet import reactor

    point = TCP4ClientEndpoint(reactor, args.address, args.port)

    gui = TerminalGUI(args.username)
    d = point.connect(ServerProtocolFactory(gui))

    p = stdio.StandardIO(StdIOCommandProtocol(gui))

    def finished_protocol(_):
        gui._show_choices()

    d.addCallback(finished_protocol)

    reactor.run()


if __name__ == '__main__':
    main()
