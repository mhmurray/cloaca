define(['util', 'jquery', 'jqueryui'],
function(Util, $, _){
    function Display(record, username) {
        this.id = record.id;
        this.players = record.players;
        this.user = username;
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

        this.poolWrapper = Util.makeCardZone('game-'+id+'-pool', 'Pool');
        this.pool = this.poolWrapper.find('.card-container');

        var players = this.players;

        // List the user first, if possible
        var playerIndex = players.indexOf(this.user);
        if(playerIndex == -1) { playerIndex = 0; }
        var players_rotated = players.slice(playerIndex).concat(
                                players.slice(0, playerIndex));

        for(var i=0; i<players_rotated.length; i++) {
            var ip = ((playerIndex+i) % players_rotated.length) + 1;
            var $p = $('<div />').addClass('player-box').appendTo(this.playerInfo);
            var player = players_rotated[i];
            $p.html('<b>Player '+(ip)+': ' + player+'</b>');

            $p.append(Util.makeCardZone('game'+id+'-p'+ip+'-hand', 'Hand'));
            $p.append(Util.makeCardZone('game'+id+'-p'+ip+'-camp', 'Camp'));
            $p.append(Util.makeCardZone('game'+id+'-p'+ip+'-stockpile', 'Stockpile'));
            $p.append(Util.makeCardZone('game'+id+'-p'+ip+'-vault', 'Vault'));
            $p.append(Util.makeCardZone('game'+id+'-p'+ip+'-vault', 'Clientele'));

            var $influence = $('<div />', {
                id: 'game'+id+'-p'+ip+'-influence',
                class: 'influence'
            }).text('Influence');
            $p.append($influence);

            var buildingZone = $('<div />', {
                id: 'game'+id+'-p'+ip+'-buildings',
                class: 'building-container'
            }).text('Buildings');
            $p.append(buildingZone);

        };

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

        this.sites = $('<div/>').attr('id', 'sites-'+id)
                .addClass('sites-container');

        $.each(['Rubble', 'Wood', 'Concrete', 'Brick', 'Stone', 'Marble'],
                function(i, item) {
                    this.sites.append(Util.makeSitesStack(item, 0, 0));
                }.bind(this));

        // Dialog and control buttons
        this.dialogWrapper = $('<div>').addClass('dialog-wrapper');
        this.dialog = $('<div/>').addClass('dialog');
        this.dialogBtns = $('<div/>').append([
            $('<button/>').attr('id', 'okay-btn-'+id).text('OK'),
            $('<button/>').attr('id', 'cancel-btn-'+id).text('Cancel'),
            $('<button/>').attr('id', 'skip-btn-'+id).text('Skip'),
            $('<button/>').attr('id', 'petition-btn-'+id).text('Petition'),
            $('<button/>').attr('id', 'lead-role-btn-'+id).text('Lead a Role'),
            $('<button/>').attr('id', 'glory-btn-'+id).text('Glory to Rome!'),
        ]);
        var $roleBtns = $('<div/>').attr('id', 'role-select-'+id).append(
                $.map(
                    ['Patron', 'Laborer', 'Architect',
                        'Craftsman', 'Legionary', 'Merchant'],
                    function(role) {
                        var id = role.toLowerCase()+'-'+id;
                        var _class = Util.roleToMaterial(role).toLowerCase();
                        return $('<button/>').attr('id', id).text(role)
                                .addClass(_class).data('role', role);
                    }.bind(this))
        );

        this.dialogWrapper.append(this.dialog, this.dialogBtns.append($roleBtns));

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
        var is_started = gs.is_started;
        var turn_number = gs.turn_number;
        var library = gs.library.cards;
        var jack_pile = gs.jack_pile.cards;
        var players = gs.players;
        var leader_index = gs.leader_index;
        var leader = players[leader_index];
        var expected_action = gs.expected_action;
        console.log('Expected action from '+gs.active_player.name+
            ': ' + expected_action);
    
        /*
        function populateCardZone(zone, cards) {
            var $cardList = zone.children('.card-container');
            $cardList.empty();
            for(var j=0; j<cards.length; j++) {
                console.dir(Util.makeCard(cards[j].ident));
                $cardList.append(Util.makeCard(cards[j].ident));
            }
            console.dir($cardList);
            return zone;
        };
        */

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
                    var $span = this.sites.find('.site.'+material.toLowerCase()+' .site-count');
                    $span.text(in_town_counts[material]+'/'+out_of_town_counts[material]);
        }.bind(this));

        populateCardZone(this.pool, gs.pool.cards);

        for(var i=0; i<gs.players.length; i++) {
            var ip = i + 1;
            var player = gs.players[i];
            var prefix = 'game'+this.id+'-p'+ip+'-';
            $.map(['hand', 'camp', 'stockpile', 'vault', 'clientele'],
                    function(s) {
                        var z = populateCardZone($('#'+prefix+s), player[s].cards)
                    });

            var influence = player.influence;
            var $influence = $(prefix+'influence');
            for(var j=0; j<influence.length; j++) {
                $influence.append(Util.makeSite(influence[j]));
            }

            var buildings = player.buildings;
            var $buildings = $(prefix+'buildings');
            for(var j=0; j<buildings.length; j++) {
                var b = buildings[j];
                buildingZone.append(Util.makeBuilding(
                        prefix+'-building'+b.foundation.ident,
                        b.foundation.ident,
                        b.site,
                        b.materials.cards,
                        b.stairway_materials.cards,
                        b.complete
                ));
            }
        }

        $info = $('#gameinfo-'+id);
        $info.text('Game '+id+'   Turn #'+turn_number
                +'   Leader: '+leader['name']);

        $('#deck-'+id+' .pile-count').text(library.length);
        $('#jacks-'+id+' .pile-count').text(jack_pile.length);
        $('#deck-'+id).data({nCards: library.length});
        $('#jacks-'+id).data({nCards: jack_pile.length});

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
