import gtrutils
import card_manager
from itertools import izip, izip_longest, count
from card import Card
import json
from error import GameActionError, ParsingError

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
SERVERERROR     = 34
PRISON          = 35
TAKEPOOLCARDS   = 36

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
        
#Card = str
#Card = int
_action_args_dict = {
    REQGAMESTATE   : GTRActionSpec('reqgamestate',   (), () ),
    GAMESTATE      : GTRActionSpec('gamestate',      ( (str,  'game_state'), ), () ), 
    SETPLAYERID    : GTRActionSpec('setplayerid',    ( (int,  'id'), ), () ),
    REQJOINGAME    : GTRActionSpec('reqjoingame',    (), () ),
    JOINGAME       : GTRActionSpec('joingame',       (), () ),
    REQCREATEGAME  : GTRActionSpec('reqcreategame',  (), () ),
    CREATEGAME     : GTRActionSpec('creategame',     (), () ),
    LOGIN          : GTRActionSpec('login',          ( (str, 'session_id'), ), () ),
    REQSTARTGAME   : GTRActionSpec('reqstartgame',   (), () ),
    STARTGAME      : GTRActionSpec('startgame',      (), () ),
    REQGAMELIST    : GTRActionSpec('reqgamelist',    (), () ),
    GAMELIST       : GTRActionSpec('gamelist',       ( (str, 'game_list'), ), () ),
    SERVERERROR    : GTRActionSpec('servererror',    ( (str, 'err_msg'), ), () ),

    THINKERORLEAD  : GTRActionSpec('thinkerorlead',  ( (bool, 'do_thinker'), ), () ),
    THINKERTYPE    : GTRActionSpec('thinkertype',    ( (bool, 'for_jack'), ), () ),
    SKIPTHINKER    : GTRActionSpec('skipthinker',    ( (bool, 'skip'), ), () ),
    USELATRINE     : GTRActionSpec('uselatrine',     ( (Card, 'to_discard'), ), () ),
    USEVOMITORIUM  : GTRActionSpec('usevomitorium',  ( (bool, 'discard_all'), ), () ),
    USEFOUNTAIN    : GTRActionSpec('usefountain',    ( (bool, 'use_fountain'), ), () ),
    USESENATE      : GTRActionSpec('usesenate',      (), (Card, 'jacks') ),
    BARORAQUEDUCT  : GTRActionSpec('baroraqueduct',  ( (bool, 'bar_first'), ), () ),
    PATRONFROMPOOL : GTRActionSpec('patronfrompool', ( (Card, 'from_pool'), ), () ),
    PATRONFROMDECK : GTRActionSpec('patronfromdeck', ( (bool, 'from_deck'), ), () ),
    PATRONFROMHAND : GTRActionSpec('patronfromhand', ( (Card, 'from_hand'), ), () ),
    GIVECARDS      : GTRActionSpec('givecards',      (), (Card, 'cards') ),
    USESEWER       : GTRActionSpec('usesewer',       (), (Card, 'c1') ),
    LEGIONARY      : GTRActionSpec('legionary',      (), (Card, 'from_hand') ),
    TAKEPOOLCARDS  : GTRActionSpec('takepoolcards',  (), (Card, 'from_pool') ),
    PRISON         : GTRActionSpec('prison',         ( (Card, 'building_to_steal'), ), () ),
    LABORER        : GTRActionSpec('laborer',
        ( (Card, 'from_hand'), (Card, 'from_pool') ), () ),

    ARCHITECT      : GTRActionSpec('architect',
        (   (Card, 'building'), (Card, 'material'),
            (str, 'site') ), () ),

    CRAFTSMAN      : GTRActionSpec('craftsman',
        (   (Card, 'building'), (Card, 'material'), (str, 'site') ), () ),

    MERCHANT       : GTRActionSpec('merchant',
        (   (Card, 'from_stockpile'), (Card, 'from_hand'), (bool, 'from_deck') ), () ),

    LEADROLE       : GTRActionSpec('leadrole',
        (   (str, 'role'), (int, 'n_actions'), (Card, 'c1') ), (Card, 'cards') ),

    FOLLOWROLE     : GTRActionSpec('followrole',
        (   (bool, 'think'), (int, 'n_actions'), (Card, 'c1') ), (Card, 'cards') ),

    FOUNTAIN       : GTRActionSpec('fountain',
        (   (bool, 'skip'), (Card, 'building'),
            (Card, 'material'), (str, 'site') ), () ),

    STAIRWAY       : GTRActionSpec('stairway',
        (   (Card, 'building'), (Card, 'material') ), () ),
    }


class Command(object):
    """Command passed to the game server or client.

    This is a GameAction object and the id of the game it's
    intended for.
    """
    def __init__(self, game, action):
        if game is None:
            self.game = game
        else:
            try:
                self.game = int(game)
            except ValueError:
                raise GameActionError('Game id must be an integer or None: '+str(game))

        self.action = action

        if type(self.action) is not GameAction:
            raise TypeError('Action must be a GameAction object: '+str(action)+
                    '('+str(type(action))+')')

    def to_json(self):
        """Return this action converted to a JSON string.
        """
        def convert(o):
            if type(o) is Card:
                return o.ident
            else:
                return o.__dict__

        return json.dumps(self, default=convert)

    @staticmethod
    def from_json(s):
        """Parse a JSON string and return a Command object.

        Raises ParsingError if s is not a valid command object
        or is invalid JSON.
        """
        try:
            d = json.loads(s)
        except ValueError:
            raise ParsingError('Failed to parse JSON: ' + s)

        try:
            game, action_dict = d['game'], d['action']
        except KeyError:
            raise ParsingError('Failed to decode Command object from JSON: '+s)

        try:
            action, args = action_dict['action'], action_dict['args']
        except KeyError:
            raise ParsingError('Failed to decode GameAction when'
                    'parsing Command from JSON')

        return Command(game, GameAction(action, *args))


class GameAction(object):
    """ Class that represents a game action that the client submits
    to the game server. Consists of an action type and one or more
    arguments, each of which should be representable by a string.

    Raises a GameActionError if the action type is not valid or if the
    arguments don't match the action type signature.
    """
    def __init__(self, action, *args):
        self.action = action
        self.args = list(args)

        self.check_type()
        self.check_args()
        self.convert_args()

    def check_type(self):
        """ Raises an InvalidGameActionError if this is not a valid game
        action.
        """
        if self.action < 0 or self.action >= len(_action_args_dict):
            raise GameActionError('Invalid action type ({0})'.format(self.action))

    def check_args(self):
        """ Raises an GameActionError if there's a problem
        with the arguments.
        """
        spec = _action_args_dict[self.action]
        
        if not spec.has_extended and len(self.args) != spec.n_req_args:
            raise GameActionError(
                'Number of args doesn\'t match (args={0}, n_args must be {1})'
                .format(self.args, spec.n_req_args))

        elif spec.has_extended and len(self.args) < spec.n_req_args:
            raise GameActionError(
                'Number of args doesn\'t match (args={0}, n_args must be >= {1})'
                .format(self.args, n_args))

        # Regular args
        for i, arg, (_type,name) in izip(count(), self.args, spec.required_arg_specs):
            card_arg_match = _type is Card and type(arg) is int
            bad_arg_match = type(arg) is not _type
            arg_is_none = arg is None
            str_unicode_error = type(arg) is str and _type is unicode \
                    or type(arg) is unicode and _type is str

            if bad_arg_match and not arg_is_none and not str_unicode_error and not card_arg_match:
                raise GameActionError(
                    'Argument {0} ("{1}"), {2} doesn\'t match type ({3} != {4})'
                    .format(i, name, str(arg), str(_type), str(type(arg))))

        # Extended args
        for i, arg in izip(count(spec.n_req_args), self.args[spec.n_req_args:]):
            _type, name = spec.extended_arg_spec

            card_arg_match = _type is Card and type(arg) is int
            bad_arg_match = type(arg) is not _type
            arg_is_none = arg is None
            str_unicode_error = type(arg) is str and _type is unicode \
                    or type(arg) is unicode and _type is str

            if bad_arg_match and not arg_is_none and not str_unicode_error and not card_arg_match:
                raise GameActionError(
                    'Argument {0} ("{1}"), {2} doesn\'t match type ({3} != {4})'
                    .format(i, name, str(arg), str(_type), str(type(arg))))


    def convert_args(self):
        """Convert the args that are represented by other types.

        Card objects are transmited as ints.

        Raise GameActionError if the argument can't be converted.

        Args:
        action -- int, with symbolic representation found in message.py.
        args -- sequence, with type of items found in message.py
        """
        try:
            spec = _action_args_dict[self.action]
        except KeyError:
            raise Exception('Invalid action: ' + str(action))

        def parse_arg(type_, token, name):
            """Converts token to type type_.
            
            This includes special cases for some argument types,
            such as Card, bool, and NoneType.
            """
            if type_ is Card and token is not None and type(token) is not Card:
                try:
                    arg = Card(int(token))
                except ValueError:
                    raise GameActionError(
                        'Error converting "{0}" argument: {1} token: "{2}"'
                        .format(name, str(type_), token))

                return arg

            else:
                return token


        req_tokens = self.args[:spec.n_req_args]
        req_args = []

        for i, tok, (typ, name) in izip(count(), req_tokens, spec.required_arg_specs):
            try:
                arg = parse_arg(typ, tok, name)
            except GameActionError, e:
                # If we failed in parse_arg, message can be appended for details
                raise
                #raise GameActionError(
                #    'Could not convert argument {0}. '.format(i) + e.message)

            req_args.append(arg)


        extended_tokens = self.args[spec.n_req_args:]
        extended_args = []
        
        for i, tok in izip(count(spec.n_req_args), extended_tokens):
            typ, name = spec.extended_arg_spec
            try:
                arg = parse_arg(typ, tok, name)
            except GameActionError, e:
                # If we failed in parse_arg, message can be appended for details
                raise GameActionError(
                    'Could not convert argument {0}. '.format(i) + e.message)

            extended_args.append(arg)

        self.args = req_args + extended_args


    def __str__(self):
        """ Convert to string, eg. str(THINKERORLEAD) -> 'THINKERORLEAD'
        """
        return _action_args_dict[self.action].name

    def __repr__(self):
        r = 'GameAction({0!s}, {1})'.format(self.action, ', '.join(map(repr, self.args)))
        return r

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def to_json(self):
        """Return this action converted to a JSON string.
        """
        def convert(o):
            if type(o) is Card:
                return o.ident
            else:
                return o.__dict__

        return json.dumps(self, default=convert)

    @staticmethod
    def from_json(s):
        """Parse the JSON string and return a GameAction object.

        Raise ParsingError if the string is invalid JSON.

        Raise ParsingError if the JSON is correctly decoded, but represents
        an invalid GameAction object.
        """
        try:
            d = json.loads(s)
        except ValueError:
            raise ParsingError('Failed to parse JSON: ' + s)

        try:
            action, args = d['action'], d['args']
        except KeyError:
            raise ParsingError('Failed to decode Command object from JSON: '+s)

        return GameAction(action, *args)
