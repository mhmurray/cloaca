from cloaca.card import Card
from cloaca.error import GTRError

from collections import Counter

class Zone(object):
    """An iterable container for Card objects.
    """

    def __init__(self, cards=[], name='zone'):
        """Initialize an instance with an iterable of Card objects.

        Additionally the "name" keyword argument is used as the name
        attribute (defaults to "zone"). 
        """
        self.cards = list(cards)
        self.name = name

    def set_content(self, cards):
        """Set the content of this zone to the specified cards.

        The cards currently in this zone are lost.

        Args:
            cards -- iterable of Card objects.
        """
        if not hasattr(cards, '__iter__'):
            raise TypeError('An iterable object is required for Zone.set_content(). '
                    '{0} is not iterable.'.format(type(cards).__name__))

        for c in cards:
            if not isinstance(c, Card):
                raise GTRError('Tried to add an object to \'{0}\' '
                    'that isn\'t of class Card.'.format(self.name))

        self.cards = list(cards)


    def move_card(self, card, target_zone):
        """Move the card from this zone to the target_zone.
        
        The card can be specified by name (string) or as a Card object.
        Raise GTRError if hte card does not exist in this zone.

        Args:
            card -- Either a Card object or a card name (string).
            target_zone -- Zone object.
        """
        try:
            i = self.index(card)
        except ValueError:
            raise GTRError('Source zone "{0}" does not contain {1}. '
                    'Move to zone "{1}" failed.'
                    .format(self.name, str(card), target_zone.name))

        target_zone.append(self.pop(i))


    def pop(self, index=-1):
        """Pop a card at given index (default last), just like a list."""
        return self.cards.pop(index)
        

    def __len__(self):
        return len(self.cards)


    def __contains__(self, card):
        try:
            self.index(card)
            return True
        except ValueError:
            return False


    def intersection(self, cards):
        """Return the intersection of this zone and the iterable of Card objects as
        a collections.Counter object.
        """
        return (Counter(cards) & Counter(self.cards))


    def contains(self, cards):
        """Return True if this contains all cards in the sequence.
        
        Repeated card names must be in this zone multiple times.
        If cards is a sequence of Card objects, they are compared by Card.ident.
        If cards is empty, return True.

        Args:
            cards -- sequence of names of cards or Card objects. Do not mix strings
                and Card objects.
        """
        if len(cards) == 0:
            return True

        if type(cards[0]) is Card:
            return self.intersection(cards) == Counter(cards)

        else:
            h = Counter(map(lambda x: x.name, self.cards))
            c = Counter(cards)

            return (c & h) == c # intersection


    def equal_contents(self, other):
        """Return True if other contains exactly the same cards.

        Args:
            other -- iterable of Card objects.
        """
        return len(Counter(self.cards) - Counter(other.cards)) == 0

    
    def index(self, card):
        if isinstance(card, Card):
            try:
                return self.cards.index(card)
            except ValueError:
                raise ValueError('{0!r} is not in zone \'{1}\''
                        .format(card, self.name))

        elif isinstance(card, basestring):
            for i, c in enumerate(self.cards):
                if c.name == card: return i

            raise ValueError('{0!r} is not in zone \'{1}\''
                    .format(card, self.name))


    def extend(self, cards):
        """Add the sequence of Card objects.
        """
        for c in cards:
            if not isinstance(c, Card):
                raise GTRError( 'Tried to add an object to \'{0}\' '
                    'that isn\'t of class Card.'.format(self.name))

        self.cards.extend(cards)


    def append(self, card):
        if not isinstance(card, Card):
            raise GTRError( 'Tried to add an object to \'{0}\' '
                'that isn\'t of class Card.'.format(self.name))

        self.cards.append(card)


    def count(self, card_name):
        """Return the count of cards with the card name.
        """
        return len(filter(lambda c:c.name == card_name, self.cards))

    def get_cards(self, card_names):
        """Return Card objects corresponding to the strings in the cards list.

        Do not remove the cards from this zone.

        Raises ValueError if any of the cards aren't in this zone.
        """
        out = []
        cards = Zone(list(self.cards))

        for name in card_names:
            try:
                i = cards.index(name)
            except IndexError:
                raise ValueError('Not enough cards in this zone.')

            out.append(cards.pop(i))

        return out

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __iter__(self):
        return self.cards.__iter__()

    def __next__(self):
        return self.cards.__next__()

    def __repr__(self):
        return 'Zone({cards!r}, name={name!r})'.format(**self.__dict__)

    def __str__(self):
        return '{0}: {1}'.format(self.name, str(map(lambda x:x.name,self.cards)))
