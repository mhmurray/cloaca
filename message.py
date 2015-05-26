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

# A dictionary of the number of arguments for each action type
# and their signature.
# If the number is not limited, but has a minimum, it will be negative
# eg. -3 means there are at least 3 arguments, but maybe more.
# The signature is a tuple of tuples with (type, string) entries,
# eg. 'int n_actions', or 'Card from_pool', though note that
# "Card" is not a type. Cards are just strings.
Card = str
_action_args_dict = {
        THINKERORLEAD  : ('thinkerorlead', 1, ( (bool, 'do_thinker'), ) ),
        USELATRINE     : ('uselatrine', 1, ( (Card, 'to_discard'), ) ),
        USEVOMITORIUM  : ('usevomitorium', 1, ( (bool, 'discard_all'), ) ),
        PATRONFROMPOOL : ('patronfrompool', 1, ( (Card, 'from_pool'), ) ),
        BARORAQUEDUCT  : ('baroraqueduct', 1, ( (bool, 'bar_first'), ) ),
        PATRONFROMDECK : ('patronfromdeck', 1, ( (bool, 'from_deck'), ) ),
        PATRONFROMHAND : ('patronfromhand', 1, ( (Card, 'from_hand'), ) ),
        USEFOUNTAIN    : ('usefountain', 1, ( (bool, 'use_fountain'), ) ),
        FOUNTAIN       : ('fountain', 4, ( (bool, 'skip'), (Card, 'building'), (Card, 'material'), (Card, 'site') ) ),
        LEGIONARY      : ('legionary', -1, ( (Card, 'from_hand'), ) ),
        GIVECARDS      : ('givecards', -1, ( (Card, 'cards'), ) ),
        THINKERTYPE    : ('thinkertype', 1, ( (bool, 'for_jack'), ) ),
        SKIPTHINKER    : ('skipthinker', 1, ( (bool, 'skip'), ) ),
        USESEWER       : ('usesewer', -1, ( (Card, 'c1'), ) ),
        USESENATE      : ('usesenate', 1, ( (bool, 'use_senate'), ) ),
        LABORER        : ('laborer', 2, ( (Card, 'from_hand'), (Card, 'from_pool') ) ),
        STAIRWAY       : ('stairway', 4, ( (str, 'player'), (Card, 'building'), (Card, 'material'), (bool, 'from_pool') ) ),
        ARCHITECT      : ('architect', 4, ( (Card, 'building'), (Card, 'material'), (Card, 'site'), (bool, 'from_pool') ) ),
        CRAFTSMAN      : ('craftsman', 3, ( (Card, 'building'), (Card, 'material'), (Card, 'site') ) ),
        MERCHANT       : ('merchant', 3, ( (Card, 'from_stockpile'), (Card, 'from_hand'), (bool, 'from_deck') ) ),
        LEADROLE       : ('leadrole', -3, ( (str, 'role'), (int, 'n_actions'), (Card, 'c1') ) ),
        FOLLOWROLE     : ('followrole', -3, ( (bool, 'think'), (int, 'n_actions'), (Card, 'c1') ) ),
        }

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
            raise ValueError(msg='Invalid action type ({0})'.format(self.action))

    def check_args(self):
        """ Raises an InvalidGameActionArgsError if there's a problem
        with the arguments.
        """
        name, n_args, type_list = _action_args_dict[self.action]
        
        if n_args >= 0 and len(self.args) != n_args:
            msg = 'Number of args doesn\'t match ({0} != {1})'.format(self.args, n_args)
            raise ValueError(msg)
        elif n_args < 0 and len(self.args) < abs(n_args):
            msg = 'Number of args doesn\'t match ({0} < {1})'.format(self.args, -1*n_args)
            raise ValueError(msg)

        # Any extra arguments must have the same type as the last argument.
        for (arg_type, _), arg in izip_longest(type_list, self.args, fillvalue=type_list[-1]):
            if type(arg) is not arg_type and arg is not None:
                msg = 'Argument {0} is not of type {1}'.format(arg, str(arg_type))
                raise ValueError(msg)

    def __str__(self):
        """ Convert to string, eg. str(THINKERORLEAD) -> 'THINKERORLEAD'
        """
        return _action_args_dict[self.action][0]


### Client interface ###
# def ThinkerOrLeadDialog(self): bool thinker_or_lead
# def UseLatrineDialog(self): Card card_to_discard (or None)
# def UseVomitoriumDialog(self): bool discard_all
# def PatronFromPoolDialog(self): Card card_from_pool
# def PatronFromDeckDialog(self): bool 
# def PatronFromHandDialog(self): Card card_from_hand
# def UseFountainDialog(self): bool
# def FountainDialog(self): (bool skip, Card building, Card material, Card site)
# def LegionaryDialog(self): Card card_from_hand
# def ThinkerTypeDialog(self): bool
# def UseSewerDialog(self): list<Card> cards_to_move
# def UseSenateDialog(self): bool
# def LaborerDialog(self): (Card from_hand, Card from_pool)
# def StairwayDialog(self): (string player_name, Card building, Card material, bool get_mat_from_pool)
# def ArchitectDialog(self): (Card building, Card material, Card site, bool from_pool)
# def CraftsmanDialog(self): (Card building, Card material, Card site)
# def MerchantDialog(self): (Card from_stockpile, Card from_hand, bool from_deck)
# def LeadRoleDialog(self): (string role_led, int n_actions, Card c1, Card c2, ...)
# def FollowRoleDialog(self): (int n_actions, Card c1, Card c2, ...) (multiple from Petition, Palace)

### Internal ###
# def SelectRoleDialog(self, role=None, unselectable=None,
# def PetitionDialog(self, unselectable = None):
