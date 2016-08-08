#!/usr/bin/env python

from cloaca.game import Game
from cloaca.player import Player
from cloaca.building import Building
from cloaca.error import GTRError

import cloaca.card_manager as cm

import cloaca.message as message

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup
from test_setup import TestDeck

import unittest

class TestMerchant(unittest.TestCase):
    """ Test handling merchant responses.
    """

    def setUp(self):
        """ This is run prior to every test.
        """
        self.deck = TestDeck()
        self.game = test_setup.two_player_lead('Merchant', deck=self.deck)
        self.p1, self.p2 = self.game.players


    def test_expects_merchant(self):
        """ The Game should expect a MERCHANT action.
        """
        self.assertEqual(self.game.expected_action, message.MERCHANT)


    def test_merchant_one_from_stockpile(self):
        """ Take one card from the stockpile with merchant action.
        """
        d = self.deck
        self.p1.stockpile.set_content([d.atrium0])

        a = message.GameAction(message.MERCHANT, False, d.atrium0)
        self.game.handle(a)

        self.assertNotIn(d.atrium0, self.p1.stockpile)
        self.assertIn(d.atrium0, self.p1.vault)

    
    def test_merchant_non_existent_card(self):
        """ Take a non-existent card from the stockpile with merchant action.

        This invalid game action should leave the game state unchanged.
        """
        d = self.deck
        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.MERCHANT, False, d.atrium0)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))

    
    def test_merchant_at_vault_limit(self):
        """ Merchant a card when the vault limit has been reached.

        This invalid game action should leave the game state unchanged.
        """
        d = self.deck
        self.p1.stockpile.set_content([d.atrium0])
        self.p1.vault.set_content([d.insula, d.dock])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.MERCHANT, False, d.atrium0)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_merchant_past_higher_vault_limit(self):
        """ Merchant a card above a higher vault limit.

        This invalid game action should leave the game state unchanged.
        """
        d = self.deck
        self.p1.stockpile.set_content([d.atrium0])
        self.p1.vault.set_content([d.insula, d.dock, d.palisade])
        self.p1.influence.append('Wood')

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.MERCHANT, False, d.atrium0)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_merchant_at_higher_vault_limit(self):
        """ Merchant a card after a higher vault limit has been achieved.

        This invalid game action should leave the game state unchanged.
        """
        d = self.deck
        self.p1.stockpile.set_content([d.atrium0])
        self.p1.vault.set_content([d.insula, d.dock])
        self.p1.influence.append('Wood')

        a = message.GameAction(message.MERCHANT, False, d.atrium0)
        self.game.handle(a)

        self.assertNotIn(d.atrium0, self.p1.stockpile)
        self.assertIn(d.atrium0, self.p1.vault)


if __name__ == '__main__':
    unittest.main()
