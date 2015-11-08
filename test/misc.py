#!/usr/bin/env python

import unittest
from cloaca import gtrutils

class TestCheckPetitionCombos(unittest.TestCase):
    """Test Palace / petition checker function.

        def check_petition_combos(
            n_actions, n_on_role, n_off_role, two_card, three_card):

    It checks if the n_actions number of actions can be constructed
    using n_on_role cards of the role being led and n_off_role cards
    not of the role being led. The boolean flags two_card and three_card
    specify which kinds of petitions are allowed. The function should
    be valid for any combination of inputs.
    """

    def test_invalid_inputs(self):
        """Returns False for out of range inputs.
        """
        f = gtrutils.check_petition_combos
        
        self.assertFalse( f(-1, 1, 0, False, False))
        self.assertFalse( f( 0, 1, 0, False, False))
        self.assertFalse( f( 1, 0, 0, False, False))
        self.assertFalse( f( 1, 1,-1, False, False))
        self.assertFalse( f( 1,-1, 0, False, False))
        self.assertFalse( f( 1, 1, 1, False, False)) # n_off_role can never be 1
        self.assertFalse( f( 1, 1, 1,  True, False)) # n_off_role can never be 1
        self.assertFalse( f( 1, 1, 1, False,  True)) # n_off_role can never be 1
        self.assertFalse( f( 1, 1, 1,  True,  True)) # n_off_role can never be 1

    def test_no_petitions(self):
        """Test with no petitions allowed.
        """
        f = gtrutils.check_petition_combos

        self.assertTrue(  f( 0, 0, 0, False, False))

        self.assertFalse( f( 1, 0, 0, False, False))
        self.assertFalse( f( 1, 1, 2, False, False))
        self.assertFalse( f( 1, 1, 3, False, False))
        self.assertFalse( f( 1, 1, 4, False, False))

        self.assertTrue(  f( 1, 1, 0, False, False))
        self.assertFalse( f( 1, 2, 0, False, False))
        self.assertFalse( f( 1, 3, 0, False, False))

        self.assertFalse( f( 2, 1, 0, False, False))
        self.assertTrue(  f( 2, 2, 0, False, False))
        self.assertFalse( f( 2, 3, 0, False, False))

        self.assertFalse( f( 3, 1, 0, False, False))
        self.assertFalse( f( 3, 2, 0, False, False))
        self.assertTrue(  f( 3, 3, 0, False, False))

        self.assertTrue(  f(13,13, 0, False, False))

    def test_only_three_card_petitions(self):
        """Test with only three-card petitions allowed.
        """
        f = gtrutils.check_petition_combos

        self.assertTrue(  f( 0, 0, 0, False, True))

        self.assertFalse( f( 1, 0, 0, False, True))
        self.assertTrue(  f( 1, 1, 0, False, True))
        self.assertTrue(  f( 1, 0, 3, False, True))
        self.assertTrue(  f( 1, 3, 0, False, True))

        self.assertFalse( f( 1, 1, 2, False, True))
        self.assertFalse( f( 1, 1, 3, False, True))
        self.assertFalse( f( 1, 1, 4, False, True))

        self.assertTrue(  f( 2, 2, 0, False, True))
        self.assertTrue(  f( 2, 1, 3, False, True))
        self.assertTrue(  f( 2, 3, 3, False, True))
        self.assertTrue(  f( 2, 6, 0, False, True))
        self.assertTrue(  f( 2, 0, 6, False, True))
        self.assertFalse( f( 2, 4, 3, False, True))

        self.assertFalse( f( 3, 1, 0, False, True))
        self.assertFalse( f( 3, 2, 0, False, True))
        self.assertFalse( f( 3, 0, 3, False, True))
        self.assertFalse( f( 3, 0, 6, False, True))
        self.assertTrue(  f( 3, 3, 0, False, True))
        self.assertTrue(  f( 3, 2, 3, False, True))
        self.assertTrue(  f( 3, 3, 6, False, True))
        self.assertTrue(  f( 3, 1, 6, False, True))
        self.assertTrue(  f( 3, 0, 9, False, True))

        self.assertTrue(  f(13,13, 0, False, True))
        self.assertTrue(  f(13,39, 0, False, True))
        self.assertTrue(  f(13, 0,39, False, True))
        self.assertTrue(  f(13,15,24, False, True))
        self.assertTrue(  f(13,15, 0, False, True))
        self.assertTrue(  f(13,12, 3, False, True))
        self.assertFalse( f(13,14, 0, False, True))

    def test_only_two_card_petitions(self):
        """Test with only two-card petitions
        """
        f = gtrutils.check_petition_combos

        self.assertTrue(  f( 0, 0, 0, True, False))

        self.assertFalse( f( 1, 0, 0, True, False))
        self.assertFalse( f( 1, 0, 1, True, False))
        self.assertTrue(  f( 1, 0, 2, True, False))
        self.assertFalse( f( 1, 0, 3, True, False))
        self.assertFalse( f( 1, 0, 4, True, False))

        self.assertTrue(  f( 1, 1, 0, True, False))
        self.assertFalse( f( 1, 1, 2, True, False))

        self.assertFalse( f( 2, 0, 2, True, False))
        self.assertFalse( f( 2, 0, 3, True, False))
        self.assertTrue(  f( 2, 0, 4, True, False))
        self.assertFalse( f( 2, 0, 5, True, False))
        
        self.assertTrue(  f( 2, 1, 2, True, False))
        self.assertFalse( f( 2, 1, 3, True, False))
        self.assertFalse( f( 2, 1, 4, True, False))

        self.assertTrue(  f(13, 26,  0, True, False))
        self.assertTrue(  f(13,  0, 26, True, False))
        self.assertTrue(  f(13, 14, 12, True, False))
        self.assertTrue(  f(13, 13, 10, True, False))
        self.assertFalse( f(13, 15, 11, True, False))

    def test_two_and_three_card_petitions(self):
        """Test with two- and three-card petitions
        """
        f = gtrutils.check_petition_combos

        self.assertTrue(  f( 0, 0, 0, True, True))

        self.assertFalse( f( 1, 0, 0, True, True))
        self.assertFalse( f( 1, 0, 1, True, True))
        self.assertTrue(  f( 1, 0, 2, True, True))
        self.assertTrue(  f( 1, 0, 3, True, True))
        self.assertFalse( f( 1, 0, 4, True, True))
        self.assertTrue(  f( 1, 1, 0, True, True))
        self.assertTrue(  f( 1, 2, 0, True, True))
        self.assertTrue(  f( 1, 3, 0, True, True))
        self.assertFalse( f( 1, 4, 0, True, True))

        self.assertFalse( f( 1, 1, 2, True, True))
        self.assertFalse( f( 1, 1, 3, True, True))
        self.assertFalse( f( 1, 2, 2, True, True))
        self.assertFalse( f( 1, 3, 2, True, True))
        self.assertFalse( f( 1, 3, 3, True, True))

        self.assertTrue(  f( 2, 1, 2, True, True))
        self.assertTrue(  f( 2, 1, 3, True, True))
        self.assertTrue(  f( 2, 0, 4, True, True))
        self.assertTrue(  f( 2, 0, 5, True, True))
        self.assertTrue(  f( 2, 0, 6, True, True))
        self.assertTrue(  f( 2, 4, 0, True, True))
        self.assertTrue(  f( 2, 5, 0, True, True))
        self.assertTrue(  f( 2, 6, 0, True, True))
        
        self.assertTrue(  f(13, 26,  0, True, True))
        self.assertTrue(  f(13, 39,  0, True, True))
        self.assertTrue(  f(13,  0, 26, True, True))
        self.assertTrue(  f(13, 14, 12, True, True))
        self.assertTrue(  f(13, 13, 10, True, True))
        self.assertTrue(  f(13, 15, 11, True, True))
        self.assertFalse( f(13, 40,  0, True, True))
        self.assertFalse( f(13, 11,  3, True, True))
 

if __name__ == '__main__':
    unittest.main()
