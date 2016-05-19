#!/usr/bin/env python

from cloaca.game import Game
from cloaca.player import Player
from cloaca.building import Building
from cloaca.error import GTRError

import cloaca.card_manager as cm

import cloaca.message as message

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup

import unittest

class TestPatron(unittest.TestCase):
    """ Test handling patron responses.
    """

    def setUp(self):
        self.game = test_setup.two_player_lead('Patron')
        self.p1, self.p2 = self.game.players


    def test_expects_patron(self):
        """ The Game should expect a PATRONFROMPOOL action.
        """
        self.assertEqual(self.game.expected_action, message.PATRONFROMPOOL)


    def test_patron_one_from_pool(self):
        """ Take one card from the pool with patron action.
        """
        atrium = cm.get_card('Atrium')
        self.game.pool.set_content([atrium])

        a = message.GameAction(message.PATRONFROMPOOL, atrium)
        self.game.handle(a)

        self.assertNotIn('Atrium', self.game.pool)
        self.assertIn('Atrium', self.p1.clientele)

    
    def test_patron_non_existent_card(self):
        """ Take a non-existent card from the pool with patron action.

        This invalid game action should leave the game state unchanged.
        """
        atrium, dock = cm.get_cards(['Atrium', 'Dock'])
        self.game.pool.set_content([atrium])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.PATRONFROMPOOL, dock)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_patron_at_clientele_limit(self):
        """ Patron a card when the vault limit has been reached.

        This invalid game action should leave the game state unchanged.
        """
        atrium, insula, dock = cm.get_cards(['Atrium', 'Insula', 'Dock'])
        self.game.pool.set_content([atrium])
        self.p1.clientele.set_content([insula, dock])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.PATRONFROMPOOL, atrium)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_patron_past_higher_clientele_limit(self):
        """ Patron a card above a higher vault limit.

        This invalid game action should leave the game state unchanged.
        """
        atrium, insula, dock, palisade = cm.get_cards(['Atrium', 'Insula', 'Dock', 'Palisade'])
        self.game.pool.set_content([atrium])
        self.p1.clientele.set_content([insula, dock, palisade])
        self.p1.influence.append('Wood')

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.PATRONFROMPOOL, atrium)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_patron_with_higher_clientele_limit(self):
        """ Patron a card after a higher vault limit has been achieved.

        This invalid game action should leave the game state unchanged.
        """
        atrium, insula, dock = cm.get_cards(['Atrium', 'Insula', 'Dock'])
        self.game.pool.set_content([atrium])
        self.p1.clientele.set_content([insula, dock])
        self.p1.influence.append('Wood')

        a = message.GameAction(message.PATRONFROMPOOL, atrium)
        self.game.handle(a)

        self.assertNotIn('Atrium', self.game.pool)
        self.assertIn('Atrium', self.p1.clientele)




if __name__ == '__main__':
    unittest.main()
