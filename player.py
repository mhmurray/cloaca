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
import card_manager
from building import Building

import logging
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
    self.performed_craftsman = False

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

  def owns_building(self, building):
    """ Whether this player owns a building, complete or otherwise.
    The parameter building is a string.
    """
    return building in self.get_owned_building_names()

  def get_owned_buildings(self):
    """ Returns a list of all Building objects this player owns,
    complete or incomplete.
    """
    return self.buildings

  def get_owned_building_names(self):
    """ Returns a list of the names of all buildings this
    player owns, complete or incomplete.
    """
    return [b.foundation for b in self.buildings]

  def get_completed_building_names(self):
    """ Returns a list of the building names (string) for all (owned)
    completed buildings.
    """
    return [b.foundation for b in self.buildings]

  def get_completed_buildings(self):
    """ Returns a list of all owned completed Building objects.
    """
    return filter(Building.is_completed, self.buildings)

  def get_incomplete_building_names(self):
    """ Returns a list of all incomplete building names.
    """
    return [b.foundation for b in self.buildings]

  def get_incomplete_buildings(self):
    """ Returns a list of all incomplete Building objects.
    """
    return [b for b in self.buildings if not b.is_completed()]

  def get_building(self, building_name):
    """ Gets the Building object from the name of the building.
    """
    return [b for b in self.buildings if b.foundation == building_name][0]

  def get_active_buildings(self):
    """ Returns a list of just the building names for all buildings
    that are active. This includes an incomplete marble building while
    we have a completed Gate.

    This doesn't check other players for Stairway modifications.
    """
    active_buildings = self.get_completed_buildings()
    if 'Gate' in self.get_completed_building_names():
      # find marble buildings and append to active buildings list
      incomplete_marble_buildings =\
        filter(lambda x : x.is_composed_of('Marble'), self.get_incomplete_buildings())
      active_buildings.extend(incomplete_marble_buildings)

    return active_buildings

  def get_active_building_names(self):
    """ Returns a list of just the building names for all buildings
    that are active. This includes an incomplete marble building while
    we have a completed Gate.

    This doesn't check other players for Stairway modifications.
    """
    return [b.foundation for b in self.get_active_buildings()]

  def get_stairwayed_buildings(self):
    """ Returns a list of Building objects that have a material added
    via the Stairway.
    """
    return [b for b in self.get_owned_buildings() if b.is_stairwayed]

  def get_stairwayed_building_names(self):
    return [b.foundation for b in self.get_stairwayed_buildings()]

  def get_n_clients(self, role=None):
    """ Return the number of clients of the specified role. This counts
    the effect of Storeroom and Ludus Magna, but not Circus Maximus.

    If role is not specified or is None, returns the number of clients
    of all roles.
    """
    if role is None:
      n_clients = len(self.clientele)
    elif role == 'Laborer' and 'Storeroom' in self.get_active_buildings():
      n_clients = len(self.clientele)
    else:
      role_list = map(card_manager.get_role_of_card, self.clientele)
      n_clients = role_list.count(role)

      # Ludus Magna adds to any non-Merchant count.
      if role != 'Merchant' and 'Ludus Magna' in self.get_active_buildings():
        n_clients += role_list.count('Merchant')

    return n_clients

  def get_n_client_cards_of_role(self, role):
    role_list = [card_manager.get_role_of_card(x) for x in self.clientele]
    return role_list.count(role)

  def is_following_or_leading(self):
    return len(self.camp) > 0

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
    roles = []
    for card in self.clientele:
      roles.append(card_manager.get_role_of_card(card))
    cards_string = 'Clientele : ' + get_short_zone_summary(roles)
    return cards_string

  def describe_stockpile(self):
    """ Returns a string describing a player's stockpile.
    """
    materials = []
    for card in self.stockpile:
      materials.append(card_manager.get_material_of_card(card))
    cards_string = 'Stockpile : ' + get_short_zone_summary(materials)
    return cards_string

  def describe_buildings(self):
    """ Returns a string describing the player's buildings.
    """
    # buildings are lists of lists, where the 
    cards_string = 'Buildings: \n' 
    buildings_info = []
    for building in self.buildings:
        if building:
          buildings_info.append(get_building_info(building))
    cards_string += '\n'.join(buildings_info)
    return cards_string

  def get_influence_points(self):
    # influence cards are foundations, of form "Material"
    influence = 2
    for card in self.influence:
      value = card_manager.get_value_of_material(card)
      if value is None:
        logging.error('Unexpected card {0} in influence'.format(card))
      else:
        influence += value
    return influence

  def describe_influence(self):
    influence_string = 'Influence : {0}'.format(self.get_influence_points())
    return influence_string

  def describe_camp(self):
    cards_string = 'Camp : \n' + get_detailed_zone_summary(self.camp)
    return cards_string

  def describe_revealed(self):
    cards_string = 'Revealed : \n' + get_detailed_zone_summary(self.revealed)
    return cards_string

    

if __name__ == '__main__':

  test_player = Player()
  print test_player

# vim: ts=8:sts=2:sw=2:et
