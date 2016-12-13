"""Encode and decode game objects for storage or network transmission.

Top-level encoding is handled by the functions that convert a Game object
into a base64-encoded bytestring and vice versa.
    - game_to_str(game)
    - str_to_game(buffer)

Objects are encoded with the functions:
    - encode_game(game)
    - encode_zone(zone)
    - encode_player(player)
    - encode_frame(frame, players)
    - encode_building(building)
    - encode_stack(stack, players)

and decoded by passing the binary buffer to these:
    - decode_game(buffer)
    - decode_zone(buffer, offset)
    - decode_player(buffer, offset)
    - decode_building(buffer, offset)
    - decode_frame(buffer, offset)
    - decode_stack(buffer, offset)

where the offset into the buffer is used to decode more efficiently
using struct.unpack_from().

Additionally, the encoding header that includes a checksum and encoding
version is manipulated with:
    - make_header(encoded_game)
    - decode_header(data)

The following functions are available for formatting help,
but these are specific to the encoding format, and may change
in future versions:
    - _material_to_int(material)
    - _int_to_material(id)
    - _role_to_int(role)
    - _int_to_role(id)
    - _frame_func_to_int(function_name)
    - _int_to_frame_func(id)
    - _encode_frame_args(args, players)
    - _decode_frame_args(args, players)
    - _encode_sites(sites)
    - _decode_sites(sites_list)
    - _encode_winners(winners, players)
    - _decode_winners(winner_flags, players)

Encoding and decoding errors are reported by raising GTREncodingError.

There are a few module-level variables that are useful.
The magic number that prefixes all encoded games is available as the
module-level property MAGIC_NUMBER.
The byte-sized encoding for anonymous cards is ANONCARD and values like None
or the null byte for hidden zones are represented with NULLCODE.
These are simply 0xFE and 0xFF, respectively.


Full format specification
=========================

Roles, Materials, and Sites are represented as integers in several
places. They are placed in canonical order, which is Patron, Laborer,
Architect, Craftsman, Legionary, Merchant, and likewise for the
corresponding material or site.

All numbers are unsigned integers unless otherwise specified.

The <length> field for stack frames, buildings, and players is the
number of all of the _other_ bytes, not including the length field
itself.

Header
------
A header includes non-game meta-information.
    
    <magic_number> : (4 bytes) magic number to identify Game encodings
    <encoding_version> : (4 bytes) version of this encoding.
    <checksum> : (4 bytes) CRC32 checksum of the remaining data section

Game
----
First the fixed size set of game properties:

    <game_id> : (4 byte integer)
    <turn_number> : (4 byte integer)
    <action_number> : (4 byte integer)
    <hostname> : (21 byte pascal string) 
    <legionary_count> : (1 byte integer)
    <used_oot> : (1 byte boolean) 0 or 1
    <oot_allowed> : (1 byte boolean) 0 or 1
    <role_led> : (1 byte integer) 0xFF for None or Role 0-5 in canonical order
    <expected_action> : (1 byte integer) 0xFF for None or action #.
    <legionary_player_index> : (1 byte integer) 0xFF for None or player index 0-4
    <leader_index> : (1 byte integer) 0xFF for None or player index 0-4
    <active_player_index> : (1 byte integer) 0xFF for None or player index 0-4

    <in_town_sites> : (6 bytes) count of Sites in canonical order.
    <out_of_town_sites> : (6 bytes) count of Sites in canonical order
    <winners> : (5 bytes) For each player, a True byte if that player is a winner.
        All False if no winner.


The global Game zones follow. See the Zone encoding for details.

    <jacks> : (Zone)
    <library> : (Zone)
    <pool> : (Zone)

The number of players and each player are encoded next. See Player encoding.

    <n_players> : (1 byte) # of players
    <player1> : (Player)
    ...

then the current frame:

    <current_frame> : (Frame) current frame or 0-length frame if it's None

and the stack, which is just a length and list of frames,

    <n_stack_frames> : (4 bytes) # of stack frames. 0 for empty stack.
    <stack_frame1> : (Frame)
    ...

Zone
----
A zone is either of the following two formats:

    <length> (1 byte) number of cards in the zone.
    <card1> (1 byte) Card.ident, or 0xFE if the card is anonymous (ident = -1).
    ...

OR, if all cards in the zone are anonymous (ident = -1):

    <length> (1 byte) number of cards
    <0xFF> (1 byte) Fixed byte with value 0xFF.

Note that anonymous cards can be stored in a zone alongside non-anonymous
cards, but the second format cannot be used. The intention is to compress
the frequent situation where a Game object is privatized for presentation
to a single player, who cannot see other players' hands, the deck, etc.


Player
------
A player is stored first as the fixed-length properties

    <name> : (21 byte pascal string)
    <uid> : (4 bytes), player user id
    <fountain_card> : (1 byte) fountain card ident or 0xFF for None or 0xFE for anonymous
    <n_actions> : (1 byte) camp actions
    <performed_craftsman> : (1 byte) 1 or 0
    <influence> : (6 bytes) Count of sites in canonical order

Followed by the player zones in the following order. The hand is split into
Jacks and non-Jacks to facilitate the anonymous card compression. See
Zone encoding for details.

    <camp> : (Zone)
    <jack_hand> : (Zone)
    <non_jack_hand> : (Zone)
    <stockpile> : (Zone)
    <clientele> : (Zone)
    <revealed> : (Zone)
    <prev_revealed> : (Zone)
    <clients_given> : (Zone)
    <vault> : (Zone)

Following these, the number of buildings and the buildings are encoded.
See Building encoding for details.

    <n_buildings> : (1 byte) number of buildings
    <building1> : (Building)
    <building2> : (Building)
    ...


Building
--------
A building is encoded as the building length and the fixed-length properties,
including the materials, where invalid material slots are marked. There can be
an arbitrary number of stairway materials following these.
The site, foundation, materials, and stairway materials cannot be anonymous or
None.
    
        <len> : (1 byte) length of encoded struct
        <foundation> : (1 byte) Card ident
        <site> : (1 byte) Site as canonically-numbered material.
        <complete> : (1 byte) 1 or 0
        <mat1> : (1 byte) Card ident or 0 if material slot is empty.
        <mat2> : (1 byte) Card ident
        <mat3> : (1 byte) Card ident
        <stairway_mat1> : (1 byte) Card ident
        ...


Stack Frame
-----------
Frames are encoded using a mapping for the possible function names
and an integer encoding for their arguments. The format is the following:

    <len> : (1 byte) length of encoded struct
    <function> : (1 byte) Function #
    <executed> : (1 byte) boolean
    <arg1> : (1 byte) Argument 1, integer-mapped
    <arg2> : (1 byte)
    ...

The mapping for integer to function name and the types of arguments
for that function is the following. An entry '-' indicate that the
function takes no arguments.

    Integer | Stack frame function name   | Argument types
    -------------------------------------------------------
          0 | '_advance_turn'             | -
          1 | '_await_action'             | (ACTION, PLAYER)
          2 | '_do_end_turn'              | (PLAYER)
          3 | '_do_kids_in_pool'          | (PLAYER)
          4 | '_do_senate'                | (PLAYER)
          5 | '_end_turn'                 | -
          6 | '_kids_in_pool'             | -
          7 | '_perform_clientele_action' | (PLAYER, ROLE)
          8 | '_perform_patron_action'    | (PLAYER)
          9 | '_perform_role_action'      | (PLAYER, ROLE)
         10 | '_perform_role_being_led'   | (PLAYER)
         11 | '_perform_thinker_action'   | (PLAYER)
         12 | '_take_turn_stacked'        | (PLAYER)

The mapping for function arguments uses offsets to separate the types of the
arguments. This is not strictly necessary, since the types of the arguments can
be inferred from the function name, but it requires no more space and can help
minimize ambiguity. The mapping is one-to-one, so the inverse mapping is used
for decoding.

    Stack frame function argument to integer mapping
        None: 0
        Player index N: (0x10 + N)
        Role in canonical numbering 0-5, R: (0x20 + R)
        GameAction as integer from cloaca.message, A: (0x30 + A)

Stack
-----
The Stack object is encoded simply as a list of frames, with
the number of frames first.
    
    <n_frames> (1 byte)
    <frame1> (Frame)
    ...
"""

import copy
import struct
from collections import Counter
import base64
from binascii import crc32

from cloaca.zone import Zone
from cloaca.building import Building
from cloaca.game import Game
from cloaca.card import Card
from cloaca.player import Player
from cloaca.stack import Stack, Frame

MAGIC_NUMBER = 0x89477452
NULLCODE = 0xFF;
ANONCARD = 0xFE;

class GTREncodingError(Exception):
    pass

def _encode_sites(sites):
    c = Counter(sites)
    return [c['Marble'], c['Rubble'], c['Concrete'], c['Wood'], c['Brick'], c['Stone']]

_MATERIALS = ['Marble', 'Rubble', 'Concrete', 'Wood', 'Brick', 'Stone']
def _decode_sites(list_of_counts):
    sites = []
    for count, material in zip(list_of_counts, _MATERIALS):
        sites.extend([material]*count)
    return sites


def _encode_visible_zone(obj):
    """Encode a zone of cards and return the bytestring."""
    cards = [ANONCARD if c.ident == -1 else c.ident for c in obj.cards]

    fmt = '!B'+str(len(cards))+'B'
    return struct.pack(fmt, len(cards), *cards)


def _encode_hidden_zone(obj):
    """Encode a zone that contains only anonymous cards and return the
    bytestring.
    """
    n_cards = len(obj.cards)

    fmt = '!BB'
    return struct.pack(fmt, n_cards, NULLCODE)


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

_MATERIAL_TO_INT = {
        'Marble':0, 'Rubble':1, 'Concrete':2,
        'Wood':3, 'Brick':4, 'Stone':5,
        None: NULLCODE
        }

_INT_TO_MATERIAL = {v:k for k,v in _MATERIAL_TO_INT.items()}
def site_to_int(site):
    return _MATERIAL_TO_INT[site]

def int_to_site(i):
    return _INT_TO_MATERIAL[i]


_INT_TO_STACK_FUNC = {v:k for k,v in _STACK_FUNC_TO_INT.items()}
def frame_func_to_int(func_name):
    return _STACK_FUNC_TO_INT[func_name]

def int_to_frame_func(i):
    return _INT_TO_STACK_FUNC[i]


_ROLE_TO_INT = {
        'Patron':0, 'Laborer':1, 'Architect':2,
        'Craftsman':3, 'Legionary':4, 'Merchant':5,
        None: NULLCODE
        }
_INT_TO_ROLE = {v:k for k,v in _ROLE_TO_INT.items()}
def role_to_int(role):
    return _ROLE_TO_INT[role]

def int_to_role(i):
    return _INT_TO_ROLE[i]


def _encode_frame_args(frame, players):
    """Convert the Frame arguments to numerical values using the 
    data from `game`. Return a list of the new args.
    """
    # Roles are strings, but in case they change to an enum or integer
    # represenation, we will not use that to distinguish from actions,
    # which are integers.
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
            if arg is None:
                newargs.append(0x26)
            else:
                new_args.append(0x20 + role_to_int(arg))
        elif arg_type == _ARG_ACTION:
            new_args.append(0x30 + arg)
        else:
            raise GTREncodingError('Unknown Frame argument type: '+str(arg_type))

    return new_args


def _decode_frame_args(args, function_name, players):
    """Convert frame args from the serialized (integer) types
    to python types. See `_encode_frame_args` for format.
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


def encode_zone(obj):
    """Encode a Zone object and return a bytestring.

    Zones with all anonymous cards are stored as only a length.

    See module documentation for format specification.
    """
    all_anon = next((False for c in obj.cards if not c.is_anon), True)
    visible = not(len(obj.cards) and all_anon)

    if visible:
        return _encode_visible_zone(obj)
    else:
        return _encode_hidden_zone(obj)


def decode_zone(buffer, offset):
    """Decode a Zone object from `buffer` starting at `offset` and
    return a tuple (<bytes>. <zone>) where <bytes> is the number of bytes
    consumed.
    """
    length = struct.unpack_from('!B', buffer, offset)[0]
    hidden = False
    if length:
        first_byte = struct.unpack_from('!B', buffer, offset+1)[0]

        hidden = (first_byte == NULLCODE)

    if hidden:
        return (2, Zone([Card(-1)]*length))
    else:
        idents = struct.unpack_from('!'+str(length)+'B', buffer, offset+1)
        cards = [Card(i) for i in idents]
        return (length+1, Zone(cards))


def encode_building(obj):
    """Encode a building object and return a bytestring.

    See module documentation for format specification.
    """
    mat_cards = [c.ident for c in obj.materials]
    mat_cards += [0]*(3-len(mat_cards))

    stairway_mat_cards = [c.ident for c in obj.stairway_materials]

    fmt = '!7B' + str(len(stairway_mat_cards)) + 'B'

    return struct.pack(fmt, 6+len(stairway_mat_cards),
            obj.foundation.ident,
            site_to_int(obj.site),
            int(obj.complete),
            *(mat_cards+stairway_mat_cards))


def decode_building(buffer, offset):
    """Decode a Building object from `buffer` starting at `offset` and
    return a tuple (<bytes>. <building>) where <bytes> is the total number
    of bytes consumed from the buffer.
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


def encode_frame(frame, players):
    """Encode a Frame object and return a bytestring.

    The list of players from this frame's game is needed to convert
    the function args. See module documentation for format specification.
    """
    if frame is None:
        return struct.pack('!B', 0)

    new_args = _encode_frame_args(frame, players)

    func_int = frame_func_to_int(frame.function_name)
    fmt = '!'+str(3+len(new_args))+'B'
    length = 2+len(new_args)

    return struct.pack(fmt, length, func_int, int(frame.executed), *new_args)
            

def decode_frame(buffer, offset, players):
    """Decode a stack frame. See `encode_frame` for format.

    Returns a tuple (<bytes>. <frame>) where <bytes> is the total number
    of bytes consumed from the buffer and <frame> is a Frame object.
    """
    length = struct.unpack_from('!B', buffer, offset)[0]

    if length == 0:
        return (1, None)

    fmt = '!'+str(length)+'B'
    values = struct.unpack_from(fmt, buffer, offset+1)
    function_name = int_to_frame_func(values[0])
    executed = bool(values[1])
    args = values[2:]

    new_args = _decode_frame_args(args, function_name, players)

    return (length+1, Frame(function_name, args=new_args, executed=executed))


def encode_player(obj):
    """Encode a Player object and return a bytestring.
    
    See module documentation for format specification.
    """
    chunks = []

    fmt = '!21pIBBB6B'

    if obj.fountain_card is None:
        fountain_int = NULLCODE;
    elif obj.fountain_card.is_anon:
        fountain_int = ANONCARD
    else:
        fountain_int = obj.fountain_card.ident

    chunks.append(struct.pack(fmt,
            obj.name,
            obj.uid,
            fountain_int,
            obj.n_camp_actions,
            obj.performed_craftsman,
            *_encode_sites(obj.influence)))

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


def decode_player(buffer, offset):
    """Decode a Player object from `buffer` starting at `offset` and
    return a tuple (<bytes>. <Player>) where <bytes> is the total number
    of bytes consumed from the buffer.
    """
    offset_orig = offset
    fmt = '!21pIBBB6B'

    values = struct.unpack_from(fmt, buffer, offset)
    offset += struct.calcsize(fmt)

    name = values[0]
    uid = values[1]
    if values[2] == ANONCARD:
        fountain_card = Card(-1)
    elif values[2] == NULLCODE:
        fountain_card = None
    else:
        fountain_card = Card(values[2])

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

    p = Player(uid=uid, name=name, hand=hand, stockpile=stockpile,
            clientele=clientele, vault=vault, camp=camp,
            fountain_card=fountain_card, n_camp_actions=n_camp_actions,
            buildings=buildings, influence=influence, revealed=revealed,
            prev_revealed=prev_revealed, clients_given=clients_given,
            performed_craftsman=performed_craftsman)

    return (offset-offset_orig, p)


def encode_stack(stack, players):
    """Encode a Stack object and return a bytestring.

    The list of Player objects from the Game this stack belongs to is required
    for serialization of the Frame arguments. See module documentation for
    format specification.
    """
    chunks = []
    chunks.append(struct.pack('!B', len(stack.stack)))
    for f in stack.stack:
        chunks.append(encode_frame(f, players))

    return ''.join(chunks)


def decode_stack(buffer, offset, players):
    offset_orig = offset

    fmt = '!B'
    n_stack_frames = struct.unpack_from(fmt, buffer, offset)[0]
    offset += struct.calcsize(fmt)

    stack_frames = []
    for i in range(n_stack_frames):
        length, f = decode_frame(buffer, offset, players)
        offset += length
        stack_frames.append(f)

    return (offset-offset_orig, Stack(stack_frames))


def decode_game(buffer, offset=0):
    """Decode and return a Game object from `buffer` starting at `offset`

    Returns a tuple (<bytes>. <game>) where <bytes> is the total number
    of bytes consumed from the buffer and <game> is a Game object.
    """
    fmt = '!III21pBBBBBBBB'
    offset = struct.calcsize(fmt)

    values = struct.unpack(fmt, buffer[:offset])

    game_id, turn_number, action_number, hostname, legionary_count, used_oot, \
            oot_allowed, role_led, expected_action, legionary_player_index, \
            leader_index, active_player_index = values

    used_oot = bool(used_oot)
    oot_allowed = bool(oot_allowed)
    role_led = int_to_role(role_led)
    
    if expected_action == NULLCODE: expected_action = None
    if legionary_player_index == NULLCODE: legionary_player_index = None
    if leader_index == NULLCODE: leader_index = None
    if active_player_index == NULLCODE: active_player_index = None

    fmt = '!6B'
    length = struct.calcsize(fmt)
    in_town_site_counts = struct.unpack(fmt, buffer[offset:offset+length])
    offset += length
    out_of_town_site_counts = struct.unpack(fmt, buffer[offset:offset+length])
    offset += length

    in_town_sites = _decode_sites(in_town_site_counts)
    out_of_town_sites = _decode_sites(out_of_town_site_counts)

    fmt = '!5B'
    length = struct.calcsize(fmt)
    winner_flags = struct.unpack(fmt, buffer[offset:offset+length])
    offset += length

    length, jacks = decode_zone(buffer, offset)
    jacks.name = 'jacks'
    offset += length

    length, library = decode_zone(buffer, offset)
    library.name = 'library'
    offset += length
    
    length, pool = decode_zone(buffer, offset)
    pool.name = 'pool'
    offset += length

    fmt = '!B'
    n_players = struct.unpack_from(fmt, buffer, offset)[0]
    offset += struct.calcsize(fmt)

    players = []
    for i in range(n_players):
        length, p = decode_player(buffer, offset)
        players.append(p)
        offset += length

    winners = _decode_winners(winner_flags, players)

    length, current_frame = decode_frame(buffer, offset, players)
    offset += length
    
    length, stack = decode_stack(buffer, offset, players)
    
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


def _encode_winners(winners, players):
    """Encode the winning player list and return a list of 5 flags."""
    if winners is None:
        return [0]*5

    flags = [0]*5
    for p in winners:
        flags[players.index(p)] = 1

    return flags


def _decode_winners(winner_flags, players):
    """Decode the list of flags and return a list of winning Player objects."""
    return [p for p, win in zip(players, winner_flags) if win]



def encode_game(obj):
    """Encode the game object and return a bytestring.

    See module documentation for format specification.
    """
    chunks = []

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
            obj.expected_action if obj.expected_action is not None else NULLCODE,
            obj.legionary_player_index if obj.legionary_player_index is not None else NULLCODE,
            obj.leader_index if obj.leader_index is not None else NULLCODE,
            obj.active_player_index if obj.active_player_index is not None else NULLCODE,
            ))
    
    fmt = '!6B6B5B'
    chunks.append(struct.pack(fmt,
            *(_encode_sites(obj.in_town_sites) +\
            _encode_sites(obj.out_of_town_sites) +\
            _encode_winners(obj.winners, obj.players))
            ))

    chunks.append(encode_zone(obj.jacks))
    chunks.append(encode_zone(obj.library))
    chunks.append(encode_zone(obj.pool))

    fmt = '!B'
    chunks.append(struct.pack(fmt, len(obj.players)))

    for p in obj.players:
        chunks.append(encode_player(p))

    chunks.append(encode_frame(obj._current_frame, obj.players))
    chunks.append(encode_stack(obj.stack, obj.players))


    game_bytes = ''.join(chunks)
    checksum = crc32(game_bytes)
    version = 1

    # crc32 returns an unsigned integer
    header = struct.pack('!IIi', MAGIC_NUMBER, version, checksum)

    return ''.join([header, game_bytes])


def game_to_str(game):
    """Convert Game object to string representation for storage or network
    transmission.
    """
    # print ''.join('{:02x}'.format(x) for x in bytearray(encode_game(game)))
    # print len(encode_game(game))
    return base64.b64encode(encode_game(game))


def decode_header(buffer):
    """Decode the header and return a tuple (magic_number, version, checksum).
    """


def str_to_game(s):
    try:
        bytestring = base64.b64decode(s)
    except TypeError as e:
        raise GTREncodingError('Invalid base64.')

    offset=0

    # Check magic number
    fmt='!I'
    try:
        magic_number = struct.unpack_from(fmt, bytestring, offset)[0]
    except struct.error as e:
        raise GTREncodingError('Error unpacking header: ' + e.message)

    offset += struct.calcsize(fmt)

    if magic_number != MAGIC_NUMBER:
        raise GTREncodingError('Decoding error: invalid record format')

    fmt = '!I'
    try:
        version = struct.unpack_from(fmt, bytestring, offset)[0]
    except struct.error as e:
        raise GTREncodingError('Error unpacking header: ' + e.message)
    offset += struct.calcsize(fmt)

    if version != 1:
        raise GTREncodingError('Decoding error: format version {0:d} unsupported'.format(version))

    fmt = '!i'
    try:
        record_checksum = struct.unpack_from(fmt, bytestring, offset)[0]
    except struct.error as e:
        raise GTREncodingError('Error unpacking header: ' + e.message)
    offset += struct.calcsize(fmt)

    computed_checksum = crc32(bytestring[offset:])
    if record_checksum != computed_checksum:
        raise GTREncodingError('Decoding error: checksum mismatch.')

    try:
        game = decode_game(bytestring[offset:])
    except struct.error as e:
        raise GTREncodingError('Error unpacking game: ' + e.message)

    return game

