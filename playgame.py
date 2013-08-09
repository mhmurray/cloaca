#!/usr/bin/env python

import gtr
from gamestate import GameState
from player import Player
import pprint

pp = pprint.PrettyPrinter(indent=4)

players = []
for i in range(1,4):
  player = Player('Player {0:d}'.format(i))
  players.append(player)

print 'Starting a game...'
game = gtr.Game(GameState(players))
#print repr(game)

print 'Initializing the game...'
game.init_common_piles(len(players))
#print repr(game)

print 'Initializing the players...'
game.game_state.init_players()
#pp.pprint(vars(game))

#pp.pprint(vars(game.game_state))

game.show_public_game_state()


