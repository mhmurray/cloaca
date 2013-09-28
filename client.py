#!/usr/bin/env python

"""
A simple client.  Maybe this should be a class
10 Aug 2013 Starting with pickle -- AGS
"""


import os
import glob
import time
import json
import glob
import pickle
import sys
import logging
import pickle
import collections
import card_manager

import gtr
import gtrutils
from player import Player
from gamestate import GameState


class StartOverException(Exception):
  pass

class CancelDialogException(Exception):
  pass

def get_previous_game_state(log_file_prefix='log_state'):
  """
  Return saved game state from file
  """
  log_files = glob.glob('{0}*.log'.format(log_file_prefix))
  log_files.sort()
  #for log_file in log_files: # print all log file names, for debugging
  #  logging.debug(log_file)

  if not log_files:
    return None

  log_file_name = log_files[-1] # last element
  time_stamp = log_file_name.split('_')[-1].split('.')[0:1]
  time_stamp = '.'.join(time_stamp)
  asc_time = time.asctime(time.localtime(float(time_stamp)))
  #logging.debug('Retrieving game state from {0}'.format(asc_time))

  log_file = file(log_file_name, 'r')
  game_state = pickle.load(log_file)
  log_file.close()
  return game_state


def save_game_state(game_state, log_file_prefix='log_state'):
  """
  Save game state to file
  """
  # get the current time, in seconds 
  time_stamp = time.time()
  game_state.time_stamp = time_stamp
  file_name = '{0}_{1}.log'.format(log_file_prefix, time_stamp)
  log_file = file(file_name, 'w')
  pickle.dump(game_state, log_file)
  log_file.close()

def describe_game_for_player(game, player_index):
  game.show_public_game_state()
  logging.info(game.game_state.players[player_index].describe_hand_private())


def wait_for_my_turn(my_index):
  """
  Wait until this player has priority
  """
  previous_priority_index = None
  priority_index = None
  # keep checking game state until it is my turn
  while my_index is not priority_index:
    time.sleep(0.1)
    game_state = get_previous_game_state()
    priority_index = game_state.priority_index
    leader_index = game_state.leader_index
    # print info about changes to priority
    if previous_priority_index is not priority_index:
      previous_priority_index = priority_index
      # print the current game state after every change
      game = gtr.Game(game_state=get_previous_game_state())
      describe_game_for_player(game, my_index)
      logging.info('--> Waiting to get priority...')

  asc_time = time.asctime(time.localtime(game_state.time_stamp))
  logging.info('--> You have priority (as of {0})!'.format(asc_time))


def get_possible_zones_list(game_state, player_index):
  """ Returns (currently truncated) list of zones, prints an indexed menu """

  player = game_state.players[player_index]
  possible_zones = []
  possible_zones.append(('Your camp', player.camp))
  possible_zones.append(('Your hand', player.hand))
  possible_zones.append(('Your clientele', player.clientele))
  possible_zones.append(('Your stockpile', player.stockpile))
  possible_zones.append(('Your influence', player.influence))
  possible_zones.append(('Your vault', player.vault))
  try:
    possible_zones.append(('Your revealed cards', player.revealed))
  except AttributeError:
    player.revealed = []
    possible_zones.append(('Your revealed cards', player.revealed))
  possible_zones.append(('Pool', game_state.pool))
  possible_zones.append(('Foundations', game_state.foundations))
  try:
    possible_zones.append(('Exchange area', game_state.exchange_area))
  except AttributeError:
    game_state.exchange_area = []
    possible_zones.append(('Exchange area', game_state.exchange_area))
  

  empty_site_exists = False
  for building in player.buildings:
      if not building:
          empty_site_exists = True
          name = 'Start a new building'
      else:
          name = 'Building {0}'.format(building[0])
      possible_zones.append((name, building))
  if not empty_site_exists:
      # add an empty site
      building = []
      player.buildings.append(building)
      possible_zones.append(('Start a new building', building))

  # print these possiblities
  for zone_index, (name, zone) in enumerate(possible_zones):
    logging.info('  [{0}] {1}'.format(zone_index+1, name))
  return possible_zones

def get_possible_cards_list(card_list):
  """ Returns list of cards, prints an indexed menu """
  try:
    card_list.sort()
    for card_index, card_name in enumerate(card_list):
        card_description = gtrutils.get_detailed_card_summary(card_name)
        logging.info('  [{0}] {1}'.format(card_index+1, card_description))
    return card_list
  except AttributeError:
    # special handling for foundations, which are dicts of lists
    card_list = card_list.keys()
      

def get_possible_buildings_list(game_state, player_index):
  player = game_state.players[player_index]



 
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
      (name, card_source) = possible_zones[response_int-1]
      logging.debug('source zone = {0!s}'.format(name))
    except:
      logging.info('your response was {0!s}... try again'.format(response_str))


    # buildings is a "zone of zones!"

    player = game_state.players[player_index]
    if card_source is player.buildings:
      logging.debug('card source is buildings!')

    
    break


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
      card_name = possible_cards[response_int-1]
      logging.debug('card_name = {0!s}'.format(card_name))
      break
    except:
      logging.info('your response was {0!s}... try again'.format(response_str))

  # choose the destination zone:
  logging.info('Move a Card: Choose the destination zone:')
  possible_zones = get_possible_zones_list(game_state, player_index)
  while True:
    response_str = raw_input('--> Card Destination ([q]uit, [s]tart over): ')
    if response_str in ['s', 'start over']: continue
    elif response_str in ['q', 'quit']: return ('','','')
    try:
      response_int = int(response_str)
      (name, card_destination) = possible_zones[response_int-1]
      logging.debug('destination zone = {0!s}'.format(name))
      break
    except:
      logging.info('your response was {0!s}... try again'.format(response_str))

  logging.debug('attempting to move {0} from {1} to {2}'.format(card_name,
    card_source, card_destination))
  return (card_name, card_source, card_destination)

def print_selections(choices_list):
  for i, choice in enumerate(choices_list):
    logging.info('  [{0}] {1}'.format(i+1, choice))

def choices_dialog(choices_list, 
                   prompt = 'Please make a selection'):
  """ Returns the index in the choices_list selected by the user or
  raises a StartOverException or a CancelDialogExeption. """

  print_selections(choices_list)
  
  while True:
    prompt_str = '--> {0} [1-{1}] ([q]uit, [s]tart over): '
    response_str = raw_input(prompt_str.format(prompt, len(choices_list)))
    if response_str in ['s', 'start over']: raise StartOverException
    elif response_str in ['q', 'quit']: raise CancelDialogException
    try:
      response_int = int(response_str)
    except:
      logging.info('your response was {0!s}... try again'.format(response_str))
      continue
    if response_int <= len(choices_list) and response_int > 0:
      # return the 0-indexed choice
      return response_int-1
    else:
      logging.info('Invalid selection ({0}). Please enter a number between 1 and {1}'.format(response_int, len(choices_list)))


  

def LeadOrFollowRoleDialog(game_state, player_index):
  """ Players can only lead or follow from their hands to their camp. 
  Returns a list of [<role>, <card1>, <card2>, ...] where <role> is
  the role being lead or followed and the remainder of the list
  are the card or cards used to lead/follow.
  This is usually only one card, but petitioning allows the player
  to use 3 cards as a jack.
  Raises a StartOverException if the user enters the Start Over option
  or if the user attempts an illegal action (petition without the needed
  multiple of a single role).
  """
  # Choose the role card
  logging.info('Lead or Follow a role: choose the card:')
  hand = game_state.players[player_index].hand
  sorted_hand = sorted(hand)
  card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]
  card_choices.append('Jack')
  card_choices.append('Petition')

  card_index = choices_dialog(card_choices, 'Select a card to lead/follow')


  role_index = -1
  # If it's a jack, figure out what role it needs to be
  if card_choices[card_index] == 'Jack':
    role_index = choices_dialog(card_manager.get_all_roles(), 
                                'Select a role for the Jack')
    return (card_manager.get_all_roles()[role_index], 'Jack')

  elif card_index == card_choices.index('Petition'):
    # check if petition is possible
    petition_count = 3   # 2 for circus
    non_jack_hand = filter(lambda x:x!='Jack', game_state.players[player_index].hand)
    hand_roles = map(card_manager.get_role_of_card, non_jack_hand)
    role_counts = collections.Counter(hand_roles)
    possible_petitions = [role for (role,count) in role_counts.items()
                          if count>=petition_count]

    if len(possible_petitions) < 1:
      logging.info('Petitioning requires {0} cards of the same role'.format(petition_count))
      raise StartOverException

    # Petition can be used for any role
    role_index = choices_dialog(card_manager.get_all_roles(), 'Select a role to petition')
    petition_role = card_manager.get_all_roles()[role_index]

    # Determine which cards will be used to petition
    cards_to_petition = []
    petition_cards = filter(
      lambda x : role_counts[card_manager.get_role_of_card(x)] >= petition_count, non_jack_hand)
    # Get first petition card, then filter out the roles that don't match
    for i in range(0, petition_count):
      card_index = choices_dialog(petition_cards, 
        "Select {0:d} cards to use for petition".format(petition_count - len(cards_to_petition)))
      cards_to_petition.append(petition_cards.pop(card_index))

      if len(cards_to_petition) == 1:
        def roles_match_petition(card): 
          return card_manager.get_role_of_card(card) == \
                    card_manager.get_role_of_card(cards_to_petition[0])
        
        petition_cards = filter(roles_match_petition, petition_cards)

    ret_value = ['Petition']
    ret_value.extend(cards_to_petition)
    return ret_value

  else:
    card = sorted_hand[card_index]
    return [card_manager.get_role_of_card(card), card]
    
def ThinkerTypeDialog(game_state, player_index):

  logging.info('Thinker:')
  player = game_state.players[player_index]
  logging.info('[1] Jack')
  n_possible_cards = player.get_n_possible_thinker_cards()
  logging.info('[2] Fill up from library ({0} cards)'.format(n_possible_cards))
  while True:
    response_str = raw_input('--> Your choice ([q]uit, [s]tart over): ')
    if response_str in ['s', 'start over']: continue
    elif response_str in ['q', 'quit']: return ('','','')
    try:
      response_int = int(response_str)
      if response_int == 1:
        game_state.draw_one_jack_for_player(player)
      elif response_int == 2:
        game_state.thinker_fillup_for_player(player)
      else:
        continue
      logging.info(player.describe_hand_private())
      save_game_state(game_state)
      break
    except:
      logging.info('your response was {0!s}... try again'.format(response_str))

    

def main():

  # options:
  logging.basicConfig(level=logging.INFO, format='%(message)s')

  logging.info('--> Welcome to the game!')

  # add player to game
  default_name = os.getenv('USER')
  my_name = raw_input('Enter your name [{0}]: '.format(default_name))
  if my_name == '':
    my_name = default_name

  # check whether game exists, if not start a new one
  game_state = get_previous_game_state()
  if game_state:  
    logging.info('--> Joining existing game...')  
  else:
    logging.info('--> Starting a new game...')
    game_state = GameState()

  n_players = game_state.get_n_players()
  my_index = game_state.find_or_add_player(my_name)
  # only save the game state if player was added
  if n_players < game_state.get_n_players():
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
      game_state = get_previous_game_state()
      n_players = game_state.get_n_players() 
      logging.info('--> There are {0:d} players including you.'.format(n_players))
      response = raw_input(
        '--> Would you like to start? [y/n (enter=wait for more players)] : ')
      if response is 'y':
        game_state = get_previous_game_state()

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
    game_state = get_previous_game_state()
    # It is now my turn and the game state was just printed
    while True:
      #game_state = get_previous_game_state()
      asc_time = time.asctime(time.localtime(game_state.time_stamp))
      logging.debug('--> Previous game state is from {0}'.format(asc_time))
      # Just take the first character of the reponse, lower case.
      response_string=raw_input(
        '--> Take action: [M]ove card, [T]hinker, [L]ead or Follow a role, [P]ass priority, [E]nd turn, [R]eprint game state: ')
      try:
        response = response_string.lower()[0]
      except IndexError:
        continue
      if response == 'm':
        card_name, source, dest = MoveACardDialog(game_state, my_index)
        try:
          gtrutils.get_card_from_zone(card_name, source)
          gtrutils.add_card_to_zone(card_name, dest)
          save_game_state(game_state)
        except: 
          logging.warning('Move was not successful')
          continue

      if response == 'l':
        try:
          resp_list = LeadOrFollowRoleDialog(game_state, my_index)
          print 'resp_list = ' + str(resp_list)
        except StartOverException:
          logging.debug('Start over exception caught')
          continue
        except CancelDialogException:
          logging.debug('Cancel dialog exception caught')
          continue
        role, cards = resp_list[0], resp_list[1:]
        source = game_state.players[my_index].hand
        dest = game_state.players[my_index].camp
        for card in cards:
          try:
            gtrutils.get_card_from_zone(card, source)
            gtrutils.add_card_to_zone(card, dest)
          except: 
            raise
            logging.warning('Move was not successful')
            continue
        save_game_state(game_state)

      elif response == 't':
        thinker_type = ThinkerTypeDialog(game_state, my_index)
        save_game_state(game_state)

      elif response == 'p':
        game_state.increment_priority_index()
        save_game_state(game_state)
        break
        
      elif response == 'e':
        game_state.increment_priority_index()
        game_state.increment_leader_index()
        save_game_state(game_state)
        break

      elif response == 'r':
        #game = gtr.Game(game_state=game_state)
        #describe_game_for_player(game, my_index)
        break
      
        



if __name__ == '__main__':

  main()

