import gtrutils
import card_manager
from itertools import izip_longest

THINKERORLEAD   =  0
USELATRINE      =  1
USEVOMITORIUM   =  2
PATRONFROMPOOL  =  3
BARORAQUEDUCT   =  4
PATRONFROMDECK  =  5
PATRONFROMHAND  =  6
USEFOUNTAIN     =  7
FOUNTAIN        =  8
LEGIONARY       =  9
GIVECARDS       = 10
THINKERTYPE     = 11
SKIPTHINKER     = 12
USESEWER        = 13
USESENATE       = 14
LABORER         = 15
STAIRWAY        = 16
ARCHITECT       = 17
CRAFTSMAN       = 18
MERCHANT        = 19
LEADROLE        = 20
FOLLOWROLE      = 21
REQGAMESTATE    = 22
GAMESTATE       = 23
SETPLAYERID     = 24
REQJOINGAME     = 25
JOINGAME        = 26
REQCREATEGAME   = 27
CREATEGAME      = 28
LOGIN           = 29
REQSTARTGAME    = 30
STARTGAME       = 31
REQGAMELIST     = 32
GAMELIST        = 33

# A dictionary of the number of arguments for each action type
# and their signature.
# If the number is not limited, but has a minimum, the third
# element will be True.
# eg. ('leadrole', 3, True, ...) means there are at least 3
# arguments, but maybe more.
# The signature is a tuple of tuples with (type, string) entries,
# eg. 'int n_actions', or 'Card from_pool', though note that
# "Card" is not a type. Cards are just strings.
Card = str
_action_args_dict = {
    REQGAMESTATE   : ('reqgamestate',   0, False, () ),
    GAMESTATE      : ('gamestate',      1, False, ( (str,  'game_state'), ) ),
    SETPLAYERID    : ('setplayerid',    1, False, ( (int,  'id'), ) ),
    REQJOINGAME    : ('reqjoingame',    1, False, ( (int, 'game_id'), ) ),
    JOINGAME       : ('joingame',       1, False, ( (int, 'game_id'), ) ),
    REQCREATEGAME  : ('reqcreategame',  0, False, () ),
    CREATEGAME     : ('creategame',     0, False, () ),
    LOGIN          : ('login',          1, False, ( (str, 'user_name'), ) ),
    REQSTARTGAME   : ('reqstartgame',   0, False, () ),
    STARTGAME      : ('startgame',      0, False, () ),
    REQGAMELIST    : ('reqgamelist',    0, False, () ),
    GAMELIST       : ('gamelist',       1, False, ( (str, 'game_list'), ) ),


    THINKERORLEAD  : ('thinkerorlead',  1, False, ( (bool, 'do_thinker'), ) ),
    THINKERTYPE    : ('thinkertype',    1, False, ( (bool, 'for_jack'), ) ),
    SKIPTHINKER    : ('skipthinker',    1, False, ( (bool, 'skip'), ) ),
    USELATRINE     : ('uselatrine',     1, False, ( (Card, 'to_discard'), ) ),
    USEVOMITORIUM  : ('usevomitorium',  1, False, ( (bool, 'discard_all'), ) ),
    USEFOUNTAIN    : ('usefountain',    1, False, ( (bool, 'use_fountain'), ) ),
    USESENATE      : ('usesenate',      1, False, ( (bool, 'use_senate'), ) ),
    BARORAQUEDUCT  : ('baroraqueduct',  1, False, ( (bool, 'bar_first'), ) ),
    PATRONFROMPOOL : ('patronfrompool', 1, False, ( (Card, 'from_pool'), ) ),
    PATRONFROMDECK : ('patronfromdeck', 1, False, ( (bool, 'from_deck'), ) ),
    PATRONFROMHAND : ('patronfromhand', 1, False, ( (Card, 'from_hand'), ) ),
    GIVECARDS      : ('givecards',      1, True,  ( (Card, 'cards'), ) ),
    USESEWER       : ('usesewer',       1, True,  ( (Card, 'c1'), ) ),
    LEGIONARY      : ('legionary',      1, True,  ( (Card, 'from_hand'), ) ),
    LABORER        : ('laborer',        2, False,
        (   (Card, 'from_hand'), (Card, 'from_pool') ) ),

    ARCHITECT      : ('architect',      4, False,
        (   (Card, 'building'), (Card, 'material'),
            (Card, 'site'), (bool, 'from_pool') ) ),

    CRAFTSMAN      : ('craftsman',      3, False,
        (   (Card, 'building'), (Card, 'material'), (Card, 'site') ) ),

    MERCHANT       : ('merchant',       3, False,
        (   (Card, 'from_stockpile'), (Card, 'from_hand'), (bool, 'from_deck') ) ),

    LEADROLE       : ('leadrole',       3, True,
        (   (str, 'role'), (int, 'n_actions'), (Card, 'c1') ) ),

    FOLLOWROLE     : ('followrole',     3, True, 
        (   (bool, 'think'), (int, 'n_actions'), (Card, 'c1') ) ),

    FOUNTAIN       : ('fountain',       4, False,
        (   (bool, 'skip'), (Card, 'building'),
            (Card, 'material'), (Card, 'site') ) ),

    STAIRWAY       : ('stairway',       4, False,
        (   (str, 'player'), (Card, 'building'),
            (Card, 'material'), (bool, 'from_pool') ) ),
    }

def get_action_name(action):
    """ Returns the lower-case name for the given action,
    eg. 'usesewer' for message.USESEWER.

    Takes the action type.
    """
    return _action_args_dict[action][0]

def parse_action(action_string):
    """ Parses the action string into a valid action or
    raises a BadGameActionError.
    It should be formatted like this:

        ARCHITECT,Foundation,Material,Site

    which are typed:

        int, str, str, str

    See message.py for the spec for each action.
    """
    action_tokens = action_string.split(',', 1)

    try:
        action_type = int(action_tokens[0])
    except IndexError:
        raise BadGameActionError('Invalid action format: ' + action_string)
    except ValueError:
        raise BadGameActionError('Invalid action value: ' + action_tokens[0])

    try:
        action_spec = _action_args_dict[action_type]
    except KeyError:
        raise Exception('Action value out of range: ' + str(action_type))

    try:
        n_args, extras_allowed, arg_specs = action_spec[1:4]
    except IndexError:
        raise Exception('Missing # args spec for action: ' + str(action_type))

    # Split only to the number of allowed actions.
    # Some GameActions (GAMESTATE) contain commas, and rely on n_args.
    if n_args > 0:
        arg_tokens = action_tokens[1].split(',', -1 if extras_allowed else n_args-1)
    else:
        arg_tokens = []

    if len(arg_tokens) < n_args:
        raise BadGameActionError('Not enough arguments for action: '
                + str(action_type) + ', args: ' + str(arg_tokens))

    args = []

    if arg_specs:
        types_args = izip_longest(arg_specs, arg_tokens, fillvalue=arg_specs[-1])
        for (arg_type, _), token in types_args:
            if arg_type == bool:
                if token == 'True':
                    arg = True
                elif token == 'False':
                    arg = False
                else:
                    arg = None

            elif token == 'None':
                arg = None

            else:
                try:
                    arg = arg_type(token)
                except ValueError:
                    raise BadGameActionError(
                            'Could not convert argument: {0}({1})'.format(
                                str(arg_type), token))

            args.append(arg)

    return GameAction(action_type, *args)


class BadGameActionError(Exception):
    pass

class GameAction:
    """ Class that represents a game action that the client submits
    to the game server. Consists of an action type and one or more
    arguments, each of which should be representable by a string.

    Raises a ValueError if the action type is not valid or if the
    arguments don't match the action type signature.
    """
    def __init__(self, action, *args):
        self.action = action
        self.args = list(args)

        self.check_type()
        self.check_args()

    def check_type(self):
        """ Raises an InvalidGameActionError if this is not a valid game
        action.
        """
        if self.action < 0 or self.action >= len(_action_args_dict):
            raise BadGameActionError(msg='Invalid action type ({0})'.format(self.action))

    def check_args(self):
        """ Raises an BadGameActionError if there's a problem
        with the arguments.
        """
        name, n_args, unbounded, type_list = _action_args_dict[self.action]
        
        if not unbounded and len(self.args) != n_args:
            msg = 'Number of args doesn\'t match (args={0}, n_args must be {1})'.format(self.args, n_args)
            raise BadGameActionError(msg)

        elif unbounded and len(self.args) < n_args:
            msg = 'Number of args doesn\'t match (args={0}, n_args must be >= {1})'.format(self.args, n_args)
            raise BadGameActionError(msg)

        if type_list:
            # Any extra arguments must have the same type as the last argument.
            types_args = izip_longest(type_list, self.args, fillvalue=type_list[-1])
            for (arg_type, _), arg in types_args:
                bad_arg_match = type(arg) is not arg_type
                arg_is_none = arg is None
                str_unicode_error = type(arg) is str and arg_type is unicode \
                        or type(arg) is unicode and arg_type is str

                if bad_arg_match and not arg_is_none and not str_unicode_error:
                    print 'Error on this action: ' + repr(self)
                    msg = 'Argument {0} is not of type {1}'.format(arg, str(arg_type))
                    raise BadGameActionError(msg)

    def privatize(self):
        """ Re-names any information in this GameAction instance that is
        not public. For example, MERCHANT(None, 'Wall', False) becomes
        MERCHANT(None, 'Card', False). Modifies this object.
        
        This merchant-from-hand with Basilica is the only case where
        a card moves from a private zone to a hidden zone.
        """
        if self.action == MERCHANT:
            if self.args[1]:
                self.args[1] = 'Card'

    def __str__(self):
        """ Convert to string, eg. str(THINKERORLEAD) -> 'THINKERORLEAD'
        """
        return _action_args_dict[self.action][0]

    def __repr__(self):
        r = 'GameAction({0!s}, {1})'.format(self.action, ', '.join(map(repr, self.args)))
        return r
