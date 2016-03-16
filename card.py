#!/usr/bin/env python

import card_manager as cm

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
             hand.

    Attributes (read-only):
    name -- name of foundation, or 'Jack'
    material -- string like 'Brick', 'Rubble'. None for Jacks.
    value -- integer 1-3 or None for Jacks.
    role -- string like 'Merchant', 'Laborer'. None for Jacks.
    text -- rules text of the card. Empty string for Jacks.
    """

    def __init__(self, ident):
        self.ident = ident

    def get_name(self):
        if self.ident < 0: return 'Card'
        else: return cm.standard_deck()[self.ident]

    name = property(lambda self: cm.standard_deck()[self.ident])
    material = property(lambda self: cm.get_material_of_card(self.name))
    value = property(lambda self: cm.get_value_of_card(self.name))
    role = property(lambda self: cm.get_role_of_card(self.name))
    text = property(lambda self: cm.get_function_of_card(self.name))

    def __repr__(self):
        rep = ('Card({ident!r})')
        return rep.format(**self.__dict__)

    def __str__(self):
        return self.name

    def __cmp__(self, card):
        return cmp(self.ident, card.ident)

    def __hash__(self):
        return self.ident

    def compare_jacks_first(self, other):
        c1, c2 = self.name.lower(), card.name.lower()
        if c1 == c2:
            return 0
        elif c1 == 'Jack':
            return -1
        elif c2 == 'Jack':
            return 1
        else:
            return cmp(c1,c2)

    def same_name(self, other):
        return self.name == other.name
