"""Encode and decode game objects for storage or network transmission.
"""
import json
import copy

from cloaca.zone import Zone
from cloaca.building import Building
from cloaca.game import Game
from cloaca.card import Card
from cloaca.player import Player
from cloaca.stack import Stack
from cloaca.stack import Frame

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

    elif isinstance(obj, Stack):
        return encode(obj.__dict__)

    elif isinstance(obj, Frame):
        return encode(obj.__dict__)

    elif isinstance(obj, Game):
        d = dict(obj.__dict__)

        # The args list of Frames sometimes contains a Player object.
        # To prevent duplication, we store just the player index.
        # However, to indicate that the stored int is supposed to be
        # a reference to the player, a list of ['Player', 2] is stored.
        for i, frame in enumerate(d['stack'].stack):
            new_args = []
            for arg in frame.args:
                if type(arg) is Player:
                    player_ref = ['Player', obj.find_player_index(arg.name)]
                    new_args.append(player_ref)
                else:
                    new_args.append(arg)
            d['stack'].stack[i].args = new_args

        if d['_current_frame'] is not None:
            new_args = []
            for i, arg in enumerate(d['_current_frame'].args):
                if type(arg) is Player:
                    player_ref = ['Player', obj.find_player_index(arg.name)]
                    new_args.append(player_ref)
                else:
                    new_args.append(arg)
                d['_current_frame'].args = new_args

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
        stack = obj['stack']
        _current_frame = obj['_current_frame']
    except KeyError as e:
        raise GTREncodingError(e.message)

    game_dict = copy.deepcopy(obj)

    game_dict['players'] = [decode_player(p) for p in players]

    game_dict['jacks'] = decode_zone(jacks, 'jacks')
    game_dict['library'] = decode_zone(library, 'library')
    game_dict['pool'] = decode_zone(pool, 'pool')

    game_dict['_current_frame'] = decode_frame(_current_frame)
    game_dict['stack'] = decode_stack(stack)

    # Revert the ['Player', <n>] refs to Game.players[<n>]
    for i, frame in enumerate(game_dict['stack'].stack):
        new_args = []
        for arg in frame.args:
            if type(arg) is list and arg[0] == 'Player':
                player = game_dict['players'][arg[1]]
                new_args.append(player)
            else:
                new_args.append(arg)

        game_dict['stack'].stack[i].args = new_args

    if game_dict['_current_frame'] is not None:
        new_args = []
        for arg in game_dict['_current_frame'].args:
            if type(arg) is list and arg[0] == 'Player':
                player = game_dict['players'][arg[1]]
                new_args.append(player)
            else:
                new_args.append(arg)

        game_dict['_current_frame'].args = new_args



    #TODO: Why are we doing this and not Game(**game_dict), checking for TypeError?
    game_obj = Game()
    for k, v in game_dict.items():
        setattr(game_obj, k, v)

    return game_obj


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

    try:
        player_obj = Player(**player_dict)
    except TypeError as e:
        raise GTREncodingError('Error decoding Player: ' + e.message)

    return player_obj


def decode_zone(obj, name):
    """Zones are just lists. Turn them into cards."""
    try:
        zone_obj = Zone([Card(c) for c in obj], name)
    except TypeError as e:
        raise GTREncodingError('Error decoding Zone: ' + e.message)

    return zone_obj


def decode_building(obj):
    building_dict = copy.deepcopy(obj)

    building_dict['materials'] = decode_zone(building_dict['materials'], 'materials')
    building_dict['stairway_materials'] = decode_zone(
            building_dict['stairway_materials'], 'stairway_materials')
    building_dict['foundation'] = Card(building_dict['foundation'])

    try:
        building_obj = Building(**building_dict)
    except TypeError as e:
        raise GTREncodingError('Error decoding Building: ' + e.message)

    return building_obj


def decode_stack(obj):
    stack_dict = copy.deepcopy(obj)

    stack_dict['stack'] = map(decode_frame, stack_dict['stack'])

    try:
        stack_obj = Stack(**stack_dict)
    except TypeError as e:
        raise GTREncodingError('Error decoding Stack: ' + e.message)

    return stack_obj


def decode_frame(obj):
    if obj is None:
        return None

    frame_dict = copy.deepcopy(obj)

    # Args can contain Player objects, but they are replaced
    # by lists ['Player', 1] in the encode() serialization.
    # Leave these until decoding is complete, so the references
    # can be restored.
    try:
        frame_obj = Frame(**frame_dict)
    except TypeError as e:
        raise GTREncodingError('Error decoding Frame: ' + e.message)

    return frame_obj


def game_to_json(game, indent=None):
    """Transform a Game object into JSON.
    """
    return json.dumps(encode(game), sort_keys=True, indent=indent)

def json_to_game(game_json):
    """Transform JSON into game object.
    """
    try:
        game_dict = json.loads(game_json)
    except ValueError as e:
        raise GTREncodingError(e.message)

    return decode_game(game_dict)
