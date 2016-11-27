"""Encode and decode game objects for storage or network transmission.
"""
import json
import copy
import uuid
import struct
from collections import Counter
import base64

from cloaca.zone import Zone
from cloaca.building import Building
from cloaca.game import Game
from cloaca.card import Card
from cloaca.player import Player
from cloaca.stack import Stack
from cloaca.stack import Frame

class GTREncodingError(Exception):
    pass

def _convert_sites(sites):
    c = Counter(sites)
    return [c['Marble'], c['Rubble'], c['Concrete'], c['Wood'], c['Brick'], c['Stone']]

def encode_zone(obj, buffer, offset, visible=None):
    """Encode a zone at the given `offset` into `buffer`, returning the number
    of bytes written.

    Zones can be hidden or visible, which is determined with the following algorithm:

        1) This function's parameter `visible` overrides other considerations.
        2) The zone is hidden if the length is non-zero and all `Card` objects
        in the zone are anonymous with the `ident` -1.
        3) Otherwise the zone is visible.

    """
    if visible is None:
        visible = next((False for c in obj.cards if not c.is_anon), True)

    if visible:
        return _encode_visible_zone(obj, buffer, offset)
    else:
        return _encode_hidden_zone(obj, buffer, offset)


def _encode_visible_zone(obj, buffer, offset):
    """Returns number of bytes written to buffer starting at offset.
    """
    cards = [c.ident for c in obj.cards]

    # Length of cards (unsigned char) + cards (unsigned chars)
    fmt = '!B'+str(len(cards))+'B'
    struct.pack_into(fmt, buffer, offset, len(cards), *cards)
    return struct.calcsize(fmt)

def _decode_zone(buffer, offset):
    """Decode an encoded visible zone. See `encode_visible_zone` for format.

    Returns a tuple (<bytes>. <zone>) where <bytes> is the total number
    of bytes consumed from the buffer.
    """
    length = struct.unpack_from('!B', buffer, offset)[0]
    hidden = False
    if length:
        first_byte = struct.unpack_from('!B', buffer, offset+1)[0]

        hidden = (first_byte == 0xFF)

    if hidden:
        return (2, Zone([Card(-1)]*length))
    else:
        idents = struct.unpack_from('!'+str(length)+'B', buffer, offset+1)
        cards = [Card(i) for i in idents]
        return (length+1, Zone(cards))


def _encode_hidden_zone(obj, buffer, offset):
    """Returns number of bytes written to buffer starting at offset.

    Encodes a hidden zone as the length of the zone and a single 0xFF byte.
    """
    n_cards = len(obj.cards)

    fmt = '!BB'
    struct.pack_into(fmt, buffer, offset, n_cards, 0xFF)
    return struct.calcsize(fmt)


def encode_building(obj, buffer, offset):
    """Encodes building as the following 7 unsigned bytes.

        <len> : (unsigned char) length of struct
        <foundation> : (unsigned char) card ident
        <site> : (unsigned char) ident
        <complete> : (unsigned char) 1 if complete, 0 if not
        <mat1> : (unsigned char) material 1 (0 if empty)
        <mat2> : (unsigned char) material 2 (0 if empty)
        <mat3> : (unsigned char) material 3 (0 if empty)

    Followed by a variable number of stairway materials:

        <stairway_mat1> : (unsigned char) Stairway material 1
    
    Returns number of bytes written to buffer starting at offset.
    """
    mat_cards = [c.ident for c in obj.materials]
    mat_cards += [0]*(3-len(mat_cards))

    stairway_mat_cards = [c.ident for c in obj.stairway_materials]

    fmt = '!7B' + str(len(stairway_mat_cards)) + 'c'

    struct.pack_into(fmt, buffer, offset, 6+len(stairway_mat_cards),
            obj.foundation.ident,
            site_to_int(obj.site),
            obj.complete,
            *(mat_cards+stairway_mat_cards))

    return struct.calcsize(fmt)


def decode_building(buffer, offset):
    """Decode a building. See `encode_building` for format.

    Returns a tuple (<bytes>. <building>) where <bytes> is the total number
    of bytes consumed from the buffer and <building> is a Building object.
    """
    length = struct.unpack_from('!B', buffer, offset)[0]

    fmt = '!'+str(length)+'B'
    values = struct.unpack_from(fmt, buffer, offset+1)
    foundation = Card(values[0])
    site = int_to_site(values[1])
    complete = bool(values[2])
    materials = Zone([Card(i) for i in values[3:6] if i != 0])
    stairway_materials = Zone([Card(i) for i in values[6:]])

    return (length+1,
            Building(foundation, site, materials, stairway_materials, complete))


def encode_frame(obj, buffer, offset):
    """Encodes frame as the following

        <len> : (unsigned char) length of struct
        <function> : (unsigned char) function enum
        <executed> : (unsigned char) boolean
        <arg1> : (unsigned char) argument 1
        <arg2> : (unsigned char) argument 2
        ...
    
    Frame arguments are players, roles, and actions.
    These all must be pre-converted to integers with the following mapping:

        0: None
        0x10 -> 0x14: Player indices 0-5.
        0x20 -> 0x25: Roles 0-5 (pat, lab, arc, cra, leg, mer)
        0x30 + : GameActions 0-?

    Returns number of bytes written to buffer starting at offset.
    """
    func_int = stack_func_to_int(obj.function_name)
    fmt = '!'+str(3+len(args))+'B'
    length = 2+len(args)

    struct.pack_into(fmt, buffer, offset,
            length, func_int, int(obj.executed), *obj.args)

    return struct.calcsize(fmt)
            

def decode_frame(buffer, offset):
    """Decode a stack frame. See `encode_frame` for format.

    Returns a tuple (<bytes>. <frame>) where <bytes> is the total number
    of bytes consumed from the buffer and <frame> is a Frame object.
    """
    length = struct.unpack_from('!B', buffer, offset)[0]

    fmt = '!'+str(length)+'B'
    values = struct.unpack_from(fmt, buffer, offset+1)
    func_name = int_to_stack_func(values[0])
    executed = bool(values[1])
    args = values[2:]

    return (length+1, Frame(func_name, args=args, executed=executed))


_STACK_FUNC_TO_INT = {
        '_advance_turn' : 0,
        '_await_action' : 1,
        '_do_end_turn' : 2,
        '_do_kids_in_pool' : 3,
        '_do_senate' : 4,
        '_end_turn' : 5,
        '_kids_in_pool' : 6,
        '_perform_clientele_action' : 7,
        '_perform_patron_action' : 8,
        '_perform_role_action' : 9,
        '_perform_role_being_led' : 10,
        '_perform_thinker_action' : 11,
        '_take_turn_stacked' : 12,
}
_INT_TO_STACK_FUNC = {v:k for k,v in _STACK_FUNC_TO_INT.items()}
def stack_func_to_int(func_name):
    return _STACK_FUNC_TO_INT[func_name]

def int_to_stack_func(i):
    return _INT_TO_STACK_FUNC[i]


_SITE_TO_INT = {'Marble':0, 'Rubble':1, 'Concrete':2, 'Wood':3, 'Brick':4, 'Stone':5}
_INT_TO_SITE = {v:k for k,v in _SITE_TO_INT.items()}
def site_to_int(site):
    return _SITE_TO_INT[site]

def int_to_site(i):
    return _INT_TO_SITE[i]

_ROLE_TO_INT = {'Patron':0, 'Laborer':1, 'Architect':2, 'Craftsman':3, 'Legionary':4, 'Merchant':5}
_INT_TO_ROLE = {v:k for k,v in _ROLE_TO_INT.items()}
def role_to_int(site):
    return _ROLE_TO_INT[role]

def int_to_role(i):
    return _INT_TO_ROLE[i]



def decode_player(buffer, offset):
    """Decode a Player. See `encode_player` for format.

    Returns a tuple (<bytes>. <Player>) where <bytes> is the total number
    of bytes consumed from the buffer and <Player> is a Player object.
    """
    fmt = '!21p16sBBB'

    values = struct.unpack_from(fmt, buffer, offset)

    name = values[0]
    uid = uuid.UUID(bytes=values[1]).int
    fountain_card = Card(values[2])
    n_camp_actions = values[3]
    performed_craftsman = values[4]

    offset += struct.calcsize(fmt)
    
    n_bytes, camp = decode_zone(buffer, offset)
    camp.name = 'camp'
    offset += n_bytes
    n_bytes, hand = decode_zone(buffer, offset)
    hand.name = 'hand'
    offset += n_bytes
    n_bytes, stockpile = decode_zone(buffer, offset)
    stockpile.name = 'stockpile'
    offset += n_bytes
    n_bytes, clientele = decode_zone(buffer, offset)
    clientele.name = 'clientele'
    offset += n_bytes
    n_bytes, influence = decode_zone(buffer, offset)
    influence.name = 'influence'
    offset += n_bytes
    n_bytes, revealed = decode_zone(buffer, offset)
    revealed.name = 'revealed'
    offset += n_bytes
    n_bytes, prev_revealed = decode_zone(buffer, offset)
    prev_revealed.name = 'prev_revealed'
    offset += n_bytes
    n_bytes, clients_given = decode_zone(buffer, offset)
    clients_given.name = 'clients_given'
    offset += n_bytes

    n_bytes, vault = decode_zone(buffer, offset)
    vault.name = 'vault'
    offset += n_bytes

    n_buildings = struct.unpack_from('!B', buffer, offset)[0]
    offset += 1

    buildings = []
    for i in range(n_buildings):
        n_bytes, building = decode_building(buffer, offset)
        offset += n_bytes
        buildings.append(building)

    return Player(uid=uid, name='', hand=hand, stockpile=stockpile,
            clientele=clientele, vault=vault, camp=camp,
            fountain_card=fountain_card, n_camp_actions=n_camp_actions,
            buildings=buildings, influence=influence, revealed=revealed,
            prev_revealed=prev_revealed, clients_given=clients_given,
            performed_craftsman=performed_craftsman)



def encode_player(obj, buffer, offset):
    """Encodes Player as the following ? bytes. The length is unsigned,
    but the remaining bytes are signed.

        <name> : (21 byte pascal string), player name (must be 3-20 char)
        <uid> : (16 bytes), player user id
        <fountain_card> : (unsigned char) card ident
        <n_actions> : (unsigned char) camp actions
        <performed_craftsman> : (unsigned char) 1 or 0
        <influence> : (6 bytes) counts of sites in influence (mar, rub, woo, con, bri, sto)

    Followed by the zones in the following order. The hand is split into
    Jacks and non-Jacks so that hidden hands can be compressed.

        <camp> : (Visible Zone)
        <jack_hand> : (Visible Zone)
        <non_jack_hand> : (Visible Zone)
        <stockpile> : (Visible Zone)
        <clientele> : (Visible Zone)
        <revealed> : (Visible Zone)
        <prev_revealed> : (Visible Zone)
        <clients_given> : (Visible Zone)

    And the vault, which is a Hidden Zone. This is encoded as just the
    number of cards.

        <vault> : (Hidden Zone)

    Following these, the number of buildings and the buildings are listed
    in order. Each building writes its length first.

        <n_buildings> : (unsigned char) number of buildings
        <building1> : (Building)
        <building2> : (Building)
        ...
    
    Returns number of bytes written to buffer starting at offset.
    """
    orig_offset = offset

    fmt = '!21p16sBBB6B'

    struct.pack_into(fmt, buffer, offset,
            uuid.UUID(int=obj.uid).bytes,
            obj.fountain_card or 0,
            obj.n_camp_actions,
            obj.performed_craftsman
            *_convert_sites(obj.influence))

    offset += struct.calcsize(fmt)

    offset += encode_zone(obj.camp, buffer, offset)

    # Split hand into Jacks and non-jacks
    non_jack_hand = []
    jack_hand = []
    for c in obj.hand:
        if c.is_jack:
            jack_hand.append(c)
        else:
            non_jack_hand.append(c)

    offset += encode_zone(jack_hand, buffer, offset)
    offset += encode_zone(non_jack_hand, buffer, offset)
    offset += encode_zone(obj.stockpile, buffer, offset)
    offset += encode_zone(obj.clientele, buffer, offset)
    offset += encode_zone(obj.revealed, buffer, offset)
    offset += encode_zone(obj.prev_revealed, buffer, offset)
    offset += encode_zone(obj.clients_given, buffer, offset)

    offset += encode_hidden_zone(obj.vault, buffer, offset)

    # Number of buildings
    fmt = '!B'
    struct.pack_into(fmt, buffer, offset, len(obj.buildings))
    offset += struct.calcsize(fmt)
    
    for b in obj.buildings:
        offset += encode_building(b, buffer, offset)

    return offset-orig_offset



def encode_game(obj, buffer, offset, player_view=None):
    """Encodes Game as the following ? bytes.

        <game_id> : (4 bytes), game id
        <turn_number> : (4 bytes)
        <action_number> : (4 bytes)

        <host> : (21 bytes) name of host

        <legionary_count> : (1 byte)
        <used_oot> : (1 byte)
        <oot_allowed> : (1 byte)
        <role_led> : (1 byte)
        <expected_action> : (1 byte)
        <legionary_player_index> : (1 byte)
        <leader_index> : (1 byte)
        <active_player_index> : (1 byte)

        <in_town_sites> : (6 bytes) mar, rub, con, woo, bri, sto
        <out_of_town_sites> : (6 bytes) mar, rub, con, woo, bri, sto
        <winners> : (5 bytes) or 5 bits?

    followed by the global zones,

        <jacks> : visible zone
        <library> : hidden zone
        <pool> : visible zone

    the players,

        <n_players> : (1 byte) # of players
        <player1> : (Player)
        ...

    the current frame:

        <current_frame> : (Frame)

    and the stack,

        <n_stack_frames> : (4 bytes) # of stack frames
        <stack_frame1> : (Frame)
        ...

    The Game object as viewed by a player contains hidden zones that don't
    require as much space to store (e.g. the deck of cards is hidden to all
    players). If a zone's first card has `ident = -1`, the zones is
    considered hidden, and will be encoded with `encode_hidden_zone` instead of
    `encode_visible_zone`. The exception is players' hands, which can also
    contain Jacks, which are always visible. Hands are always encoded with
    `encode_visible_zone`.
    It is an error to have a zone with a mix of anonymous cards (`ident == 1`)
    and visible cards, except for players' hands.

    Note that this merely storage compression and has no bearing on the game
    information received by a client, the user must convert cards to be
    anonymous before invoking this method if that is desired.
    """
    orig_offset = offset
    fmt = '!III21pBBBBBBBB6B6B5B'

    def convert_winners(winners):
        if winners is None:
            return [0]*5

        return [obj.players.index(p) for p in obj.players]

    struct.pack_into(fmt, buffer, offset,
            obj.game_id,
            obj.turn_number,
            obj.action_number,
            obj.host,
            obj.legionary_count,
            int(obj.used_oot),
            int(obj.oot_allowed),
            role_to_int(obj.role_led),
            obj.expected_action,
            obj.legionary_player_index,
            obj.active_player_index,
            _convert_sites(obj.in_town_sites) +\
            _convert_sites(obj.out_of_town_sites) +\
            convert_winners(obj.winners),
            )

    offset += struct.calc_size(fmt)

    offset += encode_zone(obj.jacks, buffer, offset)
    offset += encode_zone(obj.library, buffer, offset)
    offset += encode_zone(obj.pool, buffer, offset)

    fmt = '!B'
    struct.pack_into(fmt, buffer, offset, len(obj.players))
    offset += struct.calcsize(fmt)

    for p in obj.players:
        offset += encode_player(p)

    offset += encode_frame(obj._current_frame)

    fmt = '!B'
    struct.pack_into(fmt, buffer, offset, len(obj.stack.stack))
    offset += struct.calcsize(fmt)

    for f in obj.stack.stack:
        offset += encode_frame(f)

    return offset-orig_offset

            


def game_to_str(game):
    """Convert Game object to string representation for storage or network
    transmission.
    """
    return base64.b64encode(encode_game(game))

def str_to_game(s):
    bytestring = base64.b64decode(s)

    game = decode_game(bytestring)
