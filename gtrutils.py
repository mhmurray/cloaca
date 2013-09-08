#!/usr/bin/env python

import logging
import collections

""" Utility functions for GTR.
"""

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

def get_short_zone_summary(card_list):
  """ Return a single-line string with 4-letter card abbreviations and numbers
  of card instances.
  """
  counter = collections.Counter(card_list)
  cards_string = ''
  for card, count in counter.items():
    cards_string += '{0}[{1:d}], '.format(card[:4], count)
  cards_string.rstrip(', ')
  return cards_string



if __name__ == '__main__':

  # simple tests...
  logging.basicConfig(level=logging.DEBUG, format='%(message)s')
  
  test_zone = ['a', 'a', 'b', 'c']
  card_one = get_card_from_zone('a', test_zone)
  card_two = get_card_from_zone('c', test_zone)
  add_card_to_zone(card_one, test_zone)

  print get_short_zone_summary(test_zone)

