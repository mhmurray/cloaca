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
import copy


class TestObjectComparison(unittest.TestCase):
    """Test equality comparison for objects.
    """

    def setUp(self):
        self.game = test_setup.two_player_lead('Craftsman',
                buildings=[['Temple', 'Wall'], ['Road']],
                clientele=[['Fountain'],['Dock']])

        self.p0, self.p1 = self.game.players

    def test_game(self):
        game_copy = copy.deepcopy(self.game)

        self.assertEqual(game_copy, self.game)
        game_copy.used_oot = not game_copy.used_oot
        self.assertNotEqual(game_copy, self.game)

    def test_player(self):
        d = TestDeck()
        for p in self.game.players:
            p_copy = copy.deepcopy(p)
            
            self.assertEqual(p_copy, p)
            p_copy.hand.append(d.road0)
            self.assertNotEqual(p_copy, p)

    def test_zone(self):
        d = TestDeck()
        pool_copy = copy.deepcopy(self.game.pool)

        self.assertEqual(pool_copy, self.game.pool)
        pool_copy.cards.append(d.road0)
        self.assertNotEqual(pool_copy, self.game.pool)

    def test_frame(self):
        current_frame_copy = copy.deepcopy(self.game._current_frame)

        self.assertEqual(current_frame_copy, self.game._current_frame)
        current_frame_copy.function_name = 'test_function'
        self.assertNotEqual(current_frame_copy, self.game._current_frame)

    def test_stack(self):
        stack_copy = copy.deepcopy(self.game.stack)

        self.assertEqual(stack_copy, self.game.stack)
        stack_copy.stack[0].function_name = 'test_function'
        self.assertNotEqual(stack_copy, self.game.stack)


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

    def test_public_zones(self):
        g = _encode_decode(self.game)
        self.assertEqual(g.library, self.game.library)
        self.assertEqual(g.pool, self.game.pool)
        self.assertEqual(g.jacks, self.game.jacks)

    def test_privatized_public_zones(self):
        gpriv = self.game.privatized_game_state_copy(self.p0.name)

        g = _encode_decode(gpriv)
        self.assertEqual(g.library, gpriv.library)
        self.assertEqual(g.pool, gpriv.pool)
        self.assertEqual(g.jacks, gpriv.jacks)


class TestStack(unittest.TestCase):
    """Test the python objects that are encoded and decoded to ensure
    they are the same.
    """

    def setUp(self):
        """Initialize a three-player game before the first turn."""
        self.d = TestDeck()
        self.game = test_setup.simple_n_player(3, deck=self.d)
        self.p0, self.p1, self.p2 = self.game.players

    def test_stack(self):
        g = _encode_decode(self.game)

        self.assertEqual(g.stack, self.game.stack)

    def test_privatized_stack(self):
        gpriv = self.game.privatized_game_state_copy(self.p0.name)

        g = _encode_decode(gpriv)
        self.assertEqual(g.stack, gpriv.stack)


class TestPlayerProperties(unittest.TestCase):
    """Test the python objects that are encoded and decoded to ensure
    they are the same.
    """

    def setUp(self):
        """Initialize a three-player game before the first turn."""
        self.d = TestDeck()
        self.game = test_setup.simple_n_player(3, deck=self.d)
        self.p0, self.p1, self.p2 = self.game.players

        self.p0.fountain_card = self.d.road0

        self.p0.influence = ['Rubble', 'Wood']
        self.p1.influence = []
        self.p1.influence = ['Rubble', 'Rubble', 'Marble', 'Wood', 'Marble']

        self.p1.n_camp_actions = 4

        self.p0.performed_craftsman = True

    def test_players(self):
        g = _encode_decode(self.game)
        for p, q in zip(self.game.players, g.players):
            self.assertEqual(p, q)

    def test_privatized_players(self):
        gpriv = self.game.privatized_game_state_copy(self.p0.name)
        g = _encode_decode(gpriv)
        for p, q in zip(gpriv.players, g.players):
            self.assertEqual(p, q)


class TestPlayerBuildings(unittest.TestCase):
    """Test the python objects that are encoded and decoded to ensure
    they are the same.
    """

    def setUp(self):
        """Initialize a three-player game before the first turn."""
        d = self.d = TestDeck()
        self.game = test_setup.simple_n_player(3, deck=self.d)
        self.p0, self.p1, self.p2 = self.game.players
        
        self.p0.buildings.extend([
                Building(d.road0, 'Rubble', [d.road1], [d.road2], True),
                Building(d.statue0, 'Wood', [d.temple0], [], True),
                Building(d.temple0, 'Marble', [], [], False),
                ])

        self.p1.buildings.extend([
                Building(d.wall0, 'Concrete', [d.bridge1, d.bridge0], [d.wall2], True),
                Building(d.statue0, 'Marble', [d.temple0], [], True),
                ])

    def test_players_equal(self):
        g = _encode_decode(self.game)
        for p, q in zip(self.game.players, g.players):
            self.assertEqual(p, q)

    def test_privatized_players(self):
        gpriv = self.game.privatized_game_state_copy(self.p0.name)
        g = _encode_decode(gpriv)
        for p, q in zip(gpriv.players, g.players):
            self.assertEqual(p, q)


class TestPlayerZone(unittest.TestCase):
    """Test the python objects that are encoded and decoded to ensure
    they are the same.
    """

    def setUp(self):
        """Initialize a three-player game with a variety of
        cards in each player's zones.
        """
        d = self.d = TestDeck()
        self.game = test_setup.simple_n_player(3, deck=self.d)
        self.p0, self.p1, self.p2 = self.game.players

        self.p0.hand.set_content([d.jack0, d.latrine0])
        self.p1.hand.set_content([d.atrium0, d.jack1])
        self.p2.hand.set_content([d.jack3, d.jack2])

        self.p0.camp.set_content([d.jack4])
        self.p1.camp.set_content([])
        self.p2.camp.set_content([d.jack5])

        self.p0.stockpile.set_content([d.temple0, d.temple1])
        self.p1.stockpile.set_content([d.road0, d.wall0])
        self.p2.stockpile.set_content([d.insula0, d.insula1, d.insula2, d.insula3])

        self.p0.vault.set_content([d.foundry0, d.temple2])
        self.p1.vault.set_content([d.road1, d.wall1])
        self.p2.vault.set_content([d.archway0, d.archway1, d.archway2])

        self.p0.clientele.set_content([d.villa0, d.fountain0])
        self.p1.clientele.set_content([])
        self.p2.clientele.set_content([d.dock0, d.dock1, d.circus0])

        self.p0.revealed.set_content([d.latrine0])
        self.p1.revealed.set_content([d.atrium0, d.atrium1])
        self.p2.revealed.set_content([])

        self.p0.prev_revealed.set_content([d.latrine1])
        self.p1.prev_revealed.set_content([d.school0, d.school1])
        self.p2.prev_revealed.set_content([])

        self.p0.clients_given.set_content([])
        self.p1.clients_given.set_content([d.school1])
        self.p2.clients_given.set_content([])

    def test_player_zones(self):
        g = _encode_decode(self.game)

        for p, q in zip(self.game.players, g.players):
            self.assertEqual(p.hand, q.hand)
            self.assertEqual(p.stockpile, q.stockpile)
            self.assertEqual(p.camp, q.camp)
            self.assertEqual(p.clientele, q.clientele)
            self.assertEqual(p.vault, q.vault)
            self.assertEqual(p.revealed, q.revealed)
            self.assertEqual(p.prev_revealed, q.prev_revealed)
            self.assertEqual(p.clients_given, q.clients_given)


    def test_player_equal(self):
        g = _encode_decode(self.game)

        for p, q in zip(self.game.players, g.players):
            self.assertEqual(p, q)


    def test_privatized_player_zones(self):
        gpriv = self.game.privatized_game_state_copy(self.p0.name)
        g = _encode_decode(gpriv)

        for p, q in zip(gpriv.players, g.players):
            self.assertEqual(p.hand, q.hand)
            self.assertEqual(p.stockpile, q.stockpile)
            self.assertEqual(p.camp, q.camp)
            self.assertEqual(p.clientele, q.clientele)
            self.assertEqual(p.vault, q.vault)
            self.assertEqual(p.revealed, q.revealed)
            self.assertEqual(p.prev_revealed, q.prev_revealed)
            self.assertEqual(p.clients_given, q.clients_given)


if __name__ == '__main__':
    unittest.main()
