#!/usr/bin/env python

import re
import logging
import collections
import card_manager
import termcolor

""" Utility functions for GTR.
"""

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
        logging.error('Error! card {0!s} not found in zone {1!s}'.format(card, zone))
        raise

def add_card_to_zone(card, zone):
    """
    """
    logging.debug('adding card {0!s} to zone {1!s}'.format(card, zone))
    zone.append(card)

def move_card(card, source_zone, dest_zone):
    """ Concatenates get_card_from_zone() and add_card_to_zone().
    """
    try:
        card = get_card_from_zone(card, source_zone)
    except ValueError as e:
        logging.info('Failed to move card')

    add_card_to_zone(card, dest_zone)

def get_short_zone_summary(card_list, n_letters=3):
    """ Return a single-line string with n-letter card abbreviations and numbers
    of card instances.

    Note that n_letters=3 activates the coloring of the output text. 4-letter
    strings are not colorized.
    """
    counter = collections.Counter(card_list)
    cards_string = ''
    for card, count in counter.items():
        cards_string += '{0}[{1:d}], '.format(card[:n_letters], count)
    cards_string.rstrip(', ')
    return cards_string

def get_detailed_card_summary(card, count=None):
    """ return a single-line string to describe one card in detail """

    card_string = '{0:<4}'.format(card[:4])
    if count:
        card_string += '[{0:d}]'.format(count)
    if card != 'Jack':
        material = card_manager.get_material_of_card(card)
        role = card_manager.get_role_of_card(card)
        value = card_manager.get_value_of_card(card)
        function = card_manager.get_function_of_card(card)
        card_string += ' | {0}'.format(material[:3])
        card_string += '-{0}'.format(role[:3])
        card_string += '-{0}'.format(value)
        card_string += ' | {0}'.format(function)
    return card_string

def get_detailed_zone_summary(zone):
    """ return a multi-line description of cards in zone """

    counter = collections.Counter(zone)
    counter_dict = dict(counter)
    cards = counter_dict.keys()
    cards.sort() # alphabetize
    zone_string = '  Card      | Mat-Rol-$ | Description \n'
    for card in cards:
        count = counter_dict[card]
        zone_string += '  * ' + get_detailed_card_summary(card, count)
        zone_string += '\n'
    return zone_string


def get_building_info(building):
    """ Return a string to describe a building """
    if not building.foundation:
        return ''
    title_card = building.foundation
    function = card_manager.get_function_of_card(title_card)
    value = card_manager.get_value_of_card(title_card)
    title_material = card_manager.get_material_of_card(title_card)
    title_value = card_manager.get_value_of_card(title_card)

    info = '  * {0} | {1}-{2} | '.format(title_card, title_material[:3], value)
    if building.site:
        info += '{0} site + '.format(building.site)
    if building.materials:
        info += ''.join([card_manager.get_material_of_card(m)[0] for m in building.materials])
    else: info += '___'
    info += ' | ' + function
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
