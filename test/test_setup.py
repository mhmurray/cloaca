from cloaca.player import Player
from cloaca.gamestate import GameState
from cloaca.gtr import Game
import cloaca.message as message

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
    gs.pool = []
    
    p1.hand = []
    p2.hand = []

    gs.turn_index = 0
    gs.leader_index = 0
    gs.priority_index = 0

    gs.stack.push_frame('take_turn_stacked', p1)

    g.pump()

    return g

def two_player_lead(role):
    """ Two player game, advanced to the point where
    p1 has led the specified role with a Jack and p2 thinks.

    Based on simple_two_player().
    """
    g = simple_two_player()
    p1, p2 = g.game_state.players

    # Indicate that p1 will lead
    a = message.GameAction(message.THINKERORLEAD, False)
    g.handle(a)

    p1.hand = ['Jack']

    # p1 leads Laborer
    a = message.GameAction(message.LEADROLE, role, 1, 'Jack')
    g.handle(a)

    # p2 thinks for a Jack
    a = message.GameAction(message.FOLLOWROLE, True, 0, None)
    g.handle(a)

    a = message.GameAction(message.THINKERTYPE, True)
    g.handle(a)

    return g


def two_player_lead(role, p1_clientele=[], p2_clientele=[]):
    """ Two player game, advanced to the point where
    p1 has led the specified role with a Jack and p2 thinks.

    Optionally allowed to specify clients for each player (copies list).

    Based on simple_two_player().
    """
    g = simple_two_player()
    p1, p2 = g.game_state.players

    p1.clientele = list(p1_clientele)
    p2.clientele = list(p2_clientele)

    # Indicate that p1 will lead
    a = message.GameAction(message.THINKERORLEAD, False)
    g.handle(a)

    p1.hand = ['Jack']

    # p1 leads Laborer
    a = message.GameAction(message.LEADROLE, role, 1, 'Jack')
    g.handle(a)

    # p2 thinks for a Jack
    a = message.GameAction(message.FOLLOWROLE, True, 0, None)
    g.handle(a)

    a = message.GameAction(message.THINKERTYPE, True)
    g.handle(a)

    return g
