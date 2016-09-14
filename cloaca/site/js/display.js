define(['util', 'jquery', 'jqueryui'],
function(Util, $, _){
    function Display(id, username, players) {
        this.id = id;
        this.players = players;
        //this.id = record.id;
        //this.players = record.players;
        this.user = username;
    };

    // Return card objects from zone of player with specified index, counted from
    // 0, not 1. If the zone is 'pool', the player index doesn't mater.
    Display.prototype.zoneCards = function(zone, playerIndex) {
        if(zone === 'pool') {
            return $('#pool > .card');
        } else if(zone === 'sites') {
            return this.sites.children('.site');
        } else {
            return $('#p'+(playerIndex+1)+'-'+zone+'> .card');
        }
    };

    // Return container object from zone of player with specified index, counted from
    // 0, not 1. If the zone is 'pool', the player index doesn't mater.
    Display.prototype.zone = function(zone, playerIndex) {
        if(zone === 'pool') {
            return $('#pool');
        } else if(zone === 'sites') {
            return this.sites;
        } else {
            return $('#p'+(playerIndex+1)+'-'+zone);
        }
    };


    // Return buildings for given player index, zero-indexed
    Display.prototype.buildings = function(playerIndex) {
        return $('#p'+(playerIndex+1)+'-buildings > .building');
    };

    // Return the button using a title from 
    // refresh, exit, ok, cancel, skip, petition, lead-role, glory, 
    // patron, laborer, architect, craftsman, legionary, merchant
    Display.prototype.button = function(title) {
        return $('#'+title+'-btn');
    };

    // Return all role buttons.
    Display.prototype.roleButtons = function() {
        return $('#role-select > button');
    };

    Display.prototype.createPlayerZones = function() {
        var players = this.players;

        // List the user first, if possible
        var playerIndex = players.indexOf(this.user);
        if(playerIndex == -1) { playerIndex = 0; }

        this.playerZones = [];


        for(var i=0; i<players.length; i++) {
            var ip = i+1;

            var playerZones = {
                hand: Util.makeCardZone('p'+ip+'-hand', 'Hand'),
                camp: Util.makeCardZone('p'+ip+'-camp', 'Camp'),
                stockpile: Util.makeCardZone('p'+ip+'-stockpile', 'Stockpile'),
                vault: Util.makeCardZone('p'+ip+'-vault', 'Vault'),
                clientele: Util.makeCardZone('p'+ip+'-clientele', 'Clientele'),
                influence: Util.makeCardZone('p'+ip+'-influence', 'Influence')
            };

            /*
            playerZones.influence = $('<div />', {
                id: 'p'+ip+'-influence',
                class: 'influence'
            }).text('Influence');
            */

            playerZones.buildings = $('<div />', {
                id: 'p'+ip+'-buildings',
                class: 'building-container'
            }).text('Buildings');

            this.playerZones.push(playerZones);
        };

        for(var i=0; i<players.length; i++) {
            var i_rot = (i+playerIndex) % players.length;
            var ip = i_rot+1;

            var $p = $('<div />').addClass('player-box').appendTo(this.playerInfo);
            var player = players[i_rot];
            $p.html('<b>Player '+(ip)+': ' + player+'</b>');

            var playerZones = this.playerZones[i_rot];
            $p.append(playerZones.hand);
            $p.append(playerZones.camp);
            $p.append(playerZones.stockpile);
            $p.append(playerZones.vault);
            $p.append(playerZones.clientele);
            $p.append(playerZones.influence);
            $p.append(playerZones.buildings);
        };

    };


    // Adds game div to #page-wrapper and an anchor to the #tabs list.
    // Does not refresh the tab list.
    Display.prototype.initialize = function() {
        var $pageWrapper = $('#page-wrapper');
        var $tabList = $('#tabs > ul');

        this.gameWrapper = $('<div/>').attr('id', 'game-wrapper')
                .addClass('game-wrapper');
        this.cardsPanel = $('<div/>').addClass('cards-panel');

        this.gameControls = $('<div/>')
                .append($('<button/>', {
                    text: 'Refresh',
                    id: 'refresh-btn'}))
                .append($('<button/>', {
                    text: 'Close Game',
                    id: 'exit-btn'}));

        $('#refresh-btn').click(function() {
            Net.sendAction(this.id, Util.Action.REQGAMESTATE);
        }.bind(this));

        this.playerInfo = $('<div/>').attr('id', 'player-info');

        this.poolWrapper = Util.makeCardZone('pool', 'Pool');
        this.pool = this.poolWrapper.find('.card-container');

        this.createPlayerZones();

        // display for leader, turn, game id, etc.
        this.gameInfo = $('<div/>').attr('id', 'gameinfo');
        
        this.decks = $('<div/>').attr('id', 'decks').addClass('deck-container');
        this.deck = $('<div/>', {
            id: 'deck',
            class: 'pile orders',
            html: '<div class="pile-title">Deck</div>'+
                  '<div class="pile-count">0</div>'
        });
        this.jacks = $('<div/>', {
            id: 'jacks',
            class: 'pile jack',
            html: '<div class="pile-title">Jacks</div>'+
                  '<div class="pile-count">0</div>'
        });
        this.decks.append(this.deck, this.jacks);

        this.sites = $('<div/>').attr('id', 'sites')
                .addClass('sites-container');

        $.each(['Rubble', 'Wood', 'Concrete', 'Brick', 'Stone', 'Marble'],
                function(i, item) {
                    var _id = 'sites-'+item.toLowerCase();
                    this.sites.append(Util.makeSitesStack(_id, item, 0, 0));
                }.bind(this));

        // Dialog and control buttons
        this.dialogWrapper = $('<div>').attr('id', 'dialog-wrapper');
        this.dialog = $('<div/>').attr('id', 'dialog');
        this.dialogBtns = $('<div/>').append([
            $('<button/>').attr('id', 'ok-btn').text('OK'),
            $('<button/>').attr('id', 'cancel-btn').text('Cancel'),
            $('<button/>').attr('id', 'skip-btn').text('Skip'),
            $('<button/>').attr('id', 'petition-btn').text('Petition'),
            $('<button/>').attr('id', 'lead-role-btn').text('Lead a Role'),
            $('<button/>').attr('id', 'glory-btn').text('Glory to Rome!'),
        ]);
        this.roleBtns = $('<div/>').attr('id', 'role-select').append(
                $.map(
                    ['Patron', 'Laborer', 'Architect',
                        'Craftsman', 'Legionary', 'Merchant'],
                    function(role) {
                        var _id = role.toLowerCase()+'-btn';
                        var _class = Util.roleToMaterial(role).toLowerCase();
                        return $('<button/>').attr('id', _id).text(role)
                                .addClass(_class).data('role', role);
                    }.bind(this))
        );
        this.choiceBtns = $('<div/>').attr('id', '#choice-btns');

        this.dialogBtns.append(this.roleBtns, this.choiceBtns)
        this.dialogWrapper.append(this.dialog, this.dialogBtns);

        this.gameLog = $('<div/>').attr('id', 'log').addClass('log');

        this.cardsPanel.append(this.gameControls, this.poolWrapper, this.playerInfo);

        this.gameWrapper.append(
                this.cardsPanel, this.gameInfo,
                this.decks, this.sites, this.dialogWrapper, this.gameLog
                );

        $pageWrapper.append(this.gameWrapper);
        var $li = $('<li/>');
        $li.append($('<a/>').prop('href','#game-wrapper').text('Game '+this.id));

        $tabList.append($li);
    };

    Display.prototype.updateGameState = function(gs) {

        //Dev tools
        $('#gamestate-copy').text('GameState:\n'+JSON.stringify(gs, null, 2));

        if(this.id !== gs.game_id) {
            alert('Mismatched game ids during update: '+id+'!='+gs.game_id);
        }
        var is_started = gs.turn_number > 0;
        var turn_number = gs.turn_number;
        var library = gs.library;
        var jacks = gs.jacks;
        var players = gs.players;
        var leader_index = gs.leader_index;
        var leader = players[leader_index];
        var expected_action = gs.expected_action;
        var active_player = gs.players[gs.active_player_index]

        function populateCardZone(zone, cards) {
            zone.empty();
            for(var j=0; j<cards.length; j++) {
                zone.append(Util.makeCard(cards[j]));
            }
            return zone;
        };


        var playerInfluence = [];

        for(var i=0; i<gs.players.length; i++) {
            var influence = gs.players[i].influence;
            var points = { Rubble: 1, Wood: 1, Concrete: 2, Brick: 2, Stone: 3, Marble: 3};
            var playerPoints = 2;
            for(var j=0; j<influence.length; j++) {
                playerPoints += points[influence[j]];
            }
            playerInfluence.push(playerPoints);
        }


        var clienteleLimit = [];
        for(var i=0; i<gs.players.length; i++) {
            var limit = playerInfluence[i];
            if(Util.playerHasActiveBuilding(gs, i, 'Insula')) {
                limit += 2;
            }
            if(Util.playerHasActiveBuilding(gs, i, 'Aqueduct')) {
                limit *= 2;
            }
            clienteleLimit.push(limit);
        }

        var vaultLimit = [];
        for(var i=0; i<gs.players.length; i++) {
            var limit = playerInfluence[i];
            if(Util.playerHasActiveBuilding(gs, i, 'Market')) {
                limit += 2;
            }
            vaultLimit.push(limit);
        }

        var visibleScore = [];
        for(var i=0; i<gs.players.length; i++) {
            var score = playerInfluence[i];
            if(Util.playerHasActiveBuilding(gs, i, 'Statue')) {
                score += 3;
            }
            if(Util.playerHasActiveBuilding(gs, i, 'Wall')) {
                wallScore = Math.floor(gs.players[i].stockpile.length/2);
                score += wallScore;
            }
            visibleScore.push(score);
        }


        var in_town_counts = {
            Rubble : 0,
            Wood : 0,
            Concrete : 0,
            Brick : 0,
            Marble : 0,
            Stone : 0,
        };
        var out_of_town_counts = $.extend({}, in_town_counts); // shallow copy
        
        var accumulate = function(counts, x) { counts[x]+=1; return counts; };

        gs.in_town_sites.reduce(accumulate, in_town_counts);
        gs.out_of_town_sites.reduce(accumulate, out_of_town_counts);

        $.each(['Rubble', 'Wood', 'Concrete', 'Brick', 'Stone', 'Marble'],
                function(i, material) {
                    var $site = this.zoneCards('sites').filter('.'+material.toLowerCase());
                    var $count = $site.children('.site-count');
                    $count.text(in_town_counts[material]+'/'+out_of_town_counts[material]);
                    $site.data({
                        inTown: in_town_counts[material],
                        outOfTown: out_of_town_counts[material]
                    });
        }.bind(this));

        populateCardZone(this.pool, gs.pool);

        this.playerInfo.empty();
        this.createPlayerZones();

        for(var i=0; i<gs.players.length; i++) {
            var zones = this.playerZones[i];
            var ip = i + 1;
            var player = gs.players[i];
            var prefix = 'p'+ip+'-';
            $.map(['hand', 'camp', 'stockpile', 'vault', 'clientele'],
                    function(s) {
                        var z = populateCardZone(this.zone(s, i), player[s])
                    }.bind(this));

            var influence = player.influence;
            //var $influence = zones.influence;
            var $influence = this.zone('influence', i);
            $influence.empty();
            for(var j=0; j<influence.length; j++) {
                value = Util.materialToValue(influence[j]);

                $site = Util.makeSite(influence[j]);
                $site.text(value.toString());

                $influence.append($site);
            }

            $('#'+prefix+'clientele-title').text(
                    'Clientele ('+player.clientele.length+'/'+clienteleLimit[i]+')');
            $('#'+prefix+'vault-title').text(
                    'Vault ('+player.vault.length+'/'+vaultLimit[i]+')');
            $('#'+prefix+'influence-title').text(
                    'Influence ('+visibleScore[i]+')');

            var buildings = player.buildings;
            var $buildings = zones.buildings;
            $buildings.empty();
            for(var j=0; j<buildings.length; j++) {
                var b = buildings[j];
                var $building = Util.makeBuilding(
                        prefix+'building'+b.foundation,
                        b.foundation,
                        b.site,
                        b.materials,
                        b.stairway_materials,
                        b.complete
                );
                if(Util.playerHasActiveBuilding(gs, i, Util.cardName(b.foundation))) {
                    $building.addClass('active');
                }

                $buildings.append($building);
            }
        }

        this.gameInfo.text('Game '+this.id+'   Turn #'+turn_number
                +'   Leader: '+leader['name']);

        this.deck.children('.pile-count').text(library.length);
        this.deck.data({nCards: library.length});
        this.jacks.children('.pile-count').text(jacks.length);
        this.jacks.data({nCards: jacks.length});

        this.gameLog.html(gs.game_log.join('<br>'));
        this.gameLog[0].scrollTop = this.gameLog[0].scrollHeight;
                        
        $('.card-container').sortable({
            tolerance: 'intersect',
            //connectWith: $('.card-container') // Drag-and-drop
        });
        $('.card-container').disableSelection();
    };

    return Display;
});
