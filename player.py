#!/usr/bin/env python

""" Contains the Player class, which is a wrapper for all of the
zones associated with a player. Much like the GameState class,
this class does not enforce anything more than physical limitations,
like failing to get a card from an empty stack.
"""

from gtrutils import get_card_from_zone
from gtrutils import get_short_zone_summary
from gtrutils import get_detailed_card_summary
from gtrutils import get_building_info
from gtrutils import get_detailed_zone_summary
import collections

class Player:
  """ Contains the piles and items controlled by a player. """
  max_hand_size = 5
  # Must use this None->(if hand)->[] method because all players end up
  # pointing to the same list if the default is [].
  def __init__(self, name='Player', hand=None, stockpile=None, clientele=None,
               vault=None, camp=None, buildings=None, influence=None,
               revealed=None):
    self.name = name
    self.hand = hand if hand is not None else []
    self.stockpile = stockpile if stockpile is not None else []
    self.clientele = clientele if clientele is not None else []
    self.vault = vault if vault is not None else []
    self.camp = camp if camp is not None else []
    self.buildings = buildings if buildings is not None else []
    self.influence = influence if influence is not None else []
    self.revealed = revealed or []

  def __repr__(self):
    rep = ('Player(name={name!r}, hand={hand!r}, stockpile={stockpile!r}, '
           'clientele={clientele!r}, vault={vault!r}, camp={camp!r}, '
           'buildings={buildings!r}, influence={influence!r})')
    return rep.format(
      name=self.name, hand=self.hand, stockpile=self.stockpile,
      clientele=self.clientele, vault=self.vault, camp=self.camp,
      buildings=self.buildings, influence=self.influence)

  def get_max_hand_size(self):
    return Player.max_hand_size

  def get_n_possible_thinker_cards(self):
    """ get number of cards that can be drawn when thiking """
    n_possible_cards = self.get_max_hand_size() - len(self.hand)
    if n_possible_cards < 1:
      n_possible_cards = 1
    if n_possible_cards == 0:
        n_possible_cards = 1
    return n_possible_cards


  def get_card_from_hand(self, card):
    return get_card_from_zone(card, self.hand)

  def get_card_from_stockpile(self, card):
    return get_card_from_zone(card, self.stockpile)

  def get_card_from_vault(self, card):
    return get_card_from_zone(card, self.vault)

  def get_card_from_clientele(self, card):
    return get_card_from_zone(card, self.clientele)

  def get_card_from_influence(self, card):
    return get_card_from_zone(card, self.influence)

  def get_card_from_camp(self,card):
    return get_card_from_zone(card, self.camp)

  def add_cards_to_hand(self, cards):
    self.hand.extend(cards)

  def add_cards_to_stockpile(self, cards):
    self.stockpile.extend(cards)

  def add_cards_to_vault(self, cards):
    self.vault.extend(cards)

  def add_cards_to_clientele(self, cards):
    self.clientele.extend(cards)

  def add_cards_to_influence(self, cards):
    self.influence.extend(cards)

  def play_cards(self, cards):
    self.camp.extend(cards)

  def get_n_jacks_in_hand(self):
    return self.hand.count('Jack')

  def describe_hand_public(self):
    """ Returns a string describing the player's public-facing hand.
    
    Revealed information is the number of cards and the number of jacks.
    """
    n_jacks = self.get_n_jacks_in_hand()
    hand_string = 'Hand : {0:d} cards (inc. {1:d} jacks)'
    return hand_string.format(len(self.hand), n_jacks)

  def describe_hand_private(self):
    """ Returns a string describing all of the player's hand.
    """
    #cards_string = 'Hand : ' + get_short_zone_summary(self.hand)

    cards_string = '{0}: \n'.format(self.describe_hand_public())
    cards_string += get_detailed_zone_summary(self.hand)
        
    return cards_string

  def describe_vault_public(self):
    """ Returns a string describing the player's public-facing vault.
    
    Revealed information is the number of cards and the number of jacks.
    """
    return 'Vault : {0:d} cards'.format(len(self.vault))

  def describe_clientele(self):
    """ Returns a string describing a player's clientele.
    """
    cards_string = 'Clientele : ' + get_short_zone_summary(self.clientele)
    return cards_string

  def describe_stockpile(self):
    """ Returns a string describing a player's stockpile.
    """
    cards_string = 'Stockpile : ' + get_short_zone_summary(self.stockpile)
    return cards_string

  def describe_buildings(self):
    """ Returns a string describing the player's buildings.
    """
    # buildings are lists of lists, where the 
    cards_string = 'Buildings: \n' 
    for building in self.buildings:
        if building:
          cards_string += get_building_info(building)
          cards_string += '\n'

    return cards_string



  def describe_camp(self):
    cards_string = 'Camp : \n' + get_detailed_zone_summary(self.camp)
    return cards_string

  def describe_revealed(self):
    cards_string = 'Revealed : \n' + get_detailed_zone_summary(self.revealed)
    return cards_string

    

if __name__ == '__main__':

  test_player = Player()
  print test_player
