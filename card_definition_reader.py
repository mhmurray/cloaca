#!/usr/bin/env python

"""
This script imports the CSV list of cards for use during the game.

Right now the function get_cards_dict() is called by gtr.Game.init_library().
The json file is just for testing; it is not used by the code.  AGS 07 Sep 2013
"""

import json


def get_cards_dict():


  # read in the CSV file
  cards_csv = file('GTR_cards.csv', 'r')
  line_index = 0

  # setup a dict to hold the card data
  cards_dict = {}

  # loop over all lines in the CSV file, making a card definition from each
  for line in cards_csv:
    line_index = line_index+1

    # skip the first lines:
    if line_index > 3:
      line_list = line.split(',')

      # make a dict for this card
      card_data = {}
      card_data['material'] = line_list[1]
      #card_data['value'] = line_list[2]
      card_data['card_count'] = line_list[3]
      #card_data['role'] = line_list[4]
      #card_data['timing'] = line_list[5]
      card_data['function'] = line_list[6]
      #card_data['type'] = line_list[7]
      #print card_data

      # insert this card's data into the global dict:
      card_name = line_list[0]
      cards_dict[card_name] = card_data
      #print cards_dict

      #break # for debugging


  cards_csv.close()

  return cards_dict




if __name__ == '__main__':

  cards_dict = get_cards_dict()

  # write to a json file
  json_file = file('GTR_cards.json', 'w')
  json.dump(cards_dict, json_file, sort_keys=True, indent=2)
  json_file.close()


