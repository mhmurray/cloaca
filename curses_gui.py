#!/usr/bin/env python

import urwid
from urwid import ListBox, LineBox, Filler, SimpleListWalker, Text, Frame, Pile, Edit, Columns, MainLoop
import logging
import re

def main():

    c = CursesGUI()
    def choice_callback(i):
        c.update_choices(range(1,i+1))
    c.choice_callback = choice_callback

    c.update_state('This\nis my long string\nthat spans mulitple\n\n lines\n')
    c.run_twisted()

class RollLogHandler(logging.Handler):
    """Log handler that writes messages using two functions, write_msg
    and write_err. These functions are provided when making the object
    or can be set by simply modifying the properties.
    """

    def __init__(self, write_msg, write_err):
        logging.Handler.__init__(self, logging.INFO)
        self.write_msg = write_msg
        self.write_err = write_err

    def handle(self, record):
        """Handles a logging record. This only pipes it to write_msg
        or write_err depending on the logging level.
        """
        if record.levelno >= logging.WARNING:
            self.write_err(record.getMessage())
        else:
            self.write_msg(record.getMessage())

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
                ]

        self.choice_callback = choice_callback
        self.command_callback = command_callback
        self.help_callback = help_callback

        self.screen = None
        self.loop = None

        self.quit_flag = False
        self.edit_msg = "Make selection ('q' to quit): "
        self.roll_list = SimpleListWalker([Text('first!')])
        self.choices_list = SimpleListWalker([Text('Choice '+str(i)) for i in range(10)])

        self.state_text = SimpleListWalker([Text('State goes here...')])

        self.edit_widget = Edit(self.edit_msg)
        self.roll = ListBox(self.roll_list)
        self.choices = ListBox(self.choices_list)
        self.state = ListBox(self.state_text)

        self.frame = Pile([
                LineBox(self.state),
                (13, LineBox(self.choices)),
                ])

        self.state.set_focus(len(self.state_text)-1)

        self.columns = Columns([('weight', 0.75, self.frame),
                                ('weight', 0.25, LineBox(self.roll))
                                ])
        self.frame_widget = Frame(footer=self.edit_widget,
                                  body=self.columns,
                                  focus_part='footer')

        game_lg = logging.getLogger('gtr.game')
        game_lg.addHandler(RollLogHandler(self.roll_write, self.roll_write))
        game_lg.setLevel(logging.INFO)
        game_lg.info('Set up logger')
        game_lg.warn('Warning. Set up logger')

    def run(self):
        loop = MainLoop(self.frame_widget, unhandled_input=self.handle_input)
        loop.run()

    def run_twisted(self):
        from twisted.internet import reactor
        evloop = urwid.TwistedEventLoop(reactor)
        self.screen = urwid.raw_display.Screen()
        self.screen.register_palette(self.palette)
        self.loop = MainLoop(self.frame_widget, unhandled_input=self.handle_input,
                             screen = self.screen,
                             event_loop = evloop)
        self.loop.set_alarm_in(0.1, lambda loop, _: loop.draw_screen())
        self.loop.run()

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

    def roll_write(self, line):
        """Add a line to the roll.
        """
        self.roll_list.append(Text(line))
        self.roll_list.set_focus(len(self.roll_list)-1)
        self.modified()

    def _state_add(self, line):
        self.state_text.append(Text(line))
        self.modified()

    def update_state(self, state):
        """Sets the game state window via one large string.
        """
        self.state_text[:] = [self.colorize(s) for s in state.split('\n')]
        self.modified()

    def update_choices(self, choices):
        """Update choices list.
        """
        self.choices_list[:] = [self.colorize(str(c)) for c in choices]
        self.modified()

    def update_prompt(self, prompt):
        """Set the prompt for the input field.
        """
        self.edit_widget.set_caption(prompt)
        self.modified()


    def modified(self):
        if self.loop:
            self.loop.draw_screen()


    def quit(self):
        """Quit the program.
        """
        raise urwid.ExitMainLoop()

    def handle_invalid_choice(self, s):
        if len(s):
            text = '! Invalid choice: "' + s + '". Please enter an integer.'
            self.roll_write(text)

    def handle_quit_request(self):
        if True or self.quit_flag:
            self.quit()
        else:
            self.quit_flag = True
            text = 'Are you sure you want to quit? Press Q again to confirm.'
            self.roll_write(text)

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
