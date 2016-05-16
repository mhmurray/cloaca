#!/usr/bin/env python

from cloaca.gtr import Game
from cloaca.player import Player
from cloaca.building import Building

import cloaca.card_manager as cm

import cloaca.message as message
from cloaca.message import GameActionError

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup

import unittest

class TestMerchant(unittest.TestCase):
    """ Test handling merchant responses.
    """

    def setUp(self):
        """ This is run prior to every test.
        """
        self.game = test_setup.two_player_lead('Merchant')
        self.p1, self.p2 = self.game.players


    def test_expects_merchant(self):
        """ The Game should expect a MERCHANT action.
        """
        self.assertEqual(self.game.expected_action, message.MERCHANT)


    def test_merchant_one_from_stockpile(self):
        """ Take one card from the stockpile with merchant action.
        """
        atrium = cm.get_card('Atrium')
        self.p1.stockpile.set_content([atrium])

        a = message.GameAction(message.MERCHANT, atrium, None, False)
        self.game.handle(a)

        self.assertNotIn('Atrium', self.p1.stockpile)
        self.assertIn('Atrium', self.p1.vault)

    
    def test_merchant_non_existent_card(self):
        """ Take a non-existent card from the stockpile with merchant action.

        This invalid game action should leave the game state unchanged.
        """
        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.MERCHANT, cm.get_card('Atrium'), None, False)
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game))

    
    def test_merchant_at_vault_limit(self):
        """ Merchant a card when the vault limit has been reached.

        This invalid game action should leave the game state unchanged.
        """
        atrium, insula, dock = cm.get_cards(['Atrium', 'Insula', 'Dock'])
        self.p1.stockpile.set_content([atrium])
        self.p1.vault.set_content([insula, dock])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.MERCHANT, atrium, None, False)
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_merchant_past_higher_vault_limit(self):
        """ Merchant a card above a higher vault limit.

        This invalid game action should leave the game state unchanged.
        """
        atrium, insula, dock, palisade = cm.get_cards(['Atrium', 'Insula', 'Dock', 'Palisade'])
        self.p1.stockpile.set_content([atrium])
        self.p1.vault.set_content([insula, dock, palisade])
        self.p1.influence.append('Wood')

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.MERCHANT, atrium, None, False)
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_merchant_at_higher_vault_limit(self):
        """ Merchant a card after a higher vault limit has been achieved.

        This invalid game action should leave the game state unchanged.
        """
        atrium, insula, dock, palisade = cm.get_cards(['Atrium', 'Insula', 'Dock', 'Palisade'])
        self.p1.stockpile.set_content([atrium])
        self.p1.vault.set_content([insula, dock])
        self.p1.influence.append('Wood')

        a = message.GameAction(message.MERCHANT, atrium, None, False)
        self.game.handle(a)

        self.assertNotIn('Atrium', self.p1.stockpile)
        self.assertIn('Atrium', self.p1.vault)


if __name__ == '__main__':
    unittest.main()
