from cloaca.player import Player
from cloaca.game import Game
from cloaca.building import Building
import cloaca.card_manager as cm
import cloaca.message as message
from cloaca.zone import Zone

import re
from sys import stderr
from uuid import uuid4
from itertools import izip_longest


class TestDeck(object):
    """Utility class for testing that makes it easy to pick specific cards.

    The problem with using card names is that there are multiple copies of
    each card, so specifying the name isn't enough to make an unambiguous
    actions. Cards are labeled with an <ident> parameter that is simply
    an integer. This is hard to remember, though. Which card is 102?

    For regular game interactions, this rarely matters, because cards
    are always dealt with via one level of reference, and only the names
    matter. The game doesn't care which one of the 3 Catacombs is finished,
    the game is still over.

    In testing, though, one wants to populate a game state with a specific
    set of cards and then use assert* methods to test that they made it
    to their proper end points. Acquiring and maintaining a permanent
    reference to a card is a pain, though. Much moreso when tracking
    several cards.

    To solve this, the TestDeck class allows specific Card objects to be accessed
    by name and index. This is called the *enumerated pull*.

        td = TestDeck()
        g = Game()
        ...
        g.pool.set_content([td.shrine0, td.shrine1, td.school0])
        g.players[0].hand.set_content([td.road5, td.school6])

        assertIn(td.shrine1, g.pool)

    Additionally, one might want to create a test deck and pull non-specific
    cards from it, but then be sure not to pull the same cards on subsequent
    pulls. For instance, we want a player to have a completed building, but
    out of cards we don't use later. This is called the *anonymous pull*.

        td = TestDeck()
        b = Building(td.shrine, 'Brick', materials=[td.shrine, td.academy], complete=True)

        # Two of the three shrines are used.
        shrine = td.shrine0
        shrine = td.shrine1 # raises AttributeError

    There should be no need to access an anonymously pulled card again, because the card
    could have been pulled with the enumerated pull.

    The cards are treated as attributes for quick typing, but this means developers
    must not define methods with the same name as any card, including Jack.
    
    Card names are case insensitive, so TestDeck().AqUeduCt2 is valid. The spaces
    in building names that have them should be removed, eg. TestDeck().CircusMaximus
    """

    def __init__(self):
        # Dictionary of (<cardname> : <n_anon_pulls>)
        self._anon_pulls = {}

    def __getattr__(self, attr):
        try:
            return object.__getattr__(attr)
        except AttributeError:
            try:
                return self.card(attr)
            except AttributeError:
                print 'No such card: '+attr
                raise

    def card(self, s):
        """Gets the card with name like 'shrine2'.

        Invalid name formats are an AttributeError.
        """
        match = re.match('(.*?)([0-9]*)$', s)
        if match is None:
            raise AttributeError('Invalid card pull: ' + s)
        else:
            groups = match.groups()
            if len(groups) != 2:
                raise AttributeError('Invalid card pull: ' +s)
            else:
                try:
                    index = int(match.group(2))
                except ValueError:
                    index = None

            name = match.group(1)
            if 'ludus' in name.lower():
                name = 'Ludus Magna'
            elif 'maximus' in name.lower():
                name = 'Circus Maximus'
            else:
                name = name[0].upper() + name[1:].lower()

            try:
                pulls = self._anon_pulls[name]
            except KeyError:
                pulls = 0

            n_tot = int(cm.get_card_dict(name)['card_count'])
            if name.lower() == 'jack':
                n_tot = 6

            max_index = n_tot - pulls - 1

            if index is None:
                self._anon_pulls[name] = pulls+1

                # Get anonymous cards starting from the highest index
                return cm.get_card(name, max_index)
            else:
                return cm.get_card(name, index)



def simple_two_player():
    """Two-player game with nothing in hands, stockpiles,
    or common piles. Player 1 (p1) goes first.

    One frame of take_turn_stacked is pushed, and the game
    is pumped, so it's ready for the first player (p1) to 
    thinker or lead.
    """
    return simple_n_player(2)


def simple_n_player(n):
    """N-player game with nothing in hands, stockpiles,
    or common piles. Player 1 (p1) goes first.

    One frame of take_turn_stacked is pushed, and the game
    is pumped, so it's ready for the first player (p1) to 
    thinker or lead.
    """
    g = Game()

    players = ['p{0:d}'.format(i+1) for i in range(n)]

    for p in players:
        uid = uuid4().int
        g.add_player(uid, p)

    g.controlled_start()

    return g


def n_player_lead(n, role, clientele=[], buildings=[], deck=None, follow=False):
    """N player game, advanced to the point where
    p1 has led the specified role with a Jack and p2 through p<n> think.

    Use follow=True to have the other players follow the action.

    Optionally allowed to specify clients and buildings for each player. The
    clientele argument is an iterable of iterables, where the primary index is
    the players in order 1, 2, 3... and each element is a list of clients that player
    should have. Likewise with the buildings argument. The buildings should be
    just the name of the foundations and will be completed without any material
    cards. For example:

        # Leg. and arch. client for p1, craftsman for p2.
        clientele = (['Bath', 'Storeroom'], ['Dock'])
        
        # Complete Fountain for p2.
        buildings = ([], ['Fountain'])

        game = n_player_lead(2, 'Craftsman', clientele, buildings)

    Adding clientele must be done before resolving the lead role action so they
    are counted. Adding buildings usually can be done in the individual test
    cases if they add static effects (eg. Archway), but the Fountain or Circus
    Maximus need to be done before the lead role action. This is also more
    convenient if you just want a static building ability active.

    Optionally takes a TestDeck object so the foundations can be taken from
    the deck. The building names can also use the TestDeck format, eg.
    "shrine2" to get a specific card as the foundation.
    """
    #print clientele, buildings, role
    g = simple_n_player(n)
    p1 = g.players[0]
    others = g.players[1:]

    if deck is None:
        d = TestDeck()
    else:
        d = deck

    for p, p_clientele, p_buildings in \
            izip_longest(g.players, clientele, buildings, fillvalue=[]):

        p.clientele.set_content([getattr(d, c.replace(' ','')) for c in p_clientele])

        for b in p_buildings:
            foundation = getattr(d, b)
            b = Building(foundation, foundation.material, [], None, True)
            p.buildings.append(b)
            

    # Indicate that p1 will lead
    a = message.GameAction(message.THINKERORLEAD, False)
    g.handle(a)

    p1.hand.set_content([d.jack0])

    a = message.GameAction(message.LEADROLE, role, 1, d.jack0)
    g.handle(a)

    # other players think for a Jack
    for i, p in enumerate(others):
        if follow:
            jack = getattr(d, 'jack'+str(i+1))
            p.hand.set_content([jack])
            a = message.GameAction(message.FOLLOWROLE, 1, jack)
            g.handle(a)

        else:
            a = message.GameAction(message.FOLLOWROLE, 0)
            g.handle(a)
            a = message.GameAction(message.THINKERTYPE, True)
            g.handle(a)

    return g

def two_player_lead(role, clientele=[], buildings=[], deck=None, follow=False):
    return n_player_lead(2, role, clientele, buildings, deck, follow)
