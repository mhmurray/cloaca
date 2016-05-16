#!/usr/bin/env python

from cloaca.gtr import Game
from cloaca.gamestate import GameState
from cloaca.player import Player
from cloaca.building import Building

import cloaca.card_manager as cm
import cloaca.message as message
from cloaca.message import GameActionError

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup

import unittest

class TestLaborer(unittest.TestCase):
    """ Test handling laborer responses.
    """

    def setUp(self):
        """ This is run prior to every test.
        """
        self.game = test_setup.two_player_lead('Laborer')
        self.p1, self.p2 = self.game.game_state.players


    def test_expects_laborer(self):
        """ The Game should expect a LABORER action.
        """
        self.assertEqual(self.game.expected_action, message.LABORER)


    def test_laborer_one_from_pool(self):
        """ Take one card from the pool with laborer action.
        """
        atrium = cm.get_card('Atrium')
        self.game.game_state.pool.set_content([atrium])

        a = message.GameAction(message.LABORER, None, atrium)
        self.game.handle(a)

        self.assertNotIn('Atrium', self.game.game_state.pool)
        self.assertIn('Atrium', self.p1.stockpile)

    
    def test_laborer_non_existent_card(self):
        """ Take a non-existent card from the pool with laborer action.

        This invalid game action should leave the game state unchanged.
        """
        self.game.game_state.pool.set_content(cm.get_cards(['Atrium']))

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.LABORER, None, cm.get_card('Dock'))
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


if __name__ == '__main__':
    unittest.main()
