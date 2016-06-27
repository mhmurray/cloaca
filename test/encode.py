#!/usr/bin/env python

from cloaca.game import Game
from cloaca.player import Player
from cloaca.building import Building
from cloaca.zone import Zone
import cloaca.card_manager as cm
from cloaca.error import GTRError
import cloaca.encode as encode

import cloaca.message as message

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup

import unittest

class TestEncodeGame(unittest.TestCase):

    def setUp(self):
        """ This is run prior to every test.
        """
        self.game = test_setup.two_player_lead('Craftsman')

    def test_encode(self):
        game_dict = encode.encode(self.game)
        self.assertIsInstance(game_dict, dict)

        print str(game_dict)
        game_json = encode.game_to_json(self.game)
        game = encode.json_to_game(game_json)
        game_json2 = encode.game_to_json(game)

        self.assertEqual(game_json, game_json2)

if __name__ == '__main__':
    unittest.main()
