#!/usr/bin/env python

import logging

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


if __name__ == '__main__':

  # simple tests...
  logging.basicConfig(level=logging.DEBUG, format='%(message)s')
  
  test_zone = ['a', 'a', 'b']
  get_card_from_zone('a', test_zone)
  get_card_from_zone('c', test_zone)

