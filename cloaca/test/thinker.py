#!/usr/bin/env python

from cloaca.game import Game
from cloaca.player import Player
from cloaca.building import Building
import cloaca.message as message
import cloaca.card_manager as cm
from cloaca.card import Card
from cloaca.error import GTRError, GameOver

import cloaca.test.test_setup as test_setup
from test_setup import TestDeck
from cloaca.test.monitor import Monitor

import unittest

class TestHandleThinker(unittest.TestCase):

    def setUp(self):
        """ This is run prior to every test.
        """
        self.deck = TestDeck()

        self.game = test_setup.simple_two_player()
        self.p1, self.p2 = self.game.players

        a = message.GameAction(message.THINKERORLEAD, True)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.THINKERTYPE)


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

        with self.assertRaises(GTRError):
            self.game.handle(a)
        

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

    def test_empty_deck_ends_game(self):
        """An empty deck ends the game immediately. Test thinker
        to empty deck. (The other way is using a Fountain.)
        """
        d = self.deck

        self.game.library.set_content([d.road, d.road, d.road, d.road, d.road])
        self.p1.hand.set_content([])

        a = message.GameAction(message.THINKERTYPE, False)

        with self.assertRaises(GameOver):
            self.game.handle(a)

        self.assertIsNotNone(self.game.winners)


    def test_thinker_from_empty_jack_pile(self):
        """Raise GTRError if thinker from empty Jack pile is requested.
        """
        d = self.deck

        self.game.jacks.set_content([])
        a = message.GameAction(message.THINKERTYPE, True)

        mon = Monitor()
        mon.modified(self.game)

        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_temple_hand_limit(self):
        d = self.deck

        self.p1.hand.set_content([])
        self.p1.buildings.append(Building(d.temple, 'Marble', complete=True))

        a = message.GameAction(message.THINKERTYPE, False)
        self.game.handle(a)

        self.assertEqual(len(self.p1.hand), 9)

    def test_shrine_hand_limit(self):
        d = self.deck

        self.p1.hand.set_content([])
        self.p1.buildings.append(Building(d.shrine, 'Brick', complete=True))

        a = message.GameAction(message.THINKERTYPE, False)
        self.game.handle(a)

        self.assertEqual(len(self.p1.hand), 7)

    def test_shrine_and_temple_hand_limit(self):
        d = self.deck

        self.p1.hand.set_content([])
        self.p1.buildings.append(Building(d.shrine, 'Brick', complete=True))
        self.p1.buildings.append(Building(d.temple, 'Marble', complete=True))

        a = message.GameAction(message.THINKERTYPE, False)
        self.game.handle(a)

        self.assertEqual(len(self.p1.hand), 11)

    def test_think_past_higher_hand_limit(self):
        d = self.deck

        self.p1.hand.set_content([
                d.road, d.road, d.road,
                d.road, d.road, d.road,
                d.wall, d.wall, d.wall])

        self.p1.buildings.append(Building(d.temple, 'Marble', complete=True))

        a = message.GameAction(message.THINKERTYPE, False)
        self.game.handle(a)

        self.assertEqual(len(self.p1.hand), 10)



if __name__ == '__main__':
    unittest.main()
