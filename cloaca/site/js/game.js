define(['jquery', 'action_builder', 'games', 'display', 'net', 'util'],
function($, AB, Games, Display, Net, Util) {
    function Game(id, players) {
        this.id = id;
        this.display = new Display(id, Games.user, players);
    };

    // Build the game state HTML
    Game.prototype.initialize = function() {
        this.display.initialize();

        $('#refresh-btn').click(function() {
            Net.sendAction(this.id, null, Util.Action.REQGAMESTATE);
        }.bind(this));
    };
    
    // Reset buttons/cards to be unclickable, remove onclicks, blank
    // the dialog, etc.
    Game.prototype.resetUIElements = function() {
        var $btns = this.display.dialogBtns.find('button');
        $btns.off('click').hide().prop('disabled', true).removeClass('selected selectable');
        $('#deck, #jacks').off('click').removeClass('selectable');

        var $dialogBtns = $('#ok-cancel-btns > button');
        $dialogBtns.off('click').prop('disabled', true)
                   .removeClass('selected selectable')
                   .hide();

        var $cards = $('.card');
        $cards.removeClass('selected selectable').off('click');

        $('#dialog').text('Waiting for server...');
    };


    Game.prototype.updateState = function(gs) {
        console.log('GameState received');
        console.dir(gs);
        // the game state will be null if the game isn't started
        if (gs === null) {
            console.log("Game not started yet.");
            return;
        }
        var player_index = null;
        var active_player_index = null;
        for(var i=0; i<gs.players.length; i++) {
            if(gs.players[i].name === Games.user) {
                player_index = i;
            }
            active_player_index = gs.active_player_index;
        }

        var active_player = gs.players[active_player_index];

        this.id = gs.game_id;
        AB.playerIndex = player_index;

        this.resetUIElements();
        this.display.updateGameState(gs);

        current_game_id = Display.game_id;

        var game_over = (gs.winners !== null) && (gs.winners.length>0);
        if(game_over) {
            console.log('Game has ended.');
            $('#dialog').text('Game over!');
            return;
        }

        if(active_player_index !== player_index) {
            $('#dialog').text('Waiting on ' + active_player.name + '...');
            return;
        }

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

        if(gs.expected_action == Util.Action.THINKERORLEAD || gs.expected_action == Util.Action.LEADROLE) {
            var petitionMin = 3;
            var petitionMax = 3;
            var hasPalace = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Palace');
            var hasCircus = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Circus');
            if(hasCircus) {
                petitionMin = 2;
            }
            AB.leadRole(this.display, hasPalace, petitionMin, petitionMax, function(action, args) {
                if(action == Util.Action.THINKERTYPE) {
                    Net.sendAction(gs.game_id, gs.action_number, Util.Action.THINKERORLEAD, [true]);
                    // TODO: Check for latrine in here.
                    Net.sendAction(gs.game_id, gs.action_number+1, action, args);
                } else {
                    Net.sendAction(gs.game_id, gs.action_number, Util.Action.THINKERORLEAD, [false]);
                    Net.sendAction(gs.game_id, gs.action_number+1, Util.Action.LEADROLE, args);
                }
            });

        } else if(gs.expected_action == Util.Action.THINKERTYPE) {
            AB.thinkerType(this.display,
                    function(action, args) {
                        Net.sendAction(gs.game_id, gs.action_number,
                                Util.Action.THINKERTYPE, args);
                    }
            );

        } else if(gs.expected_action == Util.Action.FOLLOWROLE) {
            var roleLed = gs.role_led;
            var petitionMin = 3;
            var petitionMax = 3;
            var hasPalace = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Palace');
            var hasCircus = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Circus');
            if(hasCircus) {
                petitionMin = 2;
            }
            var invocations = 0;
            AB.followRole(this.display, roleLed, hasPalace, petitionMin, petitionMax,
                    function(action, args) {
                        Net.sendAction(gs.game_id, gs.action_number+invocations, action, args);
                        invocations += 1;
                    }
            );

        } else if (gs.expected_action == Util.Action.PATRONFROMHAND) {
            var limit = clienteleLimit[AB.playerIndex];
            function callback(card) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.PATRONFROMHAND, [card]);
            }
            if(gs.players[AB.playerIndex].clientele.length < limit) {
                AB.patronFromHand(this.display, limit, callback);
            } else {
                callback(null);
            }

        } else if (gs.expected_action == Util.Action.PATRONFROMPOOL) {
            var limit = clienteleLimit[AB.playerIndex];
            function callback(card) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.PATRONFROMPOOL, [card]);
            }
            if(gs.players[AB.playerIndex].clientele.length < limit) {
                AB.patronFromPool(this.display, limit, callback);
            } else {
               callback(null);
            }

        } else if (gs.expected_action == Util.Action.USELATRINE) {
            function callback(card) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.USELATRINE, [card]);
            }
            if(gs.players[AB.playerIndex].hand.length > 0) {
                AB.useLatrine(this.display, callback);
            } else {
                callback(null);
            }

        } else if (gs.expected_action == Util.Action.USESEWER) {
            AB.useSewer(this.display, function(cards) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.USESEWER, cards);
            });

        } else if (gs.expected_action == Util.Action.PATRONFROMDECK) {
            var limit = clienteleLimit[AB.playerIndex];
            function callback(useBar) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.PATRONFROMDECK, [useBar]);
            }
            if(gs.players[AB.playerIndex].clientele.length < limit) {
                AB.singleChoice(this.display, 'Patron from deck using Bar?',
                        [{text: 'Yes', result: true},
                         {text: 'No', result: false}
                        ], callback);
            } else {
                callback(false);
            }

        } else if (gs.expected_action == Util.Action.USEVOMITORIUM) {
            function callback(use) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.USEVOMITORIUM, [use]);
            }
            if(gs.players[AB.playerIndex].hand.length > 0) {
                AB.singleChoice(this.display,
                        'Discard hand before thinking with Vomitorium?',
                        [{text: 'Yes', result: true},
                         {text: 'No', result: false}
                        ], callback);
            } else {
                callback(false);
            }

        } else if (gs.expected_action == Util.Action.BARORAQUEDUCT) {
            function callback(use) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.BARORAQUEDUCT, [use]);
            }
            var hasNonJackInHand = false;
            var hand = gs.players[AB.playerIndex].hand;
            for(var i=0; i<hand.length; i++) {
                if(hand[i]>=6) { hasNonJackInHand = true; break; }
            }

            var limit = clienteleLimit[AB.playerIndex];
            if(gs.players[AB.playerIndex].clientele.length < limit && hasNonJackInHand) {
                AB.singleChoice(this.display, 'Patron first with Bar or Aqueduct?',
                        [{text: 'Bar', result: true},
                         {text: 'Aqueduct', result: false}
                        ], callback);
            } else {
                callback(true);
            };

        } else if (gs.expected_action == Util.Action.USEFOUNTAIN) {
            AB.singleChoice(this.display, 'Use Fountain to Craftsman from deck?',
                    [{text: 'Use Fountain', result: true},
                     {text: 'Skip', result: false}
                    ], function(use) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.USEFOUNTAIN, [use]);
            });

        } else if (gs.expected_action == Util.Action.SKIPTHINKER) {
            AB.singleChoice(this.display, 'Skip optional Thinker action?',
                    [{text: 'Thinker', result: false},
                     {text: 'Skip', result: true}
                    ], function(use) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.SKIPTHINKER, [use]);
            });

        } else if (gs.expected_action == Util.Action.USESENATE) {
            AB.useSenate(this.display, function(jacks) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.USESENATE, jacks);
            });

        } else if (gs.expected_action == Util.Action.LABORER) {
            var hasDock = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Dock');
            AB.laborer(this.display, hasDock, function(handCard, poolCard) {
                var cards = [];
                if(!(handCard === null)) {
                    cards.push(handCard);
                }
                if(!(poolCard === null)) {
                    cards.push(poolCard);
                }
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.LABORER, cards);
            });
        } else if (gs.expected_action == Util.Action.MERCHANT) {
            var hasBasilica = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Basilica');
            var hasAtrium = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Atrium');
            function callback(fromStockpile, fromHand, fromDeck) {
                var cards = [];
                if(!(fromHand === null)) {
                    cards.push(fromHand);
                }
                if(!(fromStockpile === null)) {
                    cards.push(fromStockpile);
                }
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.MERCHANT,
                    [fromDeck].concat(cards));
            };

            if(gs.players[AB.playerIndex].vault.length < vaultLimit[AB.playerIndex]) {
                AB.merchant(this.display, hasBasilica, hasAtrium, callback);
            } else {
                callback(null, null, false);
            }


        } else if (gs.expected_action == Util.Action.CRAFTSMAN) {
            var hasRoad = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Road');
            var hasTower = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Tower');
            var hasScriptorium = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Scriptorium');
            var ootAllowed = gs.oot_allowed;
            AB.craftsman(this.display, ootAllowed, hasRoad, hasTower, hasScriptorium,
                    function(building, material, site) {
                        Net.sendAction(gs.game_id, gs.action_number,
                            Util.Action.CRAFTSMAN,
                            [building, material, site]);
            });

        } else if (gs.expected_action == Util.Action.FOUNTAIN) {
            var hasRoad = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Road');
            var hasTower = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Tower');
            var hasScriptorium = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Scriptorium');
            var ootAllowed = gs.oot_allowed;
            var fountainCard = gs.players[AB.playerIndex].fountain_card;
            AB.fountain(this.display, fountainCard, ootAllowed, hasRoad, hasTower, hasScriptorium,
                    function(building, material, site) {
                        Net.sendAction(gs.game_id, gs.action_number,
                            Util.Action.FOUNTAIN,
                            [building, material, site]);
            });

        } else if (gs.expected_action == Util.Action.ARCHITECT) {
            var hasRoad = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Road');
            var hasTower = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Tower');
            var hasScriptorium = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Scriptorium');
            var hasArchway = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Archway');
            var ootAllowed = gs.oot_allowed;
            AB.architect(this.display, ootAllowed, hasRoad, hasTower,
                    hasScriptorium, hasArchway,
                    function(building, material, site, fromPool) {
                        Net.sendAction(gs.game_id, gs.action_number,
                            Util.Action.ARCHITECT,
                            [building, material, site]);
            });

        } else if (gs.expected_action == Util.Action.STAIRWAY) {
            var hasRoad = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Road');
            var hasTower = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Tower');
            var hasScriptorium = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Scriptorium');
            var hasArchway = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Archway');
            AB.stairway(this.display, hasRoad, hasTower, hasScriptorium,
                    hasArchway,
                    function(building, material) {
                        Net.sendAction(gs.game_id, gs.action_number,
                            Util.Action.STAIRWAY,
                            [building, material]);
            });

        } else if (gs.expected_action == Util.Action.PRISON) {
            AB.prison(this.display, function(building) {
                        Net.sendAction(gs.game_id, gs.action_number,
                            Util.Action.PRISON,
                            [building]);
            });

        } else if (gs.expected_action == Util.Action.LEGIONARY) {
            var revealed = gs.players[AB.playerIndex].prev_revealed;
            AB.legionary(this.display, gs.legionary_count, revealed, function(cards) {
                    Net.sendAction(gs.game_id, gs.action_number, Util.Action.LEGIONARY, cards);
            });

        } else if (gs.expected_action == Util.Action.GIVECARDS) {
            var hasBridge = Util.playerHasActiveBuilding(gs, gs.legionary_player_index, 'Bridge');
            var hasColiseum = Util.playerHasActiveBuilding(gs, gs.legionary_player_index, 'Coliseum');
            var hasPalisade = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Palisade');
            var hasWall = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Wall');
            var immune = hasWall || (hasPalisade && !hasBridge);
            var revealed = gs.players[gs.legionary_player_index].revealed;
            var materials = $.map(revealed, function(card) {
                return Util.cardProperties(card).material;
            });

            AB.giveCards(this.display, materials, hasBridge, hasColiseum, immune,
                    function(cards) {
                        Net.sendAction(gs.game_id, gs.action_number, Util.Action.GIVECARDS, cards);
                    }
            );
        } else if (gs.expected_action == Util.Action.TAKEPOOLCARDS) {
            var revealed = gs.players[gs.legionary_player_index].revealed;
            var materials = $.map(revealed, function(card) {
                return Util.cardProperties(card).material;
            });

            AB.takePoolCards(this.display, materials, function(cards) {
                        Net.sendAction(gs.game_id, gs.action_number, Util.Action.TAKEPOOLCARDS, cards);
                    }
            );
        } else {
            console.warn('Action unmatched : ' + gs.expected_action);
        }
    };

    return Game;
});
