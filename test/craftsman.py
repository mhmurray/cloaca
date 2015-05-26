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

class TestCraftsman(unittest.TestCase):
    """ Test handling craftsman responses.
    """

    def setUp(self):
        """ This is run prior to every test.
        """
        self.game = test_setup.two_player_lead('Craftsman')
        self.p1, self.p2 = self.game.game_state.players


    def test_expects_craftsman(self):
        """ The Game should expect a CRAFTSMAN action.
        """
        self.assertEqual(self.game.expected_action, message.CRAFTSMAN)


    def test_skip_action(self):
        """ An action with (None, None, None) skips.
        """
        a = message.GameAction(message.CRAFTSMAN, None, None, None)
        self.game.handle(a)

        self.assertEqual(self.game.game_state.leader_index, 1)
        self.assertEqual(self.game.expected_action, message.THINKERORLEAD)


    def test_start_in_town(self):
        """ Start an in-town building.
        """
        self.p1.hand = ['Latrine']

        a = message.GameAction(message.CRAFTSMAN, 'Latrine', None, 'Rubble')
        self.game.handle(a)

        self.assertNotIn('Latrine', self.p1.hand)

        self.assertTrue(self.p1.owns_building('Latrine'))
        self.assertEqual(self.p1.buildings[0], Building('Latrine', 'Rubble'))

        self.assertFalse(self.game.player_has_active_building(self.p1, 'Latrine'))

    
    def test_add_to_empty_building(self):
        """ Add a valid material to a building with no materials.
        """
        self.p1.hand = ['Atrium']
        self.p1.buildings = [Building('Foundry', 'Brick')]

        a = message.GameAction(message.CRAFTSMAN, 'Foundry', 'Atrium', None)
        self.game.handle(a)

        self.assertNotIn('Atrium', self.p1.hand)

        self.assertEqual(self.p1.buildings[0],
                Building('Foundry', 'Brick', materials=['Atrium']))

        self.assertFalse(self.game.player_has_active_building(self.p1, 'Foundry'))


    def test_add_to_nonempty_building(self):
        """ Add a valid material to a building with one material, but this
        does not complete it.
        """
        self.p1.hand = ['Statue']
        self.p1.buildings = [Building('Temple', 'Marble', materials=['Temple'])]

        a = message.GameAction(message.CRAFTSMAN, 'Temple', 'Statue', None)
        self.game.handle(a)

        self.assertNotIn('Statue', self.p1.hand)

        self.assertEqual(self.p1.buildings[0],
                Building('Temple', 'Marble', materials=['Temple', 'Statue']))

        self.assertFalse(self.game.player_has_active_building(self.p1, 'Temple'))

    
    def test_complete_building(self):
        """ Complete a building by adding a material.
        """
        self.p1.hand = ['Statue']
        self.p1.buildings = [Building('Temple', 'Marble', materials=['Temple', 'Fountain'])]

        a = message.GameAction(message.CRAFTSMAN, 'Temple', 'Statue', None)
        self.game.handle(a)

        self.assertNotIn('Statue', self.p1.hand)
        self.assertIn('Marble', self.p1.influence)
        self.assertTrue(self.game.player_has_active_building(self.p1, 'Temple'))
    
        # The completed building keeps its site. A copy is added to influence.
        self.assertEqual(self.p1.buildings[0],
                Building('Temple', 'Marble',
                    materials=['Temple', 'Fountain', 'Statue'],
                    completed=True))

    
    def test_non_existent_card(self):
        """ Use a non-existent card.

        This invalid game action should leave the game state unchanged.
        """
        self.p1.hand = ['Atrium']

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.CRAFTSMAN, 'Latrine', None, 'Rubble')
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))

    
    def test_wrong_site(self):
        """ Use the wrong site to start a building.

        This invalid game action should leave the game state unchanged.
        """
        self.p1.hand = ['Atrium']

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.CRAFTSMAN, 'Atrium', None, 'Rubble')
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


    def test_add_to_nonexistent_building(self):
        """ Add a valid material to a building that the player doesn't own.

        This invalid game action should leave the game state unchanged.
        """
        self.p1.hand = ['Atrium']

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.CRAFTSMAN, 'Foundry', 'Atrium', None)
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


    def test_specifying_material_and_site(self):
        """ Invalid craftsman action specifying both a material and a site.

        This invalid game action should leave the game state unchanged.
        """
        self.p1.hand = ['Atrium']

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.CRAFTSMAN, 'Foundry', 'Atrium', 'Brick')
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


if __name__ == '__main__':
    unittest.main()
