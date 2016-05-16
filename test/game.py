#!/usr/bin/env python

from cloaca.gtr import Game
from cloaca import message
from cloaca.error import GTRError

import unittest
from uuid import uuid4

class TestGame(unittest.TestCase):
    """Test Game interface.
    """

    def test_add_player(self):

        g = Game()
        g.add_player(uuid4(), 'p1')
        gs = g.game_state

        self.assertEqual(len(gs.players), 1)

        g.add_player(uuid4(), 'p2')

        self.assertEqual(len(gs.players), 2)


    def test_start(self):
        """Starting a game puts orders and jacks in the hands of the players,
        populates the pool, and sets the turn number to 1
        """

        g = Game()
        gs = g.game_state
        g.add_player(uuid4(), 'p1')
        g.add_player(uuid4(), 'p2')

        g.start()
        
        self.assertEqual(len(gs.jacks), 4)

        # We don't know how many cards because of tiebreakers in determining
        # who goes first but each player at least needs 4 cards + 1 in the pool
        self.assertTrue(len(gs.library) <= 134)
        self.assertTrue(len(gs.library) > 0)

        for p in gs.players:
            self.assertIn('Jack', p.hand)

        self.assertTrue(g.is_started)
        self.assertEqual(gs.expected_action, message.THINKERORLEAD)


    def test_start_again(self):
        """Starting an already-started game raises a GTRError.
        """

        g = Game()
        g.add_player(uuid4(), 'p1')
        g.add_player(uuid4(), 'p2')

        g.start()

        with self.assertRaises(GTRError):
            g.start()


    def test_add_player_after_start(self):
        """Attempting to add a player after the game has started throws
        a GTRError.
        """
        g = Game()
        g.add_player(uuid4(), 'p1')
        g.add_player(uuid4(), 'p2')

        g.start()

        with self.assertRaises(GTRError):
            g.add_player(uuid4(), 'p3')


    def test_add_too_many_players(self):
        """Adding a sixth player raises GTRError.
        """
        g = Game()
        g.add_player(uuid4(), 'p1')
        g.add_player(uuid4(), 'p2')
        g.add_player(uuid4(), 'p3')
        g.add_player(uuid4(), 'p4')
        g.add_player(uuid4(), 'p5')

        with self.assertRaises(GTRError):
            g.add_player(uuid4(), 'p6')


    def test_add_player_with_same_name(self):
        """Adding two players with the same name raises GTRError.
        """
        g = Game()
        g.add_player(uuid4(), 'p1')

        with self.assertRaises(GTRError):
            g.add_player(uuid4(), 'p1')


if __name__ == '__main__':
    unittest.main()
