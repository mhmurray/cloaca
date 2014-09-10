#!/usr/bin/env python

import gtr
from gamestate import GameState
from player import Player
import pprint
import logging

pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

game = gtr.Game()
game.game_state.find_or_add_player('M')
game.game_state.find_or_add_player('L')
#print repr(game)

game.init_common_piles(n_players=2)
#print repr(game)

game.game_state.testing_init_players()
game.testing_init_piles(2)
#pp.pprint(vars(game))

#pp.pprint(vars(game.game_state))

game.show_public_game_state()

players = game.game_state.players

while True:
    print
    game.show_public_game_state()
    game.print_complete_player_state(players[game.game_state.leader_index])
    game.take_turn(players[game.game_state.leader_index])
    game.game_state.increment_leader_index()
