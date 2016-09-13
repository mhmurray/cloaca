#!/usr/bin/env python

from cloaca.game import Game
from cloaca.card_manager import Card
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
    """Comparing the stack frames is tricky. They are somewhat-nested
    structures with arbitrary functions in the Frame objects, so
    element-by-element comparison is not easy. Instead, we resort
    to comparing the str(frame.__dict__) for each Frame or the JSON
    string obtained with encode.game_to_json(game).
    """

    def encode_decode_compare_game(self, game):
        """Using encode.game_to_json and encode.json_to_game,
        encode the game, decode the game, and encode it again,
        then assert that the JSON strings are the same.
        """
        game_dict = encode.encode(game)
        self.assertIsInstance(game_dict, dict)

        game_json = encode.game_to_json(game)
        game = encode.json_to_game(game_json)
        game_json2 = encode.game_to_json(game)

        self.assertEqual(game_json, game_json2)

    def test_empty_game(self):
        game = Game()
        self.encode_decode_compare_game(game)

    def test_library(self):
        game = Game()
        game._init_library()
        self.jacks = Zone([Card(i) for i in range(6)])
        self.encode_decode_compare_game(game)

    def test_sites(self):
        game = Game()
        game._init_sites(2)
        self.encode_decode_compare_game(game)

    def test_player(self):
        game = Game()
        game.add_player(0, 'p0')
        self.encode_decode_compare_game(game)

    def test_all_common_piles(self):
        game = Game()
        game.add_player(0, 'p0')
        game.add_player(1, 'p1')
        game._init_common_piles(2)
        self.encode_decode_compare_game(game)

    # @unittest.skip('fails...')
    def test_start_frames(self):
        game = Game()
        game.add_player(0, 'p0')
        game.add_player(1, 'p1')
        game.start()

        from pprint import pprint
        pprint(encode.encode(game))
        pprint(encode.decode_game(encode.encode(game)).__dict__)
        pprint(game.__dict__)

        # self.encode_decode_compare_game(game)

    def test_frame(self):
        game = Game()
        game.add_player(0, 'p0')
        game.add_player(1, 'p1')
        game.start()

        frame = game._current_frame
        frame_dict = encode.encode(frame)
        frame_recovered = encode.decode_frame(frame_dict)
        frame_dict2 = encode.encode(frame_recovered)
        self.assertEqual(str(frame_dict), str(frame_dict2))
        
        for frame in game.stack.stack:
            frame_dict = encode.encode(frame)
            frame_recovered = encode.decode_frame(frame_dict)
            frame_dict2 = encode.encode(frame_recovered)
            self.assertEqual(str(frame_dict), str(frame_dict2))

    def test_frame_player_conversion(self):
        game = test_setup.two_player_lead('Craftsman', follow=True)

        game_dict = encode.encode(game)
        game_recovered = encode.decode_game(game_dict)
        game_dict2 = encode.encode(game_recovered)

        self.assertEqual(str(game._current_frame.__dict__),
                str(game_recovered._current_frame.__dict__))

        for fr, fr2 in zip(game.stack.stack, game_recovered.stack.stack):
            self.assertEqual(str(fr.__dict__), str(fr2.__dict__))



if __name__ == '__main__':
    unittest.main()
