#!/usr/bin/env python

"""Test illegal combinations of GameAction arguments,
trying to prevent bad input.
"""

from cloaca.game import Game
from cloaca.player import Player
from cloaca.building import Building
from cloaca.card import Card

import cloaca.card_manager as cm

import cloaca.message as message
from cloaca.message import GameAction
from cloaca.error import GTRError, GameOver, GameActionError

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup
from cloaca.test.test_setup import TestDeck

import unittest


class TestIllegalThinkerOrLead(unittest.TestCase):

    def setUp(self):
        self.deck = d = TestDeck()

        self.game = test_setup.simple_two_player()
        self.p1, self.p2 = self.game.players

 
    def test_bad_input(self):
        d = self.deck

        with self.assertRaises(GameActionError):
            a = GameAction(message.THINKERORLEAD, None)
            self.game.handle(a)

        with self.assertRaises(GameActionError):
            a = GameAction(message.THINKERORLEAD, d.jack0)
            self.game.handle(a)

        with self.assertRaises(GameActionError):
            a = GameAction(message.THINKERORLEAD, 0)
            self.game.handle(a)

        with self.assertRaises(GameActionError):
            a = GameAction(message.THINKERORLEAD, 1)
            self.game.handle(a)

        with self.assertRaises(GameActionError):
            a = GameAction(message.THINKERORLEAD, Card(-1))
            self.game.handle(a)



if __name__ == '__main__':
    unittest.main()
