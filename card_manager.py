#!/usr/bin/env python

"""
This module reads data from a json file and returns card properties as strings,
except card value, which is returned as an int.
Currently there is barely any error handling! -- AGS 13 Sep 2013
"""

import json
import logging
from os import path

  
def get_cards_dict_from_json_file():
  """ Return dict of data for ALL cards from the json file.  """
  # json should be in the GTR directory, with this module
  gtr_dir = path.dirname( __file__)
  json_file = file('{0}/GTR_cards.json'.format(gtr_dir), 'r')
  cards_dict = json.load(json_file)
  json_file.close()
  return cards_dict


def get_card_dict(card_name):
  """ Return dict of data for ONE card. """
  cards_dict = get_cards_dict_from_json_file()
  card_dict = cards_dict[card_name]
  return card_dict

def get_function_of_card(card_name):
  """ Return function string for the specified card. """
  card_dict = get_card_dict(card_name)
  function = card_dict['function']
  return function
  
def get_material_of_card(card_name):
  """ Return material string for the specified card. """
  card_dict = get_card_dict(card_name)
  material = card_dict['material']
  return material
  
def get_count_of_card(card_name):
  """ Return card count for the specified card. """
  card_dict = get_card_dict(card_name)
  count = card_dict['card_count']
  count =  int(count)
  return count

def get_materials():
  materials = [
    'Brick',
    'Concrete',
    'Marble',
    'Rubble',
    'Stone',
    'Wood'
  ]
  return materials

def get_role_of_material(material):
  if material == 'Brick':
      return 'Legionary'
  elif material == 'Concrete':
      return 'Architect'
  elif material == 'Marble':
      return 'Patron'
  elif material == 'Rubble':
      return 'Laborer'
  elif material == 'Stone':
      return 'Merchant'
  elif material == 'Wood':
      return 'Craftsman'
  else:
      logging.error('----> Role of {0} not found!'.format(material))
  
def get_role_of_card(card_name):
  material = get_material_of_card(card_name)
  role = get_role_of_material(material)
  return role

def get_value_of_material(material):
  if material == 'Brick':
      return 2
  elif material == 'Concrete':
      return 2
  elif material == 'Marble':
      return 3
  elif material == 'Rubble':
      return 1
  elif material == 'Stone':
      return 3
  elif material == 'Wood':
      return 1
  else:
      logging.error('----> Value of {0} not found!'.format(material))

def get_value_of_card(card_name):
  material = get_material_of_card(card_name)
  value = get_value_of_material(material)
  return value

def get_all_roles():
  """ Returns a list of all 6 possible roles. """
  return ['Patron', 'Laborer', 'Architect', 
          'Craftsman', 'Legionnary', 'Merchant']
  
def get_all_materials():
  """ Returns a list of all possible materials """
  foundations = [
    'Brick',
    'Cement',
    'Marble',
    'Rubble',
    'Stone',
    'Wood',
  ]
  return foundations



if __name__ == '__main__':

  cards_dict = get_cards_dict_from_json_file()
  card_names = cards_dict.keys()
  card_names.sort()
  #print cards_dict

  for card_name in card_names:
    print '--- {0} ---'.format(card_name.upper())
    #print get_card_dict(card_name)
    print get_function_of_card(card_name)
    print get_material_of_card(card_name)
    print get_count_of_card(card_name)
    print get_role_of_card(card_name)
    print get_value_of_card(card_name)

  print get_all_roles()



