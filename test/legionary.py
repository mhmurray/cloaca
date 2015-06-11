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

class TestLegionary(unittest.TestCase):
    """ Test handling legionary responses.
    """

    def setUp(self):
        """ This is run prior to every test.
        """
        self.game = test_setup.two_player_lead('Legionary')
        self.p1, self.p2 = self.game.game_state.players


    def test_expects_legionary(self):
        """ The Game should expect a LEGIONARY action.
        """
        self.assertEqual(self.game.expected_action(), message.LEGIONARY)


    def test_legionary(self):
        """ Take one card from the pool with legionary action.
        """
        self.p1.hand = ['Atrium']
        self.game.game_state.pool = ['Foundry']

        a = message.GameAction(message.LEGIONARY, 'Atrium')
        self.game.handle(a)

        self.assertNotIn('Foundry', self.game.game_state.pool)
        self.assertIn('Foundry', self.p1.stockpile)

        self.assertIn('Atrium', self.p1.revealed) 

        self.assertEqual(self.game.expected_action(), message.GIVECARDS)


    def test_give_cards(self):
        """ Take one card from opponent.
        """
        self.p1.hand = ['Atrium']
        self.p2.hand = ['Foundry']

        a = message.GameAction(message.LEGIONARY, 'Atrium')
        self.game.handle(a)

        a = message.GameAction(message.GIVECARDS, 'Foundry')
        self.game.handle(a)

        self.assertIn('Foundry', self.p1.stockpile)
        self.assertNotIn('Foundry', self.p2.hand)

        # It should be p2's turn now
        self.assertEqual(self.game.expected_action(), message.THINKERORLEAD)



    
if __name__ == '__main__':
    unittest.main()
