define(['util', 'jquery', 'jqueryui'],
function(Util, $, _){
    function Display(record, username) {
        this.id = record.id;
        this.players = record.players;
        this.user = username;
    };

    // Return card objects from zone of player with specified index, counted from
    // 1, not 0. If the zone is 'pool', the player index doesn't mater.
    Display.prototype.zoneCards = function(zone, playerIndex) {
        if(zone === 'pool') {
            return $('#game'+this.id+'-pool > .card');
        } else if(zone === 'sites') {
            return this.sites.children('.site');
        } else {
            return $('#game'+this.id+'-p'+playerIndex+'-'+zone+'> .card');
        }
    };

    // Return container object from zone of player with specified index, counted from
    // 1, not 0. If the zone is 'pool', the player index doesn't mater.
    Display.prototype.zone = function(zone, playerIndex) {
        if(zone === 'pool') {
            return $('#game'+this.id+'-pool');
        } else if(zone === 'sites') {
            return this.sites;
        } else {
            return $('#game'+this.id+'-p'+playerIndex+'-'+zone);
        }
    };

    // Return the button using a title from 
    // refresh, exit, ok, cancel, skip, petition, lead-role, glory, 
    // patron, laborer, architect, craftsman, legionary, merchant
    Display.prototype.button = function(title) {
        return $('#'+title+'-btn-'+this.id);
    };

    // Return all role buttons.
    Display.prototype.roleButtons = function() {
        return $('#role-select-'+this.id+' > button');
    };

    Display.prototype.createPlayerZones = function() {
        var players = this.players;
        var id = this.id;

        // List the user first, if possible
        var playerIndex = players.indexOf(this.user);
        if(playerIndex == -1) { playerIndex = 0; }

        this.playerZones = [];


        for(var i=0; i<players.length; i++) {
            var ip = i+1;

            var playerZones = {
                hand: Util.makeCardZone('game'+id+'-p'+ip+'-hand', 'Hand'),
                camp: Util.makeCardZone('game'+id+'-p'+ip+'-camp', 'Camp'),
                stockpile: Util.makeCardZone('game'+id+'-p'+ip+'-stockpile', 'Stockpile'),
                vault: Util.makeCardZone('game'+id+'-p'+ip+'-vault', 'Vault'),
                clientele: Util.makeCardZone('game'+id+'-p'+ip+'-clientele', 'Clientele')
            };

            playerZones.influence = $('<div />', {
                id: 'game'+id+'-p'+ip+'-influence',
                class: 'influence'
            }).text('Influence');

            playerZones.buildings = $('<div />', {
                id: 'game'+id+'-p'+ip+'-buildings',
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
        var id = this.id;
        var $pageWrapper = $('#page-wrapper');
        var $tabList = $('#tabs > ul');

        this.gameWrapper = $('<div/>').attr('id', 'game-wrapper-'+id)
                .addClass('game-wrapper');
        this.cardsPanel = $('<div/>').addClass('cards-panel');

        this.gameControls = $('<div/>')
                .append($('<button/>', {
                    text: 'Refresh',
                    id: 'refresh-btn-'+id}))
                .append($('<button/>', {
                    text: 'Close Game',
                    id: 'exit-btn-'+id}));

        $('#refresh-btn-'+id).click(function() {
            Net.sendAction(id, Util.Action.REQGAMESTATE);
        }.bind(this));

        this.playerInfo = $('<div/>').attr('id', 'player-info-'+id);

        this.poolWrapper = Util.makeCardZone('game'+id+'-pool', 'Pool');
        this.pool = this.poolWrapper.find('.card-container');

        this.createPlayerZones();

        // display for leader, turn, game id, etc.
        this.gameInfo = $('<div/>').attr('id', 'gameinfo-'+id);
        
        this.decks = $('<div/>').attr('id', 'decks-'+id).addClass('deck-container');
        this.deck = $('<div/>', {
            id: 'deck-'+id,
            class: 'pile orders',
            html: '<div class="pile-title">Deck</div>'+
                  '<div class="pile-count">0</div>'
        });
        this.jacks = $('<div/>', {
            id: 'jacks-'+id,
            class: 'pile jack',
            html: '<div class="pile-title">Jacks</div>'+
                  '<div class="pile-count">0</div>'
        });
        this.decks.append(this.deck, this.jacks);

        this.sites = $('<div/>').attr('id', 'game'+id+'-sites-'+id)
                .addClass('sites-container');

        $.each(['Rubble', 'Wood', 'Concrete', 'Brick', 'Stone', 'Marble'],
                function(i, item) {
                    var _id = 'game'+id+'-sites-'+item.toLowerCase();
                    this.sites.append(Util.makeSitesStack(_id, item, 0, 0));
                }.bind(this));

        // Dialog and control buttons
        this.dialogWrapper = $('<div>').addClass('dialog-wrapper');
        this.dialog = $('<div/>').addClass('dialog');
        this.dialogBtns = $('<div/>').append([
            $('<button/>').attr('id', 'ok-btn-'+id).text('OK'),
            $('<button/>').attr('id', 'cancel-btn-'+id).text('Cancel'),
            $('<button/>').attr('id', 'skip-btn-'+id).text('Skip'),
            $('<button/>').attr('id', 'petition-btn-'+id).text('Petition'),
            $('<button/>').attr('id', 'lead-role-btn-'+id).text('Lead a Role'),
            $('<button/>').attr('id', 'glory-btn-'+id).text('Glory to Rome!'),
        ]);
        this.roleBtns = $('<div/>').attr('id', 'role-select-'+id).append(
                $.map(
                    ['Patron', 'Laborer', 'Architect',
                        'Craftsman', 'Legionary', 'Merchant'],
                    function(role) {
                        var _id = role.toLowerCase()+'-btn-'+id;
                        var _class = Util.roleToMaterial(role).toLowerCase();
                        return $('<button/>').attr('id', _id).text(role)
                                .addClass(_class).data('role', role);
                    }.bind(this))
        );
        this.choiceBtns = $('<div/>').attr('id', '#choice-btns-'+id);

        this.dialogBtns.append(this.roleBtns, this.choiceBtns)
        this.dialogWrapper.append(this.dialog, this.dialogBtns);

        this.gameLog = $('<div/>').attr('id', 'log-'+id).addClass('log');

        this.cardsPanel.append(this.gameControls, this.poolWrapper, this.playerInfo);

        this.gameWrapper.append(
                this.cardsPanel, this.gameInfo,
                this.decks, this.sites, this.dialogWrapper, this.gameLog
                );

        $pageWrapper.append(this.gameWrapper);
        var $li = $('<li/>');
        $li.append($('<a/>').prop('href','#game-wrapper-'+id).text('Game '+id));

        $tabList.append($li);
    };

    Display.prototype.updateGameState = function(gs) {
        var id = this.id;

        //Dev tools
        $('#gamestate-copy').text('GameState:\n'+JSON.stringify(gs, null, 2));

        if(id !== gs.game_id) {
            alert('Mismatched game ids during update: '+id+'!='+gs.game_id);
        }
        var is_started = gs.turn_number > 0;
        var turn_number = gs.turn_number;
        var library = gs.library.cards;
        var jacks = gs.jacks.cards;
        var players = gs.players;
        var leader_index = gs.leader_index;
        var leader = players[leader_index];
        var expected_action = gs.expected_action;
        console.log('Expected action from '+gs.active_player.name+
            ': ' + expected_action);

        this.players = players;

        function populateCardZone(zone, cards) {
            zone.empty();
            for(var j=0; j<cards.length; j++) {
                zone.append(Util.makeCard(cards[j].ident));
            }
            return zone;
        };


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

        populateCardZone(this.pool, gs.pool.cards);

        this.playerInfo.empty();
        this.createPlayerZones();

        for(var i=0; i<gs.players.length; i++) {
            var zones = this.playerZones[i];
            var ip = i + 1;
            var player = gs.players[i];
            var prefix = 'game'+this.id+'-p'+ip+'-';
            $.map(['hand', 'camp', 'stockpile', 'vault', 'clientele'],
                    function(s) {
                        var z = populateCardZone(this.zone(s, ip), player[s].cards)
                    }.bind(this));

            var influence = player.influence;
            var $influence = zones.influence;
            $influence.empty();
            for(var j=0; j<influence.length; j++) {
                $influence.append(Util.makeSite(influence[j]));
            }

            var buildings = player.buildings;
            var $buildings = zones.buildings;
            $buildings.empty();
            for(var j=0; j<buildings.length; j++) {
                var b = buildings[j];
                $buildings.append(Util.makeBuilding(
                        prefix+'-building'+b.foundation.ident,
                        b.foundation.ident,
                        b.site,
                        b.materials.cards,
                        b.stairway_materials.cards,
                        b.complete
                ));
            }
        }

        this.gameInfo.text('Game '+id+'   Turn #'+turn_number
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
