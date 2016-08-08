#!/usr/bin/env python

from cloaca.game import Game
from cloaca.player import Player
from cloaca.building import Building
from cloaca.zone import Zone
from cloaca.card import Card
import cloaca.card_manager as cm

import cloaca.test.test_setup as test_setup
from test_setup import TestDeck

from cloaca.test.monitor import Monitor

import cloaca.message as message
from cloaca.error import GameActionError, GTRError, GameOver

import unittest
from cloaca import gtrutils

from collections import Counter
from uuid import uuid4

class TestInitPool(unittest.TestCase):
    """Test initialization of the pool and determining who goes first.
    """

    def test_two_player(self):

        g = Game()
        g.add_player(uuid4(), 'p1')
        g.add_player(uuid4(), 'p2')

        gs = g
        gs.library.set_content(cm.get_cards(['Bar', 'Circus']))

        first = g._init_pool(len(gs.players))

        self.assertEqual(first, 0)
        self.assertIn('Bar', gs.pool)
        self.assertIn('Circus', gs.pool)

    def test_five_player(self):
        g = Game()
        g.add_player(uuid4(), 'p1')
        g.add_player(uuid4(), 'p2')
        g.add_player(uuid4(), 'p3')
        g.add_player(uuid4(), 'p4')
        g.add_player(uuid4(), 'p5')

        gs = g
        gs.library.set_content(cm.get_cards(['Statue', 'Circus', 'Dock', 'Dock', 'Ludus Magna']))

        first = g._init_pool(len(gs.players))

        self.assertEqual(first, 1)
        self.assertIn('Statue', gs.pool)
        self.assertIn('Circus', gs.pool)
        self.assertIn('Ludus Magna', gs.pool)
        self.assertEqual(gs.pool.count('Dock'), 2)

    def test_resolve_tie(self):
        g = Game()
        g.add_player(uuid4(), 'p1')
        g.add_player(uuid4(), 'p2')
        g.add_player(uuid4(), 'p3')

        gs = g
        gs.library.set_content(cm.get_cards(
            ['Circus', 'Circus', 'Circus', 'Circus Maximus', 'Circus', 'Circus',
             'Ludus Magna', 'Ludus Magna', 'Statue', 'Coliseum',
             ]))


        first = g._init_pool(len(gs.players))

        self.assertEqual(first, 2)
        z = Zone(cm.get_cards(
                ['Circus', 'Circus', 'Circus', 'Circus Maximus', 'Circus',
                 'Circus', 'Ludus Magna', 'Ludus Magna', 'Statue', 'Coliseum']))
        self.assertTrue(z.equal_contents(gs.pool))


class TestGameStatePrivatize(unittest.TestCase):
    """Test hiding the non-public elements of the game state.
        
    These are the library, opponents' hands except Jacks, all vaults,
    and the card drawn with the fountain.
    """

    def test_privatize_library(self):
        """Test hiding the library.
        """
        g = Game()
        g.add_player(uuid4(), 'p1')
        g.add_player(uuid4(), 'p2')
        gs = g

        gs.library.set_content(cm.get_cards(
            ['Circus', 'Circus', 'Circus', 'Circus Maximus', 'Circus', 'Circus',
             'Ludus Magna', 'Ludus Magna', 'Statue', 'Coliseum',
             ]))

        gs_private = g.privatized_game_state_copy('p1')

        self.assertFalse(gs_private.library.contains('Circus'))
        self.assertEqual(gs_private.library, Zone([Card(-1)]*len(gs_private.library), name='library'))

    def test_privatize_hands(self):
        """Test hiding opponents' hands.
        """
        g = Game()
        g.add_player(uuid4(), 'p0')
        g.add_player(uuid4(), 'p1')
        gs = g

        p0, p1 = gs.players

        latrine, insula, jack, road = cm.get_cards(['Latrine', 'Insula', 'Jack', 'Road'])
        p0.hand.set_content([latrine, insula])
        p1.hand.set_content([jack, road])

        gs_private = g.privatized_game_state_copy('p0')
        p0, p1 = gs_private.players

        self.assertIn(jack, p1.hand)
        self.assertIn(Card(-1), p1.hand)
        self.assertNotIn(road, p1.hand)

        self.assertIn(latrine, p0.hand)
        self.assertIn(insula, p0.hand)

        self.assertEqual(len(p0.hand), 2)
        self.assertEqual(len(p1.hand), 2)

    
    def test_privatize_vaults(self):
        """Test hiding all vaults.
        """
        g = Game()
        g.add_player(uuid4(), 'p0')
        g.add_player(uuid4(), 'p1')
        gs = g

        p0, p1 = gs.players

        latrine, insula, statue, road = cm.get_cards(['Latrine', 'Insula', 'Statue', 'Road'])
        p0.vault.set_content([latrine, insula])
        p1.vault.set_content([statue, road])

        gs_private = g.privatized_game_state_copy('p1')
        p0, p1 = gs_private.players

        self.assertEqual(p0.vault, Zone([Card(-1)]*2, name='vault'))
        self.assertEqual(p1.vault, Zone([Card(-1)]*2, name='vault'))


    def test_privatize_fountain_card(self):
        """Test hiding the card revealed with the fountain.
        """
        g = Game()
        g.add_player(uuid4(), 'p0')
        g.add_player(uuid4(), 'p1')

        gs = g
        p0, p1 = gs.players

        latrine, insula, statue, road = cm.get_cards(['Latrine', 'Insula', 'Statue', 'Road'])
        p0.fountain_card = latrine

        gs_private = g.privatized_game_state_copy('p1')
        p0, p1 = gs_private.players

        self.assertEqual(p0.fountain_card, Card(-1))


class TestCheckPetitionCombos(unittest.TestCase):
    """Test Palace / petition checker function.

        def check_petition_combos(
            n_actions, n_on_role, n_off_role, two_card, three_card):

    It checks if the n_actions number of actions can be constructed
    using n_on_role cards of the role being led and n_off_role cards
    not of the role being led. The boolean flags two_card and three_card
    specify which kinds of petitions are allowed. The function should
    be valid for any combination of inputs.
    """

    def test_invalid_inputs(self):
        """Returns False for out of range inputs.
        """
        f = gtrutils.check_petition_combos
        
        self.assertFalse( f(-1, 1, [], False, False))
        self.assertFalse( f( 0, 1, [], False, False))
        self.assertFalse( f( 1, 0, [], False, False))
        self.assertFalse( f( 1, 1, [-1], False, False))
        self.assertFalse( f( 1,-1, [], False, False))
        self.assertFalse( f( 1, 1, [1], False, False)) # n_off_role can never be 1
        self.assertFalse( f( 1, 1, [1],  True, False)) # n_off_role can never be 1
        self.assertFalse( f( 1, 1, [1], False,  True)) # n_off_role can never be 1
        self.assertFalse( f( 1, 1, [1],  True,  True)) # n_off_role can never be 1
        self.assertFalse( f( 1, 1, [1,3],  True,  True)) # n_off_role can never be 1

        self.assertFalse( f( 3, 0, [2,3,3],  False,  True)) # n_off_role can never be 1
        self.assertFalse( f( 3, 0, [2,3,3],  True,  False)) # n_off_role can never be 1
        self.assertFalse( f( 2, 0, [2,3,3],  False,  True)) # n_off_role can never be 1
        self.assertFalse( f( 2, 0, [2,3,3],  True,  False)) # n_off_role can never be 1
        self.assertFalse( f( 5, 1, [6,6],  True,  False)) # n_off_role can never be 1

    def test_no_petitions(self):
        """Test with no petitions allowed.
        """
        f = gtrutils.check_petition_combos

        self.assertTrue(  f( 0, 0, [ 0], False, False))

        self.assertFalse( f( 1, 0, [], False, False))
        self.assertFalse( f( 1, 1, [2], False, False))
        self.assertFalse( f( 1, 1, [3], False, False))
        self.assertFalse( f( 1, 1, [4], False, False))

        self.assertTrue(  f( 1, 1, [], False, False))
        self.assertFalse( f( 1, 2, [], False, False))
        self.assertFalse( f( 1, 3, [], False, False))

        self.assertFalse( f( 2, 1, [], False, False))
        self.assertTrue(  f( 2, 2, [], False, False))
        self.assertFalse( f( 2, 3, [], False, False))

        self.assertFalse( f( 3, 1, [], False, False))
        self.assertFalse( f( 3, 2, [], False, False))
        self.assertTrue(  f( 3, 3, [], False, False))

        self.assertTrue(  f(13,13, [], False, False))

        self.assertFalse( f( 1, 1, [0,0,0,3], False, False))
        self.assertFalse( f( 2, 1, [0,0,0,3], False, False))
        self.assertFalse( f( 3, 1, [0,0,0,3], False, False))

    def test_only_three_card_petitions(self):
        """Test with only three-card petitions allowed.
        """
        f = gtrutils.check_petition_combos

        self.assertTrue(  f( 0, 0, [0], False, True))

        self.assertFalse( f( 1, 0, [0], False, True))
        self.assertTrue(  f( 1, 1, [0], False, True))
        self.assertTrue(  f( 1, 0, [3], False, True))
        self.assertTrue(  f( 1, 3, [0], False, True))

        self.assertFalse( f( 1, 1, [2], False, True))
        self.assertFalse( f( 1, 1, [3], False, True))
        self.assertFalse( f( 1, 1, [4], False, True))

        self.assertTrue(  f( 2, 2, [0], False, True))
        self.assertTrue(  f( 2, 1, [3], False, True))
        self.assertTrue(  f( 2, 3, [3], False, True))
        self.assertTrue(  f( 2, 6, [0], False, True))
        self.assertTrue(  f( 2, 0, [6], False, True))
        self.assertFalse( f( 2, 4, [3], False, True))

        self.assertFalse( f( 3, 1, [], False, True))
        self.assertFalse( f( 3, 2, [], False, True))
        self.assertFalse( f( 3, 0, [3], False, True))
        self.assertFalse( f( 3, 0, [6], False, True))
        self.assertTrue(  f( 3, 3, [], False, True))
        self.assertTrue(  f( 3, 2, [3], False, True))
        self.assertTrue(  f( 3, 3, [6], False, True))
        self.assertTrue(  f( 3, 1, [6], False, True))
        self.assertTrue(  f( 3, 0, [9], False, True))

        self.assertTrue(  f(13,13, [], False, True))
        self.assertTrue(  f(13,39, [], False, True))
        self.assertTrue(  f(13, 0, [39], False, True))
        self.assertTrue(  f(13,15, [24], False, True))
        self.assertTrue(  f(13,15, [], False, True))
        self.assertTrue(  f(13,12, [3], False, True))
        self.assertFalse( f(13,14, [], False, True))

        self.assertFalse( f( 6, 1, [3,6,9], False, True))
        self.assertTrue( f( 7, 1, [3,6,9], False, True))
        self.assertFalse( f( 8, 1, [3,6,9], False, True))

    def test_only_two_card_petitions(self):
        """Test with only two-card petitions
        """
        f = gtrutils.check_petition_combos

        self.assertTrue(  f( 0, 0, [0], True, False))

        self.assertFalse( f( 1, 0, [], True, False))
        self.assertFalse( f( 1, 0, [1], True, False))
        self.assertTrue(  f( 1, 0, [2], True, False))
        self.assertFalse( f( 1, 0, [3], True, False))
        self.assertFalse( f( 1, 0, [4], True, False))

        self.assertTrue(  f( 1, 1, [], True, False))
        self.assertFalse( f( 1, 1, [2], True, False))

        self.assertFalse( f( 2, 0, [2], True, False))
        self.assertFalse( f( 2, 0, [3], True, False))
        self.assertTrue(  f( 2, 0, [4], True, False))
        self.assertFalse( f( 2, 0, [5], True, False))
        
        self.assertTrue(  f( 2, 1, [2], True, False))
        self.assertFalse( f( 2, 1, [3], True, False))
        self.assertFalse( f( 2, 1, [4], True, False))

        self.assertTrue(  f(13, 26, [], True, False))
        self.assertTrue(  f(13,  0, [26], True, False))
        self.assertTrue(  f(13, 14, [12], True, False))
        self.assertTrue(  f(13, 13, [10], True, False))
        self.assertFalse( f(13, 15, [11], True, False))

        self.assertFalse( f( 6, 1, [2,4,6], True, False))
        self.assertTrue( f( 7, 1, [2,4,6], True, False))
        self.assertFalse( f( 8, 1, [2,4,6], True, False))

    def test_two_and_three_card_petitions(self):
        """Test with two- and three-card petitions
        """
        f = gtrutils.check_petition_combos

        self.assertTrue(  f( 0, 0, [], True, True))

        self.assertFalse( f( 1, 0, [], True, True))
        self.assertFalse( f( 1, 0, [1], True, True))
        self.assertTrue(  f( 1, 0, [2], True, True))
        self.assertTrue(  f( 1, 0, [3], True, True))
        self.assertFalse( f( 1, 0, [4], True, True))
        self.assertTrue(  f( 1, 1, [], True, True))
        self.assertTrue(  f( 1, 2, [], True, True))
        self.assertTrue(  f( 1, 3, [], True, True))
        self.assertFalse( f( 1, 4, [], True, True))

        self.assertFalse( f( 1, 1, [2], True, True))
        self.assertFalse( f( 1, 1, [3], True, True))
        self.assertFalse( f( 1, 2, [2], True, True))
        self.assertFalse( f( 1, 3, [2], True, True))
        self.assertFalse( f( 1, 3, [3], True, True))

        self.assertTrue(  f( 2, 1, [2], True, True))
        self.assertTrue(  f( 2, 1, [3], True, True))
        self.assertTrue(  f( 2, 0, [4], True, True))
        self.assertTrue(  f( 2, 0, [5], True, True))
        self.assertTrue(  f( 2, 0, [6], True, True))
        self.assertTrue(  f( 2, 4, [], True, True))
        self.assertTrue(  f( 2, 5, [], True, True))
        self.assertTrue(  f( 2, 6, [], True, True))
        
        self.assertTrue(  f(13, 26, [], True, True))
        self.assertTrue(  f(13, 39, [], True, True))
        self.assertTrue(  f(13,  0, [26], True, True))
        self.assertTrue(  f(13, 14, [12], True, True))
        self.assertTrue(  f(13, 13, [10], True, True))
        self.assertTrue(  f(13, 15, [11], True, True))
        self.assertFalse( f(13, 40, [], True, True))
        self.assertFalse( f(13, 11, [3], True, True))

        self.assertFalse( f(4, 1, [2,3,6], True, True))
        self.assertTrue(  f(5, 1, [2,3,6], True, True))
        self.assertTrue(  f(6, 1, [2,3,6], True, True))
        self.assertFalse( f(7, 1, [2,3,6], True, True))


class TestClienteleLimit(unittest.TestCase):

    def test_initial_limit(self):
        """Test limit at beginning of game.
        """

        g = test_setup.simple_two_player()

        p1, p2 = g.players

        self.assertEqual(g._clientele_limit(p1), 2)
        self.assertEqual(g._clientele_limit(p2), 2)


    def test_limit_with_influence(self):
        """Test limit with some completed buildings.
        """

        g = test_setup.simple_two_player()

        p1, p2 = g.players

        p1.influence = ['Stone']
        p2.influence = ['Rubble']

        self.assertEqual(g._clientele_limit(p1), 5)
        self.assertEqual(g._clientele_limit(p2), 3)
 
        p1.influence = ['Wood']
        p2.influence = ['Marble']

        self.assertEqual(g._clientele_limit(p1), 3)
        self.assertEqual(g._clientele_limit(p2), 5)
 
        p1.influence = ['Brick']
        p2.influence = ['Concrete']

        self.assertEqual(g._clientele_limit(p1), 4)
        self.assertEqual(g._clientele_limit(p2), 4)
 
        p1.influence = ['Brick', 'Concrete', 'Marble']
        p2.influence = ['Concrete', 'Stone', 'Rubble', 'Rubble', 'Rubble']

        self.assertEqual(g._clientele_limit(p1), 9)
        self.assertEqual(g._clientele_limit(p2), 10)
 

    def test_limit_with_insula(self):
        """Test limit with completed Insula.
        """
        d = TestDeck()

        g = test_setup.simple_two_player()

        p1, p2 = g.players

        self.assertEqual(g._clientele_limit(p1), 2)

        p1.buildings.append(Building(d.insula, 'Rubble', complete=True))

        self.assertEqual(g._clientele_limit(p1), 4)

        p1.influence = ['Stone']

        self.assertEqual(g._clientele_limit(p1), 7)


    def test_limit_with_aqueduct(self):
        """Test limit with completed Aqueduct.
        """
        d = TestDeck()

        g = test_setup.simple_two_player()

        p1, p2 = g.players

        self.assertEqual(g._clientele_limit(p1), 2)

        p1.buildings.append(Building(d.aqueduct, 'Concrete', complete=True))

        self.assertEqual(g._clientele_limit(p1), 4)

        p1.influence = ['Stone']

        self.assertEqual(g._clientele_limit(p1), 10)


    def test_limit_with_insula_and_aqueduct(self):
        """Test limit with completed Aqueduct.
        """
        d = TestDeck()

        g = test_setup.simple_two_player()

        p1, p2 = g.players

        self.assertEqual(g._clientele_limit(p1), 2)

        p1.buildings.append(Building(d.aqueduct, 'Concrete', complete=True))
        p1.buildings.append(Building(d.insula, 'Rubble', complete=True))

        self.assertEqual(g._clientele_limit(p1), 8)

        p1.influence = ['Stone']

        self.assertEqual(g._clientele_limit(p1), 14)


class TestSites(unittest.TestCase):
    """Test mechanics of sites.
    """

    def test_start_last_site_ends_game(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.road0])
        game.in_town_sites = ['Rubble']

        a = message.GameAction(message.ARCHITECT, d.road0, None, 'Rubble')
        with self.assertRaises(GameOver):
            game.handle(a)

        self.assertIn('Road', p1.building_names)
        self.assertIsNotNone(game.winners)


    def test_no_more_out_of_town_sites(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                buildings=[['Tower'], []],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.dock0])

        game.in_town_sites = ['Rubble']
        game.out_of_town_sites = ['Rubble']

        mon = Monitor()
        mon.modified(game)

        a = message.GameAction(message.ARCHITECT, d.dock0, None, 'Wood')
        with self.assertRaises(GTRError):
            game.handle(a)

        self.assertFalse(mon.modified(game))



if __name__ == '__main__':
    unittest.main()
