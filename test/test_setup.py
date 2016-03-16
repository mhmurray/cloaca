from cloaca.player import Player
from cloaca.gamestate import GameState
from cloaca.gtr import Game
from cloaca.building import Building
import cloaca.card_manager as cm
import cloaca.message as message
from cloaca.zone import Zone

from sys import stderr

""" Utilities to easily set up test game states.
"""

def simple_two_player():
    """ Two-player game with nothing in hands, stockpiles,
    or common piles. Player 1 (p1) goes first.

    One frame of take_turn_stacked is pushed, and the game
    is pumped, so it's ready for the first player (p1) to 
    thinker or lead.
    """
    p1 = Player('p1')
    p2 = Player('p2')

    gs = GameState(players=['p1','p2'])
    gs.players[0] = p1
    gs.players[1] = p2

    g = Game(gs)
    g.init_common_piles(2)
    gs.pool = Zone()
    
    p1.hand = Zone()
    p2.hand = Zone()

    gs.turn_index = 0
    gs.leader_index = 0
    gs.priority_index = 0

    gs.stack.push_frame('take_turn_stacked', p1)

    g.pump()

    return g


def two_player_lead(role, clientele=[], buildings=[]):
    """ Two player game, advanced to the point where
    p1 has led the specified role with a Jack and p2 thinks.

    Optionally allowed to specify clients and buildings for each player. The
    clientele argument is an iterable of iterables, where the primary index is
    the players in order 1, 2 and each element is a list of clients that player
    should have. Likewise with the buildings argument. The buildings should be
    just the name of the foundations and will be completed with more copies of
    that foundation. For example:

        # Leg. and arch. client for p1, craftsman for p2.
        clientele = (['Bath', 'Storeroom'], ['Dock'])
        
        # Complete Fountain for p2.
        buildings = ([], ['Fountain'])

        game = two_player_lead('Craftsman', clientele, buildings)

    Adding clientele must be done before resolving the lead role action so they
    are counted. Adding buildings usually can be done in the individual test
    cases if they add static effects (eg. Archway), but the Fountain or Circus
    Maximus need to be done before the lead role action. This is also more
    convenient if you just want a static building ability active.
    """
    g = simple_two_player()
    p1, p2 = g.game_state.players

    if clientele:
        try:
            p1.clientele.set_content(cm.get_cards(clientele[0]))
            p2.clientele.set_content(cm.get_cards(clientele[1]))
        except IndexError:
            stderr.write('Failed to initialize clientele.\n')
            raise

    if buildings:
        try:
            p1_buildings, p2_buildings = buildings
        except IndexError:
            stderr.write('Failed to initialize buildings.\n')
            raise

        for p, buildings in zip([p1, p2], [p1_buildings, p2_buildings]):
            for building in buildings:
                # To complete the building we need more materials of
                # the same material, but we don't want to use the exact smae
                # card as the foundation.
                foundation = cm.get_card(building)
                others = cm.get_cards_of_material(foundation.material)
                others.remove(foundation)
                materials = others[:foundation.value]
                b = Building(foundation, None, others, None, True)
                p.buildings.append(b)
            

    # Indicate that p1 will lead
    a = message.GameAction(message.THINKERORLEAD, False)
    g.handle(a)

    p1.hand.set_content(cm.get_cards(['Jack']))

    # p1 leads Laborer
    a = message.GameAction(message.LEADROLE, role, 1, 'Jack')
    g.handle(a)

    # p2 thinks for a Jack
    a = message.GameAction(message.FOLLOWROLE, True, 0, None)
    g.handle(a)

    a = message.GameAction(message.THINKERTYPE, True)
    g.handle(a)

    return g
