#!/usr/bin/env python

from cloaca.zone import Zone
import cloaca.card_manager as cm
from cloaca.card import Card

import unittest


class TestZone(unittest.TestCase):
    """Tests for the Zone object.
    """

    def test_get_cards(self):
        z = Zone(cm.get_cards(['Latrine', 'Latrine', 'Circus', 'Dock', 'Latrine']))

        l = z.get_cards(['Latrine', 'Latrine', 'Dock'])

        z2 = Zone(l)

        self.assertEqual(z2.count('Latrine'), 2)
        self.assertEqual(z2.count('Dock'), 1)
        self.assertEqual(len(l), 3)

    def test_iterating(self):
        l = ['Latrine', 'Latrine', 'Circus', 'Dock', 'Latrine']
        z = Zone(cm.get_cards(l))

        l2 = [c.name for c in z]

        self.assertEqual(l2, l)


    def test_get_cards_raises(self):
        z = Zone(cm.get_cards(['Latrine', 'Latrine', 'Circus', 'Dock', 'Latrine']))

        with self.assertRaises(ValueError):
            z.get_cards(['Latrine', 'Dock', 'Dock'])


if __name__ == '__main__':
    unittest.main()
