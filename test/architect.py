#!/usr/bin/env python

from cloaca.game import Game
from cloaca.player import Player
from cloaca.building import Building
from cloaca.zone import Zone
from cloaca.card import Card
from cloaca.error import GTRError

import cloaca.card_manager as cm

import cloaca.message as message

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup

import unittest

class TestArchitect(unittest.TestCase):
    """ Test handling architect responses.
    """

    def setUp(self):
        self.game = test_setup.two_player_lead('Architect')
        self.p1, self.p2 = self.game.players


    def test_expects_architect(self):
        """ The Game should expect a ARCHITECT action.
        """
        self.assertEqual(self.game.expected_action, message.ARCHITECT)


    def test_skip_action(self):
        """ An action with (None, None, None, False) skips.
        """
        a = message.GameAction(message.ARCHITECT, None, None, None)
        self.game.handle(a)

        self.assertEqual(self.game.leader_index, 1)
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_start_in_town(self):
        """ Start an in-town building.
        """
        latrine = cm.get_card('Latrine')
        self.p1.hand.set_content([latrine])

        a = message.GameAction(message.ARCHITECT, latrine, None, 'Rubble')
        self.game.handle(a)

        self.assertNotIn(latrine, self.p1.hand)

        self.assertEqual(self.p1.buildings[0], Building(latrine, 'Rubble'))

        self.assertFalse(self.game._player_has_active_building(self.p1, 'Latrine'))

    
    def test_add_to_empty_building(self):
        """ Add a valid material to a building with no materials.
        """
        atrium = cm.get_card('Atrium')
        foundry = cm.get_card('Foundry')
        self.p1.stockpile.set_content([atrium])
        self.p1.buildings = [Building(foundry, 'Brick')]

        a = message.GameAction(message.ARCHITECT, foundry, atrium, None)
        self.game.handle(a)

        self.assertNotIn('Atrium', self.p1.stockpile)


        self.assertEqual(self.p1.buildings[0].materials,
                Building(foundry, 'Brick', materials=[atrium]).materials)
        self.assertEqual(self.p1.buildings[0],
                Building(foundry, 'Brick', materials=[atrium]))

        self.assertFalse(self.game._player_has_active_building(self.p1, 'Foundry'))


    def test_add_to_nonempty_building(self):
        """ Add a valid material to a building with one material, but this
        does not complete it.
        """
        statue = cm.get_card('Statue')
        temple = cm.get_card('Temple')
        stairway = cm.get_card('Stairway')
        self.p1.stockpile.set_content([statue])
        self.p1.buildings = [Building(temple, 'Marble', materials=[stairway])]

        a = message.GameAction(message.ARCHITECT, temple, statue, None)
        self.game.handle(a)

        self.assertNotIn(statue, self.p1.stockpile)

        self.assertEqual(self.p1.buildings[0],
                Building(temple, 'Marble', materials=[stairway, statue]))

        self.assertFalse(self.game._player_has_active_building(self.p1, 'Temple'))


    def test_complete_building(self):
        """ Complete a building.
        """
        statue, temple, fountain, stairway = cm.get_cards(
                ['Statue', 'Temple', 'Fountain', 'Stairway'])
        self.p1.stockpile.set_content([statue])
        self.p1.buildings = [Building(temple, 'Marble', materials=[fountain,stairway])]

        a = message.GameAction(message.ARCHITECT, temple, statue, None)
        self.game.handle(a)

        self.assertNotIn(statue, self.p1.stockpile)
        self.assertIn('Marble', self.p1.influence)
        self.assertTrue(self.game._player_has_active_building(self.p1, 'Temple'))

        self.assertEqual(self.p1.buildings[0],
                Building(temple, 'Marble',
                    materials=[fountain, stairway, statue],
                    complete=True))



    def test_start_with_non_existent_card(self):
        """ Start a building with a non-existent card.

        This invalid game action should leave the game state unchanged.
        """
        atrium, latrine = cm.get_cards(['Atrium', 'Latrine'])
        self.p1.hand.set_content([atrium])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.ARCHITECT, latrine, None, 'Rubble')
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

        a = message.GameAction(message.ARCHITECT, atrium, None, 'Rubble')
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_add_to_nonexistent_building(self):
        """ Add a valid material to a building that the player doesn't own.

        This invalid game action should leave the game state unchanged.
        """
        atrium, foundry = cm.get_cards(['Atrium', 'Foundry'])
        self.p1.stockpile.set_content([atrium])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.ARCHITECT, foundry, atrium, None)
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_specifying_material_and_site(self):
        """ Invalid architect action specifying both a material and a site.stockpile

        This invalid game action should leave the game state unchanged.
        """
        atrium, foundry = cm.get_cards(['Atrium', 'Foundry'])
        self.p1.stockpile.set_content([atrium])

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.ARCHITECT, foundry, atrium, 'Brick')
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


    def test_illegal_out_of_town(self):
        """ Start a building and add a material.
        """
        bridge = cm.get_card('Bridge')
        self.p1.hand.set_content([bridge])

        # Empty the in-town sites of Concrete
        self.game.in_town_sites = ['Rubble']

        mon = Monitor()
        mon.modified(self.game)

        a = message.GameAction(message.ARCHITECT, bridge, None, 'Concrete')
        with self.assertRaises(GTRError):
            self.game.handle(a)

        self.assertFalse(mon.modified(self.game))


class TestArchitectClientele(unittest.TestCase):
    """Test architect responses with clients.
    """

    def setUp(self):
        """This is run prior to every test.
        """
        self.game = test_setup.two_player_lead('Architect', (['Storeroom'], ['Storeroom']))
        self.p1, self.p2 = self.game.players


    def test_skip_client(self):
        """ Skip action and client action for p1.
        """
        a = message.GameAction(message.ARCHITECT, None, None, None)
        self.game.handle(a)

        self.assertEqual(self.game.active_player, self.p1)

        self.game.handle(a)

        self.assertEqual(self.game.leader_index, 0)
        self.assertEqual(self.game.active_player, self.p2)
        self.assertEqual(self.game.expected_action, message.ARCHITECT)


    def test_add_two_materials(self):
        """ Add materials with subsequent architect actions.
        """
        wall, storeroom = cm.get_cards(['Wall', 'Storeroom'])
        tower = cm.get_card('Tower')
        self.p1.stockpile.set_content([wall, storeroom])
        self.p1.buildings = [Building(tower, 'Concrete')]

        a = message.GameAction(message.ARCHITECT, tower, wall, None)
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[0],
                Building(tower, 'Concrete', materials=[wall]))

        a = message.GameAction(message.ARCHITECT, tower, storeroom, None)
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[0],
                Building(tower, 'Concrete', materials=[wall, storeroom], complete=True))


    def test_start_and_add(self):
        """Start a building and add a material.
        """
        wall, tower = cm.get_cards(['Wall', 'Tower'])
        self.p1.stockpile.set_content([wall])
        self.p1.hand.set_content([tower])

        a = message.GameAction(message.ARCHITECT, tower, None, 'Concrete')
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[0], Building(tower, 'Concrete'))

        a = message.GameAction(message.ARCHITECT, tower, wall, None)
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[0],
                Building(tower, 'Concrete', materials=[wall]))


    def test_start_two_buildings(self):
        """Start two buildings.
        """
        tower, bridge = cm.get_cards(['Tower', 'Bridge'])
        self.p1.hand.set_content([tower, bridge])

        a = message.GameAction(message.ARCHITECT, tower, None, 'Concrete')
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[0], Building(tower, 'Concrete'))
        self.assertEqual(self.game.expected_action, message.ARCHITECT)

        a = message.GameAction(message.ARCHITECT, bridge, None, 'Concrete')
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[1],
                Building(bridge, 'Concrete'))

        self.assertEqual(len(self.p1.hand), 0)
        self.assertNotIn('Concrete', self.game.in_town_sites)

        self.assertEqual(self.game.active_player, self.p2)


    def test_start_out_of_town(self):
        """ Start a building out of town.
        """
        bridge = cm.get_card('Bridge')
        self.p1.hand.set_content([bridge])

        # Empty the in-town sites
        self.game.in_town_sites = ['Rubble']

        self.game.oot_allowed = True

        a = message.GameAction(message.ARCHITECT, bridge, None, 'Concrete')
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[0], Building(bridge, 'Concrete'))
        self.assertEqual(3, self.game.out_of_town_sites.count('Concrete'))

        self.assertNotIn(bridge, self.p1.hand)
        self.assertEqual(self.game.expected_action, message.ARCHITECT)
        self.assertEqual(self.game.active_player, self.p2)



    def test_follower_client(self):
        """ Add materials with subsequent architect client, even after thinking.
        """
        tower, wall, storeroom = cm.get_cards(['Tower', 'Wall', 'Storeroom'])
        self.p2.stockpile.set_content([wall, storeroom])
        self.p2.buildings = [Building(tower, 'Concrete')]

        # Skip p1 architects
        a = message.GameAction(message.ARCHITECT, None, None, None)
        self.game.handle(a)
        self.game.handle(a)


        a = message.GameAction(message.ARCHITECT, tower, wall, None)
        self.game.handle(a)

        self.assertEqual(self.p2.buildings[0],
                Building(tower, 'Concrete', materials=[wall]))

        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)
        self.assertEqual(self.game.leader_index, 1)



if __name__ == '__main__':
    unittest.main()
