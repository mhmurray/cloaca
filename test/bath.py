#!/usr/bin/env python

from cloaca.game import Game
from cloaca.player import Player
from cloaca.building import Building

import cloaca.card_manager as cm

import cloaca.message as message
from cloaca.message import GameAction
from cloaca.error import GTRError, GameOver

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup
from cloaca.test.test_setup import TestDeck

import unittest

class TestBath(unittest.TestCase):

    def setUp(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.two_player_lead('Patron',
                buildings=[['Bath'],[]])

        self.p1, self.p2 = self.game.players

        self.game.pool.set_content([d.dock0, d.road0, d.wall0, d.shrine0, d.villa0, d.temple0])

        self.assertTrue(self.game._player_has_active_building(self.p1, 'Bath'))

    def test_bath_laborer(self):
        d = self.deck

        a = message.GameAction(message.PATRONFROMPOOL, d.road0)
        self.game.handle(a)

        self.assertNotIn(d.road0, self.game.pool)
        self.assertIn(d.road0, self.p1.clientele)

        self.assertEqual(self.game.expected_action, message.LABORER)
        self.assertEqual(self.game.active_player, self.p1)


    def test_bath_craftsman(self):
        d = self.deck

        a = message.GameAction(message.PATRONFROMPOOL, d.dock0)
        self.game.handle(a)

        self.assertNotIn(d.dock0, self.game.pool)
        self.assertIn(d.dock0, self.p1.clientele)

        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)
        self.assertEqual(self.game.active_player, self.p1)


    def test_bath_patron(self):
        d = self.deck

        a = message.GameAction(message.PATRONFROMPOOL, d.temple0)
        self.game.handle(a)

        self.assertNotIn(d.temple0, self.game.pool)
        self.assertIn(d.temple0, self.p1.clientele)

        self.assertEqual(self.game.expected_action, message.PATRONFROMPOOL)
        self.assertEqual(self.game.active_player, self.p1)


    def test_bath_merchant(self):
        d = self.deck

        a = message.GameAction(message.PATRONFROMPOOL, d.villa0)
        self.game.handle(a)

        self.assertNotIn(d.villa0, self.game.pool)
        self.assertIn(d.villa0, self.p1.clientele)

        self.assertEqual(self.game.expected_action, message.MERCHANT)
        self.assertEqual(self.game.active_player, self.p1)


    def test_bath_architect(self):
        d = self.deck

        a = message.GameAction(message.PATRONFROMPOOL, d.wall0)
        self.game.handle(a)

        self.assertNotIn(d.wall0, self.game.pool)
        self.assertIn(d.wall0, self.p1.clientele)

        self.assertEqual(self.game.expected_action, message.ARCHITECT)
        self.assertEqual(self.game.active_player, self.p1)


    def test_bath_legionary(self):
        d = self.deck

        a = message.GameAction(message.PATRONFROMPOOL, d.shrine0)
        self.game.handle(a)

        self.assertNotIn(d.shrine0, self.game.pool)
        self.assertIn(d.shrine0, self.p1.clientele)

        self.assertEqual(self.game.expected_action, message.LEGIONARY)
        self.assertEqual(self.game.active_player, self.p1)


if __name__ == '__main__':
    unittest.main()
