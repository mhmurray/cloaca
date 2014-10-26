#!/usr/bin/env python

from gtr import Game
from gamestate import GameState
from player import Player
import pprint
import logging
import unittest
from building import Building


""" Testing framework for GtR. To test the ineractive parts, we need to 
commandeer the dialog methods somehow. This is done by replacing
the gtr.Game.card_choices() dialog. The individual __Dialog() methods
implement a lot of logic around the actions that we want to test,
so we can't just replace those.
"""

class TestArchitect(unittest.TestCase):
    """ Test architect actions """

    def setUp(self):
        """ This is run prior to each test """
        # Set up game state with Player M performing all the tests
        self.p1 = Player('M', hand=['Jack', 'Latrine'],
                         stockpile=['Road', 'Foundry', 'Scriptorium'],
                         buildings=[Building('Villa', 'Stone'),
                                    Building('Atrium','Brick'),
                                    Building('Road','Rubble')])
        self.p2 = Player('L', buildings=[Building('Shrine', 'Brick')])

        gs = GameState(players=[self.p1,self.p2], pool=['Insula', 'Atrium'])

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

        def __call__(self, choices_list, prompt=''):
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
        Game.choices_dialog = self.ChoicesDialogReplacement(choices)

    def test_start_building(self):
        """ Start a building from hand on an in-town site.

        ArchitectDialog will ask for
          - Start or building to add to, respond
          - Building choice, respond 1 for Latrine. 
        """
        self.replace_choices_dialog([0,1])
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
          - Start or building to add to, respond 1 for add to Atrium.
          - Choose a material, respond 0 for Foundry.
        """
        self.replace_choices_dialog([1,0])
        self.game.perform_architect_action(self.p1, False)

        self.assertTrue('Atrium' in self.p1.get_incomplete_building_names())

        b = self.p1.get_building('Atrium')

        self.assertEqual(b, Building('Atrium', 'Brick', ['Foundry']), msg='b = '+repr(b))

    def test_add_material_and_complete(self):
        """ Add material, completing building

        Sorted list of M's buildings: Atrium, Road, Villa
        Sorted list of M's stockpile: Foundry, Road, Scriptorium

        ArchitectDialog will ask for
          - Start or building to add to, respond 2 for add to Road.
          - Choose a material, respond 1 for Road.
        """
        self.replace_choices_dialog([2,1])
        self.game.perform_architect_action(self.p1, False)

        self.assertTrue('Road' in self.p1.get_incomplete_building_names())

        b = self.p1.get_building('Road')

        self.assertEqual(b, Building('Road', 'Rubble', ['Road'], completed=True), msg='b = '+repr(b))

    def test_stairway(self):
        """ Stairwaying an opponent's building. """

    def test_archway_choices_list(self):
        """ The correct cards are presented if the player has an Archway """

    def test_archway_add_material(self):
        """ A material can be added to a building from the pool """

    def test_villa_completed(self):
        """ The Villa is completed with only one material """


if __name__ == '__main__':
    unittest.main()
