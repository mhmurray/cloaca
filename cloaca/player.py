#!/usr/bin/env python

""" Contains the Player class, which is a wrapper for all of the
zones associated with a player. Much like the GameState class,
this class does not enforce anything more than physical limitations,
like failing to get a card from an empty stack.
"""

import cloaca.card_manager as card_manager
from cloaca.building import Building
from cloaca.zone import Zone
from cloaca.error import GTRError

import logging
from collections import Counter

lg = logging.getLogger(__name__)
lg.addHandler(logging.NullHandler())

class Player(object):
    """ Contains the piles and items controlled by a player. """
    max_hand_size = 5

    def __init__(self, uid, name, hand=None, stockpile=None, clientele=None,
            vault=None, camp=None, fountain_card=None, n_camp_actions=0,
            buildings=None, influence=None, revealed=None, prev_revealed=None,
            clients_given=None,
            performed_craftsman=False):

        self.name = name
        self.uid = uid
        self.hand = hand if hand is not None else Zone(name='hand')
        self.stockpile = stockpile if stockpile is not None else Zone(name='stockpile')
        self.clientele = clientele if clientele is not None else Zone(name='clientele')
        self.vault = vault if vault is not None else Zone(name='vault')
        self.camp = camp if camp is not None else Zone(name='camp')
        self.fountain_card = fountain_card
        self.n_camp_actions = n_camp_actions
        self.buildings = buildings if buildings is not None else []
        self.influence = influence if influence is not None else []
        self.revealed = revealed if revealed is not None else Zone(name='revealed')
        self.prev_revealed = prev_revealed if prev_revealed is not None else Zone(name='prev_revealed')
        self.clients_given = clients_given if clients_given is not None else Zone(name='clients_given')
        self.performed_craftsman = performed_craftsman

    def __repr__(self):
        return 'Player({uid!r}, {name!r})'.format(**self.__dict__)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        d, dother = self.__dict__, other.__dict__
        for pdict in d, dother:
            pdict['influence'] = Counter(pdict['influence'])

        return d == dother

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

    @property
    def stairwayed_buildings(self):
        """ Returns a list of Building objects that have a material added
        via the Stairway.
        """
        return [b for b in self.buildings if b.is_stairwayed]

    @property
    def is_following_or_leading(self):
        return len(self.camp) > 0

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
