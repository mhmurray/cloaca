#!/usr/bin/env python

import gtr
from gamestate import GameState
from player import Player
import pprint
import logging
import sys

pp = pprint.PrettyPrinter(indent=4)
#logging.basicConfig(level=logging.DEBUG, format='%(message)s')
lg = logging.getLogger('gtr')
formatter = logging.Formatter('%(message)s')
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
lg.addHandler(ch)
lg.setLevel(logging.DEBUG)
lg.propagate = False

game = gtr.Game()
lg.error('Test game.lg is lg : ' + str(lg is gtr.lg))
game.add_player('M')
game.add_player('L')
#print repr(game)

game.init_common_piles(n_players=2)
#game.game_state.in_town_foundations = []
#print repr(game)

#game.testing_init_piles(2)
game.game_state.init_players()
game.game_state.testing_init_players()
game.test_all_get_complete_building('Stairway')
game.test_all_get_incomplete_building('Latrine')
game.test_all_get_client('Dock')
game.test_all_get_client('Senate')
game.test_set_n_in_town(0)
game.test_set_n_out_of_town(1)
#pp.pprint(vars(game))

#pp.pprint(vars(game.game_state))

game.show_public_game_state()

players = game.game_state.players

# Load the last game on any argument
if len(sys.argv) == 2:
    game.load_game()

game.run()
