#!/usr/bin/env python

import re
import logging
import collections
import card_manager as cm
import termcolor

""" Utility functions for GTR.
"""

class GTRError(Exception):
    pass

def print_line(symbol='-'):
    """ Print a line for visual division of info """
    logging.info(symbol*80)

def print_header(title, symbol='-'):
    n_symbol = 80 - len(title)
    logging.info('{0}: {1}'.format(title, symbol*n_symbol))

def get_card_from_zone(card, zone):
    """ Wrapper around the possible exception caused by trying to
    find a non-existent card in a list. Prints an error and
    re-raises the exception.
    """
    logging.debug('getting card {0!s} from zone {1!s}'.format(card, zone))
    try:
        return zone.pop(zone.index(card))
    except ValueError as e:
        raise GTRError('Error! card {0!s} not found in zone {1!s}'.format(card, zone))

def add_card_to_zone(card, zone):
    """
    """
    logging.debug('adding card {0!s} to zone {1!s}'.format(card, zone))
    zone.append(card)

def move_card(card, source_zone, dest_zone):
    """ Concatenates get_card_from_zone() and add_card_to_zone().
    """
    source_zone.move_card(card, dest_zone)
    return 

def get_short_zone_summary(string_list, n_letters=3):
    """Return a single-line string with n-letter card abbreviations and numbers
    of card instances.

    Note that n_letters=3 activates the coloring of the output text. 4-letter
    strings are not colorized.
    """
    counter = collections.Counter(string_list)
    cards_string = ', '.join(
            ['{0}[{1:d}]'.format(card[:n_letters], cnt) for card, cnt in counter.items()])
    return cards_string

def get_detailed_card_summary(card, count=None):
    """Return a single-line string to describe one card in detail.
    """

    card_string = '{0:<4}'.format(card.name[:4])
    if count:
        card_string += '[{0:d}]'.format(count)
    if card.name not in ('Jack', 'Card'):
        function = card.text
        card_string += ' | {0}'.format(card.material[:3])
        card_string += '-{0}'.format(card.role[:3])
        card_string += '-{0}'.format(card.value)
        card_string += ' | ' + (function if len(function)<50 else function[:47] + '...')
    return card_string

def get_detailed_zone_summary(zone):
    """Return a multi-line description of cards in zone.
    """

    counter = collections.Counter([c.name for c in zone])
    counter_dict = dict(counter)
    cards = counter_dict.keys()
    cards.sort() # alphabetize
    #zone_string = '  Card      | Mat-Rol-$ | Description \n'
    zone_string = ''
    for card in cards:
        count = counter_dict[card]
        zone_string += '  * ' + get_detailed_card_summary(cm.get_card(card), count)
        zone_string += '\n'
    return zone_string

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

    n_off_role is the number of cards not of the role that was led. If
    Merchant was led, and 5 Laborers were used for petitions, this
    would be 5.

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

    if n_off_role == 1 or n_off_role<0 or n_on_role<0 or n_actions<0:
        return False

    elif not two_card and not three_card:
        return (n_off_role == 0 and n_actions == n_on_role)

    elif two_card and not three_card:
        c1 = (n_off_role%2 == 0)
        c2 = (n_on_role+1)/2 + n_off_role/2 <= n_actions
        c3 = n_actions <= n_on_role + n_off_role/2
        return c1 and c2 and c3

    elif not two_card and three_card:
        c1 = n_off_role/3 + n_on_role/3 + n_on_role%3 <= n_actions
        c2 = n_actions <= n_on_role + n_off_role/3
        c3 = (n_actions - n_off_role/3 - n_on_role/3 - n_on_role%3) % 2 == 0
        c4 = n_off_role%3 == 0
        return c1 and c2 and c3 and c4

    else: #two_card and three_card:
        c1 = (n_off_role+2)/3 + (n_on_role+2)/3 <= n_actions
        c2 = n_actions <= (n_on_role + n_off_role/2)
        return c1 and c2


def get_building_info(building):
    """ Return a string to describe a building """
    if not building.foundation:
        return ''
    title_card = building.foundation
    function = title_card.text
    value = title_card.value
    title_material = title_card.material

    info = '  * {0!s} | {1}-{2:d} | '.format(title_card, title_material[:3], value)
    if building.site:
        info += '{0} site + '.format(building.site)

    # Materials : "Concrete site + C_" for a wall with one concrete added.
    info += ''.join([c.material for c in building.materials])
    info += '_' * (value-len(building.materials))

    info += ' | ' + function[:40]
    return info

def colorize_role(any_string):
    """ Applies color to the role string (eg. 'Legionary', 'Laborer', etc.)
    """
    # The alteration operator | is never greedy. That is, it will take the
    # first match it finds. Thus, we need to make sure there are no overlaps
    # with earlier regexes. Eg, "Legionary|Leg", not "Leg|Legionary"
    role_regex_color_dict = {
      r'\b([Ll]egionaries|[Ll]egionary|[Ll]eg|LEGIONARIES|LEGIONARY|LEG)\b' : ('red',None),
      r'\b([Ll]aborers?|[Ll]ab|LABORERS?|LAB)\b' : ('yellow',None),
      r'\b([Cc]raftsmen|[Cc]raftsman|[Cc]ra|CRAFTSMEN|CRAFTSMAN|CRA)\b' : ('green',None),
      r'\b([Aa]rchitects?|[Aa]rc|ARCHITECTS?|ARC)\b' : ('white',None),
      r'\b([Mm]erchants?|[Mm]er|MERCHANTS?|MER)\b' : ('cyan',None),
      r'\b([Pp]atrons?|[Pp]at|PATRONS?|PAT)\b' : ('magenta',None),
      r'\b([Jj]acks?|JACKS?)\b' : ('grey','on_white'),
    }

    out_string=any_string
    for k,v in role_regex_color_dict.items():
        out_string = re.sub(k,lambda x : termcolor.colored(x.group(0),color=v[0],
          on_color=v[1],attrs=['bold']), out_string)

    return out_string

def colorize_material(any_string):
    """ Applies color to the material string (eg. 'Stone', 'Rub', etc.)
    """
    # The alteration operator | is never greedy. That is, it will take the
    # first match it finds. Thus, we need to make sure there are no overlaps
    # with earlier regexes. Eg, "Legionary|Leg", not "Leg|Legionary"
    material_regex_color_dict = {
      r'\b([Bb]ricks?|[Bb]ri|BRICKS?|BRI)\b' : ('red',None),
      r'\b([Rr]ubble|[Rr]ub|RUBBLE|RUB)\b' : ('yellow',None),
      r'\b([Ww]ood|[Ww]oo|WOOD|WOO)\b' : ('green',None),
      r'\b([Cc]oncrete|[Cc]on|CONCRETE|CON)\b' : ('white',None),
      r'\b([Ss]tone|[Ss]to|STONE|STO)\b' : ('cyan',None),
      r'\b([Mm]arble|[Mm]ar|MARBLE|MAR)\b' : ('magenta',None),
    }

    out_string=any_string
    for k,v in material_regex_color_dict.items():
        out_string = re.sub(k,lambda x : termcolor.colored(x.group(0),color=v[0],
          on_color=v[1],attrs=['bold']), out_string)

    return out_string




class RoleColorFilter(logging.Filter):
    """ This is a filter which colorizes roles with ANSI color sequences.
    """
    def filter(self, record):
        record.msg = colorize_role(record.msg)
        return True

class MaterialColorFilter(logging.Filter):
    """ This is a filter which colorizes roles with ANSI color sequences.
    """
    def filter(self, record):
        record.msg = colorize_material(record.msg)
        return True



if __name__ == '__main__':

    # simple tests...
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    test_zone = ['a', 'a', 'b', 'c']
    card_one = get_card_from_zone('a', test_zone)
    card_two = get_card_from_zone('c', test_zone)
    add_card_to_zone(card_one, test_zone)

    print get_short_zone_summary(test_zone)
