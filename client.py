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
    time.sleep(0.1)
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
  response = '-'
  while True:
    if response is 'y':
      break
    elif response is 'n':
      logging.warn('Goodbye!')
      exit()
    else:
      game_state = get_game_state()
      n_players = game_state.get_n_players() 
      print '--> There are {0:d} players.'.format(n_players)
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

  while True:
    time.sleep(0.1)
    wait_for_my_turn(my_index=my_index)
    # It is now my turn and the game state was just printed
    while True:
      # Just take the first character of the reposnse, lower case.
      response_string=raw_input(
        '--> Take an action: [M]ove a card between zones, [T]hinker: ')
      response = response_string.lower()[0]
      if response == 'm':
        card_name, source, dest = MoveACardDialog()
      elif response == 't':
        thinker_type = ThinkerTypeDialog()

def MoveACardDialog():
  while True:
    response_str = raw_input(
      '--> Move a Card: Please input the card name ([q]uit, [s]tart over): ')
    if response_str in ['q', 'quit']: continue
    elif response_str in ['s', 'start over']: return ('','','')
    else: card_name = response_str.lower()

    response_str = raw_input('--> Card Source: ')
    if response_str in ['q', 'quit']: continue
    elif response_str in ['s', 'start over']: return ('','','')
    else: card_source = response_str.lower()

    response_str = raw_input('--> Card Destination: ')
    if response_str in ['q', 'quit']: continue
    elif response_str in ['s', 'start over']: return ('','','')
    else: card_destination = response_str.lower()

  return (card_name, card_source, card_destination)




if __name__ == '__main__':

  main()

