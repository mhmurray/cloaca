#!/usr/bin/env python

import urwid
from urwid import ListBox, LineBox, Filler, SimpleListWalker, Text, Frame, Pile, Edit, Columns, MainLoop
import logging
import re
import sys
from time import sleep
import traceback
import pdb
from random import randint

from functools import wraps

class RollLogHandler(logging.Handler):
    """Log handler that writes messages using two functions, write_msg
    and write_err. These functions are provided when making the object
    or can be set by simply modifying the properties.

    This is set to logLevel=DEBUG, though the logger object might have
    a different level
    """

    def __init__(self, write_msg, write_err=None, write_debug=None):
        """If write_err or write_debug aren't specified, write_msg is
        used in their place.
        """
        logging.Handler.__init__(self, logging.DEBUG)
        self.write_msg = write_msg
        self.write_err = write_err if write_err else write_msg
        self.write_debug = write_debug if write_debug else write_msg

    def handle(self, record):
        """Handles a logging record. This only pipes it to write_msg
        or write_err depending on the logging level.
        """
        if record.levelno >= logging.WARNING:
            self.write_err(record.getMessage(), 'msg_err')
        elif record.levelno >= logging.INFO:
            self.write_msg(record.getMessage(), 'msg_info')
        else:
            self.write_debug(record.getMessage(),'msg_debug')

class CursesGUI(object):

    def __init__(self, choice_callback=None,
                       command_callback=None,
                       help_callback=None):

        self.palette = [
                ('brick', 'light red', 'black'),
                ('rubble', 'yellow', 'black'),
                ('wood', 'light green', 'black'),
                ('concrete', 'white', 'black'),
                ('stone', 'light cyan', 'black'),
                ('marble', 'light magenta', 'black'),
                ('jack', 'dark gray', 'white'),
                ('msg_info', 'white', 'black'),
                ('msg_err', 'light red', 'black'),
                ('msg_debug', 'light green', 'black'),
                ]

        self.choice_callback = choice_callback
        self.command_callback = command_callback
        self.help_callback = help_callback

        self.screen = None
        self.loop = None
        self.called_loop_stop = False
        self.reactor_stop_fired = False

        self.quit_flag = False
        self.edit_msg = "Make selection ('q' to quit): "
        self.roll_list = SimpleListWalker([])
        self.game_log_list = SimpleListWalker([])
        self.choices_list = SimpleListWalker([])

        self.state_text = SimpleListWalker([Text('Connecting...')])

        self.edit_widget = Edit(self.edit_msg)
        self.roll = ListBox(self.roll_list)
        self.game_log = ListBox(self.game_log_list)
        self.choices = ListBox(self.choices_list)
        self.state = ListBox(self.state_text)

        self.left_frame = Pile([
                LineBox(self.state),
                (13, LineBox(self.choices)),
                ])

        self.right_frame = Pile([
                LineBox(self.game_log),
                LineBox(self.roll)
                ])

        self.state.set_focus(len(self.state_text)-1)

        self.columns = Columns([('weight', 0.75, self.left_frame),
                                ('weight', 0.25, self.right_frame)
                                ])
        self.frame_widget = Frame(footer=self.edit_widget,
                                  body=self.columns,
                                  focus_part='footer')

        self.exc_info = None


    def register_loggers(self):
        """Gets the global loggers and sets up log handlers.
        """
        self.game_logger_handler = RollLogHandler(self._roll_write)
        self.logger_handler = RollLogHandler(self._roll_write)

        self.game_logger = logging.getLogger('gtr.game')
        self.logger = logging.getLogger('gtr')

        self.logger.addHandler(self.logger_handler)
        self.game_logger.addHandler(self.game_logger_handler)

        #self.set_log_level(logging.INFO)


    def unregister_loggers(self):
        self.game_logger.removeHandler(self.game_logger_handler)
        self.logger.removeHandler(self.logger_handler)


    def fail_safely(f):
        """Wraps functions in this class to catch arbitrary exceptions,
        shut down the event loop and reset the terminal to a normal state.

        It then re-raises the exception.
        """
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            retval = None
            try:
                retval = f(self, *args, **kwargs)
            except urwid.ExitMainLoop:
                from twisted.internet import reactor
                if not self.reactor_stop_fired and reactor.running:
                    # Make sure to call reactor.stop once
                    reactor.stop()
                    self.reactor_stop_fired = True

            except:
                #pdb.set_trace()
                from twisted.internet import reactor
                if not self.reactor_stop_fired and reactor.running:
                    # Make sure to call reactor.stop once
                    reactor.stop()
                    self.reactor_stop_fired = True

                if not self.called_loop_stop:
                    self.called_loop_stop = True
                    self.loop.stop()
                
                # Save exception info for printing later outside the GUI.
                self.exc_info = sys.exc_info()

                raise

            return retval

        return wrapper
                

    def set_log_level(self, level):
        """Set the log level as per the standard library logging module.

        Default is logging.INFO.
        """
        logging.getLogger('gtr.game').setLevel(level)
        logging.getLogger('gtr').setLevel(level)


    def run(self):
        loop = MainLoop(self.frame_widget, unhandled_input=self.handle_input)
        loop.run()

    def run_twisted(self):
        from twisted.internet import reactor
        evloop = urwid.TwistedEventLoop(reactor, manage_reactor=False)
        self.screen = urwid.raw_display.Screen()
        self.screen.register_palette(self.palette)
        self.loop = MainLoop(self.frame_widget, unhandled_input=self.handle_input,
                             screen = self.screen,
                             event_loop = evloop)
        self.loop.set_alarm_in(0.1, lambda loop, _: loop.draw_screen())

        self.loop.start()

        # The loggers get a Handler that writes to the screen. We want this to only
        # happen if the screen exists, so de-register them after the reactor stops.
        reactor.addSystemEventTrigger('after','startup', self.register_loggers)
        reactor.addSystemEventTrigger('before','shutdown', self.unregister_loggers)
        reactor.run()
        
        # We might have stopped the screen already, and the stop() method
        # doesn't check for stopping twice.
        if self.called_loop_stop:
            self.logger.warn('Internal error!')
        else:
            self.loop.stop()
            self.called_loop_stop = True

    @fail_safely
    def handle_input(self, key):
        if key == 'enter':
            text = self.edit_widget.edit_text
            if text in ['q', 'Q']:
                self.handle_quit_request()
            else:
                self.quit_flag = False

                try:
                    i = int(text)
                except ValueError:
                    i = None
                    self.handle_invalid_choice(text)

                if i is not None:
                    self.handle_choice(i)

            self.edit_widget.set_edit_text('')

    def _roll_write(self, line, attr=None):
        """Add a line to the roll with palette attributes 'attr'.

        If no attr is specified, None is used.

        Default attr is plain text
        """
        text = Text((attr, '* ' + line))
            
        self.roll_list.append(text)
        self.roll_list.set_focus(len(self.roll_list)-1)
        self._modified()

    @fail_safely
    def update_state(self, state):
        """Sets the game state window via one large string.
        """
        self.logger.debug('Drawing game state.')
        self.state_text[:] = [self.colorize(s) for s in state.split('\n')]
        self._modified()

    @fail_safely
    def update_game_log(self, log):
        """Sets the game log window via one large string.
        """
        self.logger.debug('Drawing game log.')
        self.game_log_list[:] = [self.colorize(s) for s in log.split('\n')]
        self.game_log_list.set_focus(len(self.game_log_list)-1)
        self._modified()

    @fail_safely
    def update_choices(self, choices):
        """Update choices list.
        """
        self.choices_list[:] = [self.colorize(str(c)) for c in choices]
        self._modified()

        length = len([c for c in choices if c[2] == '['])
        i = randint(1,length) if length else 0
        self.choices_list.append(self.colorize('\nPicking random choice: {0} in 1s'.format(i)))
        self._modified()
        #from twisted.internet import reactor
        #reactor.callLater(1, self.handle_choice, i)

    @fail_safely
    def update_prompt(self, prompt):
        """Set the prompt for the input field.
        """
        self.edit_widget.set_caption(prompt)
        self._modified()


    def _modified(self):
        if self.loop:
            self.loop.draw_screen()


    @fail_safely
    def quit(self):
        """Quit the program.
        """
        #import pdb; pdb.set_trace()
        #raise TypeError('Artificial TypeError')
        raise urwid.ExitMainLoop()

    def handle_invalid_choice(self, s):
        if len(s):
            text = 'Invalid choice: "' + s + '". Please enter an integer.'
            self.logger.warn(text)

    def handle_quit_request(self):
        if True or self.quit_flag:
            self.quit()
        else:
            self.quit_flag = True
            text = 'Are you sure you want to quit? Press Q again to confirm.'
            self.logger.warn(text)

    def handle_choice(self, i):
        if self.choice_callback:
            self.choice_callback(i)


    def colorize(self, s):
        """Applies color to roles found in a string.

        A string with attributes applied looks like

        Text([('attr1', 'some text'), 'some more text'])

        so we need to split into a list of tuples of text.
        """
        regex_color_dict = {
              r'\b([Ll]egionaries|[Ll]egionary|[Ll]eg|LEGIONARIES|LEGIONARY|LEG)\b' : 'brick',
              r'\b([Ll]aborers?|[Ll]ab|LABORERS?|LAB)\b' : 'rubble',
              r'\b([Cc]raftsmen|[Cc]raftsman|[Cc]ra|CRAFTSMEN|CRAFTSMAN|CRA)\b' : 'wood',
              r'\b([Aa]rchitects?|[Aa]rc|ARCHITECTS?|ARC)\b' : 'concrete',
              r'\b([Mm]erchants?|[Mm]er|MERCHANTS?|MER)\b' : 'stone',
              r'\b([Pp]atrons?|[Pp]at|PATRONS?|PAT)\b' : 'marble',
              r'\b([Jj]acks?|JACKS?)\b' : 'jack',

              r'\b([Bb]ricks?|[Bb]ri|BRICKS?|BRI)\b' : 'brick',
              r'\b([Rr]ubble|[Rr]ub|RUBBLE|RUB)\b' : 'rubble',
              r'\b([Ww]ood|[Ww]oo|WOOD|WOO)\b' : 'wood',
              r'\b([Cc]oncrete|[Cc]on|CONCRETE|CON)\b' : 'concrete',
              r'\b([Ss]tone|[Ss]to|STONE|STO)\b' : 'stone',
              r'\b([Mm]arble|[Mm]ar|MARBLE|MAR)\b' : 'marble',
        }

        def _colorize(s, regex, attr):
            """s is a tuple of ('attr', 'text'). This splits based on the regex
            and adds attr to any matches. Returns a list of tuples

            [('attr1', 'text1'), ('attr2', 'text2'), ('attr3','text3')]

            with some attributes being None if they aren't colored.
            """
            output = []
            a, t = s
            # Make a list of all tokens, split by matches
            tokens = re.split(regex, t)
            for tok in tokens:
                m = re.match(regex, tok)
                if m:
                    # matches get the new attributes
                    output.append( (attr,tok) )
                else:
                    # non-matches keep the old ones
                    output.append( (a, tok) )

            return output


        output = [ (None, s) ] 
        
        for k,v in regex_color_dict.items():
            new_output = []
            for token in output:
                new_output.extend(_colorize(token, k, v))

            output[:] = new_output

        return Text(output)


if __name__ == '__main__':
    main()
