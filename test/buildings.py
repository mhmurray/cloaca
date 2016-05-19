#!/usr/bin/env python

from cloaca.game import Game
from cloaca.player import Player
from cloaca.building import Building

import cloaca.card_manager as cm

import cloaca.message as message
from cloaca.message import GameAction
from cloaca.error import GTRError, GameOver

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup
from cloaca.test.test_setup import TestDeck

import unittest

class TestBuilding(unittest.TestCase):
    """Test Building objects.
    """

    def test_create_building(self):
        school, academy, foundry = cm.get_cards(['School', 'Academy', 'Foundry'])
        b = Building(school, 'Brick', materials=[foundry])

        self.assertIn(foundry, b.materials)
        self.assertFalse(b.complete)
        self.assertEqual(b.site, 'Brick')


    def test_create_building_with_no_site(self):
        school, academy, foundry = cm.get_cards(['School', 'Academy', 'Foundry'])

        with self.assertRaises(GTRError):
            b = Building(school, None, materials=[foundry])


    def test_finish_building(self):
        game = test_setup.two_player_lead('Craftsman')
        p1, p2 = game.players

        school, academy, foundry = cm.get_cards(['School', 'Academy', 'Foundry'])

        p1.hand.set_content([school])
        p1.buildings.append(Building(academy, 'Brick', materials=[foundry]))

        self.assertEqual(p1.influence_points, 2)
        self.assertEqual(game.expected_action, message.CRAFTSMAN)

        a = message.GameAction(message.CRAFTSMAN, academy, school, None)
        game.handle(a)

        self.assertEqual(p1.influence_points, 4)
        self.assertIn('Brick', p1.influence)
        self.assertTrue(p1.buildings[0].complete)
        

class TestBuildingResolution(unittest.TestCase):
    """Test buildings with effect upon completion.
    """

    def setUp(self):
        """ This is run prior to every test.
        """
        self.game = test_setup.two_player_lead('Craftsman')
        self.p1, self.p2 = self.game.players


    def test_finish_school(self):
        """School performs a thinker for each influence.
        """
        school, academy, foundry = cm.get_cards(['School', 'Academy', 'Foundry'])

        self.p1.hand.set_content([academy])
        self.p1.buildings.append(Building(school, 'Brick', materials=[foundry]))

        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)

        a = message.GameAction(message.CRAFTSMAN, school, academy, None)
        self.game.handle(a)

        self.assertEqual(self.game.active_player_index, 0)
        self.assertEqual(self.game.expected_action, message.SKIPTHINKER)

        # Should have 4 influence now and 4 optional thinker actions stacked up
        for i in range(4):
            a = message.GameAction(message.SKIPTHINKER, False)
            self.game.handle(a)
            a = message.GameAction(message.THINKERTYPE, False)
            self.game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(self.game.active_player_index, 1)
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_finish_foundry(self):
        """Foundry performs a laborer for each influence.
        """
        school, academy, foundry = cm.get_cards(['School', 'Academy', 'Foundry'])

        self.p1.hand.set_content([academy])
        self.p1.buildings.append(Building(foundry, 'Brick', materials=[school]))

        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)

        a = message.GameAction(message.CRAFTSMAN, foundry, academy, None)
        self.game.handle(a)

        self.assertEqual(self.game.active_player_index, 0)
        self.assertEqual(self.game.expected_action, message.LABORER)

        # Should have 4 influence now and 4 laborer actions stacked up
        for i in range(4):
            a = message.GameAction(message.LABORER, None, None)
            self.game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(self.game.active_player_index, 1)
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_finish_amphitheatre(self):
        """Amphitheatre performs a craftsman for each influence.
        """
        amphitheatre, bridge, wall, dock = cm.get_cards(['Amphitheatre', 'Bridge', 'Wall', 'Dock'])

        self.p1.hand.set_content([dock, wall])
        self.p1.buildings.append(Building(amphitheatre, 'Concrete', materials=[bridge]))

        self.game.out_of_town_sites = ['Wood']
        self.game.in_town_sites = ['Concrete']*2

        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)

        a = message.GameAction(message.CRAFTSMAN, amphitheatre, wall, None)
        self.game.handle(a)

        self.assertEqual(self.game.active_player_index, 0)
        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)

        # Should have 4 influence now and 4 craftsman actions stacked up
        # This tests if we can start out of town
        a = message.GameAction(message.CRAFTSMAN, dock, None, 'Wood')
        self.game.handle(a)
        for i in range(2):
            a = message.GameAction(message.CRAFTSMAN, None, None, None)
            self.game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(self.game.active_player_index, 1)
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_finish_garden(self):
        garden, villa, scriptorium, catacomb = cm.get_cards(
                ['Garden', 'Villa', 'Scriptorium', 'Catacomb'])

        self.p1.hand.set_content([villa])
        self.p1.buildings.append(
                Building(garden, 'Stone', materials=[scriptorium, catacomb]))

        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)

        a = message.GameAction(message.CRAFTSMAN, garden, villa, None)
        self.game.handle(a)

        self.assertEqual(self.game.active_player_index, 0)
        self.assertEqual(self.game.expected_action, message.PATRONFROMPOOL)

        # Should have 5 influence now and 5 Patron actions stacked up.
        for i in range(5):
            a = message.GameAction(message.PATRONFROMPOOL, None)
            self.game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(self.game.active_player_index, 1)
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_finish_catacomb(self):
        garden, villa, scriptorium, catacomb = cm.get_cards(
                ['Garden', 'Villa', 'Scriptorium', 'Catacomb'])

        self.p1.hand.set_content([villa])
        self.p1.buildings.append(
                Building(catacomb, 'Stone', materials=[scriptorium, garden]))

        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)

        a = message.GameAction(message.CRAFTSMAN, catacomb, villa, None)

        with self.assertRaises(GameOver):
            self.game.handle(a)

        self.assertTrue(self.game.finished)
        self.assertIn(self.p1, self.game.winners)


class TestStairway(unittest.TestCase):
    """Test using a Stairway.
    """
    def setUp(self):
        p2_buildings = ['Shrine0', 'Statue0', 'Archway0', 'Tower0', 'School0']

        self.deck = TestDeck()
        d = self.deck
        self.game = test_setup.two_player_lead('Architect',
                buildings=[['Stairway'],p2_buildings],
                deck = self.deck)

        self.p1, self.p2 = self.game.players

        self.p1.stockpile.set_content(
                [d.bath0, d.storeroom0, d.dock0, d.road, d.temple0, d.villa0])
        

    def test_stairway_in_addition(self):
        d = self.deck

        self.p1.hand.set_content([d.circus0])

        a = GameAction(message.ARCHITECT, d.circus0, None, 'Wood', False)
        self.game.handle(a)

        a = GameAction(message.STAIRWAY, d.shrine0, d.bath0, False)
        self.game.handle(a)

        self.assertIn('Bath', self.p2.get_building(d.shrine0).stairway_materials)
        self.assertTrue(self.game._player_has_active_building(self.p1, 'Shrine'))
        self.assertTrue(self.game._player_has_active_building(self.p2, 'Shrine'))

        self.assertEqual(self.p1.buildings[1], Building(d.circus0, 'Wood'))
        
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_stairway_alone(self):
        d = self.deck
        a = GameAction(message.ARCHITECT, None, None, None, False)
        self.game.handle(a)

        a = GameAction(message.STAIRWAY, d.tower0, d.storeroom0, False)
        self.game.handle(a)

        self.assertIn('Storeroom', self.p2.get_building(d.tower0).stairway_materials)
        self.assertTrue(self.game._player_has_active_building(self.p1, 'Tower'))
        self.assertTrue(self.game._player_has_active_building(self.p2, 'Tower'))

        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_skip_stairway(self):
        a = GameAction(message.ARCHITECT, None, None, None, False)
        self.game.handle(a)

        a = GameAction(message.STAIRWAY, None, None, False)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)



if __name__ == '__main__':
    unittest.main()






