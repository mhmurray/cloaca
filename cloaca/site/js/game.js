define(['jquery', 'jquerywaypoints', 'action_builder', 'games', 'display', 'net', 'util'],
function($, _, AB, Games, Display, Net, Util) {
    function Game(id, players) {
        this.id = id;
        this.display = new Display(id, Games.user, players);
        this.game_log = [];
        this.requested_log_messages = false;
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


    // Check whether more log messages are needed.
    // Return -1 if none are needed, or the index of the
    // most recent missing message.
    Game.prototype.checkLogNeeded = function() {
        var last_null = this.game_log.lastIndexOf(null);
        if(last_null === -1) {
            return -1;
        } else if(this.game_log.length - last_null > 50) {
            return -1;
        } else {
            return last_null;
        }
    };

    Game.prototype.updateLog = function(n_total, n_start, messages) {
        // Add null values for missing + new messages
        for(var i=this.game_log.length; i<n_total; i++) {
            this.game_log.push(null);
        }
        // Set new messages to received values.
        for(var i=0; i<messages.length; i++) {
            this.game_log[i+n_start] = messages[i];
        }
        this.drawLog();
        var first_missing = this.checkLogNeeded();
        if(first_missing === -1) {
            this.requested_log_messages = false;
        } else if(!this.requested_log_messages) {
            this.requestLogMessages(50, Math.max(0,first_missing-49));
        } else {
            console.debug('Backing off of log requests');
        }
    };

    Game.prototype.requestLogMessages = function(n_messages, n_start) {
        console.log('Requesting more ', n_messages, 'more log messages, starting at', n_start);
        Net.sendAction(this.id, null, Util.Action.REQGAMELOG, [n_messages, n_start]);
        this.requested_log_messages = true;
    };

    Game.prototype.drawLog = function() {
        var els = [];
        var first_missing = this.game_log.lastIndexOf(null);
        for(var i=first_missing+1; i<this.game_log.length; i++) {
            els.push($('<li />').text(this.game_log[i]));
        }
        this.display.gameLog.empty();
        this.display.gameLog.append(els);
        this.display.gameLogWrapper.scrollTop(this.display.gameLogWrapper[0].scrollHeight);
        if(this.display.log_waypoints !== null) {
            for(var i=0; i<this.display.log_waypoints.length; i++) {
                this.display.log_waypoints[i].destroy();
            }
        }
        if(first_missing === -1 || this.game_log.length-first_missing < 50) return;
        var this_game = this;
        var wp = new Waypoint({
            element: this_game.display.gameLog.children()[0],
            handler: function(direction) {
                if(direction === 'down') return;
                var first_missing = this_game.game_log.lastIndexOf(null);
                if(first_missing === -1) {
                    this.disable();
                    return;
                }

                this_game.requestLogMessages(first_missing+1, 0);
                this.disable();
            },
            context: this_game.display.gameLogWrapper[0]
        });
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

        if(this.game_log.length === 0) {
            this.requestLogMessages(0, 0);
            this.requested_log_messages = false;
        }

        var game_over = (gs.winners !== null) && (gs.winners.length>0);
        if(game_over) {
            console.log('Game has ended.');
            $('#dialog').text('Game over!');
            return;
        }

        if(active_player_index === player_index) {
            document.title = 'Your turn!'
        } else {
            document.title = 'GtR'
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

        if(gs.expected_action === Util.Action.THINKERORLEAD 
                || gs.expected_action === Util.Action.SKIPTHINKER
                || gs.expected_action === Util.Action.LEADROLE
                || gs.expected_action === Util.Action.USELATRINE
                || gs.expected_action === Util.Action.USEVOMITORIUM)
        {
            var petitionMin = 3;
            var petitionMax = 3;
            var hasPalace = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Palace');
            var hasCircus = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Circus');
            var hasLatrine = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Latrine');
            var hasVomitorium = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Vomitorium');
            if(hasCircus) {
                petitionMin = 2;
            }
            AB.leadRole(this.display, hasPalace, hasLatrine, hasVomitorium,
                petitionMin, petitionMax, gs.expected_action,
                function(actions) {
                    var complete_actions = [];
                    var a_num = gs.action_number;

                    if(gs.expected_action === Util.Action.SKIPTHINKER
                            && actions[0][0] !== Util.Action.SKIPTHINKER) {
                        complete_actions.push(
                                [gs.game_id, a_num,
                                    Util.Action.SKIPTHINKER, [false]]);
                        a_num++;
                    } else if(gs.expected_action === Util.Action.THINKERORLEAD) {
                        var do_thinker = actions[0][0] !== Util.Action.LEADROLE;
                        complete_actions.push(
                                [gs.game_id, a_num,
                                    Util.Action.THINKERORLEAD, [do_thinker]]);
                        a_num++;
                    }

                    for(var i=0; i<actions.length; i++) {
                        complete_actions.push([gs.game_id, a_num+i, actions[i][0], actions[i][1]]);
                    }
                    Net.sendActions(complete_actions);
                }
            );

        } else if(gs.expected_action === Util.Action.THINKERTYPE) {
            AB.thinkerType(this.display,
                    function(action, args) {
                        Net.sendAction(gs.game_id, gs.action_number,
                                Util.Action.THINKERTYPE, args);
                    }
            );

        } else if(gs.expected_action === Util.Action.FOLLOWROLE) {
            var roleLed = gs.role_led;
            var petitionMin = 3;
            var petitionMax = 3;
            var hasPalace = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Palace');
            var hasCircus = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Circus');
            if(hasCircus) {
                petitionMin = 2;
            }
            var invocations = 0;
            var hasLatrine = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Latrine');
            var hasVomitorium = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Vomitorium');
            AB.followRole(this.display, roleLed, hasPalace, hasLatrine, hasVomitorium,
                    petitionMin, petitionMax,
                    function(actions) {
                        var complete_actions = [];
                        var a_num = gs.action_number;

                        var do_thinker = actions[0][0] !== Util.Action.FOLLOWROLE;
                        if(do_thinker) {
                            complete_actions.push(
                                    [gs.game_id, a_num, Util.Action.FOLLOWROLE, [0]]);
                            a_num++;
                        }


                        for(var i=0; i<actions.length; i++) {
                            complete_actions.push([gs.game_id, a_num+i, actions[i][0], actions[i][1]]);
                        }
                        Net.sendActions(complete_actions);
                    }
            );

        } else if (gs.expected_action === Util.Action.PATRONFROMHAND) {
            var limit = clienteleLimit[AB.playerIndex];
            function callback(card) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.PATRONFROMHAND, [card]);
            }
            if(gs.players[AB.playerIndex].clientele.length < limit) {
                AB.patronFromHand(this.display, limit, callback);
            } else {
                callback(null);
            }

        } else if (gs.expected_action === Util.Action.PATRONFROMPOOL) {
            var limit = clienteleLimit[AB.playerIndex];
            function callback(card) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.PATRONFROMPOOL, [card]);
            }
            if(gs.players[AB.playerIndex].clientele.length < limit) {
                AB.patronFromPool(this.display, limit, callback);
            } else {
               callback(null);
            }

        } else if (false && gs.expected_action === Util.Action.USELATRINE) {
            function callback(card) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.USELATRINE, [card]);
            }
            if(gs.players[AB.playerIndex].hand.length > 0) {
                AB.useLatrine(this.display, callback);
            } else {
                callback(null);
            }

        } else if (gs.expected_action === Util.Action.USESEWER) {
            AB.useSewer(this.display, function(cards) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.USESEWER, cards);
            });

        } else if (gs.expected_action === Util.Action.PATRONFROMDECK) {
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

        } else if (false && gs.expected_action === Util.Action.USEVOMITORIUM) {
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

        } else if (gs.expected_action === Util.Action.BARORAQUEDUCT) {
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

        } else if (gs.expected_action === Util.Action.USEFOUNTAIN) {
            AB.singleChoice(this.display, 'Use Fountain to Craftsman from deck?',
                    [{text: 'Use Fountain', result: true},
                     {text: 'Skip', result: false}
                    ], function(use) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.USEFOUNTAIN, [use]);
            });

        } else if (false && gs.expected_action === Util.Action.SKIPTHINKER) {
            AB.singleChoice(this.display, 'Skip optional Thinker action?',
                    [{text: 'Thinker', result: false},
                     {text: 'Skip', result: true}
                    ], function(use) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.SKIPTHINKER, [use]);
            });

        } else if (gs.expected_action === Util.Action.USESENATE) {
            AB.useSenate(this.display, function(jacks) {
                Net.sendAction(gs.game_id, gs.action_number, Util.Action.USESENATE, jacks);
            });

        } else if (gs.expected_action === Util.Action.LABORER) {
            var hasDock = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Dock');
            var hasLudus = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Ludus Magna');
            var hasCM = Util.playerHasActiveBuilding(gs, AB.playerIndex, 'Circus Maximus');

            var n_actions = 1; // Current action is 1. Stack has the rest.
            var stack = gs.stack.stack;
            for(var i=stack.length-1; i>=0; i--) {
                var func_name = stack[i].function_name;
                var is_clientele = func_name === '_perform_clientele_action';
                var is_role = func_name === '_perform_role_action';
                if(!(is_role || is_clientele)) {
                    break;
                }

                var is_laborer = stack[i].args[1] === 'Laborer';
                var is_merchant = stack[i].args[1] === 'Merchant';
                var led_or_followed = gs.role_led === 'Laborer'
                        && gs.players[AB.playerIndex].camp.length > 0;

                if(is_laborer || (is_merchant && hasLudus && gs.role_led === 'Laborer')) {
                    n_actions++;
                    if(is_clientele && hasCM && led_or_followed) {
                        n_actions++;
                    }
                } else {
                    break;
                }

            }
            AB.laborer(this.display, hasDock, n_actions, function(handCards, poolCards) {
                var actions = [];
                for(var i=0; i<n_actions; i++) {
                    var cards = []
                    if(i<handCards.length) { cards.push(handCards[i]); }
                    if(i<poolCards.length) { cards.push(poolCards[i]); }
                    actions.push([gs.game_id, gs.action_number+i,
                            Util.Action.LABORER, cards]);
                }
                Net.sendActions(actions)
            });

        } else if (gs.expected_action === Util.Action.MERCHANT) {
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


        } else if (gs.expected_action === Util.Action.CRAFTSMAN) {
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

        } else if (gs.expected_action === Util.Action.FOUNTAIN) {
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

        } else if (gs.expected_action === Util.Action.ARCHITECT) {
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

        } else if (gs.expected_action === Util.Action.STAIRWAY) {
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

        } else if (gs.expected_action === Util.Action.PRISON) {
            AB.prison(this.display, function(building) {
                        Net.sendAction(gs.game_id, gs.action_number,
                            Util.Action.PRISON,
                            [building]);
            });

        } else if (gs.expected_action === Util.Action.LEGIONARY) {
            var revealed = gs.players[AB.playerIndex].prev_revealed;
            AB.legionary(this.display, gs.legionary_count, revealed, function(cards) {
                    Net.sendAction(gs.game_id, gs.action_number, Util.Action.LEGIONARY, cards);
            });

        } else if (gs.expected_action === Util.Action.GIVECARDS) {
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
        } else if (gs.expected_action === Util.Action.TAKECLIENTS) {
            var given_cards = [];
            var victim_index = null;
            for(var i=0; i<gs.players.length; i++) {
                if(gs.players[i].clients_given.length > 0) {
                    given_cards = gs.players[i].clients_given;
                    player_index = i;
                }
            }

            var vault_space = vaultLimit[AB.playerIndex] - gs.players[AB.playerIndex].vault.length
            AB.takeClients(this.display, vault_space, victim_index, given_cards,
                    function(cards) {
                        Net.sendAction(gs.game_id, gs.action_number, Util.Action.TAKECLIENTS, cards);
                    }
            );
        } else if (gs.expected_action === Util.Action.TAKEPOOLCARDS) {
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
