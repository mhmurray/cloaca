#!/usr/bin/env python

"""
A simple client.
10 Aug 2013 Starting with pickle -- AGS
"""


import time
import json
import glob
import pickle
import sys
import logging

import gtr
from player import Player
from gamestate import GameState
import pickle


def get_game_state(log_file_name='log_state.log'):
  """
  Return saved game state from file
  """
  log_file = file(log_file_name, 'r')
  game_state = pickle.load(log_file)
  return game_state

def save_game_state(game_state, log_file_name='log_state.log'):
  """
  Save game state to file
  """
  log_file = file(log_file_name, 'w')
  pickle.dump(game_state, log_file)
  log_file.close()



def main():

  # options:
  logging.basicConfig(level=logging.DEBUG, format='%(message)s')

  logging.info('--> Welcome to the game!')

  try:
    game_state = get_game_state()
    logging.info('--> Joining existing game...')  

  except IOError:
    logging.info('--> Starting a new game...')
    game_state = GameState()

  name = raw_input('Enter your name: ')
  player = Player(name=name)
  game_state.add_player(player)
  save_game_state(game_state)

  response = 'n'
  while response is 'n':
    game_state = get_game_state()
    n_players = game_state.get_n_players() 
    print '--> There are {n!r} players.'.format(n=n_players)
    response = raw_input('--> Would you like to start? [y/n]: ')
    if response is 'q':
      return

  game = gtr.Game(game_state=game_state)
  game.init_common_piles(n_players=n_players)
  game.game_state.init_players()

  test_state = game.game_state
  print test_state
  game.show_public_game_state()

  save_game_state(game_state)


if __name__ == '__main__':
    main()

