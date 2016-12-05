#!/usr/bin/env python

from cloaca.game import Game
from cloaca.card_manager import Card
from cloaca.player import Player
from cloaca.building import Building
from cloaca.zone import Zone
import cloaca.card_manager as cm
from cloaca.error import GTRError
import cloaca.encode_binary as encode

import cloaca.message as message
from cloaca.message import GameAction

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup
from cloaca.test.test_setup import TestDeck

import unittest

class TestEncodeDecodeGame(unittest.TestCase):
    """Tests to ensure the consistency of the encoding and decoding
    process. Encode a game, decode, and re-encode the result.
    A byte-wise comparison is done on the two encoded games.
    """

    def encode_decode_compare_game(self, game):
        """Encode a game, decode it, and re-encode it. Compare the 
        two encoded copies byte-wise.

        Repeat the process with a privatized version of the game for
        each player.
        """
        game_str = encode.game_to_str(game)
        game2 = encode.str_to_game(game_str)
        game_str2 = encode.game_to_str(game)

        self.assertEqual(game_str, game_str2)

        for p in game.players:
            game_priv = game.privatized_game_state_copy(p.name)
            game_str = encode.game_to_str(game_priv)
            game_priv2 = encode.str_to_game(game_str)
            game_str2 = encode.game_to_str(game_priv)

            self.assertEqual(game_str, game_str2)

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

    def test_start_frames(self):
        game = Game()
        game.add_player(0, 'p0')
        game.add_player(1, 'p1')
        game.start()

        self.encode_decode_compare_game(game)

    def test_two_player_lead(self):
        game = test_setup.two_player_lead('Patron')
        self.encode_decode_compare_game(game)

    def test_two_player_lead_clients(self):
        game = test_setup.two_player_lead('Patron',
                clientele=[['Temple'],['Fountain']])
        self.encode_decode_compare_game(game)

    def test_two_player_lead_buildings(self):
        game = test_setup.two_player_lead('Patron',
                buildings=[['Temple', 'Atrium'],['Fountain']])
        self.encode_decode_compare_game(game)

    def test_two_player_complicated(self):
        game = test_setup.two_player_lead('Legionary',
                buildings=[['Temple', 'Bridge'],['Fountain']],
                clientele=[['Road', 'Atrium', 'Dock'],['Fountain']],
                )
        d = TestDeck()
        game.players[0].hand.set_content([d.wall0, d.foundry0])
        game.players[1].hand.set_content([d.bridge0, d.storeroom0])
        game.players[1].stockpile.set_content([d.bridge1, d.storeroom1])

        a = GameAction(message.LEGIONARY, d.wall0, d.foundry0)
        game.handle(a)

        self.encode_decode_compare_game(game)
        self.encode_decode_compare_game(game.privatized_game_state_copy('p0'))


def _encode_decode(game):
    """Encode and then decode a game."""
    return encode.str_to_game(encode.game_to_str(game))

class TestPublicZoneEncode(unittest.TestCase):
    """Test the python objects that are encoded and decoded to ensure
    they are the same.
    """

    def setUp(self):
        """Initialize a three-player game before the first turn."""
        self.d = TestDeck()
        self.game = test_setup.simple_n_player(3, deck=self.d)
        self.p0, self.p1, self.p2 = self.game.players

    def test_library(self):
        g = _encode_decode(self.game)

        self.assertEqual(g.library, self.game.library)
        self.assertEqual(g.pool, self.game.pool)
        self.assertEqual(g.jacks, self.game.jacks)





if __name__ == '__main__':
    unittest.main()
