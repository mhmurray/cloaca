#!/usr/bin/env python

import gtr
from gamestate import GameState
from player import Player
import pprint
import logging

pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

players = []
for i in range(1,4):
  player = Player('Player {0:d}'.format(i))
  players.append(player)

game = gtr.Game(GameState(players))
#print repr(game)

game.init_common_piles(n_players=len(players))
#print repr(game)

game.game_state.init_players()
#pp.pprint(vars(game))

#pp.pprint(vars(game.game_state))

game.show_public_game_state()


