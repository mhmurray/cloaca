#!/usr/bin/env python

class Card(object):
    """Each card has an identity number, different for even duplicate cards.

    Comparison between cards can use __eq__() for comparing names, or 
    identical() to compare ident numbers.

        Card(123, 'Insula') == Card(101, 'Insula') # True
        Card(123, 'Insula') == Card(123, 'Dock') # False
        Card(123, 'Insula').identical(Card(123, 'Insula')) # True
        Card(123, 'Insula').identical(Card(101, 'Insula')) # False

    Members:
    ident -- unique id number, different for all cards
    name -- name of foundation, or 'Jack'
    material -- string like 'Brick', 'Rubble'. None for Jacks.
    value -- integer 1-3 or 0 for Jacks
    role -- string like 'Merchant', 'Laborer'. None for Jacks.
    text -- rules text of the card. Empty string for Jacks.
    """

    def __init__(self, ident, name, material, value, role, text):
        self.ident = ident
        self.name = name
        self.material = material
        self.value = value
        self.role = role
        self.text = text

    def __repr__(self):
        rep = ('Card({ident!r},{name!r},{material!r},'
               '{value!r},{role!r},{text!r})')
        return rep.format(**self.__dict__)

    def __str__(self):
        return self.name

    def __eq__(self, card):
        return self.name == card.name

    def identical(self, card):
        """Compare cards by ident number. Don't compare any other members.
        """
        return self.ident == card.ident
    
