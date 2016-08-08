#!/usr/bin/env python

import re
import logging
import collections

from cloaca.error import GTRError
import cloaca.card_manager as cm

"""Utility functions for GTR.
"""

lg = logging.getLogger(__name__)
lg.addHandler(logging.NullHandler())

def get_card_from_zone(card, zone):
    """ Wrapper around the possible exception caused by trying to
    find a non-existent card in a list. Prints an error and
    re-raises the exception.
    """
    lg.debug('getting card {0!s} from zone {1!s}'.format(card, zone))
    try:
        return zone.pop(zone.index(card))
    except ValueError as e:
        raise GTRError('Error! card {0!s} not found in zone {1!s}'.format(card, zone))

def add_card_to_zone(card, zone):
    """
    """
    lg.debug('adding card {0!s} to zone {1!s}'.format(card, zone))
    zone.append(card)

def check_petition_combos(
        n_actions, n_on_role, n_off_role, two_card, three_card):
    """Checks that the number of actions specified can be made with petitions
    using the number of on- and off-role cards, for varying petition size
    requirements. This is used to figure out if a set of non-Jack cards can be
    used to lead/follow multiple times with the Palace.

    n_actions is the number of "action units", or groups of cards leading to
    one action. e.g. 1 on-role card or 3 cards of one role for a petition.

    n_on_role is the number of cards of the role that was led. So if Merchant
    was led, and there are 3 Merchant cards used to lead/follow, this would
    be 3.

    n_off_role is a list with entries for the number of cards of roles other
    than the one that was led. If Merchant was led, and 5 Laborers were used
    for petitions, this would be (5,). If Merchant was led, and 3 Laborers and
    2 Craftsmen were supplied as petitions, this would be (3,2). Note that the
    order doesn't matter, since we don't care about the role of the petition
    cards, just that they match. If no off-role cards are provided, this should
    be an empty list.

    The flags two_card and three_card change the number of cards allowed in a
    petition. In a normal (Imperium) game, the default petition size is 3. With
    a Circus building, players are allowed to petition with 2 or 3 cards. In a
    Republic game, default petition size is 2, so 3-card petitions are not
    allowed. These parameters are set to True if that number of cards is
    allowed for a petition and False otherwise. Note that this function will
    work for both flags false, though there is no place for this in the game
    rules. (A petition of some kind is always allowed.)

    This function does not include the possibility of Jacks. It will only
    determine if petitions with Orders cards are allowed with a Palace.

    If n_actions is 0, then both n_on_role and n_off_role must also be 0.
    This isn't a valid lead or follow, but it meets the petition conditions.
    """
    # Count the number of action units allowed by off- and on-role
    # petitions separately.
    #
    # Chicken nugget numbers
    # ======================
    # For regular petitions, we can have groups of 1 or 3 cards.
    # The maximum number of units (groups) is the number of cards.
    # The minimum number of groups is N/3 + N%3.
    # Starting at the minimum number of groups, we can replace a
    # group of 3 by 3 single groups, increasing the number of units
    # by 2.
    #
    # The allowed numbers of groups is in [N/3 + N%3 + 2*i], for
    # integer i such that 0 <= i <= N/3.
    # The index max, i_max, is determined by:
    #
    #     i_max such that N = N/3 + N%3 + 2*i_max
    #     i_max = (1/2) * (N - N%3 - N/3)
    #     i_max = (1/2) * (2*(N/3)) 
    #     i_max = N/3
    #
    # For off-role cards, only 3-card petitions are allowed.
    # The only allowed number of groups is N_off/3 and N_off
    # must be a multiple of 3.
    #
    # For cases when Circus petitions are allowed, regular petitions
    # are still allowed, so groups of 1, 2, or 3 cards are allowed 
    # for an action unit, for on-role cards.
    # The maximum number of units (groups) is the number of cards.
    # The minimum number of groups is (N+2)/3.
    # Since cards can be grouped into 2 or 3 actions, we can always
    # make all numbers of groups between n_min and n_max.
    #
    # For off-role cards with two-card petitions and three-card petitions
    # allowed, any number of cards n_off > 1 is allowed.
    # The minimum number of groups for a given n_off is (n_off+2)/3
    # The maximum number of groups for a given n_off is n_off/2.
    # Any grouping in between can be achieved by replacing three 2-card
    # groups with two 3-card groups or vice versa.
    #
    # Three-card petitions only
    # -------------------------
    #
    #   1) na_off_min + na_on_min <= n_actions <= na_off_max + na_on_max
    #   2) [n_actions - (na_off_min + na_on_min) ] % 2 == 0
    #   3) n_off % 3 == 0
    #
    # With the following for mins and maxes,
    #   
    #   na_on_min = n_on/3 + n_on%3
    #   na_on_max = n_on
    #   na_off_min = n_off/3
    #   na_off_max = n_off/3
    #
    # the conditions become
    #
    #   1) (n_off/3 + n_on/3 + n_on%3) <= n_actions <= (n_on + n_off/3)
    #   2) [n_actions - (n_off/3 + n_on/3 + n_on%3)] % 2 = 0
    #   3) n_off % 3 == 0
    #
    # Three- and Two-card petitions
    # -----------------------------
    # With a Circus, though, 2-card petitions are allowed. This means the minimum
    # number of actions for a number of cards is potentially lower. (Two cards can be
    # only 1 action, whereas without a Circus, it must be 2 separate actions.)
    # Additionally, since actions can be made with 1, 2, or 3 cards, the second
    # requirement above is removed - all numbers between n_min and n_max are allowed.
    #
    # With 2-card petitions
    #
    #   na_on_min = (n_on+2)/3
    #   na_on_max = n_on
    #   na_off_min = (n_off+2)/3
    #   na_off_max = n_off/2
    #
    # So the conditions become
    #
    #   1) (n_off+2)/3 + (n_on+2)/3 <= n_actions <= (n_on + n_off/2)
    #   2) n_off != 1
    #   
    #
    # No Petitions allowed
    # --------------------
    # With no petitions allowed, n_off must be 0 and n_actions must equal n_on.
    #
    # Only two-card petitions
    # -----------------------
    #
    # With only 2-card petitions allowed, n_off must be a multiple of 2 and 
    # the number of actions is n_off/2. The maximum number of on-role
    # actions is n_on and the minimum is (n_on+1)/2. Anything in between is also
    # allowed
    
    # Check that n_off_role are in bounds (0, or >1)
    for i in n_off_role:
        if i < 0 or i == 1: return False

    n_off_role = [i for i in n_off_role if i != 0]

    if n_on_role<0 or n_actions<0:
        return False

    if not two_card and not three_card:
        return (len(n_off_role) == 0 and n_actions == n_on_role)

    elif two_card and not three_card:
        # Number of off-role actions must be n_off_role[i]/2
        n_off_role_actions = 0
        for i in n_off_role:
            if i%2 != 0: return False
            n_off_role_actions += i/2

        c1 = (n_on_role+1)/2 + n_off_role_actions <= n_actions
        c2 = n_actions <= n_on_role + n_off_role_actions
        return c1 and c2

    elif not two_card and three_card:
        # Number of off-role actions must be n_off_role[i]/3
        n_off_role_actions = 0
        for i in n_off_role:
            if i%3 != 0: return False
            n_off_role_actions += i/3

        c1 = n_off_role_actions + n_on_role/3 + n_on_role%3 <= n_actions
        c2 = n_actions <= n_on_role + n_off_role_actions
        c3 = (n_actions - n_off_role_actions - n_on_role/3 - n_on_role%3) % 2 == 0
        return c1 and c2 and c3

    else: #two_card and three_card:
        # n_off_role_actions_min = (n_off+2)/3, max = n_off/2
        n_off_role_actions_min = 0
        n_off_role_actions_max = 0
        for i in n_off_role:
            n_off_role_actions_min += (i+2)/3
            n_off_role_actions_max += i/2

        c1 = n_off_role_actions_min + (n_on_role+2)/3 <= n_actions
        c2 = n_actions <= (n_on_role + n_off_role_actions_max)
        return c1 and c2


