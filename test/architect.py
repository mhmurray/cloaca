#!/usr/bin/env python

from cloaca.gtr import Game
from cloaca.gamestate import GameState
from cloaca.player import Player
from cloaca.building import Building

import cloaca.message as message
from cloaca.message import BadGameActionError

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup

import unittest
import logging
import sys

if 0:
    lg = logging.getLogger('gtr')
    formatter = logging.Formatter('%(message)s')
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    lg.addHandler(ch)
    lg.setLevel(logging.DEBUG)
    lg.propagate = False

class TestArchitect(unittest.TestCase):
    """ Test handling architect responses.
    """

    def setUp(self):
        """ This is run prior to every test.
        """
        self.game = test_setup.two_player_lead('Architect')
        self.p1, self.p2 = self.game.game_state.players


    def test_expects_architect(self):
        """ The Game should expect a ARCHITECT action.
        """
        self.assertEqual(self.game.expected_action(), message.ARCHITECT)


    def test_skip_action(self):
        """ An action with (None, None, None, False) skips.
        """
        a = message.GameAction(message.ARCHITECT, None, None, None, False)
        self.game.handle(a)

        self.assertEqual(self.game.game_state.leader_index, 1)
        self.assertEqual(self.game.expected_action(), message.THINKERORLEAD)


    def test_start_in_town(self):
        """ Start an in-town building.
        """
        self.p1.hand = ['Latrine']

        a = message.GameAction(message.ARCHITECT, 'Latrine', None, 'Rubble', False)
        self.game.handle(a)

        self.assertNotIn('Latrine', self.p1.hand)

        self.assertTrue(self.p1.owns_building('Latrine'))
        self.assertEqual(self.p1.buildings[0], Building('Latrine', 'Rubble'))

        self.assertFalse(self.game.player_has_active_building(self.p1, 'Latrine'))

    
    def test_add_to_empty_building(self):
        """ Add a valid material to a building with no materials.
        """
        self.p1.stockpile = ['Atrium']
        self.p1.buildings = [Building('Foundry', 'Brick')]

        a = message.GameAction(message.ARCHITECT, 'Foundry', 'Atrium', None, False)
        self.game.handle(a)

        self.assertNotIn('Atrium', self.p1.stockpile)

        self.assertEqual(self.p1.buildings[0],
                Building('Foundry', 'Brick', materials=['Atrium']))

        self.assertFalse(self.game.player_has_active_building(self.p1, 'Foundry'))


    def test_add_to_nonempty_building(self):
        """ Add a valid material to a building with one material, but this
        does not complete it.
        """
        self.p1.stockpile = ['Statue']
        self.p1.buildings = [Building('Temple', 'Marble', materials=['Temple'])]

        a = message.GameAction(message.ARCHITECT, 'Temple', 'Statue', None, False)
        self.game.handle(a)

        self.assertNotIn('Statue', self.p1.stockpile)

        self.assertEqual(self.p1.buildings[0],
                Building('Temple', 'Marble', materials=['Temple', 'Statue']))

        self.assertFalse(self.game.player_has_active_building(self.p1, 'Temple'))


    def test_complete_building(self):
        """ Complete a building.
        """
        self.p1.stockpile = ['Statue']
        self.p1.buildings = [Building('Temple', 'Marble', materials=['Temple', 'Fountain'])]

        a = message.GameAction(message.ARCHITECT, 'Temple', 'Statue', None, False)
        self.game.handle(a)

        self.assertNotIn('Statue', self.p1.stockpile)
        self.assertIn('Marble', self.p1.influence)
        self.assertTrue(self.game.player_has_active_building(self.p1, 'Temple'))

        self.assertEqual(self.p1.buildings[0],
                Building('Temple', 'Marble',
                    materials=['Temple', 'Fountain', 'Statue'],
                    completed=True))



    def test_start_with_non_existent_card(self):
        """ Start a building with a non-existent card.

        This invalid game action should leave the game state unchanged.
        """
        self.p1.hand = ['Atrium']

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.ARCHITECT, 'Latrine', None, 'Rubble', False)
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))

    
    def test_wrong_site(self):
        """ Use the wrong site to start a building.

        This invalid game action should leave the game state unchanged.
        """
        self.p1.hand = ['Atrium']

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.ARCHITECT, 'Atrium', None, 'Rubble', False)
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


    def test_add_to_nonexistent_building(self):
        """ Add a valid material to a building that the player doesn't own.

        This invalid game action should leave the game state unchanged.
        """
        self.p1.stockpile = ['Atrium']

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.ARCHITECT, 'Foundry', 'Atrium', None, False)
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


    def test_specifying_material_and_site(self):
        """ Invalid architect action specifying both a material and a site.stockpile

        This invalid game action should leave the game state unchanged.
        """
        self.p1.stockpile = ['Atrium']

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.ARCHITECT, 'Foundry', 'Atrium', 'Brick', False)
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


    def test_illegal_out_of_town(self):
        """ Start a building and add a material.
        """
        self.p1.hand = ['Bridge']

        # Empty the in-town sites of Concrete
        self.game.game_state.in_town_foundations = ['Rubble']

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.ARCHITECT, 'Bridge', None, 'Concrete', False)
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


class TestArchitectClient(unittest.TestCase):
    """ Test architect responses with clients.
    """

    def setUp(self):
        """ This is run prior to every test.
        """
        self.game = test_setup.two_player_lead('Architect', ['Wall'], ['Wall'])
        self.p1, self.p2 = self.game.game_state.players


    def test_skip_client(self):
        """ Skip action and client action for p1.
        """
        a = message.GameAction(message.ARCHITECT, None, None, None, False)
        self.game.handle(a)

        self.assertEqual(self.game.game_state.active_player, self.p1)

        self.game.handle(a)

        self.assertEqual(self.game.game_state.leader_index, 0)
        self.assertEqual(self.game.game_state.active_player, self.p2)
        self.assertEqual(self.game.expected_action(), message.ARCHITECT)


    def test_add_two_materials(self):
        """ Add materials with subsequent architect actions.
        """
        self.p1.stockpile = ['Wall', 'Wall']
        self.p1.buildings = [Building('Tower', 'Concrete')]

        a = message.GameAction(message.ARCHITECT, 'Tower', 'Wall', None, False)
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[0],
                Building('Tower', 'Concrete', materials=['Wall']))

        self.game.handle(a)

        self.assertEqual(self.p1.buildings[0],
                Building('Tower', 'Concrete', materials=['Wall', 'Wall'], completed=True))


    def test_start_and_add(self):
        """ Start a building and add a material.
        """
        self.p1.stockpile = ['Wall']
        self.p1.hand = ['Tower']

        a = message.GameAction(message.ARCHITECT, 'Tower', None, 'Concrete', False)
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[0], Building('Tower', 'Concrete'))

        a = message.GameAction(message.ARCHITECT, 'Tower', 'Wall', None, False)
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[0],
                Building('Tower', 'Concrete', materials=['Wall']))


    def test_start_two_buildings(self):
        """ Start a building and add a material.
        """
        self.p1.hand = ['Tower', 'Bridge']

        a = message.GameAction(message.ARCHITECT, 'Tower', None, 'Concrete', False)
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[0], Building('Tower', 'Concrete'))

        a = message.GameAction(message.ARCHITECT, 'Bridge', None, 'Concrete', False)
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[1],
                Building('Bridge', 'Concrete'))

        self.assertEqual(self.p1.hand, [])
        self.assertNotIn('Concrete', self.game.game_state.in_town_foundations)

        self.assertEqual(self.game.game_state.active_player, self.p2)


    def test_start_out_of_town(self):
        """ Start a building and add a material.
        """
        self.p1.hand = ['Bridge']

        # Empty the in-town sites
        self.game.game_state.in_town_foundations = ['Rubble']

        a = message.GameAction(message.ARCHITECT, 'Bridge', None, 'Concrete', False)
        self.game.handle(a)

        self.assertEqual(self.p1.buildings[0], Building('Bridge', 'Concrete'))
        self.assertEqual(3, self.game.game_state.out_of_town_foundations.count('Concrete'))

        self.assertNotIn('Bridge', self.p1.hand)
        self.assertEqual(self.game.expected_action(), message.ARCHITECT)
        self.assertEqual(self.game.game_state.active_player, self.p2)



    def test_follower_client(self):
        """ Add materials with subsequent architect client, even after thinking.
        """
        self.p2.stockpile = ['Wall', 'Wall']
        self.p2.buildings = [Building('Tower', 'Concrete')]

        # Skip p1 architects
        a = message.GameAction(message.ARCHITECT, None, None, None, False)
        self.game.handle(a)
        self.game.handle(a)


        a = message.GameAction(message.ARCHITECT, 'Tower', 'Wall', None, False)
        self.game.handle(a)

        self.assertEqual(self.p2.buildings[0],
                Building('Tower', 'Concrete', materials=['Wall']))

        self.assertEqual(self.game.expected_action(), message.THINKERORLEAD)
        self.assertEqual(self.game.game_state.leader_index, 1)



if __name__ == '__main__':
    unittest.main()
