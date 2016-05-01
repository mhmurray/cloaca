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

class TestMultiLegionary(unittest.TestCase):
    """Test handling legionary responses with multiple legionary
    actions.
    """

    def setUp(self):
        """This is run prior to every test.
        """
        clientele = [['Atrium'], []]
        self.game = test_setup.two_player_lead('Legionary', clientele)
        self.p1, self.p2 = self.game.game_state.players


    def test_opponent_has_some_match(self):
        """Demand cards that opponent has only some of.
        """
        atrium, shrine, foundry = cm.get_cards(['Atrium', 'Shrine', 'Foundry'])
        self.p1.hand.set_content([atrium, shrine])
        self.p2.hand.set_content([foundry])

        a = message.GameAction(message.LEGIONARY, atrium, shrine)
        self.game.handle(a)

        a = message.GameAction(message.GIVECARDS, foundry)
        self.game.handle(a)

        self.assertNotIn('Foundry', self.p2.hand)
        self.assertIn('Foundry', self.p1.stockpile)
        self.assertEqual(len(self.p2.hand), 0)

        # It should be p2's turn now
        self.assertEqual(self.game.expected_action(), message.THINKERORLEAD)



class TestLegionary(unittest.TestCase):
    """Test handling legionary responses.
    """

    def setUp(self):
        """This is run prior to every test.
        """
        self.game = test_setup.two_player_lead('Legionary')
        self.p1, self.p2 = self.game.game_state.players


    def test_expects_legionary(self):
        """The Game should expect a LEGIONARY action.
        """
        self.assertEqual(self.game.expected_action(), message.LEGIONARY)


    def test_legionary(self):
        """Take one card from the pool with legionary action.
        """
        atrium, foundry = cm.get_cards(['Atrium', 'Foundry'])
        self.p1.hand.set_content([atrium])
        self.game.game_state.pool.set_content([foundry])

        a = message.GameAction(message.LEGIONARY, atrium)
        self.game.handle(a)

        self.assertNotIn('Foundry', self.game.game_state.pool)
        self.assertIn('Foundry', self.p1.stockpile)

        self.assertIn('Atrium', self.p1.revealed) 

        self.assertEqual(self.game.expected_action(), message.GIVECARDS)


    def test_give_cards(self):
        """Take one card from opponent.
        """
        atrium, foundry = cm.get_cards(['Atrium', 'Foundry'])
        self.p1.hand.set_content([atrium])
        self.p2.hand.set_content([foundry])

        a = message.GameAction(message.LEGIONARY, atrium)
        self.game.handle(a)

        a = message.GameAction(message.GIVECARDS, foundry)
        self.game.handle(a)

        self.assertIn('Foundry', self.p1.stockpile)
        self.assertNotIn('Foundry', self.p2.hand)

        # It should be p2's turn now
        self.assertEqual(self.game.expected_action(), message.THINKERORLEAD)


    def test_opponent_has_no_match(self):
        """Demand card that opponent doesn't have.
        """
        atrium, latrine = cm.get_cards(['Atrium', 'Latrine'])
        self.p1.hand.set_content([atrium])
        self.p2.hand.set_content([latrine])

        a = message.GameAction(message.LEGIONARY, atrium)
        self.game.handle(a)

        a = message.GameAction(message.GIVECARDS)
        self.game.handle(a)

        self.assertNotIn('Latrine', self.p1.stockpile)
        self.assertIn('Latrine', self.p2.hand)

        # It should be p2's turn now
        self.assertEqual(self.game.expected_action(), message.THINKERORLEAD)


    def test_demand_jack(self):
        """Demand Jack illegally. This should not change the game state.
        """
        atrium, latrine, jack = cm.get_cards(['Atrium', 'Latrine', 'Jack'])
        self.p1.hand.set_content([atrium, jack])
        self.p2.hand.set_content([latrine])

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.LEGIONARY, jack)
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


    def test_demand_non_existent_card(self):
        """Demand card that we don't have.
        """
        atrium, latrine = cm.get_cards(['Atrium', 'Latrine'])
        self.p1.hand.set_content([atrium])

        mon = Monitor()
        mon.modified(self.game.game_state)

        a = message.GameAction(message.LEGIONARY, latrine)
        self.game.handle(a)

        self.assertFalse(mon.modified(self.game.game_state))


    
if __name__ == '__main__':
    unittest.main()
