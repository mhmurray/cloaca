define([],
function() {
    var Encode = {
    };

    function _base64ToArrayBuffer(base64) {
        var binary_string =  window.atob(base64);
        var len = binary_string.length;
        var bytes = new Uint8Array( len );
        for (var i = 0; i < len; i++)        {
                    bytes[i] = binary_string.charCodeAt(i);
                }
        return bytes.buffer;
    }

    function ab2str(buf) {
      return String.fromCharCode.apply(null, new Uint8Array(buf));
    }

    function int2role(i) {
        if(i === 0xFF) {
            return null;
        } else {
            return ['Patron', 'Laborer', 'Architect',
                'Craftsman', 'Legionary', 'Merchant'][i];
        }
    }

    function int2material(i) {
        if(i === 0xFF) {
            return null;
        } else {
            return ['Marble', 'Rubble', 'Concrete',
                'Wood', 'Brick', 'Stone'][i];
        }
    }

    function int2card(i) {
        return i === 0xFE ? -1 : i;
    }

    // Take an array of counts, eg. [0,0,1,5,0,0] and return a list of
    // material names with counts from the array. Materials are listed
    // in canonical order.
    function site_counts_to_strings(sites) {
        var site_strings = [];
        for(var i=0; i<6; i++) {
            var count = sites[i];
            for(var j=0; j<count; j++) {
                site_strings.push(int2material(i));
            }
        }

        return site_strings;
    }

    function decode_player(data, offset) {
        var offset_orig = offset;
        var name_length = data.getUint8(offset);
        offset+=1;
        var name_bytes = data.buffer.slice(offset, offset+name_length);
        var name = ab2str(name_bytes);
        offset+=20;

        var uid = data.getUint32(offset);
        offset+=4;

        var fountain_card_int = data.getUint8(offset);
        var fountain_card = fountain_card_int === 0xFF ? null : int2card(fountain_card_int);
        offset+=1;

        var n_actions = data.getUint8(offset);
        offset+=1;
        var performed_craftsman = Boolean(data.getUint8(offset));
        offset+=1;
        var influence_counts = Array.from(new Uint8Array(data.buffer, offset, 6));
        var influence = site_counts_to_strings(influence_counts);
        offset+=6;

        var zone_length;
        var zones = [];
        for(var i=0; i<9; i++) {
            zone_length = decode_zone(data, offset);
            zones.push(zone_length.zone);
            offset+=zone_length.length;
        }

        var n_buildings = data.getUint8(offset);
        offset+=1;

        var building_length;
        var buildings = [];
        for(var i=0; i<n_buildings; i++) {
            building_length = decode_building(data, offset);
            buildings.push(building_length.building);
            offset+=building_length.length;
        }

        return {
            length: offset-offset_orig,
            player: {
                name : name,
                uid : uid,
                fountain_card : fountain_card,
                n_camp_actions : n_actions,
                performed_craftsman : performed_craftsman,
                influence : influence,
                camp : zones[0].cards,
                hand : zones[1].cards.concat(zones[2].cards),
                stockpile : zones[3].cards,
                clientele : zones[4].cards,
                revealed : zones[5].cards,
                prev_revealed : zones[6].cards,
                clients_given : zones[7].cards,
                vault : zones[8].cards,
                buildings: buildings
            }
        };
    }

    function decode_zone(data, offset) {
        var length = data.getUint8(offset);
        offset+=1;
        var byte_length = 1;

        var cards = [];
        if(length !== 0) {
            var first_byte = data.getUint8(offset);
            if(first_byte === 0xFF) {
                cards = Array(length).fill(-1);
                byte_length+=1;
            } else {
                for(var i=0; i<length; i++) {
                    cards.push(int2card(data.getUint8(offset+i)));
                }
                byte_length+=length;
            }
        }

        return {
            length: byte_length,
            zone: {cards: cards}
        };
    }

    function decode_building(data, offset) {
        var length = data.getUint8(offset);
        offset+=1;
        var foundation = data.getUint8(offset);
        offset+=1;
        var site = int2material(data.getUint8(offset));
        offset+=1;
        var complete = Boolean(data.getUint8(offset));
        offset+=1;
        var mat1 = data.getUint8(offset);
        offset+=1;
        var mat2 = data.getUint8(offset);
        offset+=1;
        var mat3 = data.getUint8(offset);
        offset+=1;
        var stairway_materials = [];
        for(var i=6; i<length; i++) {
            var mat = data.getUint8(offset);
            offset+=1;
            stairway_materials.push(mat);
        }

        var materials = [];
        if(mat1 !== 0) { materials.push(mat1); }
        if(mat2 !== 0) { materials.push(mat2); }
        if(mat3 !== 0) { materials.push(mat3); }

        return {
            length : length+1,
            building : {
                foundation : foundation,
                site : site,
                complete : complete,
                materials : materials,
                stairway_materials : stairway_materials
            }
        }
    }

    function convert_frame_arg(arg, players) {
        if(arg === 0) {
            return null;
        } else if(arg >= 0x10 && arg < 0x20) {
            var player_index = arg-0x10;
            return players[player_index];
        } else if(arg >= 0x20 && arg < 0x30) {
            var role_id = arg-0x20;
            return int2role(role_id);
        } else {
            var action = arg-0x30;
            return action;
        }
    }

    var FUNCTION_NAMES = [
        '_advance_turn',
        '_await_action',
        '_do_end_turn',
        '_do_kids_in_pool',
        '_do_senate',
        '_end_turn',
        '_kids_in_pool',
        '_perform_clientele_action',
        '_perform_patron_action',
        '_perform_role_action',
        '_perform_role_being_led',
        '_perform_thinker_action',
        '_take_turn_stacked'
    ];

    function decode_frame(data, offset, players) {
        var length = data.getUint8(offset);
        offset+=1;
        var function_id = data.getUint8(offset);
        var function_name = FUNCTION_NAMES[function_id];
        offset+=1;

        var executed = Boolean(data.getUint8(offset));
        offset+=1;

        var args = [];
        for(var i=2; i<length; i++) {
            var arg_id = data.getUint8(offset);
            args.push(convert_frame_arg(arg_id, players));
            offset+=1
        }

        return {
            length: length+1,
            frame: {
                function_name: function_name,
                executed: executed,
                args: args
            }
        };
    }

    function decode_game(game_encoded_base64) {
        // Returns object {header, game} with basically the same structure
        // as the server-side game.
        var array = _base64ToArrayBuffer(game_encoded_base64);
        var data = new DataView(array);
        var offset = 0;
        var magic_number = data.getUint32(offset);
        offset+=4;
        var version = data.getUint32(offset);
        offset+=4;
        var crc32 = data.getUint32(offset);
        offset+=4;

        var game_id = data.getUint32(offset);
        offset+=4;
        var turn_number = data.getUint32(offset);
        offset+=4;
        var action_number = data.getUint32(offset);
        offset+=4;
        var hostname_length = data.getUint8(offset);
        offset+=1;
        var hostname_bytes = data.buffer.slice(offset, offset+hostname_length);
        var hostname = ab2str(hostname_bytes);
        offset+=20;
        var legionary_count = data.getUint8(offset);
        offset+=1;
        var used_oot = Boolean(data.getUint8(offset));
        offset+=1;
        var oot_allowed = Boolean(data.getUint8(offset));
        offset+=1;
        var role_led = int2role(data.getUint8(offset));
        offset+=1;
        var expected_action = data.getUint8(offset);
        offset+=1;
        var legionary_player_index = data.getUint8(offset);
        if(legionary_player_index === 0xFF) {
            legionary_player_index = null;
        }

        offset+=1;
        var leader_index = data.getUint8(offset);
        offset+=1;
        var active_player_index = data.getUint8(offset);
        offset+=1;
        var log_length = data.getUint32(offset);
        offset+=4;

        var in_town_site_counts = Array.from(new Uint8Array(data.buffer, offset, 6));
        var in_town_sites = site_counts_to_strings(in_town_site_counts);
        offset+=6;
        var out_of_town_site_counts = Array.from(new Uint8Array(data.buffer, offset, 6));
        var out_of_town_sites = site_counts_to_strings(out_of_town_site_counts);
        offset+=6;
        var winner_flags = Array.from(new Uint8Array(data.buffer, offset, 5));
        offset+=5;

        var zone_length;
        zone_length = decode_zone(data, offset);
        var jacks = zone_length.zone;
        offset+=zone_length.length;

        zone_length = decode_zone(data, offset);
        var library = zone_length.zone;
        offset+=zone_length.length;

        zone_length = decode_zone(data, offset);
        var pool = zone_length.zone;
        offset+=zone_length.length;

        var n_players = data.getUint8(offset);
        offset+=1;

        var players = [];
        for(var i=0; i<n_players; i++) {
            var player_length = decode_player(data, offset);
            players.push(player_length.player);
            offset+=player_length.length;
        }

        var frame_length = decode_frame(data, offset, players);
        var current_frame = frame_length.frame;
        offset+=frame_length.length;

        var n_stack_frames = data.getUint8(offset);
        offset+=1;

        var stack_frames = [];
        for(var i=0; i<n_stack_frames; i++) {
            var frame_length = decode_frame(data, offset, players);
            stack_frames.push(frame_length.frame);
            offset+=frame_length.length;
        }

        var winners = [];
        for(var i=0; i<winner_flags.length; i++) {
            if(winner_flags[i]) {
                winners.push(players[i]);
            }
        }

        return {
            header: {
                magic_number: magic_number,
                version: version,
                crc32: crc32,
            },
            game: {
                game_id: game_id,
                turn_number: turn_number,
                action_number: action_number,
                host: hostname,
                legionary_count: legionary_count,
                used_oot: used_oot,
                oot_allowed: oot_allowed,
                role_led: role_led,
                expected_action: expected_action,
                legionary_player_index: legionary_player_index,
                leader_index: leader_index,
                active_player_index: active_player_index,
                in_town_sites: in_town_sites,
                out_of_town_sites: out_of_town_sites,
                winners: winners,
                jacks: jacks.cards,
                library: library.cards,
                pool: pool.cards,
                players: players,
                _current_frame: current_frame,
                stack: {stack:stack_frames},
                log_length: log_length,
                game_log: []
            }
        };
    }


    // Decode a binary-encoded game encoded with base64
    Encode.decode_game = function(game_encoded_base64) {
        var game_header = decode_game(game_encoded_base64);
        header = game_header.header;
        game = game_header.game;

        return game;
    };

    return Encode;
});
