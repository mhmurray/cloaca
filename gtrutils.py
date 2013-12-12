#!/usr/bin/env python

import logging
import collections
import card_manager

""" Utility functions for GTR.
"""

def print_line(symbol='-'):
  """ Print a line for visual division of info """
  logging.info(symbol*80)

def print_header(title, symbol='-'):
  n_symbol = 80 - len(title)
  logging.info('{0}: {1}'.format(title, symbol*n_symbol))

def get_card_from_zone(card, zone):
  """ Wrapper around the possible exception caused by trying to 
  find a non-existent card in a list. Prints an error and 
  re-raises the exception.
  """
  logging.debug('getting card {0!s} from zone {1!s}'.format(card, zone))
  try:
    return zone.pop(zone.index(card))
  except ValueError as e:
    logging.error('Error! card {0!s} not found'.format(card))
    raise

def add_card_to_zone(card, zone):
  """
  """
  logging.debug('adding card {0!s} to zone {1!s}'.format(card, zone))
  zone.append(card)

def get_short_zone_summary(card_list, n_letters=4):
  """ Return a single-line string with n-letter card abbreviations and numbers
  of card instances.
  """
  counter = collections.Counter(card_list)
  cards_string = ''
  for card, count in counter.items():
    cards_string += '{0}[{1:d}], '.format(card[:n_letters], count)
  cards_string.rstrip(', ')
  return cards_string

def get_detailed_card_summary(card, count=None):
  """ return a single-line string to describe one card in detail """

  card_string = '{0:<4}'.format(card[:4])
  if count:
    card_string += '[{0:d}]'.format(count)
  if card != 'Jack':
    material = card_manager.get_material_of_card(card)
    role = card_manager.get_role_of_card(card)
    value = card_manager.get_value_of_card(card)
    function = card_manager.get_function_of_card(card)
    card_string += ' | {0}'.format(material[:3])
    card_string += '-{0}'.format(role[:3])
    card_string += '-{0}'.format(value)
    card_string += ' | {0}'.format(function)
  return card_string

def get_detailed_zone_summary(zone):
  """ return a multi-line description of cards in zone """

  counter = collections.Counter(zone)
  counter_dict = dict(counter)
  cards = counter_dict.keys()
  cards.sort() # alphabetize
  zone_string = '  Card      | Mat-Rol-$ | Description \n'
  for card in cards:
    count = counter_dict[card]
    zone_string += '  * ' + get_detailed_card_summary(card, count) 
    zone_string += '\n'
  return zone_string


def get_building_info(building):
    """ Return a string to describe a building """

    # each building is a list where the 0th card defines the building, the other
    # orders cards are the materials, and there may be a site card

    # the 0th card is the title card
    if not building:
        return ''
    title_card = building[0]
    function = card_manager.get_function_of_card(title_card)
    value = card_manager.get_value_of_card(title_card)
    title_material = card_manager.get_material_of_card(title_card)
    title_value = card_manager.get_value_of_card(title_card)
    
    has_site = False
    has_materials = False
    materials_string = ''
    for card in building[1:]:
      try:
        material = card_manager.get_material_of_card(card)
        materials_string += material[0]
        has_materials = True
      except: 
        site_material = card
        has_site = True
        
    info = '  * {0} | {1}-{2} | '.format(title_card, title_material[:3], value)
    if has_site:
        info += '{0} site '.format(site_material[:3])
    if has_site and has_materials:
        info += '+ '
    info += '{0} | {1}'.format(materials_string, function)
    return info



if __name__ == '__main__':

  # simple tests...
  logging.basicConfig(level=logging.DEBUG, format='%(message)s')
  
  test_zone = ['a', 'a', 'b', 'c']
  card_one = get_card_from_zone('a', test_zone)
  card_two = get_card_from_zone('c', test_zone)
  add_card_to_zone(card_one, test_zone)

  print get_short_zone_summary(test_zone)

