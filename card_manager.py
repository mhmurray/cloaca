#!/usr/bin/env python

"""
This module reads data from a json file and returns card properties as strings,
except card value, which is returned as an int.
There is barely any error handling!
"""

import json
import logging
from os import path

from collections import Counter

_deck = ()

def _get_deck():
    """Initialize or return the list of card names. Six Jacks plus
    the Orders cards in alphabetical order.
    """

    global _deck
    if len(_deck) == 0:
        orders = []
        d = get_cards_dict_from_json_file()
        for name, card_dict in d.items():
            name = str(name)
            n_cards = int(card_dict['card_count'])
            orders.extend([name]*n_cards)

        orders.sort(key=lambda x:x.lower())
        _deck = tuple(['Jack']*6 + orders)

    return _deck

def standard_deck():
    """Returns a tuple of the standard cards (strings) in a deck, Jacks first,
    alphabetical after.
    """
    return _get_deck()
        

def get_card(name, copy=0):
    """Return the card of the specified name and relative
    index. If the first Dock card is 12, say, then 
    get_card('Dock', 2) returns Card(ident=14).

    Raise IndexError if copy is larger than the number
    of those cards.
    """
    c = Card(standard_deck().index(name)+copy)
    if c.name != name:
        raise IndexError('There are not {0!s} copies of {1} in the deck.'
                .format(copy+1, name))
    else:
        return c


def get_cards(card_names):
    """Return a tuple of cards with the specified names, and the first
    ident numbers in the list.

        > get_cards(['Road']*3)
        > (Card(105), Card(106), Card(107))

    Raises ValueError if too many cards of one type are requested. For
    instance, there are only 3 'Statue' cards, so get_cards(['Statue']*4)
    will raise.
    """
    d = {name:list(cards(name)) for name in set(card_names)}

    out=[]
    for name in card_names:
        try:
            c = d[name].pop(0)
        except IndexError:
            raise ValueError(
                    'There are only {0} {1} cards in the game '
                    '({2} requested).'
                    .format(len(cards(name)), name, card_names.count(name)))

        out.append(c)
    
    return tuple(out)


def get_cards_of_material(material):
    """Gets all card of the specified material.
    """
    return filter(lambda c: c.material == material, get_orders_card_set())

def card_ids(name):
    """Return generator of all card ids with the specified name.
    """
    return (i for i,c in enumerate(standard_deck()) if c==name)

def cards(name):
    """Return generator of all Card objects with the specified name. 
    They will have different ids.
    """
    return (Card(i) for i in card_ids(name))


def get_orders_card_set():
    """Returns a list with the default number of each Orders cards.
    The elements are Card objects.
    """
    return [Card(i) for i in range(6, len(_get_deck()))]
        

def get_cards_dict_from_json_file():
    """ Return dict of data for ALL cards from the json file.  """
    # json should be in the GTR directory, with this module
    gtr_dir = path.dirname(__file__)
    json_file = file(path.join(gtr_dir,'GTR_cards.json'), 'r')
    cards_dict = json.load(json_file)
    json_file.close()
    return cards_dict

def get_card_dict(card_name):
    """ Return dict of data for ONE card. """
    cards_dict = get_cards_dict_from_json_file()
    
    if card_name in ['Jack','Card'] :
        card_dict = {"card_count": "0", 
                "function": None,
                "material": None
               } 
    else:
        card_dict = cards_dict[card_name]
    return card_dict

def get_function_of_card(card_name):
    """ Return function string for the specified card. """
    card_dict = get_card_dict(card_name)
    function = card_dict['function']
    return str(function) if function else function

def get_material_of_card(card_name):
    """ Return material string for the specified card. """
    card_dict = get_card_dict(card_name)
    material = card_dict['material']
    return str(material) if material else material

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
    elif material is None:
        return None
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
    elif material is None:
        return None
    else:
        logging.error('----> Value of {0} not found!'.format(material))

def get_value_of_card(card_name):
    material = get_material_of_card(card_name)
    value = get_value_of_material(material)
    return value

def get_all_roles():
    """ Returns a list of all 6 possible roles. """
    return ['Patron', 'Laborer', 'Architect',
            'Craftsman', 'Legionary', 'Merchant']

def get_all_materials():
    """ Returns a list of all possible materials """
    foundations = [
      'Brick',
      'Concrete',
      'Marble',
      'Rubble',
      'Stone',
      'Wood',
    ]
    return foundations

def cmp_jacks_first(c1, c2):
    """ Comparator that alphabetizes cards, but puts Jacks before all
    Orders cards.
    """
    if c1 == c2:
        return 0
    if c1 == 'Jack':
        return -1
    if c2 == 'Jack':
        return 1
    return cmp(c1,c2)


class Card(object):
    """Each card has an identity number, different for even duplicate cards.

    Comparison between cards can use '==' for comparing names, or 
    identical() to compare ident numbers.

        Card(123, 'Insula') == Card(101, 'Insula') # True
        Card(123, 'Insula') == Card(123, 'Dock') # False
        Card(123, 'Insula').identical(Card(123, 'Insula')) # True
        Card(123, 'Insula').identical(Card(101, 'Insula')) # False

    Comparisons between cards using the operators (==, <, etc.) compare
    names alphabetically except that Jacks are always first.

    Members:
    ident -- unique id number, different for all cards. Negative values
             are for anonymouse cards named 'Card', eg. for your opponent's
             hand. Card with idents too large are set to -1.

    Attributes (read-only):
    name -- name of foundation, or 'Jack'
    material -- string like 'Brick', 'Rubble'. None for Jacks.
    value -- integer 1-3 or None for Jacks.
    role -- string like 'Merchant', 'Laborer'. None for Jacks.
    text -- rules text of the card. Empty string for Jacks.
    """

    def __init__(self, ident):
        if type(ident) is not int:
            raise TypeError(
                    'Card.ident must be an integer, received \'{0!s}\''
                    .format(ident))
        self.ident = ident
        if self.ident >= len(standard_deck()):
            raise TypeError('Card.ident out of range: {0}'.format(ident))

    def get_name(self):
        if self.ident < 0: return 'Card'
        else: return standard_deck()[self.ident]

    name = property(lambda self: standard_deck()[self.ident])
    material = property(lambda self: get_material_of_card(self.name))
    value = property(lambda self: get_value_of_card(self.name))
    role = property(lambda self: get_role_of_card(self.name))
    text = property(lambda self: get_function_of_card(self.name))

    def __repr__(self):
        rep = ('Card({ident!r})')
        return rep.format(**self.__dict__)

    def __str__(self):
        return self.name

    def __cmp__(self, other):
        """Custom comparison between cards. Uses the ident attribute.
        If compared to a non-Card object, the comparison uses
        cmp(id(self), id(other)).
        """
        if not isinstance(other, Card):
            return cmp(id(self), id(other))

        return cmp(self.ident, other.ident)

    def __hash__(self):
        return self.ident

    def compare_jacks_first(self, other):
        if not isinstance(other, Card):
            return cmp(id(self), id(other))

        c1, c2 = self.name.lower(), other.name.lower()
        if c1 == c2:
            return cmp(self.ident, other.ident)
        elif c1 == 'Jack':
            return -1
        elif c2 == 'Jack':
            return 1
        else:
            return cmp(self, other)

    def same_name(self, other):
        return self.name == other.name
