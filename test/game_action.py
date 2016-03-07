#!/usr/bin/env python

from cloaca.gtr import Game
from cloaca.gamestate import GameState
from cloaca.player import Player
from cloaca.building import Building

import cloaca.message as message
from cloaca.message import BadGameActionError, parse_action, GameAction

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup


import unittest

class TestParseGameAction(unittest.TestCase):
    """Test GameAction utility method to parse from string
    """

    def setUp(self):
        """This is run prior to every test.
        """
        pass

    def test_thinkorlead(self):
        """Thinker or lead is representative of all GameAction instances
        with a single required boolean argument.
        """
        a = parse_action('0,True')

        self.assertEqual(a, GameAction(message.THINKERORLEAD, True))
        self.assertNotEqual(a, GameAction(message.THINKERORLEAD, False))

        a = parse_action('0,False')

        self.assertEqual(a, GameAction(message.THINKERORLEAD, False))
        self.assertNotEqual(a, GameAction(message.THINKERORLEAD, True))

        with self.assertRaises(BadGameActionError):
            a = parse_action('0')

        with self.assertRaises(BadGameActionError):
            a = parse_action('0,None')

        with self.assertRaises(BadGameActionError):
            a = parse_action('0,4')

        with self.assertRaises(BadGameActionError):
            a = parse_action('0,Bar')

        with self.assertRaises(BadGameActionError):
            a = parse_action('0,True,True')

        with self.assertRaises(BadGameActionError):
            a = parse_action('0,False,False')

    def test_joingame(self):
        """JOINGAME is representative of GameAction instances with a single
        integer argument.
        """
        a = parse_action('26,1')
        self.assertEqual(a, GameAction(message.JOINGAME, 1))

        a = parse_action('26,0')
        self.assertEqual(a, GameAction(message.JOINGAME, 0))
        self.assertNotEqual(a, GameAction(message.JOINGAME, 1))

        with self.assertRaises(BadGameActionError):
            parse_action('26,')

        with self.assertRaises(BadGameActionError):
            parse_action('26')

        with self.assertRaises(BadGameActionError):
            parse_action('26,True')

        with self.assertRaises(BadGameActionError):
            parse_action('26,2.5')

        with self.assertRaises(BadGameActionError):
            parse_action('26,0,1')


if __name__ == '__main__':
    unittest.main()
