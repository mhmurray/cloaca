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
            raise TypeError('Card.ident must be an integer, received \'{0!s}\''.format(ident))
        self.ident = ident
        if self.ident >= len(cm.standard_deck()):
            raise TypeError('Card.ident out of range: {0}'.format(ident))

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
