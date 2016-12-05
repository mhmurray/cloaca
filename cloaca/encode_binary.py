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

_SITES = ['Marble', 'Rubble', 'Concrete', 'Wood', 'Brick', 'Stone']
def _decode_sites(list_of_counts):
    sites = []
    for count, material in zip(list_of_counts, _SITES):
        sites.extend([material]*count)
    return sites

    

def encode_zone(obj, visible=None):
    """Encode a zone at the given `offset` into `buffer`, returning a bytearray.

    Zones can be hidden or visible, which is determined with the following algorithm:

        1) This function's parameter `visible` overrides other considerations.
        2) The zone is hidden if the length is non-zero and all `Card` objects
        in the zone are anonymous with the `ident` -1.
        3) Otherwise the zone is visible.

    """
    if visible is None:
        all_anon = next((False for c in obj.cards if not c.is_anon), True)
        visible = not(len(obj.cards) and all_anon)

    if visible:
        return _encode_visible_zone(obj)
    else:
        return _encode_hidden_zone(obj)


def _encode_visible_zone(obj):
    """Returns number of bytes written to buffer starting at offset.
    """
    cards = [c.ident for c in obj.cards]

    # Length of cards (unsigned char) + cards (unsigned chars)
    fmt = '!B'+str(len(cards))+'B'
    return struct.pack(fmt, len(cards), *cards)

def decode_zone(buffer, offset):
    """Decode an encoded zone. See `encode_zone` for format.

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


def _encode_hidden_zone(obj):
    """Returns number of bytes written to buffer starting at offset.

    Encodes a hidden zone as the length of the zone and a single 0xFF byte.
    """
    n_cards = len(obj.cards)

    fmt = '!BB'
    return struct.pack(fmt, n_cards, 0xFF)


def encode_building(obj):
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

    return struct.pack(fmt, 6+len(stairway_mat_cards),
            obj.foundation.ident,
            site_to_int(obj.site),
            obj.complete,
            *(mat_cards+stairway_mat_cards))


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


_ARG_PLAYER, _ARG_ACTION, _ARG_ROLE = range(3)
_FRAME_ARG_TYPE_MAPPING = {
        '_advance_turn': (),
        '_await_action': (_ARG_ACTION, _ARG_PLAYER),
        '_do_end_turn': (_ARG_PLAYER,),
        '_do_kids_in_pool': (_ARG_PLAYER,),
        '_do_senate': (_ARG_PLAYER,),
        '_end_turn': (),
        '_kids_in_pool': (),
        '_perform_clientele_action': (_ARG_PLAYER, _ARG_ROLE),
        '_perform_patron_action': (_ARG_PLAYER,),
        '_perform_role_action': (_ARG_PLAYER, _ARG_ROLE),
        '_perform_role_being_led': (_ARG_PLAYER,),
        '_perform_thinker_action': (_ARG_PLAYER,),
        '_take_turn_stacked': (_ARG_PLAYER,),
        }

def convert_frame_args(frame, players):
    """Convert the Frame arguments to numerical values using the 
    data from `game`. Return a list of the new args.
    """
    # Roles are strings, but in case they change to an enum or integer
    # represenation, we will not use that to distinguish from numbered
    # actions.
    # Roles are arguments in the following cases:
    #   - 2nd argument of _perform_clientele_action
    #   - 2nd argument of _perform_role_action
    # Game actions are arguments only for
    #   - 1st arg of _await_action
    #
    # All we have to do is test for those function names,
    # and exclude the case where an arg is a Player object.
    new_args = []
    arg_types = _FRAME_ARG_TYPE_MAPPING[frame.function_name]
    for arg, arg_type in zip(frame.args, arg_types):
        if arg is None:
            new_args.append(0)
        elif arg_type == _ARG_PLAYER:
            new_args.append(0x10 + players.index(arg))
        elif arg_type == _ARG_ROLE:
            new_args.append(0x20 + role_to_int(arg))
        elif arg_type == _ARG_ACTION:
            new_args.append(0x30 + arg)
        else:
            raise GTREncodingError('Unknown Frame argument type: '+str(arg_type))

    return new_args

def unconvert_frame_args(args, function_name, players):
    """Convert frame args from the serialized (integer) types
    to python types. See `convert_frame_args` for format.
    """
    new_args = []
    arg_types = _FRAME_ARG_TYPE_MAPPING[function_name]
    for arg, arg_type in zip(args, arg_types):
        if arg == 0:
            new_args.append(None)
        elif arg_type == _ARG_PLAYER:
            new_args.append(players[arg-0x10])
        elif arg_type == _ARG_ROLE:
            new_args.append(int_to_role(arg-0x20))
        elif arg_type == _ARG_ACTION:
            new_args.append(arg-0x30)
        else:
            raise GTREncodingError('Unknown Frame argument type: '+str(arg_type))

    return new_args

def encode_frame(obj):
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
        0x20 -> 0x26: Roles 0-6 (None, pat, lab, arc, cra, leg, mer)
        0x30 + : GameActions 0-?

    Returns number of bytes written to buffer starting at offset.

    If the frame is None, the length is 0
    """
    if obj is None:
        return struct.pack('!B', 0)

    func_int = stack_func_to_int(obj.function_name)
    fmt = '!'+str(3+len(obj.args))+'B'
    length = 2+len(obj.args)

    return struct.pack(fmt, length, func_int, int(obj.executed), *obj.args)
            

def decode_frame(buffer, offset):
    """Decode a stack frame. See `encode_frame` for format.

    Returns a tuple (<bytes>. <frame>) where <bytes> is the total number
    of bytes consumed from the buffer and <frame> is a Frame object.
    """
    length = struct.unpack_from('!B', buffer, offset)[0]

    if length == 0:
        return (1, None)

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


_SITE_TO_INT = {
        'Marble':0, 'Rubble':1, 'Concrete':2,
        'Wood':3, 'Brick':4, 'Stone':5,
        None: 0xFF
        }
_INT_TO_SITE = {v:k for k,v in _SITE_TO_INT.items()}
def site_to_int(site):
    return _SITE_TO_INT[site]

def int_to_site(i):
    return _INT_TO_SITE[i]

_ROLE_TO_INT = {
        'Patron':0, 'Laborer':1, 'Architect':2,
        'Craftsman':3, 'Legionary':4, 'Merchant':5,
        None: 0xFF
        }
_INT_TO_ROLE = {v:k for k,v in _ROLE_TO_INT.items()}
def role_to_int(role):
    return _ROLE_TO_INT[role]

def int_to_role(i):
    return _INT_TO_ROLE[i]



def decode_player(buffer, offset):
    """Decode a Player. See `encode_player` for format.

    Returns a tuple (<bytes>. <Player>) where <bytes> is the total number
    of bytes consumed from the buffer and <Player> is a Player object.
    """
    offset_orig = offset
    fmt = '!21p16sBBB6B'

    values = struct.unpack_from(fmt, buffer, offset)
    offset += struct.calcsize(fmt)

    name = values[0]
    uid = uuid.UUID(bytes=values[1]).int
    fountain_card = None if values[2] == 0xFF else Card(values[2])
    n_camp_actions = values[3]
    performed_craftsman = values[4]
    influence_site_counts = values[5:]
    influence = _decode_sites(influence_site_counts)
    
    n_bytes, camp = decode_zone(buffer, offset)
    camp.name = 'camp'
    offset += n_bytes

    n_bytes, jack_hand = decode_zone(buffer, offset)
    offset += n_bytes
    n_bytes, non_jack_hand = decode_zone(buffer, offset)
    offset += n_bytes
    hand = Zone(jack_hand.cards+non_jack_hand.cards, name='hand')

    n_bytes, stockpile = decode_zone(buffer, offset)
    stockpile.name = 'stockpile'
    offset += n_bytes
    n_bytes, clientele = decode_zone(buffer, offset)
    clientele.name = 'clientele'
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

    p = Player(uid=uid, name='', hand=hand, stockpile=stockpile,
            clientele=clientele, vault=vault, camp=camp,
            fountain_card=fountain_card, n_camp_actions=n_camp_actions,
            buildings=buildings, influence=influence, revealed=revealed,
            prev_revealed=prev_revealed, clients_given=clients_given,
            performed_craftsman=performed_craftsman)

    return (offset-offset_orig, p)



def encode_player(obj):
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

        <camp> : (Zone)
        <jack_hand> : (Zone)
        <non_jack_hand> : (Zone)
        <stockpile> : (Zone)
        <clientele> : (Zone)
        <revealed> : (Zone)
        <prev_revealed> : (Zone)
        <clients_given> : (Zone)
        <vault> : (Zone)

    Following these, the number of buildings and the buildings are listed
    in order. Each building writes its length first.

        <n_buildings> : (unsigned char) number of buildings
        <building1> : (Building)
        <building2> : (Building)
        ...
    
    Returns bytestring for the player.
    """
    chunks = []

    fmt = '!21p16sBBB6B'

    chunks.append(struct.pack(fmt,
            obj.name,
            uuid.UUID(int=obj.uid).bytes,
            obj.fountain_card if obj.fountain_card is not None else 0xFF,
            obj.n_camp_actions,
            obj.performed_craftsman,
            *_convert_sites(obj.influence)))

    chunks.append(encode_zone(obj.camp))

    # Split hand into Jacks and non-jacks
    non_jack_hand = []
    jack_hand = []
    for c in obj.hand:
        if c.is_jack:
            jack_hand.append(c)
        else:
            non_jack_hand.append(c)

    chunks.append(encode_zone(Zone(jack_hand)))
    chunks.append(encode_zone(Zone(non_jack_hand)))
    chunks.append(encode_zone(obj.stockpile))
    chunks.append(encode_zone(obj.clientele))
    chunks.append(encode_zone(obj.revealed))
    chunks.append(encode_zone(obj.prev_revealed))
    chunks.append(encode_zone(obj.clients_given))
    chunks.append(encode_zone(obj.vault))

    # Number of buildings
    fmt = '!B'
    chunks.append(struct.pack(fmt, len(obj.buildings)))
    
    for b in obj.buildings:
        chunks.append(encode_building(b))

    return ''.join(chunks)


def decode_game(bytes):
    """Decode a Game. See `encode_game` for format.

    Returns a tuple (<bytes>. <game>) where <bytes> is the total number
    of bytes consumed from the buffer and <game> is a Game object.
    """
    fmt = '!III21pBBBBBBBB'
    offset = struct.calcsize(fmt)

    values = struct.unpack(fmt, bytes[:offset])

    game_id, turn_number, action_number, hostname, legionary_count, used_oot, \
            oot_allowed, role_led, expected_action, legionary_player_index, \
            leader_index, active_player_index = values

    used_oot = bool(used_oot)
    oot_allowed = bool(oot_allowed)
    role_led = int_to_role(role_led)
    
    if expected_action == 0xFF: expected_action = None
    if legionary_player_index == 0xFF: legionary_player_index = None
    if leader_index == 0xFF: leader_index = None
    if active_player_index == 0xFF: active_player_index = None

    fmt = '!6B'
    length = struct.calcsize(fmt)
    in_town_site_counts = struct.unpack(fmt, bytes[offset:offset+length])
    offset += length
    out_of_town_site_counts = struct.unpack(fmt, bytes[offset:offset+length])
    offset += length

    in_town_sites = _decode_sites(in_town_site_counts)
    out_of_town_sites = _decode_sites(out_of_town_site_counts)

    fmt = '!5B'
    length = struct.calcsize(fmt)
    winners = struct.unpack(fmt, bytes[offset:offset+length])
    offset += length

    length, jacks = decode_zone(bytes, offset)
    jacks.name = 'jacks'
    offset += length

    length, library = decode_zone(bytes, offset)
    library.name = 'library'
    offset += length
    
    length, pool = decode_zone(bytes, offset)
    pool.name = 'pool'
    offset += length

    fmt = '!B'
    n_players = struct.unpack_from(fmt, bytes, offset)[0]
    offset += struct.calcsize(fmt)

    players = []
    for i in range(n_players):
        length, p = decode_player(bytes, offset)
        players.append(p)
        offset += length

    length, current_frame = decode_frame(bytes, offset)
    offset += length
    if current_frame is not None:
        new_args = unconvert_frame_args(current_frame.args,
                current_frame.function_name, players)
        current_frame.args = new_args
    
    fmt = '!B'
    n_stack_frames = struct.unpack_from(fmt, bytes, offset)[0]
    offset += struct.calcsize(fmt)

    stack_frames = []
    for i in range(n_stack_frames):
        length, f = decode_frame(bytes, offset)
        offset += length
        if f is not None:
            new_args = unconvert_frame_args(f.args, f.function_name, players)
            f.args = new_args
        stack_frames.append(f)

    stack = Stack(stack_frames)
    
    game = Game(
            game_id = game_id,
            turn_number = turn_number,
            action_number = action_number,
            host = hostname,
            legionary_count = legionary_count,
            used_oot = used_oot,
            oot_allowed = oot_allowed,
            role_led = role_led,
            expected_action = expected_action,
            legionary_player_index = legionary_player_index,
            leader_index = leader_index,
            active_player_index = active_player_index,
            in_town_sites = in_town_sites,
            out_of_town_sites = out_of_town_sites,
            winners = winners,
            jacks = jacks,
            library = library,
            pool = pool,
            players = players,
            current_frame = current_frame,
            stack = stack)

    return game


def encode_game(obj):
    """
    Encodes Game as the following ? bytes.
    Canonical order for roles is Patron, Laborer, Architect, Craftsman,
    Legionary, Merchant. The same for the corresponding materials.

        <game_id> : (4 byte integer)
        <turn_number> : (4 byte integer)
        <action_number> : (4 byte integer)

        <host> : (21 byte pascal string) name of host or empty string for None

        <legionary_count> : (1 byte integer)
        <used_oot> : (1 byte boolean) 0 or 1
        <oot_allowed> : (1 byte boolean) 0 or 1
        <role_led> : (1 byte integer) 255 for None, 0-5 in canonical order
        <expected_action> : (1 byte integer) 255 for None or action #.
        <legionary_player_index> : (1 byte integer) 255 for None or index 0-4
        <leader_index> : (1 byte integer) 255 for None or index 0-4
        <active_player_index> : (1 byte integer) 255 for None or index 0-4

        <in_town_sites> : (6 bytes) count of sites in canonical order
        <out_of_town_sites> : (6 bytes) count of sites in canonical order
        <winners> : (5 bytes) byte is True if that player is a winner.
            All False if no winner.

    followed by the global zones,

        <jacks> : (Zone)
        <library> : (Zone)
        <pool> : (Zone)

    the players,

        <n_players> : (1 byte) # of players
        <player1> : (Player)
        ...

    the current frame:

        <current_frame> : (Frame) current frame or 0-length frame if it's None

    and the stack,

        <n_stack_frames> : (4 bytes) # of stack frames. 0 for empty stack.
        <stack_frame1> : (Frame)
        ...

    The Game object sometimes contains zones with hidden cards, such as
    vaults, opponent's hands, and the library.
    When the Zone contains only anonymous cards (with ident -1), only
    the length of the zone is recorded.
    See `encode_zone` for details.
    """
    chunks = []

    def convert_winners(winners):
        if winners is None:
            return [0]*5

        flags = [0]*5
        for p in winners:
            flags[obj.players.index(p)] = 1

        return flags


    fmt = '!III21pBBBBBBBB'
    chunks.append(struct.pack(fmt,
            obj.game_id,
            obj.turn_number,
            obj.action_number,
            obj.host if obj.host is not None else '',
            obj.legionary_count,
            int(obj.used_oot),
            int(obj.oot_allowed),
            role_to_int(obj.role_led),
            obj.expected_action if obj.expected_action is not None else 0xFF,
            obj.legionary_player_index if obj.legionary_player_index is not None else 0xFF,
            obj.leader_index if obj.leader_index is not None else 0xFF,
            obj.active_player_index if obj.active_player_index is not None else 0xFF,
            ))
    
    fmt = '!6B6B5B'
    chunks.append(struct.pack(fmt,
            *(_convert_sites(obj.in_town_sites) +\
            _convert_sites(obj.out_of_town_sites) +\
            convert_winners(obj.winners))
            ))

    chunks.append(encode_zone(obj.jacks))
    chunks.append(encode_zone(obj.library))
    chunks.append(encode_zone(obj.pool))

    fmt = '!B'
    chunks.append(struct.pack(fmt, len(obj.players)))

    for p in obj.players:
        chunks.append(encode_player(p))

    f = obj._current_frame
    if f is None:
        chunks.append(encode_frame(f))
    else:
        new_args = convert_frame_args(f, obj.players)
        new_frame = Frame(f.function_name, args=new_args, executed=f.executed)
        chunks.append(encode_frame(new_frame))

    fmt = '!B'
    chunks.append(struct.pack(fmt, len(obj.stack.stack)))

    for f in obj.stack.stack:
        if f is None:
            chunks.append(encode_frame(f))
        else:
            new_args = convert_frame_args(f, obj.players)
            new_frame = Frame(f.function_name, args=new_args, executed=f.executed)
            chunks.append(encode_frame(new_frame))

    return ''.join(chunks)


def game_to_str(game):
    """Convert Game object to string representation for storage or network
    transmission.
    """
    # print ''.join('{:02x}'.format(x) for x in bytearray(encode_game(game)))
    # print len(encode_game(game))
    return base64.b64encode(encode_game(game))

def str_to_game(s):
    bytestring = base64.b64decode(s)

    return decode_game(bytestring)

