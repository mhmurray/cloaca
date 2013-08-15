""" Utility functions for GTR.
"""

def _get_card_from_zone(card, l):
  """ Wrapper around the possible exception caused by trying to 
  find a non-existent card in a list. Prints an error and 
  re-raises the exception.
  """
  try:
    return l.pop(l.index(card))
  except ValueError as e:
    print 'Error! card {0!s} not found'.format(card)
    raise

