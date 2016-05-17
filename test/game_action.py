#!/usr/bin/env python

from cloaca.game import Game
from cloaca.player import Player
from cloaca.building import Building

import cloaca.message as message
from cloaca.message import GameAction, Command
from cloaca.error import GTRError, ParsingError, GameActionError

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup

import json
import unittest

class TestGameActionJSON(unittest.TestCase):
    """Test GameAction conversion to and from JSON.
    """

    def test_to_json(self):
        """Convert GameAction to JSON.
        """
        a = GameAction(message.THINKERORLEAD, True)

        a_json = a.to_json()

        d = json.loads(a_json)

        self.assertIn('action', d.keys())
        self.assertIn('args', d.keys())
        
        action, args = d['action'], d['args']

        self.assertEqual(action, message.THINKERORLEAD)
        self.assertEqual(args, [True])

    def test_multiple_args_to_json(self):
        """Convert GameAction to JSON.
        """
        a = GameAction(message.LEADROLE, 'Craftsman', 1, 106, 107, 108)

        a_json = a.to_json()

        d = json.loads(a_json)
        action, args = d['action'], d['args']

        self.assertEqual(action, message.LEADROLE)
        self.assertEqual(args, ['Craftsman', 1, 106, 107, 108])

    def test_from_json(self):
        """Convert JSON dictionary to GameAction.
        """
        a_json = '{"action": 0, "args": [true]}'
        a = GameAction.from_json(a_json)

        self.assertEqual(a.action, message.THINKERORLEAD)
        self.assertEqual(a.args, [True])

    def test_from_bad_json(self):
        """Failure to convert bad JSON raises ValueError.
        """
        a_json = '{"act]]]}' # not valid JSON

        with self.assertRaises(ParsingError):
            a = GameAction.from_json(a_json)

    def test_from_json_bad_action(self):
        """Raises ParsingError if the valid JSON doesn't
        represent a valid GameAction.
        """
        with self.assertRaises(GameActionError):
            a = GameAction.from_json('{"action": -1, "args": [true]}')

        with self.assertRaises(GameActionError):
            a = GameAction.from_json('{"action": 0, "args": []}')

        with self.assertRaises(GameActionError):
            a = GameAction.from_json('{"action": 0, "args": [true, false]}')


class TestCommandJSON(unittest.TestCase):
    """Test Command conversion to and from JSON.
    """

    def test_to_json(self):
        """Convert Command to JSON.
        """
        a = GameAction(message.THINKERORLEAD, True)
        c = Command(1, a)

        c_json = c.to_json()

        d = json.loads(c_json)

        self.assertIn('action', d.keys())
        self.assertIn('game', d.keys())
        
        action, args, game = d['action']['action'], d['action']['args'], d['game']

        self.assertEqual(action, message.THINKERORLEAD)
        self.assertEqual(args, [True])
        self.assertEqual(game, 1)

    def test_from_json(self):
        """Convert JSON dictionary to Command.
        """
        c_json = '{"game":1, "action":{"action": 0, "args": [true]}}'
        c = Command.from_json(c_json)

        self.assertEqual(c.action.action, message.THINKERORLEAD)
        self.assertEqual(c.game, 1)
        self.assertEqual(c.action.args, [True])

    def test_from_bad_json(self):
        """Failure to convert bad JSON raises ParsingError.
        """
        c_json = '{"act]]]}' # not valid JSON

        with self.assertRaises(ParsingError):
            c = Command.from_json(c_json)

    def test_from_json_bad_command(self):
        """Raises GameActionError if the valid JSON doesn't
        represent a valid Command.
        """
        c_json = '{"game":"notagame", "action":{"action": 0, "args": [true]}}'
        with self.assertRaises(GameActionError):
            a = Command.from_json(c_json)

        c_json = '{"game":"0", "action":{"args": [true]}}'
        with self.assertRaises(ParsingError):
            a = Command.from_json(c_json)


if __name__ == '__main__':
    unittest.main()
