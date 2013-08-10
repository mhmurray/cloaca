#!/usr/bin/env python

"""
A simple client.  Maybe this should be a class
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
  log_file.close()
  return game_state

def save_game_state(game_state, log_file_name='log_state.log'):
  """
  Save game state to file
  """
  log_file = file(log_file_name, 'w')
  pickle.dump(game_state, log_file)
  log_file.close()

def wait_for_my_turn(my_index):
  """
  Wait until this player has priority
  """
  logging.info('--> Waiting for your turn...')
  previous_priority_index = None
  priority_index = None
  # keep checking game state until it is my turn
  while my_index is not priority_index:
    game_state = get_game_state()
    priority_index = game_state.priority_index
    leader_index = game_state.leader_index
    # print info about changes to priority
    if previous_priority_index is not priority_index:
      previous_priority_index = priority_index
      # print the current game state after every change
      game = gtr.Game(game_state=get_game_state())
      game.show_public_game_state()
      

def main():

  # options:
  logging.basicConfig(level=logging.DEBUG, format='%(message)s')

  logging.info('--> Welcome to the game!')

  # add player to game
  my_name = raw_input('Enter your name: ')

  # check whether game exists, if not start a new one
  try:
    game_state = get_game_state()
    logging.info('--> Joining existing game...')  
  except IOError:
    logging.info('--> Starting a new game...')
    game_state = GameState()

  my_index = game_state.add_player(Player(name=my_name))
  save_game_state(game_state)


  # prompt player to join game when desired number of players is reached
  response = 'n'
  while response is not 'y':
    game_state = get_game_state()
    n_players = game_state.get_n_players() 
    print '--> There are {n!r} players.'.format(n=n_players)
    response = raw_input('--> Would you like to start? [y/n]: ')
    if response is 'y':
      game_state = get_game_state()

      # check whether someone else has started the game
      if not game_state.is_started:
        game = gtr.Game(game_state=game_state)
        game_state.is_started = True
        # initialize the game
        game.init_common_piles(n_players=n_players)
        game.game_state.init_players()
        save_game_state(game_state=game_state)

  wait_for_my_turn(my_index=my_index)


if __name__ == '__main__':

  main()

