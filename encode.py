"""Encode and decode game objects for storage or network transmission.
"""
import json
import copy

from cloaca.zone import Zone
from cloaca.building import Building
from cloaca.game import Game
from cloaca.card import Card
from cloaca.player import Player

class GTREncodingError(Exception):
    pass

def encode(obj):
    """Recursive function that transforms a Game object's attributes into
    simpler objects, like Card(123) --> int(123). The goal is to make a simple
    dictionary with the same attribute names as the objects' __dict__
    attributes. This dictionary is the minimal representation of the object.

    Transformations:
        Card --> Card.ident
        Zone --> Zone.cards
        Building --> __dict__
        Player --> __dict__
        Game --> __dict__ (except that stack and _current_frame are deleted)

    Other objects are untouched
    """
    if isinstance(obj, Card):
        return obj.ident

    elif isinstance(obj, Zone):
        return encode(obj.cards)

    elif isinstance(obj, Building):
        return encode(obj.__dict__)

    elif isinstance(obj, Player):
        return encode(obj.__dict__)

    elif isinstance(obj, list):
        return [encode(el) for el in obj]

    elif isinstance(obj, dict):
        return {k:encode(v) for k,v in obj.items()}

    elif isinstance(obj, Game):
        d = dict(obj.__dict__)
        del d['stack']
        del d['_current_frame']

        return encode(d)

    else:
        return obj


def decode_game(obj):
    """Decode a dictionary made with encode() into a Game object.
    """
    try:
        players = obj['players']
        jacks = obj['jacks']
        library = obj['library']
        pool = obj['pool']
    except KeyError as e:
        raise GTREncodingError(e.message)

    game_dict = copy.deepcopy(obj)

    game_dict['players'] = [decode_player(p) for p in players]

    game_dict['jacks'] = decode_zone(jacks, 'jacks')
    game_dict['library'] = decode_zone(library, 'library')
    game_dict['pool'] = decode_zone(pool, 'pool')

    g = Game()

    for k, v in game_dict.items():
        setattr(g, k, v)

    return g


def decode_player(obj):
    """Decode a dictionary made with encode() into a Player object.
    """
    player_dict = copy.deepcopy(obj)

    zones = ('hand', 'stockpile', 'clientele', 'vault', 'camp',
            'revealed', 'prev_revealed')

    for k in zones:
        player_dict[k] = decode_zone(player_dict[k], k)

    f_card = player_dict['fountain_card']
    player_dict['fountain_card'] = Card(f_card) if f_card is not None else None

    player_dict['buildings'] = [decode_building(b) for b in obj['buildings']]

    return Player(**player_dict)


def decode_zone(obj, name):
    """Zones are just lists. Turn them into cards."""
    return Zone([Card(c) for c in obj], name)


def decode_building(obj):
    building_dict = copy.deepcopy(obj)

    building_dict['materials'] = decode_zone(building_dict['materials'], 'materials')
    building_dict['stairway_materials'] = decode_zone(
            building_dict['stairway_materials'], 'stairway_materials')
    building_dict['foundation'] = Card(building_dict['foundation'])

    return Building(**building_dict)


def game_to_json(game):
    """Transform a Game object into JSON.
    """
    return json.dumps(encode(game), sort_keys=True)

def json_to_game(game_json):
    """Transform JSON into game object.
    """
    return decode_game(json.loads(game_json))
