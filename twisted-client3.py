#!/usr/bin/env python

""" A simple command line interface to a NetstringReceiver.
"""

from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.protocols.basic import NetstringReceiver, LineReceiver
from twisted.internet import stdio

import argparse
import collections

import message
from message import GameAction
import client3 as client
from client3 import Choice
from curses_gui import CursesGUI
from util import CircularPausingFilter

from fsm import StateMachine

import pickle

import logging
import sys

lg = logging.getLogger('gtr')

class TerminalGUI(object):

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
        self.pump_return = None

        self._gui = CursesGUI()
        self._gui.choice_callback = self.handle_choice_input
        self._gui.command_callback = self.handle_command_input
        self._gui.help_callback = self.print_help

        self.fsm = StateMachine()

        self.fsm.add_state('START', None, lambda _ : 'MAINMENU')
        self.fsm.add_state('MAINMENU',
                self._main_menu_arrival, self._main_menu_transition)
        self.fsm.add_state('SELECTGAME',
                self._select_game_arrival, self._select_game_transition)
        self.fsm.add_state('END', None, None, True)

        self.fsm.set_start('START')
        self.fsm.pump(None)

    def set_log_level(self, level):
        """Set the log level as per the standard library logging module.

        Default is logging.INFO.
        """
        self._gui.set_log_level(level)
        logging.getLogger('gtr.game').setLevel(level)
        logging.getLogger('gtr').setLevel(level)

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

    def print_help(self):
        lg.warn('Help! (q to quit)')

    def handle_command_input(self, command):
        lg.debug('Handling command input : ' + str(command))
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
            lg.error('Quitting game')
            self._server_protocol.loseConnection()
            self._gui.quit()
            return

        if self._in_game and not self.client.builder:
            lg.error("It's not your turn")
            return

    def handle_choice_input(self, choice):
        """Handles an input choice (integer, 1-indexed).
        """
        try:
            choice = int(choice)
        except ValueError:
            lg.warn('Invalid choice: {0}\n'.format(choice))
            return

        lg.debug('Selection is ' + str(choice))
        if self._in_game:
            self.client.make_choice(choice)
            action = self.client.check_action_builder()

            if action is None:
                lg.debug('More input is required, updating choices list')
                self.update_choices()
            else:
                lg.debug('Sending to server: ' + str(action))
                self.client.builder = None
                self.send_command(action)

        else:
            game_action = self._input_choice(choice)
            if game_action:
                lg.debug('Sending to server: ' + str(game_action))
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
            lg.info('Creating new game.')
            self.pump_return = GameAction(message.REQCREATEGAME)
            self._waiting_for_join = True
            return 'MAINMENU'

        elif choice == 'Start game':
            lg.info('Requesting game start.')
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
        choices_list = []
        if not self.choices:
            self.choices.append(Choice(None, "(none)"))

        for c in self.choices:
            line = ''
            if c.selectable:
                line = '  [{0:2d}] {1}'.format(i_choice, c.description)
                i_choice+=1
            else:
                line = '       {0}'.format(c.description)

            choices_list.append(line)

        self._gui.update_choices(choices_list)

        if prompt is None:
            prompt = 'Please make a selection: '

        self._gui.update_prompt(prompt)

    def send_command(self, game_action):
        self._server_protocol.send_command(self.username, self.game_id, game_action)

    def update_game_list(self, game_list):
        self._game_list = game_list

        if self._waiting_for_list:
            self._waiting_for_list = False

        game_list = ['Available games']
        

        for record in self._game_list:
            game_list.append('  ' + str(record))

        self._gui.update_state('\n'.join(game_list))
        self._show_choices()

    def update_game_state(self, game_state):
        if game_state is None:
            return

        for p in game_state.players:
            if p.name == self.username:
                player_index = game_state.players.index(p)
                self.client.player_id = player_index

        if self._waiting_for_start or game_state.is_started:
            self._waiting_for_start = False
            self._in_game = True

        old_gs = self.client.game.game_state
        old_game_id = old_gs.game_id if old_gs else None
        new_game_id = game_state.game_id

        if old_game_id is None or old_game_id != new_game_id:
            self.client.update_game_state(game_state)
            action = self.client.check_action_builder()
            if action:
                lg.debug('Action is complete without requiring a choice.')
                self.send_command(action)
            else:
                lg.debug('Action requires user input. Displaying game state.')
                self._gui.update_state('\n'.join(game_state.get_public_game_state(self.username)))
                self._gui.update_game_log('\n'.join(game_state.game_log))
                self.update_choices()

    def update_choices(self):
        choices = self.client.get_choices()

        if choices is None:
            lg.error('Choices list is empty')
            import pdb; pdb.set_trace()
            lines = ['   [1] ERROR! Choices list is empty']
        else:
            lines = []
            i_choice = 1
            for c in choices:
                if c.selectable:
                    lines.append('  [{0:2d}] {1}'.format(i_choice, c.description))
                    i_choice+=1
                else:
                    lines.append('       {0}'.format(c.description))

        self._gui.update_choices(lines)


    def set_player_id(self, i):
        self.client.player_id = i

    def join_game(self, game_id):
        lg.info('Joined game {0:d}.'.format(game_id))
        self.game_id = game_id
        self._waiting_for_join = False
        self._show_choices()

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
        lg.info('Connected to server.')
        self._ui._waiting_for_list = True
        self.send_command(self._ui.username, None, GameAction(message.REQGAMELIST))

    def send_command(self, user, game_id, game_action):
        """ Sends the command game_action to the server.
        It is of type message.GameAction.
        """
        if game_id is None:
            game_id = 0

        cmd = ','.join([user, str(game_id), str(game_action.action)] + map(str, game_action.args))

        lg.debug('Sending command to server: ' + cmd)

        self.sendString(cmd)

    def stringReceived(self, s):
        lg.debug('Received message from server.')
        try:
            a = message.parse_action(s)
        except message.BadGameActionError as e:
            lg.warn('Failure to decode GameAction from server.')
            lg.warn(e.message)
            return

        action = a.action

        if action == message.GAMESTATE:
            if a.args[0] is None:
                lg.debug('Did not receive game state. Game has not started.')
                game_state = None
            else:
                try:
                    game_state = pickle.loads(a.args[0])
                except PickleError:
                    lg.warn('Failed to unpickle GameState object.')
                    game_state = None

                lg.debug('Received game state: {0:10d}'.format(hash(game_state)))

            self._ui.update_game_state(game_state)

        elif action == message.JOINGAME:
            game_id = a.args[0]
            lg.debug('Received acknowledgement of joining game ' + str(game_id))
            self._ui.join_game(game_id)

        elif action == message.SETPLAYERID:
            player_id = a.args[0]
            lg.debug('Received player id ' + str(player_id))
            self._ui.set_player_id(player_id)

        elif action == message.GAMELIST:
            lg.debug('Received new list of games')
            try:
                game_list = pickle.loads(a.args[0])
            except PickleError:
                lg.warn('Failed to unpickle list of games.')
                game_list = None
            else:
                self._ui.update_game_list(game_list)

        else:
            lg.warn('Unknown message receieved from server: ' + str(a))

class ServerProtocolFactory(Factory):
    """A light interface for Server connection to the twisted endpoint.connect
    """
        
    def __init__(self, ui):
        self.ui = ui

    def buildProtocol(self, addr):
        return ServerProtocol(self.ui)


def main():
    parser = argparse.ArgumentParser(description='Connect to a GtR server.')
    parser.add_argument('--port', type=int, default=10000)
    parser.add_argument('--address', type=str, default='localhost')
    parser.add_argument('username')
    parser.add_argument('--start', action='store_true', default=False)
    parser.add_argument('--game-id', type=int, default=0)
    parser.add_argument('--verbose', action='store_true', default=False)

    args = parser.parse_args()


    # Set up logger
    STDOUT_QUEUE_SIZE=1000

    formatter = logging.Formatter('%(message)s')
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)

    # Set up a buffer to hold log events while we're in the GUI.
    # We can't write to stdout with the GUI active.
    cpf = CircularPausingFilter(ch, STDOUT_QUEUE_SIZE) # attaches itself

    lg.addHandler(ch)
    lg.setLevel(logging.DEBUG)
    lg.propagate = False

    lg.debug('Creating GUI')
    gui = TerminalGUI(args.username)
    if args.verbose:
        gui.set_log_level(logging.DEBUG)

    lg.debug('Connecting to server {0}:{1}'.format(args.address, args.port))

    from twisted.internet import reactor
    point = TCP4ClientEndpoint(reactor, args.address, args.port)
    d = point.connect(ServerProtocolFactory(gui))


    # The urwid MainLoop will exit cleanly when receiving a ExitMainLoop
    # exception. Any other exception causes it to shut down the screen. With
    # twisted, this leaves us with no UI and a running reactor. We should print
    # the exception and shut down the reactor.
    #
    # The event loop is run by Twisted's reactor. If we use a TwistedEventLoop
    # in urwid with manage_reactor=True, unhandled exceptions are caught by
    # TwistedEventLoop.handle_exit(). If it's a ExitMainLoop exception, the
    # reactor is stopped cleanly via reactor.stop(). However, for any other
    # exception, the sys.exc_info() is recorded, the reactor is stopped via
    # reactor.crash(). After the call to reactor.run() in
    # TwistedEventLoop.run(), there's a check for an exception (self.exc_info),
    # and it's re-raised if found.
    #
    # The reactor crash must leave the python interpreter with some sigint
    # handling from urwid or something, because merely crashing the reactor and
    # raising an exception doesn't hang things - the program just exits. Could
    # be that reactor crashing is unreliable and depends on what callbacks are
    # hooked in, like the docs say.
    #
    # I'm not sure why this leaves the terminal in a bad state, but changing
    # the reactor.crash() to reactor.stop() is the only thing I've found to fix
    # it. Probably reactor.crash() is just a bad idea, so I need to use
    # manage_reactor=False to keep the TwEvLoop from crashing it. This would
    # result in exceptions not stopping the reactor, because the handle_exit
    # wrapper in TwEvLoop isn't used.
    #
    # What about exceptions thrown by functions not wrapped in handle_exit?
    # This is only done for unhandled_input, etc, but the other functions of
    # curses_gui (like update_state()) shouldn't have this wrapper protection.
    # Update: and they don't. Exceptions in other functions will not stop the
    # reactor. The GUI stuff is still being drawn to some extent, like updating
    # single lines here and there. 
    #
    # So clearly we must have manage_reactor=False. We call "with
    # MainLoop.start():" in front of reactor.run(), which hooks the GUI stuff
    # into the idle loop. In order to catch exceptions thrown in the code so we
    # can stop the reactor
    
    # Turn off logging to stdout/stderr
    cpf.pause()

    lg.debug('Starting GUI')
    gui._gui.run_twisted()

    # Resume logging and print saved messages.
    cpf.unpause()

    # After console output is re-printed, re=raise any exception that caused the
    # loop to quit
    if gui._gui.exc_info:
        exc_info, gui._gui.exc_info = gui._gui.exc_info, None

        raise exc_info[0], exc_info[1], exc_info[2]


if __name__ == '__main__':
    main()
