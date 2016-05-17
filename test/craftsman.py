#!/usr/bin/env python

from cloaca.game import Game
from cloaca.player import Player
from cloaca.building import Building
from cloaca.error import GTRError

import cloaca.card_manager as cm

import cloaca.message as message

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup

import unittest

class TestCraftsman(unittest.TestCase):
    """ Test handling craftsman responses.
    """

    def setUp(self):
        """ This is run prior to every test.
        """
        self.game = test_setup.two_player_lead('Craftsman')
        self.p1, self.p2 = self.game.players


    def test_expects_craftsman(self):
        """ The Game should expect a CRAFTSMAN action.
        """
        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)


    def test_skip_action(self):
        """ An action with (None, None, None) skips.
        """
        a = message.GameAction(message.CRAFTSMAN, None, None, None)
        self.game.handle(a)

        self.assertEqual(self.game.leader_index, 1)
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_start_in_town(self):
        """ Start an in-town building.
        """
        latrine = cm.get_card('Latrine')
        self.p1.hand.set_content([latrine])

        a = message.GameAction(message.CRAFTSMAN, latrine, None, 'Rubble')
        self.game.handle(a)

        self.assertNotIn(latrine, self.p1.hand)

        self.assertEqual(self.p1.buildings[0], Building(latrine, 'Rubble'))

        self.assertFalse(self.game._player_has_active_building(self.p1, 'Latrine'))

    
    def test_add_to_empty_building(self):
        """ Add a valid material to a building with no materials.
        """
        atrium, foundry = cm.get_cards(['Atrium', 'Foundry'])
        self.p1.hand.set_content([atrium])

        self.p1.buildings = [Building(foundry, 'Brick')]

        a = message.GameAction(message.CRAFTSMAN, foundry, atrium, None)
        self.game.handle(a)

        self.assertNotIn(atrium, self.p1.hand)

        self.assertEqual(self.p1.buildings[0],
                Building(foundry, 'Brick', materials=[atrium]))

        self.assertFalse(self.game._player_has_active_building(self.p1, 'Foundry'))


    def test_add_to_nonempty_building(self):
        """ Add a valid material to a building with one material, but this
        does not complete it.
        """
        statue, temple, fountain, stairway = cm.get_cards(
                ['Statue', 'Temple', 'Fountain', 'Stairway'])
        self.p1.hand.set_content([statue])

        self.p1.buildings = [Building(temple, 'Marble', materials=[fountain])]

        a = message.GameAction(message.CRAFTSMAN, temple, statue, None)
        self.game.handle(a)

        self.assertNotIn(statue, self.p1.hand)

        self.assertEqual(self.p1.buildings[0],
                Building(temple, 'Marble', materials=[fountain, statue]))

        self.assertFalse(self.game._player_has_active_building(self.p1, 'Temple'))

    
    def test_complete_building(self):
        """ Complete a building by adding a material.
        """
        statue, temple, fountain, stairway = cm.get_cards(
                ['Statue', 'Temple', 'Fountain', 'Stairway'])
        self.p1.hand.set_content([statue])

        self.p1.buildings = [Building(temple, 'Marble', materials=[fountain, stairway])]

        a = message.GameAction(message.CRAFTSMAN, temple, statue, None)
        self.game.handle(a)

        self.assertNotIn(statue, self.p1.hand)
        self.assertIn('Marble', self.p1.influence)
        self.assertTrue(self.game._player_has_active_building(self.p1, 'Temple'))
    
        # The completed building keeps its site. A copy is added to influence.
        self.assertEqual(self.p1.buildings[0],
                Building(temple, 'Marble',
                    materials=[fountain, stairway, statue],
                    complete=True))

    
    def test_non_existent_card(self):
        """ Use a non-existent card.

        This invalid game action should leave the game state unchanged.
        """
        atrium, latrine = cm.get_cards(['Atrium', 'Latrine'])
        self.p1.hand.set_content([atrium])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.CRAFTSMAN, latrine, None, 'Rubble')
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))

    
    def test_wrong_site(self):
        """ Use the wrong site to start a building.

        This invalid game action should leave the game state unchanged.
        """
        atrium = cm.get_card('Atrium')
        self.p1.hand.set_content([atrium])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.CRAFTSMAN, atrium, None, 'Rubble')
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_illegal_out_of_town(self):
        """Try to start a building out of town without two actions.

        This invalid game action should leave the game state unchanged.
        """
        atrium = cm.get_card('Atrium')
        self.p1.hand.set_content([atrium])

        self.game.in_town_sites = ['Rubble']

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.CRAFTSMAN, atrium, None, 'Brick')
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_add_to_nonexistent_building(self):
        """ Add a valid material to a building that the player doesn't own.

        This invalid game action should leave the game state unchanged.
        """
        atrium, foundry = cm.get_cards(['Atrium', 'Foundry'])
        self.p1.hand.set_content([atrium])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.CRAFTSMAN, foundry, atrium, None)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_specifying_material_and_site(self):
        """ Invalid craftsman action specifying both a material and a site.

        This invalid game action should leave the game state unchanged.
        """
        atrium, foundry = cm.get_cards(['Atrium', 'Foundry'])
        self.p1.hand.set_content([atrium])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.CRAFTSMAN, foundry, atrium, 'Brick')
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


class TestFountain(unittest.TestCase):
    """Test Craftsman with an active Fountain building.
    """

    def setUp(self):
        """Run prior to every test.
        """
        clientele = []
        buildings = (['Fountain'],[])
        self.game = test_setup.two_player_lead('Craftsman', clientele, buildings)
        self.p1, self.p2 = self.game.players

    def test_fountain_skip(self):
        """Test using a fountain to look at the top card and then skip the action,
        drawing the card.
        """
        bath = cm.get_card('Bath')
        self.game.library.cards.insert(0,bath)

        a = message.GameAction(message.USEFOUNTAIN, True)
        self.game.handle(a)

        self.assertEqual(self.p1.fountain_card, bath)
        self.assertEqual(self.game.expected_action, message.FOUNTAIN)

        a = message.GameAction(message.FOUNTAIN, True, None, None, None)
        self.game.handle(a)

        self.assertIn(bath, self.p1.hand)
        self.assertIsNone(self.p1.fountain_card)
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)

    def test_fountain_start(self):
        """Test using a fountain to look at the top card and then start a
        building with it.
        """
        bath = cm.get_card('Bath')
        self.game.library.cards.insert(0,bath)

        a = message.GameAction(message.USEFOUNTAIN, True)
        self.game.handle(a)

        self.assertEqual(self.p1.fountain_card, bath)
        self.assertEqual(self.game.expected_action, message.FOUNTAIN)

        a = message.GameAction(message.FOUNTAIN, False, bath, None, 'Brick')
        self.game.handle(a)

        self.assertNotIn(bath, self.p1.hand)
        self.assertIsNone(self.p1.fountain_card)

        self.assertIn('Bath', self.p1.building_names)
        self.assertFalse(self.game._player_has_active_building(self.p1, 'Bath'))

        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_fountain_add(self):
        """Test using a fountain to look at the top card and then add it as
        a material to a building, completing it.
        """
        bath, atrium, foundry = cm.get_cards(['Bath', 'Atrium', 'Foundry'])
        self.game.library.cards.insert(0,bath)

        self.p1.buildings.append(Building(atrium, 'Brick', materials=[foundry]))

        a = message.GameAction(message.USEFOUNTAIN, True)
        self.game.handle(a)

        self.assertEqual(self.p1.fountain_card, bath)
        self.assertEqual(self.game.expected_action, message.FOUNTAIN)

        a = message.GameAction(message.FOUNTAIN, False, atrium, bath, None)
        self.game.handle(a)

        self.assertNotIn(bath, self.p1.hand)
        self.assertIsNone(self.p1.fountain_card)

        self.assertTrue(self.game._player_has_active_building(self.p1, 'Atrium'))

        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


if __name__ == '__main__':
    unittest.main()
