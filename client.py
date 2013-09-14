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
import pickle

import gtr
import gtrutils
from player import Player
from gamestate import GameState


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
      logging.info('--> Waiting to get priority...')

  logging.info('--> You have priority!')
  game.print_complete_player_state(game_state.players[my_index])


def get_possible_zones_list(game_state, player_index):
  """ Returns (currently truncated) list of zones, prints an indexed menu """

  player = game_state.players[player_index]
  possible_zones = []
  possible_zones.append(('your camp', player.camp))
  possible_zones.append(('your hand', player.hand))
  possible_zones.append(('your buildings', player.buildings))
  possible_zones.append(('pool', game_state.pool))
  possible_zones.append(('foundations', game_state.foundations))

  # print these possiblities
  for zone_index in xrange(len(possible_zones)):
    (name, zone) = possible_zones[zone_index]
    logging.info('  [{0}] {1}'.format(zone_index, name))

  return possible_zones

def get_possible_cards_list(card_list):
  """ Returns list of cards, prints an indexed menu """

  for card_index in xrange(len(card_list)):
      logging.info('  [{0}] {1}'.format(card_index, card_list[card_index]))
  return card_list




 
def MoveACardDialog(game_state, player_index):

  # choose the source zone:
  logging.info('Move a Card: Choose the source zone:')
  possible_zones = get_possible_zones_list(game_state, player_index)
  while True:
    response_str = raw_input('--> Card Source ([q]uit, [s]tart over): ')
    if response_str in ['s', 'start over']: continue
    elif response_str in ['q', 'quit']: return ('','','')
    try:
      response_int = int(response_str)
      (name, card_source) = possible_zones[response_int]
      logging.debug('source zone = {0!s}'.format(name))
      break
    except:
      logging.info('your response was {0!s}... try again'.format(response_str))

  # choose the card
  logging.info('Move a Card: Choose the card to move:')
  possible_cards = get_possible_cards_list(card_source)
  while True:
    response_str = raw_input(
      '--> Move a Card: Please input the card name ([q]uit, [s]tart over): ')
    if response_str in ['s', 'start over']: continue
    elif response_str in ['q', 'quit']: return ('','','')
    try:
      response_int = int(response_str)
      card_name = possible_cards[response_int]
      logging.debug('card_name = {0!s}'.format(card_name))
      break
    except:
      logging.info('your response was {0!s}... try again'.format(response_str))

  # choose the destination zone:
  logging.info('Move a Card: Choose the destination zone:')
  possible_zones = get_possible_zones_list(game_state, player_index)
  while True:
    response_str = raw_input('--> Card Destination: ')
    if response_str in ['s', 'start over']: continue
    elif response_str in ['q', 'quit']: return ('','','')
    try:
      response_int = int(response_str)
      (name, card_destination) = possible_zones[response_int]
      logging.debug('source zone = {0!s}'.format(name))
      break
    except:
      logging.info('your response was {0!s}... try again'.format(response_str))

  logging.debug('attempting to move {0} from {1} to {2}'.format(card_name,
  card_source, card_destination))
  return (card_name, card_source, card_destination)

def ThinkerTypeDialog():
    logging.info('Thinking...')
    logging.error('Thinking is not implemented yet.')
    return

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
      print '--> There are {0:d} players including you.'.format(n_players)
      response = raw_input(
        '--> Would you like to start? [y/n/wait for more players] : ')
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
      game_state = get_game_state()
      # Just take the first character of the reponse, lower case.
      response_string=raw_input(
        '--> Take an action: [M]ove a card between zones, [T]hinker, [E]nd turn phase: ')
      response = response_string.lower()[0]
      if response == 'm':
        card_name, source, dest = MoveACardDialog(game_state, my_index)
        try:
          gtrutils.get_card_from_zone(card_name, source)
          gtrutils.add_card_to_zone(card_name, dest)
          save_game_state(game_state)
        except: continue

      elif response == 't':
        thinker_type = ThinkerTypeDialog()
        save_game_state(game_state)

      elif response == 'e':
        game_state.increment_priority_index()
        save_game_state(game_state)
        break
        



if __name__ == '__main__':

  main()

