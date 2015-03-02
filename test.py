#!/usr/bin/env python

import gtr
from gtr import Game
from gamestate import GameState
from player import Player
import pprint
import logging
import unittest
from building import Building
import sys


""" Testing framework for GtR. To test the interactive parts, we need to 
commandeer the dialog methods. This is done by replacing
the gtr.Game.card_choices() dialog. The individual __Dialog() methods
implement a lot of logic around the actions that we want to test,
so we can't just replace those.
"""

unittest.longMessage = True

old_method = None

class TestArchitect(unittest.TestCase):
    """ Test architect actions """

    def setUp(self):
        """ This is run prior to each test """
        # Set up game state with Player M performing all the tests

        gs = GameState(players=['M','L'], pool=['Insula', 'Atrium'])
        self.p1 = Player('M', hand=['Jack', 'Latrine'],
                         stockpile=['Road', 'Foundry', 'Scriptorium'],
                         buildings=[Building('Villa', 'Stone'),
                                    Building('Atrium','Brick'),
                                    Building('Road','Rubble')])
        gs.players[0] = self.p1
        self.p2 = Player('L', buildings=[Building('Shrine', 'Brick',['Atrium','Atrium'],completed=True)])
        gs.players[1] = self.p2

        self.game = Game(gs)
        self.game.init_foundations(2) # for 2 players

    class ChoicesDialogReplacement():
        """ This class can be used to replace Game.choices_dialog().
        See the replace_choices_dialog() method for details.
        """
        def __init__(self, choices):
            self.choices = list(choices)
            self.n = len(choices)
            self.count = 0

        def __call__(self, choices_list, prompt='', selectable=None):
            if self.count == self.n:
                print 'You need to provide more choices!'
                print self.choices
                raise Exception
            else:
                i = self.count
                self.count += 1
                return self.choices[i]

    def replace_choices_dialog(self, choices):
        """ Makes a replacement method for Game.choices_dialog() that will
        automatically return the choices in order. This replaces all user
        interaction.

            choices = [2,0,1,2]
            Game.choices_dialog = self.make_choices(choices)

            game.choices_dialog(game, ['choice1', 'choice2', 'choice3'])
        
        This doesn't prompt the user, but returns 2, since that's the first
        item in the choices list.
        """
        # save old choices dialog method
        global old_method
        if old_method is None:
            old_method = Game.choices_dialog

        Game.choices_dialog = self.ChoicesDialogReplacement(choices)

    def test_start_building(self):
        """ Start a building from hand on an in-town site.

        ArchitectDialog will ask for
          - Skip, start, or building to add to, respond 1 for start
          - Building choice, respond 1 for Latrine. 
        """
        self.replace_choices_dialog([1,1])

        self.assertFalse('Latrine' in self.p1.get_incomplete_building_names())
        
        self.game.perform_architect_action(self.p1, False)

        self.assertTrue('Latrine' in self.p1.get_incomplete_building_names())

        b = self.p1.get_building('Latrine')

        self.assertEqual(b, Building('Latrine', 'Rubble'))
        self.assertNotEqual(b, Building('Latrine', 'Brick'))
        self.assertNotEqual(b, Building('Road', 'Rubble'))

    def test_add_material(self):
        """ Add material without completing building.

        Sorted list of M's buildings: Atrium, Road, Villa
        Sorted list of M's stockpile: Foundry, Road, Scriptorium

        ArchitectDialog will ask for
          - Skip, start, or building to add to, respond 2 for add to Atrium.
          - Choose a material, respond 0 for Foundry.
        """
        self.replace_choices_dialog([2,0])

        self.assertTrue('Atrium' in self.p1.get_incomplete_building_names())

        self.game.perform_architect_action(self.p1, False)

        self.assertTrue('Atrium' in self.p1.get_incomplete_building_names())

        b = self.p1.get_building('Atrium')

        self.assertEqual(b, Building('Atrium', 'Brick', ['Foundry']))

    def test_add_material_and_complete(self):
        """ Add material, completing building

        Sorted list of M's buildings: Atrium, Road, Villa
        Sorted list of M's stockpile: Foundry, Road, Scriptorium

        ArchitectDialog will ask for
          - Skip, start, or building to add to, respond 3 for add to Road.
          - Choose a material, respond 1 for Road.
        """
        self.replace_choices_dialog([3,1])

        self.assertTrue('Road' in self.p1.get_incomplete_building_names())
        
        self.game.perform_architect_action(self.p1, False)

        self.assertFalse('Road' in self.p1.get_incomplete_building_names())
        self.assertTrue('Road' in self.p1.get_completed_building_names())

        b = self.p1.get_building('Road')

        self.assertEqual(b, Building('Road', 'Rubble', ['Road'], completed=True))


    def test_archway_add_material(self):
        """ A material can be added to a building from the pool.

        Sorted list of M's buildings: Atrium, Road, Villa
        Sorted list of M's stockpile: Foundry, Road, Scriptorium
        Sorted list of pool: Atrium, Insula

        ArchitectDialog will ask for
          - Skip, start, or building to add to, respond 2 for add to Atrium.
          - Choose a material, respond 3 for Atrium. (Stockpile listed first)
        """
        self.replace_choices_dialog([2,3])
        self.p1.buildings.append(Building('Archway','Brick',['Shrine','Shrine'], completed=True))

        self.assertTrue('Archway' in self.game.get_active_building_names(self.p1))

        self.game.perform_architect_action(self.p1, False)

        self.assertTrue('Atrium' in self.p1.get_incomplete_building_names())

        b = self.p1.get_building('Atrium')

        self.assertEqual(b, Building('Atrium', 'Brick', ['Atrium']))

    def test_villa_completed(self):
        """ The Villa is completed with only one material

        Sorted list of M's buildings: Atrium, Road, Villa
        Sorted list of M's stockpile: Foundry, Road, Scriptorium

        ArchitectDialog will ask for
          - Skip, start, or building to add to, respond 4 for add to Villa.
          - Choose a material, respond 2 for Scriptorium.
        """
        self.replace_choices_dialog([4,2])

        self.assertTrue('Villa' in self.p1.get_incomplete_building_names())

        self.game.perform_architect_action(self.p1, False)

        self.assertFalse('Villa' in self.p1.get_incomplete_building_names())
        self.assertTrue('Villa' in self.p1.get_completed_building_names())

        b = self.p1.get_building('Villa')

        self.assertEqual(b, Building('Villa', 'Stone', ['Scriptorium'], completed=True))

    def test_stairway(self):
        """ Stairwaying an opponent's building.

        Sorted list of M's buildings: Atrium, Road, Stairway, Villa
        Sorted list of M's stockpile: Foundry, Road, Scriptorium
        Sorted list of L's buildings: Shrine

        ArchitectDialog will ask for
          - Skip, start, or building to add to, respond 1 for skip.
        StairwayDialog will ask for
          - Skip or building to add to, respond 2 for add to Shrine.
          - Choose a material, respond 1 for Foundry.
        """

        # Add logging back in
        if False:
          lg = logging.getLogger('gtr')
          lg.setLevel(logging.DEBUG)
          handler = logging.StreamHandler(sys.stdout)
          handler.setLevel(logging.DEBUG)
          formatter = logging.Formatter('%(message)s')
          handler.setFormatter(formatter)
          lg.addHandler(handler)
          lg.propagate = False

        # Replace the dialog with a manual one. It will have the choices
        # dialog replacement from the last test, remember.
        if False:
          global old_method
          Game.choices_dialog = old_method

        self.replace_choices_dialog([0,1,0])
        stairway_building = Building('Stairway','Marble',completed=True)
        self.p1.buildings.append(stairway_building)

        self.assertTrue('Stairway' in self.game.get_active_building_names(self.p1))
        self.assertFalse(self.game.player_has_active_building(self.p1, 'Shrine'))
        self.assertTrue(self.game.player_has_active_building(self.p2, 'Shrine'))
        self.assertEqual(self.game.get_max_hand_size(self.p1), 5)
        self.assertEqual(self.game.get_max_hand_size(self.p2), 7)
        
        self.game.perform_architect_action(self.p1, False)

        self.assertTrue(self.game.player_has_active_building(self.p1, 'Shrine'))
        self.assertTrue(self.game.player_has_active_building(self.p2, 'Shrine'))
        self.assertEqual(self.game.get_max_hand_size(self.p1), 7)
        self.assertEqual(self.game.get_max_hand_size(self.p2), 7)

        # Remove the stairway so remaining tests don't have to use it.
        self.p1.buildings.remove(stairway_building)

if __name__ == '__main__':
    unittest.main()
