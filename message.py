import gtrutils
import card_manager
from itertools import izip, izip_longest, count

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
#
#     <action> : (  <name>,  <n_required_args>,
#                   ( (<arg1_type>, <arg1_name>), (<arg2_type>, <arg2_name>) ),
#                   (<extra_args_type>, extra_args_name>)
#                 )
#
# eg. ('leadrole', 3, ...) means there are at least 3
# required arguments, but maybe more are provided.
# The signature is a tuples of duples plus one extra duple with (type, string) entries,
# eg. "(int, 'n_actions')", or "(Card, 'from_pool')", though note that
# "Card" is not a type. Cards are just strings, renamed for clarity
# The tuple of duples, listed first, is the required arguments.
# The extra duple is the signature for the unlimited number of extra arguments.
# If extra arguments are not allowed, this duple will be empty.
# The action name ('laborer') and the argument signature names ('from_pool') aren't
# critical; they're just for reporting errors and logging.
#
# Examples:
#
# Action with fixed arguments. LABORER requries a card from hand and a card
# from the pool (either of which can be None). There are no extra args.
#
# LABORER  : ('laborer', 2, ( (Card, 'from_hand'), (Card, 'from_pool') ), ())
#
# Action with extendable arguments. LEADROLE requires 3 arguments: a role to be led,
# the number of actions to perform (eg. with Palace), and at least one card to lead with.
# Extra cards are allowed, though, since you could Petition, or use the Palace to play
# multiple cards.
# 
# LEADROLE  : ('leadrole', 3, 
#              ( (str, 'role_led'), (int, 'n_actions'), (Card, 'c1') ),
#              (Card, 'extra_lead_cards') )
#
# Some actions have no arguments at all, and all signature tuples will be empty.
# There are actions that have only optional extra arguments. LEGIONARY can demand
# multiple cards, but zero is also allowed. In this case, the number of required
# args will be 0 and the extra args signature is used for all arguments.
#
# LEGIONARY  : ('legionary', 0, 
#              (),
#              (Card, 'cards_demanded') )
#
# 
#
#
class GTRActionSpec(object):
    """Contains the specs for a GTRProtocol message.
    """

    def __init__(self, name, req_arg_specs, extended_arg_spec):
        self.name = name
        self.n_req_args = len(req_arg_specs)
        self.required_arg_specs = req_arg_specs
        self.extended_arg_spec = extended_arg_spec
        self.has_extended = bool(extended_arg_spec)
        
Card = str
_action_args_dict = {
    REQGAMESTATE   : GTRActionSpec('reqgamestate',   (), () ),
    GAMESTATE      : GTRActionSpec('gamestate',      ( (str,  'game_state'), ), () ),
    SETPLAYERID    : GTRActionSpec('setplayerid',    ( (int,  'id'), ), () ),
    REQJOINGAME    : GTRActionSpec('reqjoingame',    ( (int, 'game_id'), ), () ),
    JOINGAME       : GTRActionSpec('joingame',       ( (int, 'game_id'), ), () ),
    REQCREATEGAME  : GTRActionSpec('reqcreategame',  (), () ),
    CREATEGAME     : GTRActionSpec('creategame',     (), () ),
    LOGIN          : GTRActionSpec('login',          ( (str, 'user_name'), ), () ),
    REQSTARTGAME   : GTRActionSpec('reqstartgame',   (), () ),
    STARTGAME      : GTRActionSpec('startgame',      (), () ),
    REQGAMELIST    : GTRActionSpec('reqgamelist',    (), () ),
    GAMELIST       : GTRActionSpec('gamelist',       ( (str, 'game_list'), ), () ),

    THINKERORLEAD  : GTRActionSpec('thinkerorlead',  ( (bool, 'do_thinker'), ), () ),
    THINKERTYPE    : GTRActionSpec('thinkertype',    ( (bool, 'for_jack'), ), () ),
    SKIPTHINKER    : GTRActionSpec('skipthinker',    ( (bool, 'skip'), ), () ),
    USELATRINE     : GTRActionSpec('uselatrine',     ( (Card, 'to_discard'), ), () ),
    USEVOMITORIUM  : GTRActionSpec('usevomitorium',  ( (bool, 'discard_all'), ), () ),
    USEFOUNTAIN    : GTRActionSpec('usefountain',    ( (bool, 'use_fountain'), ), () ),
    USESENATE      : GTRActionSpec('usesenate',      ( (bool, 'use_senate'), ), () ),
    BARORAQUEDUCT  : GTRActionSpec('baroraqueduct',  ( (bool, 'bar_first'), ), () ),
    PATRONFROMPOOL : GTRActionSpec('patronfrompool', ( (Card, 'from_pool'), ), () ),
    PATRONFROMDECK : GTRActionSpec('patronfromdeck', ( (bool, 'from_deck'), ), () ),
    PATRONFROMHAND : GTRActionSpec('patronfromhand', ( (Card, 'from_hand'), ), () ),
    GIVECARDS      : GTRActionSpec('givecards',      (), (Card, 'cards') ),
    USESEWER       : GTRActionSpec('usesewer',       (), (Card, 'c1') ),
    LEGIONARY      : GTRActionSpec('legionary',      (), (Card, 'from_hand') ),
    LABORER        : GTRActionSpec('laborer',
        ( (Card, 'from_hand'), (Card, 'from_pool') ), () ),

    ARCHITECT      : GTRActionSpec('architect',
        (   (Card, 'building'), (Card, 'material'),
            (Card, 'site'), (bool, 'from_pool') ), () ),

    CRAFTSMAN      : GTRActionSpec('craftsman',
        (   (Card, 'building'), (Card, 'material'), (Card, 'site') ), () ),

    MERCHANT       : GTRActionSpec('merchant',
        (   (Card, 'from_stockpile'), (Card, 'from_hand'), (bool, 'from_deck') ), () ),

    LEADROLE       : GTRActionSpec('leadrole',
        (   (str, 'role'), (int, 'n_actions'), (Card, 'c1') ), (Card, 'cards') ),

    FOLLOWROLE     : GTRActionSpec('followrole',
        (   (bool, 'think'), (int, 'n_actions'), (Card, 'c1') ), (Card, 'cards') ),

    FOUNTAIN       : GTRActionSpec('fountain',
        (   (bool, 'skip'), (Card, 'building'),
            (Card, 'material'), (Card, 'site') ), () ),

    STAIRWAY       : GTRActionSpec('stairway',
        (   (str, 'player'), (Card, 'building'),
            (Card, 'material'), (bool, 'from_pool') ), () ),
    }

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
        action_type_str = action_tokens[0]
    except (IndexError, TypeError):
        raise BadGameActionError('Invalid action format: ' + action_string)

    try:
        action_type = int(action_type_str)
    except ValueError:
        raise BadGameActionError('Invalid action value: ' + action_type_str)

    try:
        spec = _action_args_dict[action_type]
    except KeyError:
        raise Exception('Action value out of range: ' + str(action_type))

    if 0:
        try:
            n_args, extras_allowed, arg_specs = action_spec[1:4]
        except IndexError:
            raise Exception('Missing # args spec for action: ' + str(action_type))

    # Split only to the number of allowed actions.
    # Some GameActions (GAMESTATE) contain commas, and rely on n_args.
    # Actions with 0 required args and more optional args (GIVECARDS)
    # should have a blank argument: "9,". However, if only the game
    # action is specified, eg. "9", we can infer that there are no arguments
    # defensively (or they are None).
    try:
        arg_tokens_presplit = action_tokens[1]
    except IndexError:
        arg_tokens_presplit = ''

    if arg_tokens_presplit and (spec.n_req_args or spec.has_extended):
        n_split = -1 if spec.has_extended else spec.n_req_args-1
        arg_tokens = action_tokens[1].split(',', n_split)
    else:
        arg_tokens = [] # default split if no req. or optional args.

    if len(arg_tokens) < spec.n_req_args:
        raise BadGameActionError(
            'Not enough arguments ({0} required) for action: {1}: {2}'
            .format(spec.name, spec.n_req_args, str(arg_tokens)))
    # Can't check for extra args, because there's no way to distinguish
    # this from an argument with commas.

    def parse_arg(_type, token, name):
        """Converts token to type _type."""
        if _type == bool:
            if token == 'True': arg = True
            elif token == 'False': arg = False
            else:
                raise BadGameActionError('Boolean argument expected. Received' + token)

        elif token == 'None':
            arg = None

        else:
            try:
                arg = _type(token)
            except ValueError:
                raise BadGameActionError(
                    'Error converting "{0}" argument: {1}({2})'
                    .format(name, str(_type), token))

        return arg



    req_tokens = arg_tokens[:spec.n_req_args]
    req_args = []

    for i, tok, (typ, name) in izip(count(), req_tokens, spec.required_arg_specs):
        try:
            arg = parse_arg(typ, tok, name)
        except BadGameActionError, e:
            # If we failed in parse_arg, message can be appended for details
            raise BadGameActionError(
                'Could not convert argument {0}. '.format(i) + e.message)

        req_args.append(arg)


    extended_tokens = arg_tokens[spec.n_req_args:]
    extended_args = []
    
    for i, tok in izip(count(spec.n_req_args), extended_tokens):
        typ, name = spec.extended_arg_spec
        try:
            arg = parse_arg(typ, tok, name)
        except BadGameActionError, e:
            # If we failed in parse_arg, message can be appended for details
            raise BadGameActionError(
                'Could not convert argument {0}. '.format(i) + e.message)

        extended_args.append(arg)

    return GameAction(action_type, *(req_args + extended_args))


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
        spec = _action_args_dict[self.action]
        
        if not spec.has_extended and len(self.args) != spec.n_req_args:
            raise BadGameActionError(
                'Number of args doesn\'t match (args={0}, n_args must be {1})'
                .format(self.args, spec.n_req_args))

        elif spec.has_extended and len(self.args) < spec.n_req_args:
            raise BadGameActionError(
                'Number of args doesn\'t match (args={0}, n_args must be >= {1})'
                .format(self.args, n_args))

        # Regular args
        for i, arg, (_type,name) in izip(count(), self.args, spec.required_arg_specs):
            bad_arg_match = type(arg) is not _type
            arg_is_none = arg is None
            str_unicode_error = type(arg) is str and _type is unicode \
                    or type(arg) is unicode and _type is str

            if bad_arg_match and not arg_is_none and not str_unicode_error:
                raise BadGameActionError(
                    'Argument {0} ("{1}"), {2} doesn\'t match type ({3} != {4})'
                    .format(i, name, str(arg), str(_type), str(type(arg))))

        # Extended args
        for i, arg in izip(count(spec.n_req_args), self.args[spec.n_req_args:]):
            _type, name = spec.extended_arg_spec

            bad_arg_match = type(arg) is not _type
            arg_is_none = arg is None
            str_unicode_error = type(arg) is str and _type is unicode \
                    or type(arg) is unicode and _type is str

            if bad_arg_match and not arg_is_none and not str_unicode_error:
                raise BadGameActionError(
                    'Argument {0} ("{1}"), {2} doesn\'t match type ({3} != {4})'
                    .format(i, name, str(arg), str(_type), str(type(arg))))

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
        return _action_args_dict[self.action].name

    def __repr__(self):
        r = 'GameAction({0!s}, {1})'.format(self.action, ', '.join(map(repr, self.args)))
        return r

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
