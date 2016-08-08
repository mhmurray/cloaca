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

class TestLaborer(unittest.TestCase):

    def setUp(self):
        """This is run prior to every test.
        """
        d = self.deck = TestDeck()
        self.game = test_setup.two_player_lead('Laborer', deck=d)
        self.p1, self.p2 = self.game.players


    def test_expects_laborer(self):
        self.assertEqual(self.game.expected_action, message.LABORER)
        self.assertEqual(self.game.active_player, self.p1)


    def test_laborer_one_from_pool(self):
        d = self.deck
        self.game.pool.set_content([d.atrium0])

        a = message.GameAction(message.LABORER, d.atrium0)
        self.game.handle(a)

        self.assertNotIn(d.atrium0, self.game.pool)
        self.assertIn(d.atrium0, self.p1.stockpile)

    
    def test_laborer_non_existent_card(self):
        """Take a non-existent card from the pool with laborer action.

        This invalid game action should leave the game state unchanged.
        """
        d = self.deck
        self.game.pool.set_content([d.atrium0])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.LABORER, d.dock0)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


class TestLaborerWithDock(unittest.TestCase):

    def setUp(self):
        self.deck = TestDeck()
        self.game = test_setup.two_player_lead('Laborer',
                buildings=[['Dock'],[]],
                deck = self.deck)

        self.p1, self.p2 = self.game.players


    def test_laborer_from_pool_and_hand(self):
        d = self.deck

        self.game.pool.set_content([d.shrine0])
        self.p1.hand.set_content([d.foundry0])

        a = message.GameAction(message.LABORER, d.foundry0, d.shrine0)
        self.game.handle(a)

        self.assertIn(d.shrine0, self.p1.stockpile)
        self.assertIn(d.foundry0, self.p1.stockpile)
        
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_laborer_hand_only(self):
        d = self.deck

        self.game.pool.set_content([d.shrine0])
        self.p1.hand.set_content([d.foundry0])

        a = message.GameAction(message.LABORER, d.foundry0)
        self.game.handle(a)

        self.assertIn(d.shrine0, self.game.pool)
        self.assertIn(d.foundry0, self.p1.stockpile)
        
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


class TestStoreroom(unittest.TestCase):

    def setUp(self):
        self.deck = TestDeck()
        self.game = test_setup.two_player_lead('Laborer',
                clientele=[['Temple'],[]],
                buildings=[['Storeroom'],[]],
                deck = self.deck)

        self.p1, self.p2 = self.game.players


    def test_laborer_with_storeroom_client(self):
        d = self.deck

        self.assertTrue(self.game._player_has_active_building(self.p1, 'Storeroom'))

        self.game.pool.set_content([d.shrine0, d.foundry0])

        a = message.GameAction(message.LABORER, d.shrine0)
        self.game.handle(a)

        a = message.GameAction(message.LABORER, d.foundry0)
        self.game.handle(a)

        self.assertIn(d.shrine0, self.p1.stockpile)
        self.assertIn(d.foundry0, self.p1.stockpile)
        
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)



if __name__ == '__main__':
    unittest.main()
