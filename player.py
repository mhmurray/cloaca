#!/usr/bin/env python

""" Contains the Player class, which is a wrapper for all of the
zones associated with a player. Much like the GameState class,
this class does not enforce anything more than physical limitations,
like failing to get a card from an empty stack.
"""

from gtrutils import get_card_from_zone, GTRError
from gtrutils import get_short_zone_summary
from gtrutils import get_detailed_card_summary
from gtrutils import get_building_info
from gtrutils import get_detailed_zone_summary
import card_manager
from building import Building
from zone import Zone

import logging
import collections

lg = logging.getLogger('gtr')

class Player:
    """ Contains the piles and items controlled by a player. """
    max_hand_size = 5
    # Must use this None->(if hand)->[] method because all players end up
    # pointing to the same list if the default is [].
    def __init__(self, name):
        self.name = name
        self.hand = Zone()
        self.stockpile = Zone()
        self.clientele = Zone()
        self.vault = Zone()
        self.camp = Zone()
        self.fountain_card = None
        self.n_camp_actions = 0
        self.buildings = []
        self.influence = []
        self.revealed = Zone()
        self.previous_revealed = Zone()
        self.performed_craftsman = False
        self.uid = None

    def __repr__(self):
        rep = ('Player(name={name!r}, hand={hand!r}, stockpile={stockpile!r}, '
               'clientele={clientele!r}, vault={vault!r}, camp={camp!r}, '
               'buildings={buildings!r}, influence={influence!r})')
        return rep.format(
          name=self.name, hand=self.hand, stockpile=self.stockpile,
          clientele=self.clientele, vault=self.vault, camp=self.camp,
          buildings=self.buildings, influence=self.influence)

    def __str__(self):
        return self.name

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
        """Whether this player owns a building, complete or otherwise.
        The parameter building is a string.
        """
        return building.name in self.building_names

    @property
    def building_names(self):
        """ Returns a list of the names of all buildings this
        player owns, complete or incomplete.
        """
        return [b.foundation.name for b in self.buildings]

    @property
    def complete_buildings(self):
        """Returns a list of all owned complete Building objects.
        """
        return filter(lambda x: x.complete, self.buildings)

    @property
    def incomplete_buildings(self):
        """Returns a list of all incomplete Building objects.
        """
        return [b for b in self.buildings if not b.complete]

    def get_building(self, foundation):
        """Gets the Building object from foundation card of the building.
        """
        matches = [b for b in self.buildings if b.foundation == foundation]
        try:
            b = matches[0]
        except IndexError:
            raise GTRError('{0} doesn\'t own a {1!s}.'
                .format(self.name, foundation))
        return b

    def get_building_by_name(self, name):
        """Gets the Building object from the foundation card name.
        """
        b = next( (b for b in self.buildings if b.foundation.name == name), None)
        try:
            b = matches[0]
        except IndexError:
            raise GTRError('{0} doesn\'t own a {1}.'
                .format(self.name, foundation_name))
        return b


    @property
    def stairwayed_buildings(self):
        """ Returns a list of Building objects that have a material added
        via the Stairway.
        """
        return [b for b in self.buildings if b.is_stairwayed]

    def n_clients(self, role=None, active_buildings=[]):
        """ Return the number of clients of the specified role. This counts
        the effect of Storeroom and Ludus Magna, but not Circus Maximus.

        If role is not specified or is None, returns the number of clients
        of all roles.
        """
        if role is None:
            n_clients = len(self.clientele)
        elif role == 'Laborer' and 'Storeroom' in active_buildings:
            n_clients = len(self.clientele)
        else:
            n_clients = len(filter(lambda c: c.role == role, self.clientele))

            # Ludus Magna adds to any non-Merchant count.
            if role != 'Merchant' and 'Ludus Magna' in active_buildings:
                n_clients += len(filter(lambda c: c.role == 'Merchant', self.clientele))

        return n_clients

    @property
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

    @property
    def influence_points(self):
        influence = 2
        for card in self.influence:
            value = card_manager.get_value_of_material(card)
            if value is None:
                lg.error('Unexpected card {0} in influence'.format(card))
            else:
                influence += value
        return influence
