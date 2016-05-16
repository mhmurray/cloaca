#!/usr/bin/env python

from cloaca.game import Game
from cloaca.player import Player
from cloaca.building import Building
import cloaca.message as message
import cloaca.card_manager as cm
from cloaca.card import Card

import cloaca.test.test_setup as test_setup

import unittest

class TestHandleThinker(unittest.TestCase):
    """ Test handling Thinker responses
    """

    def setUp(self):
        """ This is run prior to every test.
        """
        self.game = test_setup.simple_two_player()
        self.p1, self.p2 = self.game.players

        a = message.GameAction(message.THINKERORLEAD, True)
        self.game.handle(a)


    def test_card_piles_full(self):
        """ Test that the jack and library piles aren't empty.
        """
        self.assertTrue(len(self.game.library)>5)
        self.assertEqual(len(self.game.jacks), 6)


    def test_waiting_for_thinker(self):
        """ Tests that the game is expecting a THINKERTYPE.
        """
        self.assertEqual(self.game.expected_action, message.THINKERTYPE)

        a = message.GameAction(message.SKIPTHINKER, False)

        self.assertRaises(Exception, self.game.handle, a)
        

    def test_thinker_for_five(self):
        """ Test thinker from empty hand to 5 orders cards.
        """
        a = message.GameAction(message.THINKERTYPE, False)

        self.game.handle(a)

        self.assertEqual(len(self.p1.hand), 5)


    def test_thinker_for_one(self):
        self.p1.hand.set_content(cm.get_cards(['Latrine']*5))
        self.assertEqual(len(self.p1.hand), 5)

        a = message.GameAction(message.THINKERTYPE, False)
        self.game.handle(a)

        self.assertEqual(len(self.p1.hand), 6)
        self.assertFalse('Jack' in self.p1.hand)

        
    def test_thinker_for_jack_from_empty(self):
        """Thinker for Jack with empty hand should yield a hand of one Jack.
        """
        a = message.GameAction(message.THINKERTYPE, True)
        self.game.handle(a)

        self.assertEqual(len(self.p1.hand), 1)
        self.assertIn('Jack', self.p1.hand)


    def test_thinker_for_jack_from_full(self):
        """ Thinker for Jack with full hand should draw Jack.
        """
        self.p1.hand.set_content(cm.get_cards(['Latrine']*5))

        a = message.GameAction(message.THINKERTYPE, True)
        self.game.handle(a)

        self.assertEqual(len(self.p1.hand), 6)
        self.assertIn('Jack', self.p1.hand)

    def test_thinker_for_four_cards_with_one_orders(self):
        """ Thinker for cards with 1 card in hand should draw 4.
        Test with initial card being a Jack or Latrine
        """
        self.p1.hand.set_content(cm.get_cards(['Latrine']))

        a = message.GameAction(message.THINKERTYPE, False)
        self.game.handle(a)

        self.assertEqual(len(self.p1.hand), 5)

    def test_thinker_for_four_cards_with_one_jack(self):
        """ Thinker for cards with 1 card in hand should draw 4.
        Test with initial card being a Jack or Latrine
        """
        self.p1.hand.set_content(cm.get_cards(['Jack']))

        a = message.GameAction(message.THINKERTYPE, False)
        self.game.handle(a)

        self.assertEqual(len(self.p1.hand), 5)

    # Thinker to empty deck ends game
    # Thinker from empty Jack pile not allowed


if __name__ == '__main__':
    unittest.main()
