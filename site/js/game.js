define(['jquery', 'action_builder', 'games', 'display', 'net', 'util'],
function($, AB, Games, Display, Net, Util) {
    function Game(record, user) {
        this.id = record.id;
        this.players = record.players;
        this.user = user;
        this.gs = null;
        this.display = new Display(Games.records[this.id], Games.user);
    };

    // Build the game state HTML
    Game.prototype.initialize = function() {
        this.display.initialize();
    };
    
    // Reset buttons/cards to be unclickable, remove onclicks, blank
    // the dialog, etc.
    Game.prototype.resetUIElements = function() {
            var $btns = $('#role-select').find('button');
            $btns.hide().prop('disabled', true).removeClass('selected selectable');
            $('#deck,#jacks').off('click').removeClass('selectable');

            var $dialogBtns = $('#ok-cancel-btns > button');
            $dialogBtns.off('click').prop('disabled', true)
                       .removeClass('selected selectable')
                       .hide();

            var $cards = $('.card');
            $cards.removeClass('selected selectable').off('click');

            $('#dialog').text('Waiting for server...');
    };


    Game.prototype.updateState = function(gs) {
        // the game state will be null if the game isn't started
        if (!gs) {
            console.log("Game not started yet.");
            return;
        }
        var player_index = null;
        var active_player_index = null;
        for(var i=0; i<gs.players.length; i++) {
            if(gs.players[i].name === Games.user) {
                player_index = i;
            }
            if(gs.active_player.name === gs.players[i].name){
                active_player_index = i;
            }
        }

        /*
        var gameRecord = {
            gameState: gs,
            playerIndex: player_index
        };
        Games.games[gs.game_id] = gameRecord;
        */

        this.id = gs.game_id;
        AB.playerIndex = player_index;

        this.resetUIElements();
        this.display.updateGameState(gs);

        current_game_id = Display.game_id;

        if(active_player_index !== player_index) {
            $('#dialog').text('Waiting on ' + gs.active_player.name + '...');
            console.log('Waiting on ' + gs.active_player.name + '...');
            return;
        }

        if(gs.expected_action == Util.Action.THINKERORLEAD) {
            var petitionMin = 3;
            var petitionMax = 3;
            var hasPalace = false;
            AB.leadRole(hasPalace, petitionMin, petitionMax, function(action, args) {
                if(action == Util.Action.THINKERTYPE) {
                    Net.sendAction(gs.game_id, Util.Action.THINKERORLEAD, [true]);
                    Net.sendAction(gs.game_id, action, args);
                } else {
                    Net.sendAction(gs.game_id, Util.Action.THINKERORLEAD, [false]);
                    Net.sendAction(gs.game_id, Util.Action.LEADROLE, args);
                }
            });

        } else if(gs.expected_action == Util.Action.FOLLOWROLE) {
            var roleLed = gs.role_led;
            var petitionMin = 3;
            var petitionMax = 3;
            var hasPalace = false;
            console.log('Follow role!');
            AB.followRole(roleLed, hasPalace, petitionMin, petitionMax,
                    function(action, args) {
                        Net.sendAction(gs.game_id, action, args);
                    }
            );

        } else if (gs.expected_action == Util.Action.PATRONFROMHAND) {
            AB.patronFromHand(function(card) {
                Net.sendAction(gs.game_id, Util.Action.PATRONFROMHAND, [card]);
            });

        } else if (gs.expected_action == Util.Action.PATRONFROMPOOL) {
            AB.patronFromPool(function(card) {
                Net.sendAction(gs.game_id, Util.Action.PATRONFROMPOOL, [card]);
            });

        } else if (gs.expected_action == Util.Action.USELATRINE) {
            AB.patronFromPool(function(card) {
                Net.sendAction(gs.game_id, Util.Action.USELATRINE, [card]);
            });

        } else if (gs.expected_action == Util.Action.USESEWER) {
            AB.useSewer(function(cards) {
                Net.sendAction(gs.game_id, Util.Action.USESEWER, cards);
            });

        } else if (gs.expected_action == Util.Action.PATRONFROMDECK) {
            AB.singleChoice('Patron from deck using Bar?',
                    [{text: 'Yes', return: true},
                     {text: 'No', return: false}
                    ], function(useBar) {
                Net.sendAction(gs.game_id, Util.Action.PATRONFROMDECK, [useBar]);
            });

        } else if (gs.expected_action == Util.Action.USEVOMITORIUM) {
            AB.singleChoice('Discard hand before thinking with Vomitorium?',
                    [{text: 'Yes', return: true},
                     {text: 'No', return: false}
                    ], function(use) {
                Net.sendAction(gs.game_id, Util.Action.USEVOMITORIUM, [use]);
            });

        } else if (gs.expected_action == Util.Action.BARORAQUEDUCT) {
            AB.singleChoice('Patron first with Bar or Aqueduct?',
                    [{text: 'Bar', return: true},
                     {text: 'Aqueduct', return: false}
                    ], function(use) {
                Net.sendAction(gs.game_id, Util.Action.BARORAQUEDUCT, [use]);
            });

        } else if (gs.expected_action == Util.Action.USEFOUNTAIN) {
            AB.singleChoice('Use Fountain to Craftsman from deck?',
                    [{text: 'Use Fountain', return: true},
                     {text: 'Skip', return: false}
                    ], function(use) {
                Net.sendAction(gs.game_id, Util.Action.USEFOUNTAIN, [use]);
            });

        } else if (gs.expected_action == Util.Action.SKIPTHINKER) {
            AB.singleChoice('Skip optional Thinker action?',
                    [{text: 'Thinker', return: false},
                     {text: 'Skip', return: true}
                    ], function(use) {
                Net.sendAction(gs.game_id, Util.Action.SKIPTHINKER, [use]);
            });

        } else if (gs.expected_action == Util.Action.USESENATE) {
            AB.singleChoice('Take opponent\'s Jack with Senate?',
                    [{text: 'Yes', return: true},
                     {text: 'No', return: false}
                    ], function(use) {
                Net.sendAction(gs.game_id, Util.Action.USESENATE, [use]);
            });

        } else if (gs.expected_action == Util.Action.LABORER) {
            var hasDock = false;
            AB.laborer(hasDock, function(handCard, poolCard) {
                Net.sendAction(gs.game_id, Util.Action.LABORER, [handCard, poolCard]);
            });
        } else if (gs.expected_action == Util.Action.MERCHANT) {
            var hasBasilica = false;
            var hasAtrium = false;
            AB.merchant(hasBasilica, hasAtrium,
                    function(stockpileCard, handCard, fromDeck) {
                Net.sendAction(gs.game_id, Util.Action.MERCHANT,
                    [stockpileCard, handCard, fromDeck]);
            });
        } else if (gs.expected_action == Util.Action.CRAFTSMAN) {
            var hasFountain = false;
            var hasRoad = false;
            var hasTower = false;
            var hasScriptorium = false;
            var ootAllowed = gs.oot_allowed;
            AB.craftsman(ootAllowed, hasRoad, hasTower, hasScriptorium,
                    function(building, material, site) {
                        Net.sendAction(gs.game_id,
                            Util.Action.CRAFTSMAN,
                            [building, material, site]);
            });
        } else if (gs.expected_action == Util.Action.ARCHITECT) {
            var hasFountain = false;
            var hasRoad = false;
            var hasTower = false;
            var hasScriptorium = false;
            var hasArchway = false;
            var ootAllowed = gs.oot_allowed;
            AB.architect(ootAllowed, hasRoad, hasTower,
                    hasScriptorium, hasArchway,
                    function(building, material, site, fromPool) {
                        Net.sendAction(gs.game_id,
                            Util.Action.ARCHITECT,
                            [building, material, site, fromPool]);
            });

        } else if (gs.expected_action == Util.Action.LEGIONARY) {
            AB.legionary(gs.legionary_count, function(cards) {
                    Net.sendAction(gs.game_id, Util.Action.LEGIONARY, cards);
            });

        } else if (gs.expected_action == Util.Action.GIVECARDS) {
            var hasBridge = false;
            var hasColiseum = false;
            var immune = false;
            var revealed = gs.players[gs.legionary_index].revealed.cards;
            var materials = $.map(revealed, function(card) {
                console.dir(card);
                console.log(card);
                return Util.cardProperties(card.ident).material;
            });

            AB.giveCards(materials, hasBridge, hasColiseum, immune,
                    function(cards) {
                        Net.sendAction(gs.game_id, Util.Action.GIVECARDS, cards);
                    }
            );
        } else {
            console.warn('Action unmatched : ' + gs.expected_action);
        }
    };

    return Game;
});
