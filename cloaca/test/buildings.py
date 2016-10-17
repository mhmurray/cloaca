#!/usr/bin/env python

"""Tests related to buildings. Some buildings are tested in 
separate modules.

Legionary buildings Bridge, Coliseum, and Palisade are in legionary.py.
Circus is in turn.py.

"""

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
    """Test Building code objects, rather than specific building rules.
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
            a = message.GameAction(message.LABORER)
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


class TestFoundry(unittest.TestCase):
    """Test finishing Foundry leading to a Laborer for each influence.
    """

    def test_finish_foundry(self):
        d = TestDeck()
        game = test_setup.two_player_lead('Craftsman',
                deck=d)

        p1, p2 = game.players

        p1.hand.set_content([d.academy0])
        p1.buildings.append(Building(d.foundry0, 'Brick', materials=[d.school0]))

        a = message.GameAction(message.CRAFTSMAN, d.foundry0, d.academy0, None)
        game.handle(a)

        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.expected_action, message.LABORER)

        # Should have 4 influence now and 4 laborer actions stacked up
        for i in range(4):
            a = message.GameAction(message.LABORER)
            game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(game.active_player, p2)
        self.assertEqual(game.expected_action, message.THINKERORLEAD)


class TestAmphitheatre(unittest.TestCase):
    """Finish Amphitheatre gives craftsman actions equal to influence.
    
    Also test all the ways we could get Craftsman actions and combine them
    to start out of town. These are:

        - Two Amphitheatre actions
        - The last Amphitheatre action and another Palace Craftsman action.
        - The last Amphitheatre action and another Craftsman client
        - The last Amphitheatre action and a Merchant client with Ludus
        - The last Amphitheatre action and the second half of a
          Circus Maximus client.
        - Finish Amphitheatre with Architect and start with two of the
          Craftsman actions.
        - (Not allowed to combine Architect+Craftsman action.)
    """

    def test_finish_amphitheatre_with_craftsman(self):
        d = TestDeck()
        game = test_setup.two_player_lead('Craftsman', deck=d)

        p1, p2 = game.players
        p1.hand.set_content([d.dock0, d.wall0])
        p1.buildings.append(Building(d.amphitheatre0, 'Concrete', materials=[d.bridge0]))

        a = message.GameAction(message.CRAFTSMAN, d.amphitheatre0, d.wall0, None)
        game.handle(a)

        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.expected_action, message.CRAFTSMAN)

        # Should have 4 influence now and 4 craftsman actions stacked up
        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        game.handle(a)
        for i in range(3):
            a = message.GameAction(message.CRAFTSMAN, None, None, None)
            game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(game.active_player, p2)
        self.assertEqual(game.expected_action, message.THINKERORLEAD)


    def test_amphitheatre_start_out_of_town(self):
        d = TestDeck()
        game = test_setup.two_player_lead('Craftsman', deck=d)
        game.in_town_sites = ['Brick'] # No wood site for Dock

        p1, p2 = game.players
        p1.hand.set_content([d.dock0, d.wall0])
        p1.buildings.append(Building(d.amphitheatre0, 'Concrete', materials=[d.bridge0]))

        a = message.GameAction(message.CRAFTSMAN, d.amphitheatre0, d.wall0, None)
        game.handle(a)

        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.expected_action, message.CRAFTSMAN)
        self.assertTrue(game.oot_allowed)

        # Use first 2 of 4 actions to out-of-town Dock.
        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        game.handle(a)
        for i in range(2):
            a = message.GameAction(message.CRAFTSMAN, None, None, None)
            game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(game.active_player, p2)
        self.assertEqual(game.expected_action, message.THINKERORLEAD)


    def test_amphitheatre_start_out_of_town_leading_architect(self):
        d = TestDeck()
        game = test_setup.two_player_lead('Architect', deck=d)
        game.in_town_sites = ['Brick'] # No wood site for Dock

        p1, p2 = game.players
        p1.hand.set_content([d.dock0])
        p1.stockpile.set_content([d.wall0])
        p1.buildings.append(Building(d.amphitheatre0, 'Concrete', materials=[d.bridge0]))

        a = message.GameAction(message.ARCHITECT, d.amphitheatre0, d.wall0, None)
        game.handle(a)

        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.expected_action, message.CRAFTSMAN)
        self.assertTrue(game.oot_allowed)

        # Use first 2 of 4 actions to out-of-town Dock.
        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        game.handle(a)
        for i in range(2):
            a = message.GameAction(message.CRAFTSMAN, None, None, None)
            game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(game.active_player, p2)
        self.assertEqual(game.expected_action, message.THINKERORLEAD)


    def test_amphitheatre_start_out_of_town_with_client(self):
        d = TestDeck()
        game = test_setup.two_player_lead('Craftsman', deck=d,
                clientele=[['Palisade'],[]])
        game.in_town_sites = ['Brick'] # No wood site for Dock

        p1, p2 = game.players
        p1.hand.set_content([d.dock0, d.wall0])
        p1.buildings.append(Building(d.amphitheatre0, 'Concrete', materials=[d.bridge0]))

        a = message.GameAction(message.CRAFTSMAN, d.amphitheatre0, d.wall0, None)
        game.handle(a)

        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.expected_action, message.CRAFTSMAN)

        # Skip first 3 of 4 actions and use last+client to out-of-town Dock.
        for i in range(3):
            a = message.GameAction(message.CRAFTSMAN, None, None, None)
            game.handle(a)

        self.assertTrue(game.oot_allowed)

        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(game.active_player, p2)
        self.assertEqual(game.expected_action, message.THINKERORLEAD)


    def test_amphitheatre_start_out_of_town_with_merchant_client(self):
        d = TestDeck()
        game = test_setup.two_player_lead('Craftsman', deck=d,
                clientele=[['Villa'],[]],
                buildings=[['Ludus Magna'],[]])
        game.in_town_sites = ['Brick'] # No wood site for Dock

        p1, p2 = game.players
        p1.hand.set_content([d.dock0, d.wall0])
        p1.buildings.append(Building(d.amphitheatre0, 'Concrete', materials=[d.bridge0]))

        a = message.GameAction(message.CRAFTSMAN, d.amphitheatre0, d.wall0, None)
        game.handle(a)

        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.expected_action, message.CRAFTSMAN)

        # Skip first 3 of 4 actions and use last+client to out-of-town Dock.
        for i in range(3):
            a = message.GameAction(message.CRAFTSMAN, None, None, None)
            game.handle(a)

        self.assertTrue(game.oot_allowed)

        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(game.active_player, p2)
        self.assertEqual(game.expected_action, message.THINKERORLEAD)


    def test_amphitheatre_start_out_of_town_with_second_circus_maximus(self):
        d = TestDeck()
        game = test_setup.two_player_lead('Craftsman', deck=d,
                clientele=[['Palisade'],[]],
                buildings=[['Circus Maximus'],[]])
        game.in_town_sites = ['Brick'] # No wood site for Dock

        p1, p2 = game.players
        p1.hand.set_content([d.dock0, d.wall0])
        p1.buildings.append(Building(d.amphitheatre0, 'Concrete', materials=[d.bridge0]))

        # Skip first action from leading
        a = message.GameAction(message.CRAFTSMAN, None, None, None)
        game.handle(a)

        # Finish Amphitheatre with first action off client + CM
        a = message.GameAction(message.CRAFTSMAN, d.amphitheatre0, d.wall0, None)
        game.handle(a)

        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.expected_action, message.CRAFTSMAN)

        # Skip first 3 of 4 actions and use last+client to out-of-town Dock.
        for i in range(3):
            a = message.GameAction(message.CRAFTSMAN, None, None, None)
            game.handle(a)

        self.assertTrue(game.oot_allowed)

        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(game.active_player, p2)
        self.assertEqual(game.expected_action, message.THINKERORLEAD)


    def test_amphitheatre_start_out_of_town_with_second_circus_maximus_and_ludus(self):
        d = TestDeck()
        game = test_setup.two_player_lead('Craftsman', deck=d,
                clientele=[['Villa'],[]],
                buildings=[['Circus Maximus', 'Ludus Magna'],[]])
        game.in_town_sites = ['Brick'] # No wood site for Dock

        p1, p2 = game.players
        p1.hand.set_content([d.dock0, d.wall0])
        p1.buildings.append(Building(d.amphitheatre0, 'Concrete', materials=[d.bridge0]))

        # Skip first action from leading
        a = message.GameAction(message.CRAFTSMAN, None, None, None)
        game.handle(a)

        # Finish Amphitheatre with first action off client + CM
        a = message.GameAction(message.CRAFTSMAN, d.amphitheatre0, d.wall0, None)
        game.handle(a)

        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.expected_action, message.CRAFTSMAN)

        # Skip first 3 of 4 actions and use last+client to out-of-town Dock.
        for i in range(3):
            a = message.GameAction(message.CRAFTSMAN, None, None, None)
            game.handle(a)

        self.assertTrue(game.oot_allowed)

        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(game.active_player, p2)
        self.assertEqual(game.expected_action, message.THINKERORLEAD)


    def test_amphitheatre_start_out_of_town_with_remaining_palace_action(self):
        d = TestDeck()
        game = test_setup.simple_two_player(deck=d,
                buildings=[['Palace'],[]])
        game.in_town_sites = ['Brick'] # No wood site for Dock

        p1, p2 = game.players
        p1.hand.set_content([d.dock0, d.wall0, d.jack0, d.jack1])
        p1.buildings.append(Building(d.amphitheatre0, 'Concrete', materials=[d.bridge0]))

        a = message.GameAction(message.THINKERORLEAD, False)
        game.handle(a)
        a = message.GameAction(message.LEADROLE, 'Craftsman', 2, d.jack0, d.jack1)
        game.handle(a)

        # p2 thinks
        a = message.GameAction(message.FOLLOWROLE, 0)
        game.handle(a)
        a = message.GameAction(message.THINKERTYPE, True)
        game.handle(a)

        # Finish Amphitheatre with first camp action
        a = message.GameAction(message.CRAFTSMAN, d.amphitheatre0, d.wall0, None)
        game.handle(a)

        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.expected_action, message.CRAFTSMAN)

        # Skip first 3 of 4 actions and use last+remaining camp action to out-of-town Dock.
        for i in range(3):
            a = message.GameAction(message.CRAFTSMAN, None, None, None)
            game.handle(a)

        self.assertTrue(game.oot_allowed)

        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(game.active_player, p2)
        self.assertEqual(game.expected_action, message.THINKERORLEAD)


    def test_finish_amphitheatre_with_architect(self):
        d = TestDeck()
        game = test_setup.two_player_lead('Architect', deck=d)

        p1, p2 = game.players
        p1.hand.set_content([d.dock0])
        p1.stockpile.set_content([d.wall0])
        p1.buildings.append(Building(d.amphitheatre0, 'Concrete', materials=[d.bridge0]))

        a = message.GameAction(message.ARCHITECT, d.amphitheatre0, d.wall0, None)
        game.handle(a)

        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.expected_action, message.CRAFTSMAN)

        # Should have 4 influence now and 4 craftsman actions stacked up
        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        game.handle(a)
        for i in range(3):
            a = message.GameAction(message.CRAFTSMAN, None, None, None)
            game.handle(a)
        
        # Now it's p2's turn
        self.assertEqual(game.active_player, p2)
        self.assertEqual(game.expected_action, message.THINKERORLEAD)


    def test_finish_amphitheatre_with_architect_out_of_town(self):
        d = TestDeck()
        game = test_setup.two_player_lead('Architect', deck=d)

        p1, p2 = game.players
        p1.hand.set_content([d.dock0])
        p1.stockpile.set_content([d.wall0])
        p1.buildings.append(Building(d.amphitheatre0, 'Concrete', materials=[d.bridge0]))

        a = message.GameAction(message.ARCHITECT, d.amphitheatre0, d.wall0, None)
        game.handle(a)

        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.expected_action, message.CRAFTSMAN)

        self.assertTrue(game.oot_allowed)

        # Should have 4 influence now and 4 craftsman actions stacked up
        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        game.handle(a)


    def test_amphitheatre_out_of_town_with_architect_and_craftsman_not_allowed(self):
        d = TestDeck()
        game = test_setup.two_player_lead('Architect', deck=d,
                clientele=[['Tower'],[]])
        game.in_town_sites = ['Brick'] # No wood site for Dock

        p1, p2 = game.players
        p1.hand.set_content([d.dock0])
        p1.stockpile.set_content([d.wall0])
        p1.buildings.append(Building(d.amphitheatre0, 'Concrete', materials=[d.bridge0]))

        a = message.GameAction(message.ARCHITECT, d.amphitheatre0, d.wall0, None)
        game.handle(a)

        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.expected_action, message.CRAFTSMAN)

        # Skip first 3 of 4 actions and try using last+client to out-of-town Dock.
        for i in range(3):
            a = message.GameAction(message.CRAFTSMAN, None, None, None)
            game.handle(a)

        self.assertFalse(game.oot_allowed)

        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        with self.assertRaises(GTRError):
            game.handle(a)


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

        a = GameAction(message.ARCHITECT, d.circus0, None, 'Wood')
        self.game.handle(a)

        a = GameAction(message.STAIRWAY, d.shrine0, d.bath0)
        self.game.handle(a)

        self.assertIn('Bath', self.p2.get_building(d.shrine0).stairway_materials)
        self.assertTrue(self.game._player_has_active_building(self.p1, 'Shrine'))
        self.assertTrue(self.game._player_has_active_building(self.p2, 'Shrine'))

        self.assertEqual(self.p1.buildings[1], Building(d.circus0, 'Wood'))
        
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_stairway_alone(self):
        d = self.deck
        a = GameAction(message.ARCHITECT, None, None, None)
        self.game.handle(a)

        a = GameAction(message.STAIRWAY, d.tower0, d.storeroom0)
        self.game.handle(a)

        self.assertIn('Storeroom', self.p2.get_building(d.tower0).stairway_materials)
        self.assertTrue(self.game._player_has_active_building(self.p1, 'Tower'))
        self.assertTrue(self.game._player_has_active_building(self.p2, 'Tower'))

        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_skip_stairway(self):
        a = GameAction(message.ARCHITECT, None, None, None)
        self.game.handle(a)

        a = GameAction(message.STAIRWAY, None, None)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_add_to_incomplete_building(self):
        d = self.deck

        self.p2.buildings.append(Building(d.wall0, 'Concrete'))

        a = GameAction(message.ARCHITECT, None, None, None)
        self.game.handle(a)

        a = GameAction(message.STAIRWAY, d.wall0, d.storeroom0)

        mon = Monitor()
        mon.modified(self.game)

        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


class TestPrison(unittest.TestCase):
    """Test completeing a prison and stealing buildings.
    """
    
    def setUp(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.two_player_lead('Craftsman',
                buildings=[[],['foundry0', 'temple0']],
                deck = self.deck)

        self.p1, self.p2 = self.game.players

        self.p1.buildings.append(
                Building(d.prison0, 'Stone', materials=[d.garden, d.garden]))

        self.p1.hand.set_content([d.villa0])

        a = message.GameAction(message.CRAFTSMAN, d.prison0, d.villa0, None)
        self.game.handle(a)

        self.assertTrue(self.game._player_has_active_building(self.p1, 'Prison'))
        self.assertEqual(self.game.expected_action, message.PRISON)
        self.assertIn('Stone', self.p1.influence)


    def test_prison_steal(self):
        """Test completing a prison to steal a building that doesn't do anything.
        """
        d = self.deck

        self.assertFalse(self.game._player_has_active_building(self.p1, 'Temple'))

        a = message.GameAction(message.PRISON, d.temple0)
        self.game.handle(a)

        self.assertTrue(self.game._player_has_active_building(self.p1, 'Temple'))
        self.assertFalse(self.game._player_has_active_building(self.p2, 'Temple'))

        self.assertNotIn('Stone', self.p1.influence)
        self.assertIn('Stone', self.p2.influence)


    def test_prison_no_steal(self):
        """Test completing a prison and skipping the building steal.
        """
        a = message.GameAction(message.PRISON, None)
        self.game.handle(a)

        self.assertTrue(self.game._player_has_active_building(self.p2, 'Temple'))
        self.assertFalse(self.game._player_has_active_building(self.p1, 'Temple'))

        self.assertIn('Stone', self.p1.influence)


    def test_prison_steal_and_resolve_building(self):
        """Test completing a prison to steal a building with an
        Upon completion ability, which is triggered again.
        """
        d = self.deck

        self.assertFalse(self.game._player_has_active_building(self.p1, 'Foundry'))

        a = message.GameAction(message.PRISON, d.foundry0)
        self.game.handle(a)

        self.assertTrue(self.game._player_has_active_building(self.p1, 'Foundry'))
        self.assertFalse(self.game._player_has_active_building(self.p2, 'Foundry'))

        self.assertNotIn('Stone', self.p1.influence)
        self.assertIn('Stone', self.p2.influence)

        self.assertEqual(self.game.active_player, self.p1)
        self.assertEqual(self.game.expected_action, message.LABORER)


    def test_prison_incomplete_building(self):
        """Try to illegally steal an incomplete building with Prison.
        """
        d = self.deck

        self.p2.buildings.append(Building(d.shrine0, 'Brick'))

        a = message.GameAction(message.PRISON, d.shrine0)

        mon = Monitor()
        mon.modified(self.game)

        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


class TestAcademy(unittest.TestCase):
    """Test thinker at the end of the turn with Academy.
    """

    def setUp(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.two_player_lead('Craftsman',
                buildings=[['academy0'],[]],
                deck = self.deck)

        self.p1, self.p2 = self.game.players

        self.p1.hand.set_content([d.dock0])


    def test_thinker_after_craftsman(self):
        d = self.deck

        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.SKIPTHINKER)
        self.assertEqual(self.game.active_player, self.p1)

        a = message.GameAction(message.SKIPTHINKER, False)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.THINKERTYPE)
        self.assertEqual(self.game.active_player, self.p1)

        # thinker for jack
        a = message.GameAction(message.THINKERTYPE, True)
        self.game.handle(a)

        self.assertIn('Jack', self.p1.hand)
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)
        self.assertEqual(self.game.active_player, self.p2)


    def test_skip_thinker_after_craftsman(self):
        d = self.deck

        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.SKIPTHINKER)
        self.assertEqual(self.game.active_player, self.p1)

        a = message.GameAction(message.SKIPTHINKER, True)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)
        self.assertEqual(self.game.active_player, self.p2)


    def test_perform_craftsman_flag_reset(self):
        d = self.deck

        a = message.GameAction(message.CRAFTSMAN, d.dock0, None, 'Wood')
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.SKIPTHINKER)
        self.assertEqual(self.game.active_player, self.p1)

        self.assertFalse(self.p1.performed_craftsman)


    def test_no_thinker_after_skipping_craftsman(self):
        d = self.deck

        a = message.GameAction(message.CRAFTSMAN, None, None, None)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)
        self.assertEqual(self.game.active_player, self.p2)


class TestAqueduct(unittest.TestCase):

    def setUp(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.two_player_lead('Patron',
                buildings=[['Aqueduct'],[]])

        self.p1, self.p2 = self.game.players

        self.p1.influence.append('Concrete') #two_player_lead doesn't set this.
        self.p1.hand.set_content([d.dock0])
        self.game.pool.set_content([d.wall0])


    def test_patron_from_hand_and_pool(self):
        d = self.deck

        a = message.GameAction(message.PATRONFROMPOOL, d.wall0)
        self.game.handle(a)

        self.assertNotIn('Wall', self.game.pool)
        self.assertIn('Wall', self.p1.clientele)

        a = message.GameAction(message.PATRONFROMHAND, d.dock0)
        self.game.handle(a)

        self.assertNotIn('Dock', self.p1.hand)
        self.assertIn('Dock', self.p1.clientele)

        self.assertEqual(self.game._clientele_limit(self.p1), 8)


    def test_patron_from_hand_only(self):
        d = self.deck

        a = message.GameAction(message.PATRONFROMPOOL, None)
        self.game.handle(a)

        self.assertIn('Wall', self.game.pool)
        self.assertNotIn('Wall', self.p1.clientele)

        a = message.GameAction(message.PATRONFROMHAND, d.dock0)
        self.game.handle(a)

        self.assertNotIn('Dock', self.p1.hand)
        self.assertIn('Dock', self.p1.clientele)

        self.assertEqual(self.game._clientele_limit(self.p1), 8)


class TestArchway(unittest.TestCase):

    def setUp(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.two_player_lead('Architect',
                buildings=[['Archway'],[]])

        self.p1, self.p2 = self.game.players

        self.game.pool.set_content([d.wall0])

        self.p1.buildings.append(Building(d.storeroom0, 'Concrete'))

        self.assertTrue(self.game._player_has_active_building(self.p1, 'Archway'))

    def test_add_material_from_pool(self):
        d = self.deck

        a = message.GameAction(message.ARCHITECT, d.storeroom0, d.wall0, None)
        self.game.handle(a)

        self.assertNotIn('Wall', self.game.pool)
        self.assertIn('Wall', self.p1.buildings[1].materials)


class TestAtrium(unittest.TestCase):

    def setUp(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.two_player_lead('Merchant',
                buildings=[['Atrium'],[]])

        self.p1, self.p2 = self.game.players

        self.game.library.set_content([d.dock0, d.road0, d.road1])

        self.assertTrue(self.game._player_has_active_building(self.p1, 'Atrium'))


    def test_merchant_from_deck(self):
        d = self.deck
        a = message.GameAction(message.MERCHANT, True)
        self.game.handle(a)

        self.assertNotIn(d.dock0, self.game.library)
        self.assertIn(d.dock0, self.p1.vault)
    

class TestBar(unittest.TestCase):

    def setUp(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.two_player_lead('Patron',
                buildings=[['Bar'],[]])

        self.p1, self.p2 = self.game.players

        self.game.library.set_content([d.dock0, d.dock1, d.dock2])
        self.game.pool.set_content([d.wall0])

        self.assertTrue(self.game._player_has_active_building(self.p1, 'Bar'))

    def test_patron_from_pool_and_deck(self):
        d = self.deck

        a = message.GameAction(message.PATRONFROMPOOL, d.wall0)
        self.game.handle(a)

        self.assertNotIn(d.wall0, self.game.pool)
        self.assertIn(d.wall0, self.p1.clientele)

        a = message.GameAction(message.PATRONFROMDECK, True)
        self.game.handle(a)

        self.assertNotIn(d.dock0, self.game.library)
        self.assertIn(d.dock0, self.p1.clientele)

        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)
        self.assertEqual(self.game.active_player, self.p2)


    def test_patron_from_deck_only(self):
        d = self.deck

        a = message.GameAction(message.PATRONFROMPOOL, None)
        self.game.handle(a)

        self.assertIn(d.wall0, self.game.pool)
        self.assertNotIn(d.wall0, self.p1.clientele)

        a = message.GameAction(message.PATRONFROMDECK, True)
        self.game.handle(a)

        self.assertNotIn(d.dock0, self.game.library)
        self.assertIn(d.dock0, self.p1.clientele)

        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)
        self.assertEqual(self.game.active_player, self.p2)

    
    def test_skip_all_patrons(self):
        d = self.deck

        a = message.GameAction(message.PATRONFROMPOOL, None)
        self.game.handle(a)

        self.assertIn(d.wall0, self.game.pool)
        self.assertNotIn(d.wall0, self.p1.clientele)

        a = message.GameAction(message.PATRONFROMDECK, False)
        self.game.handle(a)

        self.assertIn(d.dock0, self.game.library)
        self.assertNotIn(d.dock0, self.p1.clientele)

        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)
        self.assertEqual(self.game.active_player, self.p2)


class TestBasilica(unittest.TestCase):

    def setUp(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.two_player_lead('Merchant',
                buildings=[['Basilica'],[]])

        self.p1, self.p2 = self.game.players

        self.p1.stockpile.set_content([d.dock0])
        self.p1.hand.set_content([d.road0])

        self.assertTrue(self.game._player_has_active_building(self.p1, 'Basilica'))


    def test_merchant_from_hand_and_stockpile(self):
        d = self.deck
        a = message.GameAction(message.MERCHANT, False, d.dock0, d.road0)
        self.game.handle(a)

        self.assertNotIn(d.dock0, self.p1.stockpile)
        self.assertIn(d.dock0, self.p1.vault)

        self.assertNotIn(d.road0, self.p1.hand)
        self.assertIn(d.road0, self.p1.vault)


    def test_merchant_from_hand_only(self):
        d = self.deck
        a = message.GameAction(message.MERCHANT, False, d.road0)
        self.game.handle(a)

        self.assertIn(d.dock0, self.p1.stockpile)
        self.assertNotIn(d.dock0, self.p1.vault)

        self.assertNotIn(d.road0, self.p1.hand)
        self.assertIn(d.road0, self.p1.vault)
    

    def test_merchant_from_stockpile_only(self):
        d = self.deck
        a = message.GameAction(message.MERCHANT, False, d.dock0)
        self.game.handle(a)

        self.assertNotIn(d.dock0, self.p1.stockpile)
        self.assertIn(d.dock0, self.p1.vault)

        self.assertIn(d.road0, self.p1.hand)
        self.assertNotIn(d.road0, self.p1.vault)


class TestCircusMaximus(unittest.TestCase):

    def nothing(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.two_player_lead('Patron',
                buildings=[['Circus Maximus'],['Circus Maximus']])

        self.p1, self.p2 = self.game.players

        self.game.library.set_content([d.dock0])
        self.game.pool.set_content([d.wall0])

        self.assertTrue(self.game._player_has_active_building(self.p1, 'Bar'))


    def test_double_clientele_actions_leading(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Laborer',
                buildings=[['Circus Maximus'],[]],
                clientele=[['Insula'],[]],
                deck = d)

        p1, p2 = game.players

        game.pool.set_content([d.road0, d.road1, d.road2])

        for card in [d.road0, d.road1, d.road2]:
            a = message.GameAction(message.LABORER, card)
            game.handle(a)

        self.assertEqual(game.expected_action, message.THINKERORLEAD)
        self.assertEqual(game.active_player, p2)


    def test_double_clientele_actions_following(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Laborer',
                buildings=[[], ['Circus Maximus']],
                clientele=[[], ['Bar', 'Bar']],
                follow = True,
                deck = d)

        p1, p2 = game.players

        game.pool.set_content([d.road0, d.road1, d.road2, d.road3, d.road4])

        self.assertEqual(game.expected_action, message.LABORER)
        self.assertEqual(game.active_player, p1)

        # Laborer for nothing with p1
        a = message.GameAction(message.LABORER)
        game.handle(a)

        self.assertEqual(game.expected_action, message.LABORER)
        self.assertEqual(game.active_player, p2)

        for card in [d.road0, d.road1, d.road2, d.road3, d.road4]:
            a = message.GameAction(message.LABORER, card)
            game.handle(a)

        self.assertEqual(game.expected_action, message.THINKERORLEAD)
        self.assertEqual(game.active_player, p2)


    def test_single_clientele_actions_not_following(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Laborer',
                buildings=[[], ['Circus Maximus']],
                clientele=[[], ['Bar', 'Bar']],
                deck = d)

        p1, p2 = game.players

        game.pool.set_content([d.road0, d.road1, d.road2])

        self.assertTrue(game._player_has_active_building(p2, 'Circus Maximus'))
        self.assertEqual(game.expected_action, message.LABORER)
        self.assertEqual(game.active_player, p1)

        # Laborer for nothing with p1
        a = message.GameAction(message.LABORER)
        game.handle(a)

        self.assertEqual(game.expected_action, message.LABORER)
        self.assertEqual(game.active_player, p2)

        # Only two clients, but Circus Maximus isn't active when not following.
        for card in [d.road0, d.road1]:
            a = message.GameAction(message.LABORER, card)
            game.handle(a)

        self.assertEqual(game.expected_action, message.THINKERORLEAD)
        self.assertEqual(game.active_player, p2)


    def test_complete_circus_maximus_on_lead_doubles_clientele(self):
        """Completing the Circus Maximus with the lead action
        causes the clientele to be doubled.
        """
        d = TestDeck()

        game = test_setup.two_player_lead('Craftsman',
                buildings=[[], []],
                clientele=[['Dock'], []],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.garden0, d.bar0, d.bar1])
        p1.buildings.append(Building(d.circusmaximus0, 'Stone',
                materials = [d.villa, d.villa]))

        self.assertFalse(game._player_has_active_building(p1, 'Circus Maximus'))
        self.assertEqual(game.expected_action, message.CRAFTSMAN)
        self.assertEqual(game.active_player, p1)

        # Finish with lead action
        a = message.GameAction(message.CRAFTSMAN, d.circusmaximus0, d.garden0, None)
        game.handle(a)

        self.assertTrue(game._player_has_active_building(p1, 'Circus Maximus'))

        self.assertEqual(game.expected_action, message.CRAFTSMAN)
        self.assertEqual(game.active_player, p1)
        
        # Start and finish a Bar
        a = message.GameAction(message.CRAFTSMAN, d.bar0, None, 'Rubble')
        game.handle(a)
        a = message.GameAction(message.CRAFTSMAN, d.bar0, d.bar1, None)
        game.handle(a)

        self.assertEqual(game.expected_action, message.THINKERORLEAD)
        self.assertEqual(game.active_player, p2)


    def test_complete_circus_maximus_doubles_remaining_clientele(self):
        """Completing the Circus Maximus with a clientele action
        causes the remaining clientele to be doubled, but not the one
        that just completed the action.
        """
        d = TestDeck()

        game = test_setup.two_player_lead('Craftsman',
                buildings=[[], []],
                clientele=[['Dock', 'Dock'], []],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.garden0, d.garden1, d.bar0, d.bar1])
        p1.buildings.append(Building(d.circusmaximus0, 'Stone',
                materials = [d.villa]))

        self.assertFalse(game._player_has_active_building(p1, 'Circus Maximus'))
        self.assertEqual(game.expected_action, message.CRAFTSMAN)
        self.assertEqual(game.active_player, p1)

        # Finish CM with lead action and first clientele
        a = message.GameAction(message.CRAFTSMAN, d.circusmaximus0, d.garden0, None)
        game.handle(a)
        a = message.GameAction(message.CRAFTSMAN, d.circusmaximus0, d.garden1, None)
        game.handle(a)

        self.assertTrue(game._player_has_active_building(p1, 'Circus Maximus'))

        self.assertEqual(game.expected_action, message.CRAFTSMAN)
        self.assertEqual(game.active_player, p1)
        
        # Start and finish a Bar
        a = message.GameAction(message.CRAFTSMAN, d.bar0, None, 'Rubble')
        game.handle(a)
        a = message.GameAction(message.CRAFTSMAN, d.bar0, d.bar1, None)
        game.handle(a)

        self.assertEqual(game.expected_action, message.THINKERORLEAD)
        self.assertEqual(game.active_player, p2)


    def test_circus_maximus_legionary_count(self):
        """Legionary rolls all actions into one demand, revealing many
        cards at once. To do this, it needs to know if the Circus Maximus
        is in effect.
        """
        d = TestDeck()

        game = test_setup.two_player_lead('Legionary',
                buildings=[['Circus Maximus'], []],
                clientele=[['Shrine'], []],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.garden0, d.garden1, d.bar0])
        p2.hand.set_content([d.villa0, d.villa1, d.road0])

        self.assertTrue(game._player_has_active_building(p1, 'Circus Maximus'))
        self.assertEqual(game.expected_action, message.LEGIONARY)
        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.legionary_count, 3)

        # Demand three materials with legionary + doubled client
        a = message.GameAction(message.LEGIONARY, d.garden0, d.garden1, d.bar0)
        game.handle(a)

        a = message.GameAction(message.TAKEPOOLCARDS)
        game.handle(a)

        self.assertEqual(game.expected_action, message.GIVECARDS)
        self.assertEqual(game.active_player, p2)
        self.assertEqual(game.legionary_count, 3)

        # Give three cards
        a = message.GameAction(message.GIVECARDS, d.villa0, d.villa1, d.road0)
        game.handle(a)


    def test_circus_maximus_exceed_legionary_count(self):
        """Legionary rolls all actions into one demand, revealing many
        cards at once. To do this, it needs to know if the Circus Maximus
        is in effect. Try to illegally demand too many cards.
        """
        d = TestDeck()

        game = test_setup.two_player_lead('Legionary',
                buildings=[['Circus Maximus'], []],
                clientele=[['Shrine'], []],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.garden0, d.garden1, d.bar0, d.bar1])
        p2.hand.set_content([d.villa0, d.villa1, d.road0])

        self.assertTrue(game._player_has_active_building(p1, 'Circus Maximus'))
        self.assertEqual(game.expected_action, message.LEGIONARY)
        self.assertEqual(game.active_player, p1)
        self.assertEqual(game.legionary_count, 3)

        mon = Monitor()
        mon.modified(game)

        # Demand three materials with legionary + doubled client
        a = message.GameAction(message.LEGIONARY, d.garden0, d.garden1, d.bar0, d.bar1)
        with self.assertRaises(GTRError):
            game.handle(a)

        self.assertFalse(mon.modified(game))


class TestGate(unittest.TestCase):

    def test_gate_activates_marble_buildings(self):
        d = TestDeck()
        game = test_setup.simple_two_player()
        p1, p2 = game.players

        p1.buildings.append(Building(d.temple0, 'Marble'))
        p1.buildings.append(Building(d.statue0, 'Rubble'))
        p1.buildings.append(Building(d.basilica0, 'Basilica'))

        self.assertFalse(game._player_has_active_building(p1, 'Temple'))
        self.assertFalse(game._player_has_active_building(p1, 'Statue'))
        self.assertFalse(game._player_has_active_building(p1, 'Basilica'))

        p1.buildings.append(Building(d.gate, 'Brick', complete=True))

        self.assertTrue(game._player_has_active_building(p1, 'Temple'))
        self.assertTrue(game._player_has_active_building(p1, 'Statue'))
        self.assertTrue(game._player_has_active_building(p1, 'Basilica'))

        self.assertEqual(game._max_hand_size(p1), 9)
        self.assertEqual(game._player_score(p1), 5) # Statue points


    def test_complete_buidling_already_active_with_gate(self):
        """Complete a building that's already active because of Gate.
        """
        d = TestDeck()
        game = test_setup.two_player_lead('Craftsman',
                buildings=[['Gate'],[]],
                deck=d)

        p1, p2 = game.players

        p1.hand.set_content([d.stairway0])
        
        b_temple = Building(d.temple0, 'Marble', materials=[d.temple1, d.statue0])
        p1.buildings.append(b_temple)

        p1.buildings.append(Building(d.gate, 'Brick', complete=True))

        self.assertTrue(game._player_has_active_building(p1, 'Temple'))
        self.assertNotIn(b_temple, p1.complete_buildings)

        a = message.GameAction(message.CRAFTSMAN, d.temple0, d.stairway0, None)
        game.handle(a)

        self.assertTrue(game._player_has_active_building(p1, 'Temple'))
        self.assertIn(b_temple, p1.complete_buildings)


class TestForum(unittest.TestCase):
    """Forum is continuously active once constructed. The cases where conditions
    change such that the Forum could be active are:

    *)  Patron a new client (from hand, deck, or pool)
    *)  Finish a Forum building.
    *)  Finish a Gate, activating an incomplete Forum.
    *)  Finish a Ludus Magna or Storeroom that allows a combination
        of clients satisfying the Forum.
    *)  Stairway an opponent's forum
    *)  Stairway a Gate, activating an incomplete Forum.
    *)  Stairway a Ludus Magna or Storeroom, allowing the correct
        clientele combination
    *)  Stealing a Forum with a Prison.
    *)  Stealing a Gate, activating an incomplete Forum.
    *)  Stealing a Ludus Magna or Storeroom, allowing the correct
        clientele combination
    *)  Starting a Forum with an active Gate.

    """
    
    def test_patron_from_pool_satisfying_forum(self):
        """Patron the final client to satisfy a Forum.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Bath', 'Villa']
        g = test_setup.two_player_lead('Patron',
                clientele=[p1_clientele,[]],
                buildings=[['Forum'],[]],
                deck = d)

        p1, p2 = g.players

        g.pool.set_content([d.temple0])

        p1.influence.extend(['Stone', 'Marble']) # Need room in clientele

        a = message.GameAction(message.PATRONFROMPOOL, d.temple0)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_patron_from_hand_satisfying_forum(self):
        """Patron the final client to satisfy a Forum.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Bath', 'Villa']
        g = test_setup.two_player_lead('Patron',
                clientele=[p1_clientele,[]],
                buildings=[['Forum', 'Aqueduct'],[]],
                deck = d)

        p1, p2 = g.players

        p1.hand.set_content([d.temple0])

        p1.influence.extend(['Stone', 'Marble']) # Need room in clientele

        a = message.GameAction(message.PATRONFROMPOOL, None)
        g.handle(a)

        a = message.GameAction(message.PATRONFROMHAND, d.temple0)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_patron_from_deck_satisfying_forum(self):
        """Patron the final client to satisfy a Forum.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Bath', 'Villa']
        g = test_setup.two_player_lead('Patron',
                clientele=[p1_clientele,[]],
                buildings=[['Forum', 'Bar'],[]],
                deck = d)

        p1, p2 = g.players

        g.library.set_content([d.temple0, d.road0])

        p1.influence.extend(['Stone', 'Marble']) # Need room in clientele

        a = message.GameAction(message.PATRONFROMPOOL, None)
        g.handle(a)

        a = message.GameAction(message.PATRONFROMDECK, True)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_forum_building_resolution(self):
        """Finish a Forum building, winning the game.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Bath', 'Villa', 'Temple']
        g = test_setup.two_player_lead('Craftsman',
                clientele=[p1_clientele,[]],
                deck = d)

        p1, p2 = g.players

        p1.hand.set_content([d.stairway0])
        p1.buildings.append(Building(d.forum0, 'Marble', materials=[d.basilica, d.basilica]))

        a = message.GameAction(message.CRAFTSMAN, d.forum0, d.stairway0, None)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_gate_building_resolution(self):
        """Finish a Gate building, activating Forum, winning the game.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Bath', 'Villa', 'Temple']
        g = test_setup.two_player_lead('Craftsman',
                clientele=[p1_clientele,[]],
                deck = d)

        p1, p2 = g.players

        p1.hand.set_content([d.shrine0])
        p1.buildings.append(Building(d.forum0, 'Marble', materials=[d.basilica, d.basilica]))
        p1.buildings.append(Building(d.gate0, 'Brick', materials=[d.shrine]))

        a = message.GameAction(message.CRAFTSMAN, d.gate0, d.shrine0, None)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_build_ludus_satisfying_forum(self):
        """Build a Ludus so Merchants can fill out other roles,
        winning with a Forum.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Villa', 'Villa', 'Garden']
        g = test_setup.two_player_lead('Craftsman',
                clientele=[p1_clientele,[]],
                buildings=[['Forum'],[]],
                deck = d)

        p1, p2 = g.players

        p1.hand.set_content([d.temple0])
        p1.buildings.append(Building(d.ludusmagna0, 'Marble',
                materials=[d.temple, d.temple]))

        p1.influence.extend(['Stone', 'Marble']) # Need room in clientele

        a = message.GameAction(message.CRAFTSMAN, d.ludusmagna0, d.temple0, None)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_build_storeroom_satisfying_forum(self):
        """Build a Storeroom so Laborer can be filled by another client,
        winning with a Forum.
        """

        d = TestDeck()

        p1_clientele = ['Temple', 'Dock', 'Wall', 'Bath', 'Villa', 'Garden']
        g = test_setup.two_player_lead('Craftsman',
                clientele=[p1_clientele,[]],
                buildings=[['Forum'],[]],
                deck = d)

        p1, p2 = g.players

        p1.hand.set_content([d.wall0])
        p1.buildings.append(Building(d.storeroom0, 'Concrete',
                materials=[d.bridge]))

        a = message.GameAction(message.CRAFTSMAN, d.storeroom0, d.wall0, None)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_prison_stealing_forum(self):
        """Finish a Prison, stealing a Forum with all clientele.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Bath', 'Villa', 'Temple']
        g = test_setup.two_player_lead('Craftsman',
                clientele=[p1_clientele,[]],
                buildings=[[],['forum0']],
                deck = d)

        p1, p2 = g.players

        p1.hand.set_content([d.garden0])
        p1.buildings.append(Building(d.prison0, 'Stone', materials=[d.villa, d.villa]))

        a = message.GameAction(message.CRAFTSMAN, d.prison0, d.garden0, None)
        g.handle(a)

        a = message.GameAction(message.PRISON, d.forum0)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_prison_stealing_gate_activating_forum(self):
        """Finish a Prison, stealing a Gate, activating an incomplete Forum.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Bath', 'Villa', 'Temple']
        g = test_setup.two_player_lead('Craftsman',
                clientele=[p1_clientele,[]],
                buildings=[[],['gate0']],
                deck = d)

        p1, p2 = g.players

        p1.hand.set_content([d.garden0])
        p1.buildings.append(Building(d.forum0, 'Marble', materials=[d.basilica, d.basilica]))
        p1.buildings.append(Building(d.prison0, 'Stone', materials=[d.villa, d.villa]))

        a = message.GameAction(message.CRAFTSMAN, d.prison0, d.garden0, None)
        g.handle(a)

        a = message.GameAction(message.PRISON, d.gate0)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_prison_stealing_storeroom_activating_forum(self):
        """Finish a Prison, stealing a Storeroom, activating Forum.
        """
        d = TestDeck()

        p1_clientele = ['Temple', 'Dock', 'Wall', 'Bath', 'Villa', 'Garden']
        g = test_setup.two_player_lead('Craftsman',
                clientele=[p1_clientele,[]],
                buildings=[['Forum'],['storeroom0']],
                deck = d)

        p1, p2 = g.players

        p1.hand.set_content([d.garden0])
        p1.buildings.append(Building(d.prison0, 'Stone', materials=[d.villa, d.villa]))

        a = message.GameAction(message.CRAFTSMAN, d.prison0, d.garden0, None)
        g.handle(a)

        a = message.GameAction(message.PRISON, d.storeroom0)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_prison_stealing_ludus_activating_forum(self):
        """Finish a Prison, stealing a Ludus Magna, activating
        Forum.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Villa', 'Garden', 'Garden']
        g = test_setup.two_player_lead('Craftsman',
                clientele=[p1_clientele,[]],
                buildings=[['Forum'],['ludusmagna0']],
                deck = d)

        p1, p2 = g.players

        p1.hand.set_content([d.garden0])
        p1.buildings.append(Building(d.prison0, 'Stone', materials=[d.villa, d.villa]))

        a = message.GameAction(message.CRAFTSMAN, d.prison0, d.garden0, None)
        g.handle(a)

        a = message.GameAction(message.PRISON, d.ludusmagna0)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_stairway_forum(self):
        """Add to Forum with Stairway with all client roles.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Bath', 'Villa', 'Temple']
        g = test_setup.two_player_lead('Architect',
                clientele=[p1_clientele,[]],
                buildings=[['Stairway'],['forum0']],
                deck = d)

        p1, p2 = g.players

        p1.stockpile.set_content([d.temple0])

        a = message.GameAction(message.ARCHITECT, None, None, None)
        g.handle(a)

        a = message.GameAction(message.STAIRWAY, d.forum0, d.temple0)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_stairway_gate_activating_forum(self):
        """Add to Gate with Stairway with all client roles and an
        incomplete Forum.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Bath', 'Villa', 'Temple']
        g = test_setup.two_player_lead('Architect',
                clientele=[p1_clientele,[]],
                buildings=[['Stairway'],['gate0']],
                deck = d)

        p1, p2 = g.players

        p1.stockpile.set_content([d.bath0])
        p1.buildings.append(Building(d.forum0, 'Marble', materials=[d.basilica, d.basilica]))

        a = message.GameAction(message.ARCHITECT, None, None, None)
        g.handle(a)

        a = message.GameAction(message.STAIRWAY, d.gate0, d.bath0)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_stairway_ludus_activating_forum(self):
        """Add to Ludus with Stairway with all client roles and an
        incomplete Forum.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Villa', 'Villa', 'Garden']
        g = test_setup.two_player_lead('Architect',
                clientele=[p1_clientele,[]],
                buildings=[['Forum', 'Stairway'],['ludusmagna0']],
                deck = d)

        p1, p2 = g.players

        p1.stockpile.set_content([d.temple0])

        a = message.GameAction(message.ARCHITECT, None, None, None)
        g.handle(a)

        a = message.GameAction(message.STAIRWAY, d.ludusmagna0, d.temple0)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_stairway_storeroom_activating_forum(self):
        """Add to Storeroom with Stairway with all client roles and an
        incomplete Forum.
        """
        d = TestDeck()

        p1_clientele = ['Temple', 'Dock', 'Wall', 'Bath', 'Villa', 'Garden']
        g = test_setup.two_player_lead('Architect',
                clientele=[p1_clientele,[]],
                buildings=[['Forum', 'Stairway'],['storeroom0']],
                deck = d)

        p1, p2 = g.players

        p1.stockpile.set_content([d.wall0])

        a = message.GameAction(message.ARCHITECT, None, None, None)
        g.handle(a)

        a = message.GameAction(message.STAIRWAY, d.storeroom0, d.wall0)

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_start_forum_with_active_gate(self):
        """Start Forum with an active Gate.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Bath', 'Villa', 'Temple']
        g = test_setup.two_player_lead('Architect',
                clientele=[p1_clientele,[]],
                buildings=[['Stairway'],[]],
                deck = d)

        p1, p2 = g.players

        p1.hand.set_content([d.forum0])

        # Active Gate through Stairway
        p2.buildings.append(Building(d.gate0, 'Brick', stairway_materials=[d.shrine0]))

        a = message.GameAction(message.ARCHITECT, d.forum0, None, 'Marble')

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


    def test_start_forum_on_last_site_with_active_gate(self):
        """Start Forum with an active Gate.
        """
        d = TestDeck()

        p1_clientele = ['Road', 'Dock', 'Wall', 'Bath', 'Villa', 'Temple']
        g = test_setup.two_player_lead('Architect',
                clientele=[p1_clientele,[]],
                buildings=[['Stairway'],[]],
                deck = d)

        p1, p2 = g.players

        p1.hand.set_content([d.forum0])

        g.in_town_sites = ['Marble']

        # Active Gate through Stairway
        p2.buildings.append(Building(d.gate0, 'Brick', stairway_materials=[d.shrine0]))

        a = message.GameAction(message.ARCHITECT, d.forum0, None, 'Marble')

        with self.assertRaises(GameOver):
            g.handle(a)

        self.assertIn(p1, g.winners)


class TestLatrine(unittest.TestCase):

    def setUp(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.simple_two_player()

        self.p1, self.p2 = self.game.players

        self.p1.buildings.append(Building(d.latrine, 'Rubble', complete=True))

        self.p1.hand.set_content([d.road0, d.jack0])
        self.p2.hand.set_content([d.road1, d.jack1])


    def test_discard_on_lead(self):
        d = self.deck

        a = message.GameAction(message.THINKERORLEAD, True)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.USELATRINE)

        a = message.GameAction(message.USELATRINE, d.road0)
        self.game.handle(a)

        self.assertIn(d.road0, self.game.pool)
        self.assertNotIn(d.road0, self.p1.hand)

        self.assertEqual(self.game.expected_action, message.THINKERTYPE)
        self.assertEqual(self.game.active_player, self.p1)


    def test_discard_jack(self):
        d = self.deck

        a = message.GameAction(message.THINKERORLEAD, True)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.USELATRINE)

        a = message.GameAction(message.USELATRINE, d.jack0)
        self.game.handle(a)

        self.assertIn(d.jack0, self.game.jacks)
        self.assertNotIn(d.jack0, self.p1.hand)

        self.assertEqual(self.game.expected_action, message.THINKERTYPE)
        self.assertEqual(self.game.active_player, self.p1)


    def test_discard_following(self):
        d = self.deck

        self.p2.buildings.append(Building(d.latrine, 'Rubble', complete=True))

        a = message.GameAction(message.THINKERORLEAD, False)
        self.game.handle(a)

        a = message.GameAction(message.LEADROLE, 'Laborer', 1, d.road0)
        self.game.handle(a)

        a = message.GameAction(message.FOLLOWROLE, 0)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.USELATRINE)
        self.assertEqual(self.game.active_player, self.p2)

        a = message.GameAction(message.USELATRINE, d.road1)
        self.game.handle(a)

        self.assertIn(d.road1, self.game.pool)
        self.assertNotIn(d.road1, self.p2.hand)

        self.assertEqual(self.game.expected_action, message.THINKERTYPE)
        self.assertEqual(self.game.active_player, self.p2)


class TestLudusMagna(unittest.TestCase):

    def setUp(self):
        d = TestDeck()
        self.deck = d

        clientele = ['Dock', 'Villa']
        self.game = test_setup.two_player_lead('Craftsman',
                clientele=[clientele, clientele],
                buildings=[['Ludus Magna'],[]],
                deck = d)

        self.p1, self.p2 = self.game.players


    def test_merchant_as_craftsman(self):


        a = message.GameAction(message.CRAFTSMAN, None, None, None)
        self.game.handle(a)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)
        self.assertEqual(self.game.active_player, self.p1)

        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)
        self.assertEqual(self.game.active_player, self.p2)


    def test_merchant_as_craftsman_out_of_town(self):
        """Start out of town, but with merchant as the second client in the
        out-of-town pair.
        """
        d  = self.deck
        self.p1.hand.set_content([d.latrine0])
        self.game.in_town_sites = ['Brick']

        self.assertEqual(self.game.active_player, self.p1)
        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)
        self.assertTrue(self.game.oot_allowed)

        # Use the Craftsman action from the camp.
        a = message.GameAction(message.CRAFTSMAN, None, None, None)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)
        self.assertTrue(self.game.active_player, self.p1)
        self.assertTrue(self.game.oot_allowed)

        a = message.GameAction(message.CRAFTSMAN, d.latrine0, None, 'Rubble')
        self.game.handle(a)

        self.assertNotIn(d.latrine0, self.p1.hand)
        self.assertIn('Latrine', self.p1.building_names)
        self.assertFalse(self.game._player_has_active_building(self.p1, 'Latrine'))

        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)
        self.assertEqual(self.game.active_player, self.p2)
        self.assertFalse(self.game.oot_allowed)


    def test_merchant_as_craftsman_not_following(self):
        """Player 2 didn't follow, but both clientele get to act anyway.
        """
        self.p2.buildings.append(Building(self.deck.ludusmagna, 'Marble', complete=True))

        a = message.GameAction(message.CRAFTSMAN, None, None, None)
        self.game.handle(a)
        self.game.handle(a)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)
        self.assertEqual(self.game.active_player, self.p2)

        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)
        self.assertEqual(self.game.active_player, self.p2)

        self.game.handle(a)


    def test_finish_ludus_use_merchant_client(self):
        """The first Craftsman finishes the Ludus, which activates the second
        Merchant as a Craftsman client.
        """
        d = self.deck

        self.p2.buildings.append(Building(d.ludusmagna0, 'Marble',
                materials=[d.palace, d.palace]))

        self.p2.hand.set_content([d.temple0, d.market0])

        self.assertEqual(self.game.active_player, self.p1)

        # 2x Craftsman client for p1 (+1 already led)
        a = message.GameAction(message.CRAFTSMAN, None, None, None)
        self.game.handle(a)
        self.game.handle(a)
        self.game.handle(a)

        self.assertEqual(self.game.active_player, self.p2)

        # First crafstman finishes Ludus
        a = message.GameAction(message.CRAFTSMAN, d.ludusmagna0, d.temple0, None)
        self.game.handle(a)

        self.assertTrue(self.game._player_has_active_building(self.p2, 'Ludus Magna'))

        # Merchant can act, start a building
        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)
        self.assertEqual(self.game.active_player, self.p2)

        a = message.GameAction(message.CRAFTSMAN, d.market0, None, 'Wood')
        self.game.handle(a)


class TestMarket(unittest.TestCase):

    def test_initial_limit(self):
        """Test limit at beginning of game.
        """

        g = test_setup.simple_two_player()

        p1, p2 = g.players

        self.assertEqual(g._vault_limit(p1), 2)
        self.assertEqual(g._vault_limit(p2), 2)


    def test_limit_with_influence(self):
        """Test limit with some completed buildings.
        """

        g = test_setup.simple_two_player()

        p1, p2 = g.players

        p1.influence = ['Stone']
        p2.influence = ['Rubble']

        self.assertEqual(g._vault_limit(p1), 5)
        self.assertEqual(g._vault_limit(p2), 3)
 
        p1.influence = ['Wood']
        p2.influence = ['Marble']

        self.assertEqual(g._vault_limit(p1), 3)
        self.assertEqual(g._vault_limit(p2), 5)
 
        p1.influence = ['Brick']
        p2.influence = ['Concrete']

        self.assertEqual(g._vault_limit(p1), 4)
        self.assertEqual(g._vault_limit(p2), 4)
 
        p1.influence = ['Brick', 'Concrete', 'Marble']
        p2.influence = ['Concrete', 'Stone', 'Rubble', 'Rubble', 'Rubble']

        self.assertEqual(g._vault_limit(p1), 9)
        self.assertEqual(g._vault_limit(p2), 10)
 

    def test_limit_with_market(self):
        """Test limit with completed Market.
        """
        d = TestDeck()

        g = test_setup.simple_two_player()

        p1, p2 = g.players

        self.assertEqual(g._vault_limit(p1), 2)

        p1.buildings.append(Building(d.market, 'Wood', complete=True))

        self.assertEqual(g._vault_limit(p1), 4)

        p1.influence = ['Stone']

        self.assertEqual(g._vault_limit(p1), 7)


class TestPalace(unittest.TestCase):
    """Test leading multiple actions with Palace.
    """

    def setUp(self):
        """ This is run prior to every test.
        """
        self.game = test_setup.simple_two_player()
        self.p1, self.p2 = self.game.players

        palace, statue = cm.get_cards(['Palace', 'Statue'])
        self.p1.buildings = [Building(palace, 'Marble', materials=[statue], complete=True)]
        
        # Indicate that we want to lead
        a = message.GameAction(message.THINKERORLEAD, False)
        self.game.handle(a)

    def test_petition_with_palace_3_actions(self):
        """Tests petition with multiple lead actions using Palace.

        Using 6 Docks and 3 Roads allows 3, 5, or 7 actions.
        """
        cards = cm.get_cards(['Road']*3 + ['Dock']*6)
        self.p1.hand.set_content(cards)

        n_actions = 3
        a = message.GameAction(message.LEADROLE, 'Craftsman', n_actions, *cards)
        self.game.handle(a)

        self.assertEqual(self.game.role_led, 'Craftsman')
        self.assertEqual(self.p1.n_camp_actions, n_actions)
        self.assertTrue(self.p1.camp.contains(cards))
        self.assertFalse(self.p1.hand.contains(['Road','Dock']))
        self.assertEqual(self.game.expected_action, message.FOLLOWROLE)

    def test_petition_with_palace_5_actions(self):
        """Tests petition with multiple lead actions using Palace.

        Using 6 Docks and 3 Roads allows 3, 5, or 7 actions.
        """
        cards = cm.get_cards(['Road']*3 + ['Dock']*6)
        self.p1.hand.set_content(cards)

        n_actions = 5
        a = message.GameAction(message.LEADROLE, 'Craftsman', n_actions, *cards)
        self.game.handle(a)

        self.assertEqual(self.game.role_led, 'Craftsman')
        self.assertEqual(self.p1.n_camp_actions, n_actions)
        self.assertTrue(self.p1.camp.contains(cards))
        self.assertFalse(self.p1.hand.contains(['Road','Dock']))
        self.assertEqual(self.game.expected_action, message.FOLLOWROLE)

    def test_petition_with_palace_7_actions(self):
        """Tests petition with multiple lead actions using Palace.

        Using 6 Docks and 3 Roads allows 3, 5, or 7 actions.
        """
        cards = cm.get_cards(['Road']*3 + ['Dock']*6)
        self.p1.hand.set_content(cards)

        n_actions = 7
        a = message.GameAction(message.LEADROLE, 'Craftsman', n_actions, *cards)
        self.game.handle(a)

        self.assertEqual(self.game.role_led, 'Craftsman')
        self.assertEqual(self.p1.n_camp_actions, n_actions)
        self.assertTrue(self.p1.camp.contains(cards))
        self.assertFalse(self.p1.hand.contains(['Road','Dock']))
        self.assertEqual(self.game.expected_action, message.FOLLOWROLE)

    def test_petition_with_illegal_n_actions(self):
        """Tests petition with multiple lead actions using Palace.

        Using 6 Docks and 3 Roads allows 3, 5, or 7 actions.
        """
        cards = cm.get_cards(['Road']*3 + ['Dock']*6)
        self.p1.hand.set_content(cards)

        n_actions = 6

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.LEADROLE, 'Craftsman', n_actions, *cards)

        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_petition_with_illegal_petition_size(self):
        """Tests petition with multiple lead actions using Palace.

        Using 6 Docks and 3 Roads allows 3, 5, or 7 actions.
        """
        cards = cm.get_cards(['Road']*3 + ['Dock']*4)
        self.p1.hand.set_content(cards)

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.LEADROLE, 'Craftsman', 1, *cards)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))

        a = message.GameAction(message.LEADROLE, 'Craftsman', 2, *cards)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))

        a = message.GameAction(message.LEADROLE, 'Craftsman', 4, *cards)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


class AmericasTestPalace(unittest.TestCase):

    def setUp(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.simple_two_player()
        self.p1, self.p2 = self.game.players

        self.p1.buildings.append(Building(d.palace, 'Marble', complete=True))
        self.p2.buildings.append(Building(d.palace, 'Marble', complete=True))

        self.p1.hand.set_content([d.road0, d.bar0, d.insula0,
                d.villa0, d.villa1, d.villa2, d.jack0])
        self.p2.hand.set_content([d.jack1, d.jack2, d.jack3])

        a = message.GameAction(message.THINKERORLEAD, False)
        self.game.handle(a)


    def test_lead_multiple_orders(self):
        d = self.deck

        a = message.GameAction(message.LEADROLE, 'Laborer', 3,
                d.road0, d.bar0, d.insula0)
        self.game.handle(a)

        self.assertEqual(self.p1.n_camp_actions, 3)
        self.assertItemsEqual(self.p1.camp, [d.road0, d.bar0, d.insula0])

        a = message.GameAction(message.FOLLOWROLE, 1, d.jack1)
        self.game.handle(a)

        self.assertEqual(self.p2.n_camp_actions, 1)
        self.assertIn(d.jack1, self.p2.camp)


    def test_lead_multiple_orders_and_jacks(self):
        d = self.deck

        a = message.GameAction(message.LEADROLE, 'Laborer', 4,
                d.road0, d.bar0, d.insula0, d.jack0)
        self.game.handle(a)

        self.assertEqual(self.p1.n_camp_actions, 4)
        self.assertItemsEqual(self.p1.camp, [d.jack0, d.road0, d.bar0, d.insula0])

        a = message.GameAction(message.FOLLOWROLE, 3,
                d.jack1, d.jack2, d.jack3)
        self.game.handle(a)

        self.assertEqual(self.p2.n_camp_actions, 3)
        self.assertItemsEqual(self.p2.camp, [d.jack1, d.jack2, d.jack3])


    def test_lead_multiple_orders_jacks_and_petitions(self):
        d = self.deck

        a = message.GameAction(message.LEADROLE, 'Laborer', 3,
                d.road0, d.bar0, d.insula0, d.jack0, d.villa0, d.villa1, d.villa2)
        self.game.handle(a)

        self.assertEqual(self.p1.n_camp_actions, 3)
        self.assertItemsEqual(self.p1.camp,
                [d.road0, d.bar0, d.insula0, d.jack0, d.villa0, d.villa1, d.villa2])

        a = message.GameAction(message.FOLLOWROLE, 3,
                d.jack1, d.jack2, d.jack3)
        self.game.handle(a)

        self.assertEqual(self.p2.n_camp_actions, 3)
        self.assertItemsEqual(self.p2.camp, [d.jack1, d.jack2, d.jack3])


    def test_lead_multiple_petitions(self):
        d = self.deck

        a = message.GameAction(message.LEADROLE, 'Craftsman', 2,
                d.road0, d.bar0, d.insula0, d.villa0, d.villa1, d.villa2)
        self.game.handle(a)

        self.assertEqual(self.p1.n_camp_actions, 2)
        self.assertItemsEqual(self.p1.camp,
                [d.road0, d.bar0, d.insula0, d.villa0, d.villa1, d.villa2])

        a = message.GameAction(message.FOLLOWROLE, 3,
                d.jack1, d.jack2, d.jack3)
        self.game.handle(a)

        self.assertEqual(self.p2.n_camp_actions, 3)
        self.assertItemsEqual(self.p2.camp, [d.jack1, d.jack2, d.jack3])


    def test_illegal_lead(self):
        d = self.deck

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.LEADROLE, 'Craftsman', 2,
                d.road0, d.bar0, d.villa0, d.villa1, d.villa2)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))

        a = message.GameAction(message.LEADROLE, 'Legionary', 3,
                d.road0, d.bar0, d.insula0, d.villa0, d.villa1, d.villa2)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


class TestPalaceCircus(unittest.TestCase):

    def setUp(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.simple_two_player()
        self.p1, self.p2 = self.game.players

        self.p1.hand.set_content([d.jack1, d.jack2, d.jack3])
        self.p2.hand.set_content([d.road0, d.road1, d.road2,
                d.road3, d.road4, d.road5, d.jack0])

        self.p1.buildings.append(Building(d.palace, 'Marble', complete=True))
        self.p2.buildings.append(Building(d.palace, 'Marble', complete=True))
        self.p2.buildings.append(Building(d.circus, 'Wood', complete=True))

        a = message.GameAction(message.THINKERORLEAD, False)
        self.game.handle(a)

        a = message.GameAction(message.LEADROLE, 'Laborer', 1, d.jack1)
                
        self.game.handle(a)


    def test_multiple_three_card_petitions(self):
        d = self.deck

        a = message.GameAction(message.FOLLOWROLE, 2,
                d.road0, d.road1, d.road2, d.road3, d.road4, d.road5)
        self.game.handle(a)

        self.assertEqual(self.p2.n_camp_actions, 2)
        self.assertItemsEqual(self.p2.camp,
                [d.road0, d.road1, d.road2, d.road3, d.road4, d.road5])


    def test_multiple_two_card_petitions(self):
        d = self.deck

        a = message.GameAction(message.FOLLOWROLE, 3,
                d.road0, d.road1, d.road2, d.road3, d.road4, d.road5)
        self.game.handle(a)

        self.assertEqual(self.p2.n_camp_actions, 3)
        self.assertItemsEqual(self.p2.camp,
                [d.road0, d.road1, d.road2, d.road3, d.road4, d.road5])


    def test_mixed_petitions(self):
        d = self.deck

        a = message.GameAction(message.FOLLOWROLE, 4,
                d.road0, d.road1, d.road2, d.road3, d.road4, d.road5)
        self.game.handle(a)

        self.assertEqual(self.p2.n_camp_actions, 4)
        self.assertItemsEqual(self.p2.camp,
                [d.road0, d.road1, d.road2, d.road3, d.road4, d.road5])


    def test_illegal_petitions(self):
        d = self.deck

        self.p2.hand.set_content([d.bath0, d.bath1, d.bath2,
                d.dock0, d.dock1, d.dock2, d.jack0])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.FOLLOWROLE, 3,
                d.bath0, d.bath1, d.bath2, d.dock0, d.dock1, d.dock2)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))

        a = message.GameAction(message.FOLLOWROLE, 2, d.bath0, d.dock0)
        with self.assertRaises(GTRError):
            self.game.handle(a)


        self.assertFalse(mon.modified(self.game))


class TestRoad(unittest.TestCase):

    def test_add_non_matching_matrials(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                buildings=[['Road'],[]],
                clientele=[['Wall', 'Wall'],[]],
                deck = d)

        p1, p2 = game.players

        p1.stockpile.set_content([d.road0, d.dock0, d.statue0])

        b = Building(d.coliseum0, 'Stone')
        p1.buildings.append(b)

        for card in [d.road0, d.dock0, d.statue0]:
            a = message.GameAction(message.ARCHITECT, d.coliseum0, card, None)
            game.handle(a)

        self.assertTrue(game._player_has_active_building(p1, 'Coliseum'))


    def test_lose_road_add_non_matching_matrials(self):
        """Even if a building has a non-matching material added
        via Road, if the Road is stolen (de-Stairwayed), they can't continue
        to add non-matching materials.
        """
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                buildings=[['Road'],[]],
                clientele=[['Wall', 'Wall'],[]],
                deck = d)

        p1, p2 = game.players

        p1.stockpile.set_content([d.road0, d.dock0, d.statue0])

        b = Building(d.coliseum0, 'Stone')
        p1.buildings.append(b)

        a = message.GameAction(message.ARCHITECT, d.coliseum0, d.road0, None)
        game.handle(a)

        p1.buildings.pop(0)

        self.assertFalse(game._player_has_active_building(p1, 'Road'))

        a = message.GameAction(message.ARCHITECT, d.coliseum0, d.dock0, None)

        mon = Monitor()
        mon.modified(game)

        with self.assertRaises(GTRError):
            game.handle(a)

        self.assertFalse(mon.modified(game))


class TestScriptorium(unittest.TestCase):

    def test_finish_marble_building_with_one_marble(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Craftsman',
                buildings=[['Scriptorium'],[]],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.statue0])
        p1.buildings.append(Building(d.basilica0, 'Marble'))

        a = message.GameAction(message.CRAFTSMAN, d.basilica0, d.statue0, None)
        game.handle(a)

        self.assertTrue(game._player_has_active_building(p1, 'Basilica'))
        self.assertEqual(len(p1.buildings[1].materials), 1)
        self.assertIn('Marble', p1.influence)


    def test_finish_stone_building_with_one_marble(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Craftsman',
                buildings=[['Scriptorium'],[]],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.statue0])
        p1.buildings.append(Building(d.villa0, 'Stone'))

        a = message.GameAction(message.CRAFTSMAN, d.villa0, d.statue0, None)
        game.handle(a)

        self.assertTrue(game._player_has_active_building(p1, 'Villa'))
        self.assertEqual(len(p1.buildings[1].materials), 1)
        self.assertIn('Stone', p1.influence)


class TestSenate(unittest.TestCase):

    def test_no_opponent_jack(self):
        d = TestDeck()

        # Player with Senate leads with Jack
        game = test_setup.two_player_lead('Laborer',
                buildings=[['Senate'],[]],
                deck = d)

        p1, p2 = game.players
        p2.hand.set_content([])
        jack_led = p1.camp.cards[0]

        self.assertTrue(game._player_has_active_building(p1, 'Senate'))

        self.assertEqual(game.expected_action, message.LABORER)
        a = message.GameAction(message.LABORER)
        game.handle(a)

        self.assertEqual(game.expected_action, message.THINKERORLEAD)


    def test_take_jack_with_senate(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Laborer',
                buildings=[[],['Senate']],
                deck = d)

        p1, p2 = game.players
        p2.hand.set_content([])
        jack_led = p1.camp.cards[0]

        self.assertTrue(game._player_has_active_building(p2, 'Senate'))
        self.assertEqual(len(p2.hand), 0)

        a = message.GameAction(message.LABORER)
        game.handle(a)

        self.assertEqual(game.expected_action, message.USESENATE)
        self.assertEqual(game.active_player, p2)

        a = message.GameAction(message.USESENATE, jack_led)
        game.handle(a)

        self.assertIn(jack_led, p2.hand)


    def test_skip_take_jack_with_senate(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Laborer',
                buildings=[[],['Senate']],
                deck = d)

        p1, p2 = game.players
        p2.hand.set_content([])
        jack_led = p1.camp.cards[0]

        self.assertTrue(game._player_has_active_building(p2, 'Senate'))
        self.assertEqual(len(p2.hand), 0)

        a = message.GameAction(message.LABORER)
        game.handle(a)

        self.assertEqual(game.expected_action, message.USESENATE)
        self.assertEqual(game.active_player, p2)

        a = message.GameAction(message.USESENATE)
        game.handle(a)

        self.assertIn(jack_led, game.jacks)
        self.assertNotIn('Jack', p2.hand)
        self.assertEqual(game.expected_action, message.THINKERORLEAD)
        self.assertEqual(game.active_player, p2)

    
    def test_three_players_one_senate(self):
        """Three players, only one has Senate. Skip taking Jack
        from the leader.
        """
        d = TestDeck()

        game = test_setup.n_player_lead(3, 'Laborer',
                buildings=[[],['Senate'], []],
                deck = d)

        p1, p2, p3 = game.players

        # n_player_lead has the others think for a Jack
        p2.hand.set_content([])
        p3.hand.set_content([])
        jack_led = p1.camp.cards[0]

        self.assertTrue(game._player_has_active_building(p2, 'Senate'))
        self.assertFalse(game._player_has_active_building(p3, 'Senate'))
        self.assertEqual(len(p2.hand), 0)
        self.assertEqual(len(p3.hand), 0)

        a = message.GameAction(message.LABORER)
        game.handle(a)

        self.assertEqual(game.expected_action, message.USESENATE)
        self.assertEqual(game.active_player, p2)

        a = message.GameAction(message.USESENATE)
        game.handle(a)

        self.assertIn(jack_led, game.jacks)
        self.assertNotIn('Jack', p2.hand)

        self.assertEqual(game.expected_action, message.THINKERORLEAD)
        self.assertEqual(game.active_player, p2)


class TestSewer(unittest.TestCase):

    def setUp(self):
        d = TestDeck()
        self.deck = d

        self.game = test_setup.simple_two_player()
        self.p1, self.p2 = self.game.players

        self.p1.buildings.append(Building(d.sewer, 'Stone', complete=True))
        self.p1.buildings.append(Building(d.palace, 'Marble', complete=True))
        self.p2.buildings.append(Building(d.palace, 'Marble', complete=True))

        self.p1.hand.set_content([d.jack0, d.villa0, d.villa1, d.villa2, d.road0])
        self.p2.hand.set_content([d.jack1])

        a = message.GameAction(message.THINKERORLEAD, False)
        self.game.handle(a)

        a = message.GameAction(message.LEADROLE, 'Laborer', 3,
                d.jack0, d.villa0, d.villa1, d.villa2, d.road0)
        self.game.handle(a)

        a = message.GameAction(message.FOLLOWROLE, 1, d.jack1)
        self.game.handle(a)

        a = message.GameAction(message.LABORER)

        for i in range(4):
            self.game.handle(a)

    
    def test_sewer_required(self):
        self.assertEqual(self.game.expected_action, message.USESEWER)
        self.assertEqual(self.game.active_player, self.p1)


    def test_use_sewer_all_cards(self):
        """Move all cards to stockpile with Sewer.
        """
        d = self.deck

        a = message.GameAction(message.USESEWER,
                d.villa0, d.villa1, d.villa2, d.road0)
        self.game.handle(a)

        self.assertItemsEqual(self.p1.stockpile,
                [d.villa0, d.villa1, d.villa2, d.road0])

        self.assertIn(d.jack0, self.game.jacks)
        self.assertIn(d.jack1, self.game.jacks)
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)
        self.assertEqual(self.game.active_player, self.p2)


    def test_use_sewer_some_cards(self):
        """Move some cards to stockpile with Sewer.
        """
        d = self.deck

        a = message.GameAction(message.USESEWER,
                d.villa1, d.road0)
        self.game.handle(a)

        self.assertItemsEqual(self.p1.stockpile,
                [d.villa1, d.road0])

        self.assertIn(d.jack0, self.game.jacks)
        self.assertIn(d.jack1, self.game.jacks)
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)
        self.assertEqual(self.game.active_player, self.p2)


    def test_use_sewer_no_cards(self):
        """Skip sewer altogether.
        """
        d = self.deck

        a = message.GameAction(message.USESEWER)
        self.game.handle(a)

        self.assertEqual(len(self.p1.stockpile), 0)

        self.assertIn(d.jack0, self.game.jacks)
        self.assertIn(d.jack1, self.game.jacks)
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)
        self.assertEqual(self.game.active_player, self.p2)


    def test_illegal_sewer_raises(self):
        d = self.deck

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.USESEWER, d.garden0)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))

        a = message.GameAction(message.USESEWER, d.jack0)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))

        a = message.GameAction(message.USESEWER, d.jack1)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))

        a = message.GameAction(message.USESEWER, d.villa0, d.garden0)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


class TestStatue(unittest.TestCase):

    def test_statue_start_on_marble(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                clientele=[['Wall'],[]],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.statue0])

        game.in_town_sites = ['Marble', 'Rubble']

        a = message.GameAction(message.ARCHITECT, d.statue0, None, 'Marble')
        game.handle(a)

        self.assertEqual(p1.buildings[0], Building(d.statue0, 'Marble'))
        self.assertNotIn('Marble', game.in_town_sites)


    def test_statue_start_on_rubble(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                clientele=[['Wall'],[]],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.statue0])

        game.in_town_sites = ['Marble', 'Rubble']

        a = message.GameAction(message.ARCHITECT, d.statue0, None, 'Rubble')
        game.handle(a)

        self.assertEqual(p1.buildings[0], Building(d.statue0, 'Rubble'))
        self.assertNotIn('Rubble', game.in_town_sites)


    def test_statue_start_out_of_town_on_rubble(self):
        """Start Statue out of town on non-Marble material with
        remaining in-town Marble sites.
        """
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                clientele=[['Wall'],[]],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.statue0])

        game.in_town_sites = ['Marble', 'Wood']

        a = message.GameAction(message.ARCHITECT, d.statue0, None, 'Rubble')
        game.handle(a)

        self.assertEqual(p1.buildings[0], Building(d.statue0, 'Rubble'))


    def test_start_and_finish_statue_with_rubble(self):
        """Start Statue on Rubble and finish it with one Rubble.
        """
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                clientele=[['Wall'],[]],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.statue0])
        p1.stockpile.set_content([d.road0])

        a = message.GameAction(message.ARCHITECT, d.statue0, None, 'Rubble')
        game.handle(a)

        a = message.GameAction(message.ARCHITECT, d.statue0, d.road0, None)
        game.handle(a)

        self.assertEqual(p1.buildings[0], Building(d.statue0, 'Rubble',
                materials=[d.road0], complete=True))

        self.assertEqual(game._player_score(p1), 6) # Statue + Rubble site


    def test_start_and_finish_rubble_statue_with_marble(self):
        """Start Statue on Rubble and finish it with one Marble.
        """
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                clientele=[['Wall'],[]],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.statue0])
        p1.stockpile.set_content([d.temple0])

        a = message.GameAction(message.ARCHITECT, d.statue0, None, 'Rubble')
        game.handle(a)

        a = message.GameAction(message.ARCHITECT, d.statue0, d.temple0, None)
        game.handle(a)

        self.assertEqual(p1.buildings[0], Building(d.statue0, 'Rubble',
                materials=[d.temple0], complete=True))


    def test_statue_score(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                buildings=[['Statue'],[]],
                deck = d)

        p1, p2 = game.players
        p1.influence.append('Marble') # two_player_lead doesn't add site

        self.assertEqual(game._player_score(p1), 8)


    def test_unfinished_statue_score(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                buildings=[[],[]],
                deck = d)

        p1, p2 = game.players

        p1.buildings.append(Building(d.statue0, 'Brick'))

        self.assertEqual(game._player_score(p1), 2)


class TestTower(unittest.TestCase):

    def test_add_rubble_to_nonrubble_buildings(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                buildings=[['Tower'],[]],
                clientele=[['Wall', 'Wall'],[]],
                deck = d)

        p1, p2 = game.players

        p1.stockpile.set_content([d.road0, d.bar0, d.insula0])

        coliseum = Building(d.coliseum0, 'Stone')
        statue = Building(d.statue0, 'Marble')
        dock = Building(d.dock0, 'Wood')
        p1.buildings.extend([coliseum, statue, dock])

        a = message.GameAction(message.ARCHITECT, d.coliseum0, d.road0, None)
        game.handle(a)

        a = message.GameAction(message.ARCHITECT, d.statue0, d.bar0, None)
        game.handle(a)

        a = message.GameAction(message.ARCHITECT, d.dock0, d.insula0, None)
        game.handle(a)

        self.assertIn(d.road0, coliseum.materials)
        self.assertIn(d.bar0, statue.materials)
        self.assertIn(d.insula0, dock.materials)

        self.assertTrue(game._player_has_active_building(p1, 'Dock'))


    def test_start_out_of_town(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                buildings=[['Tower'],[]],
                deck = d)

        p1, p2 = game.players

        p1.hand.set_content([d.road0])
        game.in_town_sites = ['Wood']

        a = message.GameAction(message.ARCHITECT, d.road0, None, 'Rubble')
        game.handle(a)

        self.assertIn('Road', p1.building_names)


    def test_finish_tower_then_start_out_of_town(self):
        """Finish the Tower with the camp action then start out of town
        with a single client.
        """
        d = TestDeck()

        game = test_setup.two_player_lead('Craftsman',
                clientele=[['Dock'],[]],
                deck = d)

        p1, p2 = game.players

        p1.buildings.append(Building(d.tower0, 'Concrete', materials=[d.aqueduct]))

        p1.hand.set_content([d.road0, d.storeroom0])
        game.in_town_sites = ['Wood']

        a = message.GameAction(message.CRAFTSMAN, d.tower0, d.storeroom0, None)
        game.handle(a)

        self.assertTrue(game._player_has_active_building(p1, 'Tower'))

        a = message.GameAction(message.CRAFTSMAN, d.road0, None, 'Rubble')
        game.handle(a)

        self.assertIn('Road', p1.building_names)


    def test_lose_tower(self):
        """If the tower is lost, even after having added a Rubble to a
        non-Rubble building, player cannot continue to add Rubble to it.
        """
        d = TestDeck()

        game = test_setup.two_player_lead('Architect',
                buildings=[['Tower'],[]],
                clientele=[['Wall', 'Wall'],[]],
                deck = d)

        p1, p2 = game.players

        p1.stockpile.set_content([d.road0, d.bar0, d.insula0])

        p1.buildings.append(Building(d.coliseum0, 'Stone'))

        a = message.GameAction(message.ARCHITECT, d.coliseum0, d.road0, None)
        game.handle(a)

        a = message.GameAction(message.ARCHITECT, d.coliseum0, d.bar0, None)
        game.handle(a)

        p1.buildings.pop(0)
        self.assertFalse(game._player_has_active_building(p1, 'Tower'))

        a = message.GameAction(message.ARCHITECT, d.coliseum0, d.insula0, None)

        mon = Monitor()
        mon.modified(game)

        with self.assertRaises(GTRError):
            game.handle(a)

        self.assertFalse(mon.modified(game))


class TestVilla(unittest.TestCase):

    def test_complete_villa_with_architect_using_one_material(self):
        d = TestDeck()

        game = test_setup.two_player_lead('Architect')

        p1, p2 = game.players

        p1.stockpile.set_content([d.garden0])
        b = Building(d.villa0, 'Stone')
        p1.buildings.append(b)

        a = message.GameAction(message.ARCHITECT, d.villa0, d.garden0, None)
        game.handle(a)

        self.assertTrue(game._player_has_active_building(p1, 'Villa'))
        self.assertEqual(len(b.materials), 1)
        self.assertIn('Stone', p1.influence)


    def test_add_to_villa_with_craftsman(self):
        """Adding to Villa with Craftsman will not finish the building.
        """
        d = TestDeck()

        game = test_setup.two_player_lead('Craftsman')

        p1, p2 = game.players

        p1.hand.set_content([d.garden0])
        p1.buildings.append(Building(d.villa0, 'Stone'))

        a = message.GameAction(message.CRAFTSMAN, d.villa0, d.garden0, None)
        game.handle(a)

        self.assertFalse(game._player_has_active_building(p1, 'Villa'))
        self.assertNotIn('Stone', p1.influence)


class TestVomitorium(unittest.TestCase):

    def setUp(self):
        self.deck = TestDeck()
        d = self.deck

        self.game = test_setup.simple_two_player()

        self.p1, self.p2 = self.game.players

        self.p1.buildings.append(Building(d.vomitorium, 'Concrete', complete=True))

        self.p1.hand.set_content([d.road0, d.jack0])
        self.p2.hand.set_content([d.road1, d.jack1])


    def test_discard_on_lead(self):
        d = self.deck

        a = message.GameAction(message.THINKERORLEAD, True)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.USEVOMITORIUM)

        a = message.GameAction(message.USEVOMITORIUM, True)
        self.game.handle(a)

        self.assertIn(d.road0, self.game.pool)
        self.assertIn(d.jack0, self.game.jacks)
        self.assertNotIn(d.road0, self.p1.hand)
        self.assertNotIn(d.jack0, self.p1.hand)

        self.assertEqual(self.game.expected_action, message.THINKERTYPE)
        self.assertEqual(self.game.active_player, self.p1)


    def test_discard_following(self):
        d = self.deck

        self.p2.buildings.append(Building(d.vomitorium, 'Concrete', complete=True))

        a = message.GameAction(message.THINKERORLEAD, False)
        self.game.handle(a)

        a = message.GameAction(message.LEADROLE, 'Laborer', 1, d.road0)
        self.game.handle(a)

        a = message.GameAction(message.FOLLOWROLE, 0)
        self.game.handle(a)

        self.assertEqual(self.game.expected_action, message.USEVOMITORIUM)
        self.assertEqual(self.game.active_player, self.p2)

        a = message.GameAction(message.USEVOMITORIUM, True)
        self.game.handle(a)

        self.assertIn(d.road1, self.game.pool)
        self.assertIn(d.jack1, self.game.jacks)
        self.assertNotIn(d.road1, self.p2.hand)
        self.assertNotIn(d.jack1, self.p2.hand)

        self.assertEqual(self.game.expected_action, message.THINKERTYPE)
        self.assertEqual(self.game.active_player, self.p2)


class TestWall(unittest.TestCase):
    """Test the extra points from the Wall. The legionary immunity
    is tested in legionary.py.
    """

    def test_wall_points(self):
        d = TestDeck()

        game = test_setup.simple_two_player()

        p1, p2 = game.players

        p1.stockpile.set_content([d.road0, d.road1, d.road2, d.statue0])

        self.assertEqual(game._player_score(p1), 2)

        p1.buildings.append(Building(d.wall, 'Concrete', complete=True))

        self.assertEqual(game._player_score(p1), 4)

        # Round down
        p1.stockpile.set_content([d.road0, d.road1, d.road2])
        self.assertEqual(game._player_score(p1), 3)




if __name__ == '__main__':
    unittest.main()






