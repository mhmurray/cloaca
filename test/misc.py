#!/usr/bin/env python

from cloaca.gtr import Game
from cloaca.gamestate import GameState
from cloaca.player import Player
from cloaca.building import Building
from cloaca.zone import Zone
from cloaca.card import Card
import cloaca.card_manager as cm

import cloaca.message as message
from cloaca.message import BadGameActionError

import unittest
from cloaca import gtrutils

from collections import Counter

class TestInitPool(unittest.TestCase):
    """Test initialization of the pool and determining who goes first.
    """

    def test_two_player(self):
        p1 = Player('p1')
        p2 = Player('p2')

        gs = GameState(players=['p1','p2'])
        gs.players = (p1, p2)

        gs.library.set_content(cm.get_cards(['Bar', 'Circus']))

        g = Game(gs)

        first = g.init_pool(len(gs.players))

        self.assertEqual(first, 0)
        self.assertIn('Bar', gs.pool)
        self.assertIn('Circus', gs.pool)

    def test_five_player(self):
        gs = GameState(players=['p'+str(i) for i in range(5)])

        gs.library.set_content(cm.get_cards(['Statue', 'Circus', 'Dock', 'Dock', 'Ludus Magna']))

        g = Game(gs)

        first = g.init_pool(len(gs.players))

        self.assertEqual(first, 1)
        self.assertIn('Statue', gs.pool)
        self.assertIn('Circus', gs.pool)
        self.assertIn('Ludus Magna', gs.pool)
        self.assertEqual(gs.pool.count('Dock'), 2)

    def test_resolve_tie(self):
        gs = GameState(players=['p'+str(i) for i in range(3)])

        gs.library.set_content(cm.get_cards(
            ['Circus', 'Circus', 'Circus', 'Circus Maximus', 'Circus', 'Circus',
             'Ludus Magna', 'Ludus Magna', 'Statue', 'Coliseum',
             ]))

        g = Game(gs)

        first = g.init_pool(len(gs.players))

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
        gs = GameState(players=['p'+str(i) for i in range(2)])

        gs.library.set_content(cm.get_cards(
            ['Circus', 'Circus', 'Circus', 'Circus Maximus', 'Circus', 'Circus',
             'Ludus Magna', 'Ludus Magna', 'Statue', 'Coliseum',
             ]))

        gs.privatize('p0')

        self.assertFalse(gs.library.contains('Circus'))
        self.assertEqual(gs.library, Zone([Card(-1)]*len(gs.library)))

    def test_privatize_hands(self):
        """Test hiding opponents' hands.
        """
        gs = GameState(players=['p'+str(i) for i in range(2)])
        p0, p1 = gs.players

        latrine, insula, jack, road = cm.get_cards(['Latrine', 'Insula', 'Jack', 'Road'])
        p0.hand.set_content([latrine, insula])
        p1.hand.set_content([jack, road])

        gs.privatize('p0')

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
        gs = GameState(players=['p'+str(i) for i in range(2)])
        p0, p1 = gs.players

        latrine, insula, statue, road = cm.get_cards(['Latrine', 'Insula', 'Statue', 'Road'])
        p0.vault.set_content([latrine, insula])
        p1.vault.set_content([statue, road])

        gs.privatize('p1')

        self.assertEqual(p0.vault, [Card(-1)]*2)
        self.assertEqual(p1.vault, [Card(-1)]*2)


    def test_privatize_fountain_card(self):
        """Test hiding the card revealed with the fountain.
        """
        gs = GameState(players=['p'+str(i) for i in range(2)])
        p0, p1 = gs.players

        latrine, insula, statue, road = cm.get_cards(['Latrine', 'Insula', 'Statue', 'Road'])
        p0.fountain_card = latrine

        gs.privatize('p1')

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
        
        self.assertFalse( f(-1, 1, 0, False, False))
        self.assertFalse( f( 0, 1, 0, False, False))
        self.assertFalse( f( 1, 0, 0, False, False))
        self.assertFalse( f( 1, 1,-1, False, False))
        self.assertFalse( f( 1,-1, 0, False, False))
        self.assertFalse( f( 1, 1, 1, False, False)) # n_off_role can never be 1
        self.assertFalse( f( 1, 1, 1,  True, False)) # n_off_role can never be 1
        self.assertFalse( f( 1, 1, 1, False,  True)) # n_off_role can never be 1
        self.assertFalse( f( 1, 1, 1,  True,  True)) # n_off_role can never be 1

    def test_no_petitions(self):
        """Test with no petitions allowed.
        """
        f = gtrutils.check_petition_combos

        self.assertTrue(  f( 0, 0, 0, False, False))

        self.assertFalse( f( 1, 0, 0, False, False))
        self.assertFalse( f( 1, 1, 2, False, False))
        self.assertFalse( f( 1, 1, 3, False, False))
        self.assertFalse( f( 1, 1, 4, False, False))

        self.assertTrue(  f( 1, 1, 0, False, False))
        self.assertFalse( f( 1, 2, 0, False, False))
        self.assertFalse( f( 1, 3, 0, False, False))

        self.assertFalse( f( 2, 1, 0, False, False))
        self.assertTrue(  f( 2, 2, 0, False, False))
        self.assertFalse( f( 2, 3, 0, False, False))

        self.assertFalse( f( 3, 1, 0, False, False))
        self.assertFalse( f( 3, 2, 0, False, False))
        self.assertTrue(  f( 3, 3, 0, False, False))

        self.assertTrue(  f(13,13, 0, False, False))

    def test_only_three_card_petitions(self):
        """Test with only three-card petitions allowed.
        """
        f = gtrutils.check_petition_combos

        self.assertTrue(  f( 0, 0, 0, False, True))

        self.assertFalse( f( 1, 0, 0, False, True))
        self.assertTrue(  f( 1, 1, 0, False, True))
        self.assertTrue(  f( 1, 0, 3, False, True))
        self.assertTrue(  f( 1, 3, 0, False, True))

        self.assertFalse( f( 1, 1, 2, False, True))
        self.assertFalse( f( 1, 1, 3, False, True))
        self.assertFalse( f( 1, 1, 4, False, True))

        self.assertTrue(  f( 2, 2, 0, False, True))
        self.assertTrue(  f( 2, 1, 3, False, True))
        self.assertTrue(  f( 2, 3, 3, False, True))
        self.assertTrue(  f( 2, 6, 0, False, True))
        self.assertTrue(  f( 2, 0, 6, False, True))
        self.assertFalse( f( 2, 4, 3, False, True))

        self.assertFalse( f( 3, 1, 0, False, True))
        self.assertFalse( f( 3, 2, 0, False, True))
        self.assertFalse( f( 3, 0, 3, False, True))
        self.assertFalse( f( 3, 0, 6, False, True))
        self.assertTrue(  f( 3, 3, 0, False, True))
        self.assertTrue(  f( 3, 2, 3, False, True))
        self.assertTrue(  f( 3, 3, 6, False, True))
        self.assertTrue(  f( 3, 1, 6, False, True))
        self.assertTrue(  f( 3, 0, 9, False, True))

        self.assertTrue(  f(13,13, 0, False, True))
        self.assertTrue(  f(13,39, 0, False, True))
        self.assertTrue(  f(13, 0,39, False, True))
        self.assertTrue(  f(13,15,24, False, True))
        self.assertTrue(  f(13,15, 0, False, True))
        self.assertTrue(  f(13,12, 3, False, True))
        self.assertFalse( f(13,14, 0, False, True))

    def test_only_two_card_petitions(self):
        """Test with only two-card petitions
        """
        f = gtrutils.check_petition_combos

        self.assertTrue(  f( 0, 0, 0, True, False))

        self.assertFalse( f( 1, 0, 0, True, False))
        self.assertFalse( f( 1, 0, 1, True, False))
        self.assertTrue(  f( 1, 0, 2, True, False))
        self.assertFalse( f( 1, 0, 3, True, False))
        self.assertFalse( f( 1, 0, 4, True, False))

        self.assertTrue(  f( 1, 1, 0, True, False))
        self.assertFalse( f( 1, 1, 2, True, False))

        self.assertFalse( f( 2, 0, 2, True, False))
        self.assertFalse( f( 2, 0, 3, True, False))
        self.assertTrue(  f( 2, 0, 4, True, False))
        self.assertFalse( f( 2, 0, 5, True, False))
        
        self.assertTrue(  f( 2, 1, 2, True, False))
        self.assertFalse( f( 2, 1, 3, True, False))
        self.assertFalse( f( 2, 1, 4, True, False))

        self.assertTrue(  f(13, 26,  0, True, False))
        self.assertTrue(  f(13,  0, 26, True, False))
        self.assertTrue(  f(13, 14, 12, True, False))
        self.assertTrue(  f(13, 13, 10, True, False))
        self.assertFalse( f(13, 15, 11, True, False))

    def test_two_and_three_card_petitions(self):
        """Test with two- and three-card petitions
        """
        f = gtrutils.check_petition_combos

        self.assertTrue(  f( 0, 0, 0, True, True))

        self.assertFalse( f( 1, 0, 0, True, True))
        self.assertFalse( f( 1, 0, 1, True, True))
        self.assertTrue(  f( 1, 0, 2, True, True))
        self.assertTrue(  f( 1, 0, 3, True, True))
        self.assertFalse( f( 1, 0, 4, True, True))
        self.assertTrue(  f( 1, 1, 0, True, True))
        self.assertTrue(  f( 1, 2, 0, True, True))
        self.assertTrue(  f( 1, 3, 0, True, True))
        self.assertFalse( f( 1, 4, 0, True, True))

        self.assertFalse( f( 1, 1, 2, True, True))
        self.assertFalse( f( 1, 1, 3, True, True))
        self.assertFalse( f( 1, 2, 2, True, True))
        self.assertFalse( f( 1, 3, 2, True, True))
        self.assertFalse( f( 1, 3, 3, True, True))

        self.assertTrue(  f( 2, 1, 2, True, True))
        self.assertTrue(  f( 2, 1, 3, True, True))
        self.assertTrue(  f( 2, 0, 4, True, True))
        self.assertTrue(  f( 2, 0, 5, True, True))
        self.assertTrue(  f( 2, 0, 6, True, True))
        self.assertTrue(  f( 2, 4, 0, True, True))
        self.assertTrue(  f( 2, 5, 0, True, True))
        self.assertTrue(  f( 2, 6, 0, True, True))
        
        self.assertTrue(  f(13, 26,  0, True, True))
        self.assertTrue(  f(13, 39,  0, True, True))
        self.assertTrue(  f(13,  0, 26, True, True))
        self.assertTrue(  f(13, 14, 12, True, True))
        self.assertTrue(  f(13, 13, 10, True, True))
        self.assertTrue(  f(13, 15, 11, True, True))
        self.assertFalse( f(13, 40,  0, True, True))
        self.assertFalse( f(13, 11,  3, True, True))


 

if __name__ == '__main__':
    unittest.main()
