#!/usr/bin/env python

from cloaca.gtr import Game
from cloaca.gamestate import GameState
from cloaca.player import Player
from cloaca.building import Building

import cloaca.card_manager as cm

import cloaca.message as message
from cloaca.message import BadGameActionError

from cloaca.test.monitor import Monitor
import cloaca.test.test_setup as test_setup

import unittest

class TestPatron(unittest.TestCase):
    """ Test handling patron responses.
    """

    def setUp(self):
        """ This is run prior to every test.
        """
        self.game = test_setup.two_player_lead('Patron')
        self.p1, self.p2 = self.game.game_state.players


    def test_expects_patron(self):
        """ The Game should expect a PATRONFROMPOOL action.
        """
        self.assertEqual(self.game.expected_action(), message.PATRONFROMPOOL)


    def test_patron_one_from_pool(self):
        """ Take one card from the pool with patron action.
        """
        self.game.game_state.pool.set_content(cm.get_cards(['Atrium']))

        a = message.GameAction(message.PATRONFROMPOOL, 'Atrium')
        self.game.handle(a)

        self.assertNotIn('Atrium', self.game.game_state.pool)
        self.assertIn('Atrium', self.p1.clientele)

    
    def test_patron_non_existent_card(self):
        """ Take a non-existent card from the pool with patron action.

        This invalid game action should leave the game state unchanged.
        """
        self.game.game_state.pool.set_content(cm.get_cards(['Atrium']))

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.PATRONFROMPOOL, 'Dock')
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


    def test_patron_at_clientele_limit(self):
        """ Patron a card when the vault limit has been reached.

        This invalid game action should leave the game state unchanged.
        """
        self.game.game_state.pool.set_content(cm.get_cards(['Atrium']))
        self.p1.clientele.set_content(cm.get_cards(['Insula', 'Dock']))

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.PATRONFROMPOOL, 'Atrium')
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


    def test_patron_past_higher_clientele_limit(self):
        """ Patron a card above a higher vault limit.

        This invalid game action should leave the game state unchanged.
        """
        self.game.game_state.pool.set_content(cm.get_cards(['Atrium']))
        self.p1.clientele.set_content(cm.get_cards(['Insula', 'Dock', 'Palisade']))
        self.p1.influence.append('Wood')

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.PATRONFROMPOOL, 'Atrium')
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


    def test_patron_with_higher_clientele_limit(self):
        """ Patron a card after a higher vault limit has been achieved.

        This invalid game action should leave the game state unchanged.
        """
        self.game.game_state.pool.set_content(cm.get_cards(['Atrium']))
        self.p1.clientele.set_content(cm.get_cards(['Insula', 'Dock']))
        self.p1.influence.append('Wood')

        a = message.GameAction(message.PATRONFROMPOOL, 'Atrium')
        self.game.handle(a)

        self.assertNotIn('Atrium', self.game.game_state.pool)
        self.assertIn('Atrium', self.p1.clientele)




if __name__ == '__main__':
    unittest.main()
