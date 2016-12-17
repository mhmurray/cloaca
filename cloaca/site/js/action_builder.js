define(['jquery', 'fsm', 'util', 'selectable'],
function($, FSM, Util, Selectable){
    var AB = {
        playerIndex: null
    };

    /* FSM best practices:
     * 1) Identify "cancel" points, where the user will end up
     *    by hitting the cancel button in some state.
     * 2) The initial state should be right after the game update
     *    "cancelling" from the initial state shouldn't make sense
     *    or be allowed.
     * 3) Rule 2 probably means a whole FSM for every cycle where
     *    the user doesn't need input from other players. It might
     *    include multiple interactions with the server, though.
     * 4) Here's a list of UI elements to pay attention to:
     *      - LeadRole
     *      - ThinkerForJack, Orders
     *      - Okay
     *      - Cancel
     *      - Cards
     *      - Role buttons
     *    At the beginning of every state, check if you're
     *    enabling them and setting click functions.
     *    At the end (onleave), disable the elements you used
     *    and remove click functions.
     *    Use .one('click',func) instead of .click(func) defensively.
     */

    /* From a Selectable full of cards, extract the card idents.
     * Checks the length and returns an empty list if no cards are
     * in the selection.
     */
    AB._extractCardIds = function(selectable) {
        var cards = selectable.selected();
        return cards.length ? Util.extractCardIds(cards) : [];
    };

    /* From a Selectable, return the ident property of the first
     * card or null if the object is empty.
     */
    AB._extractCardId = function(selectable) {
        var cards = selectable.selected();
        return cards.length ? Util.extractCardIds(cards)[0] : null;
    };

    AB.laborer = function(display, hasDock, n_actions, actionCallback) {
        var $poolpicks = null;
        var $handpicks = null;
        var $pool = display.zoneCards('pool');
        var $handcards = display.zoneCards('hand', AB.playerIndex).not('.jack');
        var $dialog = display.dialog;
        var $okBtn = display.button('ok');
        var $skipBtn = display.button('skip');

        // Check for unusable action
        var viable_action = $pool.length > 0 || (hasDock && $handcards.length > 0);
        if(!viable_action) {
            actionCallback([], []);
        }

        var noun = n_actions==1 ? 'card' : 'cards';
        if(hasDock) {
            $dialog.text('Laborer: Select up to '+n_actions+' '+noun+' from pool and/or hand.');
        } else { 
            $dialog.text('Laborer: Select up to '+n_actions+' '+noun+' from pool.');
        }

        var selPool = new Selectable($pool);
        selPool.makeSelectN(n_actions);
        if(hasDock) {
            var selHand = new Selectable($handcards);
            selHand.makeSelectN(n_actions);
        }
        $okBtn.show().prop('disabled', false).one('click', function(e) {
            var frompool = AB._extractCardIds(selPool);
            selPool.reset();

            var fromhand = [];
            if(hasDock) {
                fromhand = AB._extractCardIds(selHand);
                selHand.reset();
            }

            $dialog.text('');
            actionCallback(fromhand, frompool);
        });

        return;
    };
    
    AB.useSenate = function(display, actionCallback) {
        var ip = AB.playerIndex+1;
        var $campjacks = $('[id$=-camp] > .jack').not('#p'+ip+'-camp > .jack');
        
        if($campjacks.length == 0) {
            actionCallback([]);
            return;
        }

        var $dialog = display.dialog;
        var $okBtn = display.button('ok');
        var $skipBtn = display.button('skip');

        var noun = $campjacks.length > 1 ? 'Jacks' : 'Jack';

        $dialog.text('Take opponents\' '+noun+' at end of turn? ('+$campjacks.length+' '+noun+')');

        var sel = new Selectable($campjacks);
        sel.makeSelectAny();
        sel.select($campjacks);
        $okBtn.show().prop('disabled', false).one('click', function(e) {
            var jacks = AB._extractCardIds(sel);
            sel.reset();

            $dialog.text('');
            actionCallback(jacks);
        });

        $skipBtn.show().prop('disabled', false).one('click', function(e) {
            sel.reset();
            $dialog.text('');
            actionCallback([]);
        });

        return;
    };
    
    AB.patronFromPool = function(display, limit, actionCallback) {
        var $pool = display.zoneCards('pool');
        var $dialog = display.dialog;
        var $skipBtn = display.button('skip');

        if($pool.length == 0) {
            actionCallback(null);
        }

        $dialog.text('Select client from pool.');

        var sel = new Selectable($pool);
        sel.makeSelectN(1, function($selected) {
            var selection = AB._extractCardId(sel);
            sel.reset();

            $dialog.text('');
            actionCallback(selection);
        });

        $skipBtn.show().prop('disabled', false).click(function(e) {
            sel.reset();
            $dialog.text('');
            actionCallback(null);
        });

        return;
    };
    
    AB.patronFromHand = function(display, limit, actionCallback) {
        var $hand = display.zoneCards('hand', AB.playerIndex).not('.jack');
        var $dialog = display.dialog;
        var $skipBtn = display.button('skip');

        if($hand.length == 0) {
            actionCallback(null);
        }

        $dialog.text('Select client from hand.');

        var sel = new Selectable($hand);
        sel.makeSelectN(1, function($selected) {
            var selection = AB._extractCardId(sel);
            sel.reset();

            $dialog.text('');
            actionCallback(selection);
        });

        $skipBtn.show().prop('disabled', false).click(function(e) {
            sel.reset();
            $dialog.text('');
            actionCallback(null);
        });

        return;
    };

    AB.useLatrine = function(display, actionCallback) {
        var $hand = display.zoneCards('hand', AB.playerIndex);
        var $dialog = display.dialog;
        var $skipBtn = display.button('skip');

        $dialog.text('Use latrine? Select card from hand.');

        var sel = new Selectable($hand);
        sel.makeSelectN(1, function($selected) {
            var selection = AB._extractCardId(sel);
            sel.reset();

            $dialog.text('');
            actionCallback(selection);
        });

        $skipBtn.show().prop('disabled', false).click(function(e) {
            sel.reset();
            $dialog.text('');
            actionCallback(null);
        });

        return;
    };
    
    AB.useSewer = function(display, actionCallback) {
        var $camp = $('#p'+(AB.playerIndex+1)+'-camp> .card').not('.jack');
        var $dialog = display.dialog;
        var $skipBtn = display.button('skip');
        var $okBtn = display.button('ok');

        $dialog.text('Select cards to move from Camp to Stockpile with Sewer.');

        var sel = new Selectable($camp);
        sel.makeSelectAny();
        sel.select($camp);

        $skipBtn.show().prop('disabled', false).click(function(e) {
            sel.reset();
            $dialog.text('');
            actionCallback([]);
        });

        $okBtn.show().prop('disabled', false).click(function(e) {
            var selection = AB._extractCardIds(sel);
            sel.reset();

            $dialog.text('');
            actionCallback(selection);
        });

        return;
    };

    AB.legionary = function(display, count, revealed, actionCallback) {
        var $hand = display.zoneCards('hand', AB.playerIndex).not('.jack');
        var $dialog = display.dialog;
        var $okBtn = display.button('ok');

        var revealed_names = revealed.map(function(el) {
            return Util.cardName(el);
        });

        var revText = '';
        if(revealed.length > 0) {
            revText = 'Already revealed '+revealed_names.join(', ')+'. ';
        }
        $dialog.text('Reveal up to '+count+' cards for Legionary. '+
            revText+
            'Press OK when finished.');

        var revealed_ids = revealed.map(function(el) {
            return '#card'+el;
        });
        var sel = new Selectable($hand.not(revealed_ids.join(',')));
        function finished($selected) {
            var cards = AB._extractCardIds(sel);

            sel.reset();
            actionCallback(cards);
        };

        sel.makeSelectN(count, finished);

        $okBtn.show().prop('disabled', false).click(function(e) {
            var cards = AB._extractCardIds(sel);
            sel.reset();

            $dialog.text('');
            actionCallback(cards);
        });

        return;
    };
    
    AB.giveCards = function(display, materials, hasBridge,
            hasColiseum, immune, actionCallback)
    {

        var $hand = display.zoneCards('hand', AB.playerIndex).not('.jack');
        var $clientele = display.zoneCards('clientele', AB.playerIndex);
        var $stockpile = display.zoneCards('stockpile', AB.playerIndex);
        var $dialog = display.dialog;
        var $gloryBtn = display.button('glory');
        var $okBtn = display.button('ok');


        $dialog.text('Rome demands ' + materials.join(', ')+'!');

        function gloryButton() {
            $gloryBtn.show().prop('disabled', false).click(function(e) {
                $dialog.text('');
                actionCallback([]);
            });
        };

        if(immune) { actionCallback([]); return; }

        materialNames = ['Rubble', 'Wood', 'Concrete', 'Brick', 'Stone', 'Marble'];
        materialCountsDemanded = {Rubble: 0, Wood: 0, Concrete: 0, Brick: 0, Stone: 0, Marble: 0};
        materials.forEach(function(item) {
                materialCountsDemanded[item]+=1;
        });


        // Mapping of zone -> (mapping of material -> selectable)
        var sels = {};

        var zones = ['hand'];
        if(hasBridge) {
            zones.push('stockpile');
        }
        if(hasColiseum) {
            zones.push('clientele');
        }


        // Make a selectable for each combination of (zone, material) with the right
        // number needed for each. Then the finish condition is to check all of them to
        // see if they're done. To get more info on what the user hasn't picked,
        // we'll have to know which selectables aren't finished.
        var zoneSelectableMap = {};

        function checkFinished() {
            for(var zone in zoneSelectableMap) {
                var $zone = display.zoneCards(zone, AB.playerIndex).not('.jack');
                for(var mat in zoneSelectableMap[zone]) {
                    var $cards = $zone.filter('.'+mat.toLowerCase());
                    var sel = zoneSelectableMap[zone][mat];
                    var materialCounts = Math.min(materialCountsDemanded[mat], $cards.length);
                    if(sel.selected().length !== materialCounts){
                        return;
                    }
                }
            }
            // If no selectable is unfinished, accumulate all cards and reset selectables.
            var cards = [];
            for(var zone in zoneSelectableMap) {
                for(var mat in zoneSelectableMap[zone]) {
                    var sel = zoneSelectableMap[zone][mat];
                    cards.push.apply(cards, AB._extractCardIds(sel));
                    sel.reset();
                }
            }
            $dialog.text('');
            actionCallback(cards);
        };

        var addedOne = false;
        for(var i=0; i<zones.length; i++) {
            var materialSelectableMap = {};
            var $zone = display.zoneCards(zones[i], AB.playerIndex).not('.jack');
            var materialCounts = Object.assign({}, materialCountsDemanded);
            materialNames.forEach(function(mat) {
                var $cards = $zone.filter('.'+mat.toLowerCase());
                materialCounts[mat] = Math.min(materialCounts[mat], $cards.length);
                var takeAll = materialCounts[mat] === $cards.length;
                if(materialCounts[mat]) {
                    var sel = new Selectable($cards);
                    // the "|| zone..." preselects, even if there is a choice.
                    if((takeAll || zones[i] !== 'hand') && !immune) {
                        sel.makeSelectN(materialCounts[mat], null);
                        sel.select($cards.slice(0, materialCounts[mat]));
                        sel.finishedCallback = checkFinished;
                    } else {
                        sel.makeSelectN(materialCounts[mat], checkFinished, true);
                    }
                    addedOne = true;
                    materialSelectableMap[mat] = sel;
                }
            });
            zoneSelectableMap[zones[i]] = materialSelectableMap;
        }

        if(addedOne) {
            $okBtn.show().prop('disabled', false).click(function() {
                checkFinished();
            });
        } else {
            gloryButton();
        }

        return;
    };
    
    AB.takePoolCards = function(display, materials, actionCallback)
    {
        var $pool = display.zoneCards('pool');
        var $dialog = display.dialog;

        $dialog.text('Take matching cards from pool.');

        materialCounts = {Rubble: 0, Wood: 0, Concrete: 0, Brick: 0, Stone: 0, Marble: 0};
        materials.forEach(function(item) {
                materialCounts[item]+=1;
        });

        var allowChoice = false;

        if(allowChoice) {
            var cards = [];
            var selectables = {};

            for(var m in materialCounts) {
                var $cards = $pool.filter('.'+m.toLowerCase());
                materialCounts[m] = Math.min(materialCounts[m], $cards.length);
                var count = materialCounts[m];
                if(count) {
                    var sel = new Selectable($cards);
                    sel.makeSelectN(count, function($selected) {
                        // Check if all Selectables are done. Return if not.
                        for(var mat in selectables) {
                            if(selectables[mat].selected().length !== materialCounts[mat]) {
                                return;
                            }
                        }
                        // If done, accumulate cards from all and reset them.
                        for(var mat in selectables) {
                            var sel = selectables[mat];
                            cards.push.apply(cards, AB._extractCardIds(sel));
                            sel.reset();
                        }
                        $dialog.text('');
                        actionCallback(cards);
                    });
                    selectables[m] = sel;
                }
            }

            // If we don't have any of the materials, no Selectables will be made.
            if(Object.keys(selectables).length == 0) {
                actionCallback([]);
            }
        } else {
            var card_ids = [];
            for(var m in materialCounts) {
                var $cards = $pool.filter('.'+m.toLowerCase());
                count = Math.min(materialCounts[m], $cards.length);
                var ids = $cards.slice(0, count).map(function(){
                    return $(this).data('ident');
                });
                card_ids.push.apply(card_ids, ids);
            }
            actionCallback(card_ids);
        }

        return;
    };

    AB.takeClients = function(display, vault_space, victim_index, given_cards, actionCallback)
    {
        var $cards = display.zoneCards('clientele', victim_index);
        var $okBtn = display.button('ok');
        var $dialog = display.dialog;

        $dialog.text('Vault limit will be reached. '+
            'Select '+vault_space+' of opponent\'s clientele.');


        var selector = '#card'+given_cards.join(',#card');
        var sel = new Selectable(selector);
        sel.makeSelectN(vault_space);

        $okBtn.show().prop('disabled', false).one('click', function(e) {
            var cards = AB._extractCardIds(sel);
            sel.reset();

            $dialog.text('')
            actionCallback(cards);
        });
    }




    /* Action builder for a simple choice among a few options.
     *
     * The parameter choices is a list of elements with properties
     * description, returnValue.
     *
     * The description is the text on the button choice, and
     * the returnValue is what's passed to the actionCallback.
     *
     * For example, to ask if you want to use the Bar during a Patron
     * action, you would invoke like this:
     *
     *      singleChoice('Use Bar for client from deck?',
     *          [{text: 'Yes', result: true},
     *           {text: 'No', result: false}
     *           ], actionCallbackFunction);
     */
    AB.singleChoice = function(display, dialog, choices, actionCallback) {
        var $dialog = display.dialog.text(dialog);

        var $choiceButtons = display.choiceBtns;

        $.each(choices, function(i, item) {
            $choiceButtons.append($('<button/>').click(function(e) {
                $choiceButtons.children('button').prop('disabled', true);
                $choiceButtons.empty();
                $dialog.text('');
                actionCallback(item.result);
            }).text(item.text));
        });

        return;
    };
        
    AB.merchant = function(display, hasBasilica, hasAtrium, actionCallback) {
        var $stockpile = display.zoneCards('stockpile', AB.playerIndex);
        var $handcards = display.zoneCards('hand', AB.playerIndex).not('.jack');
        var $dialog = display.dialog;
        var $okBtn = display.button('ok');

        if(hasAtrium && hasBasilica) {
            $dialog.text('Merchant: Select card from stockpile or deck, and one from your hand.');
        } else if(hasAtrium) { 
            $dialog.text('Merchant: Select card from stockpile or deck.');
        } else if(hasBasilica) { 
            $dialog.text('Merchant: Select card from stockpile and/or hand.');
        } else { 
            $dialog.text('Merchant: Select card from stockpile.');
        }

        if(hasAtrium) {
            $stockpile = $stockpile.add(display.deck);
        }
        var selStockpile = new Selectable($stockpile);
        selStockpile.makeSelectN(1);

        if(hasBasilica) {
            var selHand = new Selectable($handcards);
            selHand.makeSelectN(1);
        }

        $okBtn.show().prop('disabled', false).click(function() {
            var $stockpilePick = selStockpile.selected();

            var fromStockpile = null;
            var fromDeck = false;
            if($stockpilePick.length) {
                fromDeck = $stockpilePick[0].id === 'deck';

                if(!fromDeck) {
                    fromStockpile = AB._extractCardId(selStockpile);
                }
            } else {
                fromStockpile = null;
            }
            selStockpile.reset();

            var fromHand = null;
            if(hasBasilica) {
                fromHand = AB._extractCardId(selHand);
                selHand.reset();
            }

            $dialog.text('');
            actionCallback(fromStockpile, fromHand, fromDeck);
        });

        return;
    };
        
    /* Set up a state machine to walk through thinker or leading
     * an action, including Jacks, petition, and Palace.
     *
     * Args:
     *   hasPalace -- (bool) Player has active Palace.
     *   petitionMin -- (int) Number of cards required for Petition.
     *   petitionMax -- (int) Max number of cards allowed for Petition.
     *   actionCallback -- func(action, args) fire this with LEADROLE
     *          or THINKERTYPE action.
     */
    AB.leadRole = function(display, hasPalace, hasLatrine, hasVomitorium,
            petitionMin, petitionMax, expectedAction, actionCallback)
    {
        var $dialog = display.dialog;

        var $handcards = display.zoneCards('hand', AB.playerIndex);
        var selHand = new Selectable($handcards);

        var $handNoJacks = $($handcards).not('.jack');
        var selHandNoJacks = new Selectable($handNoJacks);

        var selPalacePetition = null;

        var role = null;
        var nActions = 1;
        var $roleBtns = display.roleButtons();
        var selRole = new Selectable($roleBtns);

        var $cancelBtn = display.button('cancel');
        var $okBtn = display.button('ok');
        var $petitionBtn = display.button('petition');
        var $skipBtn = display.button('skip');

        var $deck = display.deck;
        var $jacks = display.jacks;
        var $latrineBtn = display.button('latrine');
        var $vomitoriumBtn = display.button('vomitorium');


        var fsm = FSM.create({
            initial: 'Start',

            events: [
                { name: 'start', from: 'Start', to: 'Switchhouse' },
                { name: 'skipthinker', from: 'Switchhouse', to: 'SkippableThinker' },
                { name: 'thinkerorlead', from: 'Switchhouse', to: 'SelectingCards' },
                { name: 'uselatrine', from: 'Switchhouse', to: 'Latrine' },
                { name: 'usevomitorium', from: 'Switchhouse', to: 'Vomitorium' },
                { name: 'think', from: 'SkippableThinker', to: 'Thinker' },
                { name: 'latrine', from: 'SkippableThinker', to: 'Latrine' },
                { name: 'vomitorium', from: 'SkippableThinker', to: 'Vomitorium' },
                { name: 'think', from: 'SelectingCards', to: 'Thinker' },
                { name: 'latrine', from: 'SelectingCards', to: 'Latrine' },
                { name: 'think', from: 'Latrine', to: 'Thinker' },
                { name: 'cancel', from: 'Latrine', to: 'SelectingCards' },
                { name: 'returntoskippable', from: 'Latrine', to: 'SkippableThinker' },
                { name: 'vomitorium', from: 'SelectingCards', to: 'Vomitorium' },
                { name: 'think', from: 'Vomitorium', to: 'Thinker' },
                { name: 'cancel', from: 'Vomitorium', to: 'SelectingCards' },
                { name: 'returntoskippable', from: 'Vomitorium', to: 'SkippableThinker' },
                { name: 'orders', from: 'SelectingCards', to: 'HaveRole' },
                { name: 'jack', from: 'SelectingCards', to: 'JackRole' },
                { name: 'petition', from: 'SelectingCards', to: 'PetitionFirst' },
                { name: 'first', from: 'PetitionFirst', to: 'PetitionRest' },
                { name: 'cancel', from: 'PetitionFirst', to: 'SelectingCards' },
                { name: 'cancel', from: 'PetitionRest', to: 'PetitionFirst' },
                { name: 'finishpetition', from: 'PetitionRest', to: 'PetitionRole' },
                { name: 'role', from: 'PetitionRole', to: 'HaveRole' },
                { name: 'cancel', from: 'PetitionRole', to: 'SelectingCards' },
                { name: 'role', from: 'JackRole', to: 'HaveRole' },
                { name: 'cancel', from: 'JackRole', to: 'SelectingCards' },
                { name: 'nopalace', from: 'HaveRole', to: 'LeadRole' },
                { name: 'palace', from: 'HaveRole', to: 'Palace' },
                { name: 'addaction', from: 'Palace', to: 'AddAction' },
                { name: 'cancel', from: 'Palace', to: 'SelectingCards' },
                { name: 'addaction', from: 'AddAction', to: 'Palace' },
                { name: 'palacepetition', from: 'Palace', to: 'PalacePetitionFirst' },
                { name: 'palacefirst', from: 'PalacePetitionFirst', to: 'PalacePetitionRest' },
                { name: 'cancel', from: 'PalacePetitionFirst', to: 'Palace' },
                { name: 'cancel', from: 'PalacePetitionRest', to: 'Palace' },
                { name: 'finishpalacepetition', from: 'PalacePetitionRest', to: 'Palace' },
                { name: 'finishpalace', from: 'Palace', to: 'LeadRole' },
            ]
        });

        fsm.onenterSwitchhouse = function() {
            if(expectedAction === Util.Action.USELATRINE) { fsm.uselatrine(); }
            else if(expectedAction === Util.Action.USEVOMITORIUM) { fsm.usevomitorium(); }
            else if(expectedAction === Util.Action.SKIPTHINKER) { fsm.skipthinker(); }
            else { fsm.thinkerorlead(); }
        };

        fsm.onenterSkippableThinker = function() {
            $dialog.text('Thinker or skip?');

            if($jacks.data('nCards') > 0) {
                $jacks.addClass('selectable');
                $jacks.off('click').one('click', function() {
                    fsm.think(true);
                });
            }

            $deck.addClass('selectable');
            $deck.off('click').one('click', function() {
                fsm.think(false);
            });

            $skipBtn.show().prop('disabled', false).off('click').click(function() {
                actionCallback([ [Util.Action.SKIPTHINKER, [true]] ]);
            });

            if(hasLatrine) {
                $latrineBtn.show().prop('disabled', false).one('click', function() {
                    fsm.latrine();
                });
            }

            if(hasVomitorium) {
                $vomitoriumBtn.show().prop('disabled', false).one('click', function() {
                    fsm.vomitorium();
                });
            }
        };

        fsm.onleaveSkippableThinker = function() {
            Util.off($deck, $jacks, $vomitoriumBtn, $latrineBtn);
            $jacks.removeClass('selectable');
            $deck.removeClass('selectable');
            $dialog.text('');
        };

        fsm.onenterLatrine = function(event, from, to) {
            $dialog.text('Pick card from hand to discard with Latrine. Thinker for Jack or cards?');

            if(expectedAction != Util.Action.USELATRINE) {
                $cancelBtn.show().prop('disabled', false).one('click', function() {
                    if(from === 'SkippableThinker') {
                        fsm.returntoskippable();
                    } else {
                        fsm.cancel();
                    }
                });
            }

            selHand.makeSelectN(1);

            if($jacks.data('nCards') > 0) {
                $jacks.addClass('selectable');
                $jacks.off('click').one('click', function() {
                    fsm.think(true, AB._extractCardId(selHand));
                });
            }

            $deck.addClass('selectable');
            $deck.off('click').one('click', function() {
                fsm.think(false, AB._extractCardId(selHand));
            });
        };

        fsm.onleaveLatrine = function() {
            selHand.reset();
            Util.off($deck, $jacks);
        };

        fsm.onenterVomitorium = function(event, from, to) {
            $dialog.text('Discarding hand with Vomitorium. Thinker for Jack or cards?');

            if(expectedAction !== Util.Action.USEVOMITORIUM) {
                $cancelBtn.show().prop('disabled', false).one('click', function() {
                    if(from === 'SkippableThinker') {
                        fsm.returntoskippable();
                    } else {
                        fsm.cancel();
                    }
                });
            }

            if($jacks.data('nCards') > 0) {
                $jacks.addClass('selectable');
                $jacks.off('click').one('click', function() {
                    fsm.think(true, true);
                });
            }

            $deck.addClass('selectable');
            $deck.off('click').one('click', function() {
                fsm.think(false, true);
            });
        };

        fsm.onleaveVomitorium = function() {
            selHand.reset();
            Util.off($deck, $jacks);
        };

        fsm.onenterThinker = function(event, from, to, forJack, discard) {
            // <discard> is either the Latrine card ID or true/false for Vomitorium.
            // If we don't use the Latrine / Vomitorium, append blank actions.
            // If the Vomitorium is used, the Latrine is automatically skipped.
            if(from === 'Latrine') {
                var actions = [];
                if(hasVomitorium) { actions.push([Util.Action.USEVOMITORIUM, [false]]); }
                actions.push([Util.Action.USELATRINE, [discard]]);
                actions.push([Util.Action.THINKERTYPE, [forJack]]);
                actionCallback(actions);

            } else if(from === 'Vomitorium') {
                actionCallback([
                    [Util.Action.USEVOMITORIUM, [discard]],
                    [Util.Action.THINKERTYPE, [forJack]]
                ]);
            } else { // SelectingCards or SkippableThinker
                var actions = [];
                if(hasVomitorium) { actions.push([Util.Action.USEVOMITORIUM, [false]]); }
                if(hasLatrine) { actions.push([Util.Action.USELATRINE, [null]]); }
                actions.push([Util.Action.THINKERTYPE, [forJack]]);
                actionCallback(actions);
            }

        };

        fsm.onenterSelectingCards = function() {
            $dialog.text('Thinker or lead a role?');

            if($jacks.data('nCards') > 0) {
                $jacks.addClass('selectable');
                $jacks.off('click').one('click', function() {
                    fsm.think(true);
                });
            }

            $deck.addClass('selectable');
            $deck.off('click').one('click', function() {
                fsm.think(false);
            });

            if(hasLatrine) {
                $latrineBtn.show().prop('disabled', false).one('click', function() {
                    fsm.latrine();
                });
            }

            if(hasVomitorium) {
                $vomitoriumBtn.show().prop('disabled', false).one('click', function() {
                    fsm.vomitorium();
                });
            }

            nActions = 1;
            role = null;

            $petitionBtn.show().prop('disabled', false).one('click', function() {
                fsm.petition();
            });
            
            selHand.makeSelectN(1, function($selected) {
                selHand.makeUnselectable();
                var card = AB._extractCardId(selHand);
                if(card !== null) {
                    if(Util.cardName(card) == 'Jack') {
                        fsm.jack();
                    } else {
                        role = Util.cardProperties(card).role;
                        fsm.orders();
                    }
                }
            });
        };

        fsm.onleaveSelectingCards = function() {
            Util.off($deck, $jacks, $vomitoriumBtn, $latrineBtn,
                    $cancelBtn, $petitionBtn);
            $jacks.removeClass('selectable');
            $deck.removeClass('selectable');
            $dialog.text('');
        };

        fsm.onenterJackRole = function() {
            $dialog.text('Pick role for Jack.');

            $cancelBtn.show().prop('disabled', false).one('click', function() {
                selRole.reset();
                selHand.reset();
                fsm.cancel();
            });

            $roleBtns.show().prop('disabled', false);
            selRole.reset();
            selRole.makeSelectN(1, function($selected) {
                selRole.makeUnselectable();
                if($selected.length > 0) {
                    role = $selected.eq(0).data('role');
                    fsm.role();
                }
            });
        };

        fsm.onleaveJackRole = function() {
            Util.off($roleBtns, $cancelBtn);
        };

        fsm.onenterPetitionFirst = function() {
            $dialog.text('Pick at least '+petitionMin+' cards for petition');

            selHand.reset();
            selHandNoJacks.reset();
            selHandNoJacks.makeSelectN(1, function($selected) {
                fsm.first($selected);
            });

            $cancelBtn.show().prop('disabled', false).one('click', function() {
                selHandNoJacks.reset();
                fsm.cancel();
            });
        };

        fsm.onleavePetitionFirst = function() {
            Util.off($cancelBtn);
        };

        fsm.onenterPetitionRest = function(event, from, to, $selected) {
            $dialog.text('Pick at least '+petitionMin+' cards for petition');

            selHand.reset();
            selHand.makeSelectN(petitionMax);
            $selected.each(function(i, el) {
                selHand.select($(el));
            });

            $cancelBtn.show().prop('disabled', false).one('click', function() {
                selHand.reset();
                fsm.cancel();
            });

            $okBtn.show().prop('disabled', false).on('click', function() {
                var $selected = selHand.selected();
                if($selected.length < petitionMin) {
                    $dialog.text('Not enough cards. Pick at least ' +
                        petitionMin + ' cards for petition');
                } else {
                    selHand.makeUnselectable();
                    fsm.finishpetition();
                }
            });
        };

        fsm.onleavePetitionRest = function() {
            Util.off($cancelBtn, $okBtn);
        };

        fsm.onenterPetitionRole = function() {
            $dialog.text('Pick role for Petition.');

            $cancelBtn.prop('disabled', false).one('click', function() {
                selRole.reset();
                selHand.reset();
                fsm.cancel();
            });

            $roleBtns.show().prop('disabled', false);
            selRole.makeSelectN(1, function($selected) {
                selRole.makeUnselectable();
                if ($selected.length > 0) {
                    role = $selected.eq(0).data('role');
                    fsm.role();
                }
            });
        };

        fsm.onleavePetitionRole = function() {
            Util.off($roleBtns, $cancelBtn);
        };

        fsm.onenterHaveRole = function() {
            if(hasPalace) {
                fsm.palace();
            } else {
                fsm.nopalace();
            }
        };

        fsm.onenterLeadRole = function() {
            var card_ids = AB._extractCardIds(selHand);
            actionCallback([
                [Util.Action.LEADROLE, [role, nActions].concat(card_ids)]
            ]);
            $dialog.text('');

            selRole.reset();
            selHand.reset();
        };

        fsm.onenterPalace = function() {
            $dialog.text('Select additional '+role+' actions card with Palace.');

            $cancelBtn.show().prop('disabled', false).off('click').one('click', function() {
                selHand.reset();
                fsm.cancel();
            });

            $petitionBtn.show().prop('disabled', false).off('click').one('click', function() {
                fsm.palacepetition();
            });

            $okBtn.show().prop('disabled', false).off('click').one('click', function() {
                fsm.finishpalace();
            });
            
            // Filter to cards matching the role.
            var materialLed = Util.roleToMaterial(role);
            var $matchingHand = display.zoneCards('hand', AB.playerIndex).filter(
                    '.'+materialLed.toLowerCase()+',.jack');

            var selMatching = new Selectable($matchingHand);

            // Make 1 more card selectable, then mark already-selected cards.
            var $selectedCards = selMatching.selected();
            selMatching.reset();
            selMatching.makeSelectN($selectedCards.length+1, function($selected) {
                nActions++;
                fsm.addaction();
            });

            $selectedCards.each(function(i, el) {
                selMatching.select($(el));
            });
        };

        // This is a no-op state so that Palace can re-enter on each selection.
        fsm.onenterAddAction = function() {
            fsm.addaction();
        };

        fsm.onenterPalacePetitionFirst = function() {
            $dialog.text('Pick at least '+petitionMin+' cards for petition');

            var $cards = $handNoJacks.not(selHand.selected());
            var selPalacePetition = new Selectable($cards);
            selPalacePetition.makeSelectN(1, function($selected) {
                fsm.palacefirst($selected);
            });

            $cancelBtn.show().prop('disabled', false).off('click').one('click', function() {
                selPalacePetition.reset();
                fsm.cancel();
            });
        };

        fsm.onenterPalacePetitionRest = function(event, from, to, $first) {
            $dialog.text('Pick at least '+petitionMin+' cards for petition');

            var $cards = $handNoJacks.not(selHand.selected()).add($first);
            //TODO: Select cards that match the first petition card's role.
            //$first is already selected, no need to re-select.
            selPalacePetition = new Selectable($cards);
            selPalacePetition.makeSelectN(petitionMax);

            $cancelBtn.show().prop('disabled', false).off('click').one('click', function() {
                selPalacePetition.reset();
                fsm.cancel();
            });

            $okBtn.show().prop('disabled', false).off('click').one('click', function() {
                var $selected = selPalacePetition.selected();
                if($selected.length < petitionMin) {
                    $dialog.text('Not enough cards. Pick at least ' +
                        petitionMin + ' cards for petition');
                } else {
                    selPalacePetition.makeUnselectable();
                    nActions++;
                    fsm.finishpalacepetition();
                }
            });
        };

        fsm.start();

        return;
    };


    AB.thinkerType = function(display, actionCallback) {
        var $dialog = display.dialog;
        var $deck = display.deck;
        var $jacks = display.jacks;

        $dialog.text('Thinker for Orders cards or a Jack?');

        if($jacks.data('nCards') > 0) {
            $jacks.addClass('selectable');
            $jacks.off('click').one('click', function() {
                Util.off($deck, $jacks);
                $jacks.removeClass('selectable');
                $deck.removeClass('selectable');
                $dialog.text('');

                actionCallback(Util.Action.THINKERTYPE, [true]);
            });
        }

        $deck.addClass('selectable');
        $deck.off('click').one('click', function() {
            Util.off($deck, $jacks);
            $jacks.removeClass('selectable');
            $deck.removeClass('selectable');
            $dialog.text('');

            actionCallback(Util.Action.THINKERTYPE, [false]);
        });
    };

    AB.followRole = function(display, role, hasPalace, hasLatrine, hasVomitorium,
            petitionMin, petitionMax, actionCallback)
    {
        var materialLed = Util.roleToMaterial(role);
        var $dialog = display.dialog;

        var $hand = display.zoneCards('hand', AB.playerIndex);
        var selHand = new Selectable($hand);

        var $handNoJacks = $hand.not('.jack');
        var selHandNoJacks = new Selectable($handNoJacks);

        var $matchingHand = display.zoneCards('hand', AB.playerIndex).filter(
                '.'+materialLed.toLowerCase()+',.jack');
        var selMatching = new Selectable($matchingHand);

        var selPalacePetition = null;

        var $petitionCards = null;
        var $followCard = null;
        var $palaceCards = null;

        var nActions = 1;

        var $cancelBtn = display.button('cancel');
        var $okBtn = display.button('ok');
        var $petitionBtn = display.button('petition');
        var $latrineBtn = display.button('latrine');
        var $vomitoriumBtn = display.button('vomitorium');

        var $piles = display.decks;
        var $deck = display.deck;
        var $jacks = display.jacks;

        var fsm = FSM.create({
            initial: 'Start',

            events: [
                { name: 'start', from: 'Start', to: 'SelectingCards' },
                { name: 'think', from: 'SelectingCards', to: 'Thinker' },
                { name: 'latrine', from: 'SelectingCards', to: 'Latrine' },
                { name: 'think', from: 'Latrine', to: 'Thinker' },
                { name: 'cancel', from: 'Latrine', to: 'SelectingCards' },
                { name: 'vomitorium', from: 'SelectingCards', to: 'Vomitorium' },
                { name: 'think', from: 'Vomitorium', to: 'Thinker' },
                { name: 'cancel', from: 'Vomitorium', to: 'SelectingCards' },
                { name: 'follow', from: 'SelectingCards', to: 'HaveFirst' },
                { name: 'think', from: 'SelectingCards', to: 'Thinker' },
                { name: 'petition', from: 'SelectingCards', to: 'PetitionFirst' },
                { name: 'first', from: 'PetitionFirst', to: 'PetitionRest' },
                { name: 'cancel', from: 'PetitionFirst', to: 'SelectingCards' },
                { name: 'cancel', from: 'PetitionRest', to: 'PetitionFirst' },
                { name: 'petition', from: 'PetitionRest', to: 'HaveFirst' },
                { name: 'nopalace', from: 'HaveFirst', to: 'Follow' },
                { name: 'palace', from: 'HaveFirst', to: 'Palace' },
                { name: 'cancel', from: 'Palace', to: 'SelectingCards' },
                { name: 'addaction', from: 'Palace', to: 'AddAction' },
                { name: 'addaction', from: 'AddAction', to: 'Palace' },
                { name: 'palacepetition', from: 'Palace', to: 'PalacePetitionFirst' },
                { name: 'palacefirst', from: 'PalacePetitionFirst', to: 'PalacePetitionRest' },
                { name: 'cancel', from: 'PalacePetitionFirst', to: 'Palace' },
                { name: 'cancel', from: 'PalacePetitionRest', to: 'Palace' },
                { name: 'finishpalacepetition', from: 'PalacePetitionRest', to: 'Palace' },
                { name: 'finishpalace', from: 'Palace', to: 'Follow' },
            ]
        });

        fsm.onenterSelectingCards = function() {
            display.dialog.text('Thinker or follow '+role+'?');

            if($jacks.data('nCards') > 0) {
                $jacks.addClass('selectable');
                $jacks.one('click', function() {
                    fsm.think(true);
                });
            }

            $deck.addClass('selectable');
            $deck.one('click', function() {
                fsm.think(false);
            });

            $petitionBtn.show().prop('disabled', false).one('click', function() {
                fsm.petition();
            });
            
            selMatching.makeSelectN(1, function($selected) {
                selMatching.makeUnselectable();
                $followCard = selMatching.selected();
                fsm.follow();
            });

            if(hasLatrine) {
                $latrineBtn.show().prop('disabled', false).one('click', function() {
                    fsm.latrine();
                });
            }

            if(hasVomitorium) {
                $vomitoriumBtn.show().prop('disabled', false).one('click', function() {
                    fsm.vomitorium();
                });
            }
        };

        fsm.onleaveSelectingCards = function() {
            Util.off($deck, $jacks, $petitionBtn);
            $jacks.removeClass('selectable');
            $deck.removeClass('selectable');
            $dialog.text('');
        };

        fsm.onenterLatrine = function(event, from, to) {
            $dialog.text('Pick card from hand to discard with Latrine. Thinker for Jack or cards?');

            $cancelBtn.show().prop('disabled', false).one('click', function() {
                fsm.cancel();
            });

            selHand.makeSelectN(1);

            if($jacks.data('nCards') > 0) {
                $jacks.addClass('selectable');
                $jacks.off('click').one('click', function() {
                    fsm.think(true, AB._extractCardId(selHand));
                });
            }

            $deck.addClass('selectable');
            $deck.off('click').one('click', function() {
                fsm.think(false, AB._extractCardId(selHand));
            });
        };

        fsm.onleaveLatrine = function() {
            selHand.reset();
            Util.off($deck, $jacks);
        };

        fsm.onenterVomitorium = function() {
            $dialog.text('Discarding hand with Vomitorium. Thinker for Jack or cards?');

            $cancelBtn.show().prop('disabled', false).one('click', function() {
                fsm.cancel();
            });

            if($jacks.data('nCards') > 0) {
                $jacks.addClass('selectable');
                $jacks.off('click').one('click', function() {
                    fsm.think(true, true);
                });
            }

            $deck.addClass('selectable');
            $deck.off('click').one('click', function() {
                fsm.think(false, true);
            });
        };

        fsm.onleaveVomitorium = function() {
            selHand.reset();
            Util.off($deck, $jacks);
        };

        fsm.onenterThinker = function(event, from, to, forJack, discard) {
            if(from === 'Latrine') {
                var actions = [];
                if(hasVomitorium) { actions.push([Util.Action.USEVOMITORIUM, [false]]); }
                actions.push([Util.Action.USELATRINE, [discard]]);
                actions.push([Util.Action.THINKERTYPE, [forJack]]);
                actionCallback(actions);

            } else if(from === 'Vomitorium') {
                actionCallback([
                    [Util.Action.USEVOMITORIUM, [discard]],
                    [Util.Action.THINKERTYPE, [forJack]]
                ]);
            } else { // SelectingCards
                var actions = [];
                if(hasVomitorium) { actions.push([Util.Action.USEVOMITORIUM, [false]]); }
                if(hasLatrine) { actions.push([Util.Action.USELATRINE, [null]]); }
                actions.push([Util.Action.THINKERTYPE, [forJack]]);
                actionCallback(actions);
            }
        };

        fsm.onenterPetitionFirst = function() {
            $dialog.text('Pick at least '+petitionMin+' cards for petition');

            selMatching.reset();

            selHandNoJacks.reset();
            selHandNoJacks.makeSelectN(1, function($selected) {
                fsm.first($selected);
            });

            $cancelBtn.show().prop('disabled', false).one('click', function() {
                selHandNoJacks.reset();
                fsm.cancel();
            });
        };

        fsm.onleavePetitionFirst = function() {
            Util.off($cancelBtn);
        };

        fsm.onenterPetitionRest = function(event, from, to, $selected) {
            $dialog.text('Pick at least '+petitionMin+' cards for petition');

            selHandNoJacks.reset();
            selHandNoJacks.makeSelectN(petitionMax);
            $selected.each(function(i, el) {
                selHandNoJacks.select($(el));
            });

            $cancelBtn.show().prop('disabled', false).on('click', function() {
                selHandNoJacks.reset();
                fsm.cancel();
            });

            $okBtn.show().prop('disabled', false).on('click', function() {
                var $selected = selHandNoJacks.selected();
                if($selected.length < petitionMin) {
                    $dialog.text('Not enough cards. Pick at least ' +
                        petitionMin + ' cards for petition');
                } else {
                    selHandNoJacks.makeUnselectable();
                    fsm.petition();
                }
            });
        };

        fsm.onleavePetitionRest = function() {
            $petitionCards = selHandNoJacks.selected();
            Util.off($cancelBtn, $okBtn);
        };

        fsm.onenterHaveFirst = function() {
            if(hasPalace) {
                fsm.palace();
            } else {
                fsm.nopalace();
            }
        };

        fsm.onenterFollow = function() {
            var selHand = new Selectable($hand);
            var cardIds = AB._extractCardIds(selHand);
            selHand.reset();

            $dialog.text('');
            actionCallback([
                [Util.Action.FOLLOWROLE, [nActions].concat(cardIds)]
            ]);
        };

        fsm.onenterPalace = function() {
            $dialog.text('Select additional '+role+' actions card with Palace.');

            $cancelBtn.show().prop('disabled', false).off('click').one('click', function() {
                selHandNoJacks.reset();
                fsm.cancel();
            });

            $petitionBtn.show().prop('disabled', false).off('click').one('click', function() {
                fsm.palacepetition();
            });

            $okBtn.show().prop('disabled', false).off('click').one('click', function() {
                fsm.finishpalace();
            });
            
            // Make 1 more card selectable, then mark already-selected cards.
            var $selectedCards = selMatching.selected();
            selMatching.reset();
            selMatching.makeSelectN($selectedCards.length+1, function($selected) {
                nActions++;
                fsm.addaction();
            });

            $selectedCards.each(function(i, el) {
                selMatching.select($(el));
            });
        };

        // This is a no-op state so that Palace can re-enter on each selection.
        fsm.onenterAddAction = function() {
            fsm.addaction();
        };

        fsm.onenterPalacePetitionFirst = function() {
            $dialog.text('Pick at least '+petitionMin+' cards for petition');

            var $cards = $handNoJacks.not(selHandNoJacks.selected()).not(selMatching.selected());
            var selPalacePetition = new Selectable($cards);
            selPalacePetition.makeSelectN(1, function($selected) {
                fsm.palacefirst($selected);
            });

            $cancelBtn.show().prop('disabled', false).off('click').one('click', function() {
                selPalacePetition.reset();
                fsm.cancel();
            });
        };

        fsm.onenterPalacePetitionRest = function(event, from, to, $first) {
            $dialog.text('Pick at least '+petitionMin+' cards for petition');

            var $cards = $handNoJacks.not(selHandNoJacks.selected()).not(selMatching.selected()).add($first);
            //TODO: Select cards that match the first petition card's role.
            //$first is already selected, no need to re-select.
            selPalacePetition = new Selectable($cards);
            selPalacePetition.makeSelectN(petitionMax);

            $cancelBtn.show().prop('disabled', false).off('click').one('click', function() {
                selPalacePetition.reset();
                fsm.cancel();
            });

            $okBtn.show().prop('disabled', false).off('click').one('click', function() {
                var $selected = selPalacePetition.selected();
                if($selected.length < petitionMin) {
                    $dialog.text('Not enough cards. Pick at least ' +
                        petitionMin + ' cards for petition');
                } else {
                    selPalacePetition.makeUnselectable();
                    nActions++;
                    fsm.finishpalacepetition();
                }
            });
        };

        fsm.start();

        return;
    };

    AB.craftsman = function(display, ootAllowed, hasRoad, hasTower, hasScriptorium,
            actionCallback)
    {
        var $dialog = display.dialog;

        var $handcards = display.zoneCards('hand', AB.playerIndex).not('.jack');
        var selHand = new Selectable($handcards);

        var selBuilding = null;

        var $sites = display.zoneCards('sites');
        var selSite = null;

        var $cancelBtn = display.button('cancel');
        var $skipBtn = display.button('skip');

        var fsm = FSM.create({
            initial: 'Start',

            events: [
                { name: 'start', from: 'Start', to: 'SelectHand' },
                { name: 'card', from: 'SelectHand', to: 'SelectSite' },
                { name: 'cancel', from: 'SelectSite', to: 'SelectHand' },
                { name: 'finish', from: 'SelectSite', to: 'Finish' },
                { name: 'finish', from: 'SelectHand', to: 'Finish' },
            ]
        });

        fsm.onenterSelectHand = function() {
            $dialog.text('Choose card in hand to use with Craftsman.');
            selHand.makeSelectN(1, function($selected) {
                fsm.card();
            });

            $skipBtn.show().prop('disabled', false).off('click').click(function() {
                selHand.reset();
                fsm.finish(null, null, null);
            });
        };

        fsm.onleaveSelectHand = function() {
            selHand.makeUnselectable();
            $skipBtn.show().prop('disabled', true).off('click');
        };

        fsm.onenterSelectSite = function() {
            $dialog.text('Choose existing building to add or a site '
                    +'to start a new building.');

            var cardIdent = AB._extractCardId(selHand);
            var cardName = Util.cardName(cardIdent);
            var cardProp = Util.cardProperties(cardName);
            var cardMaterial = cardProp.material;

            var $sitesAllowed = $($sites).filter(function(i, site) {
                    var $site = $(site);
                    var siteAvail = $site.data('inTown') > 0 ||
                            (ootAllowed && $site.data('outOfTown') > 0);
                    var siteMatch = cardName === 'Statue' || 
                            $site.data('material') === cardProp.material;

                    return siteAvail && siteMatch;
            });

            selSite = new Selectable($sitesAllowed);
            selSite.makeSelectN(1, function($selected) {
                var siteName = $selected.data('material');
                fsm.finish(cardIdent, null, siteName);
            });

            var $buildings = display.buildings(AB.playerIndex).filter(
                    function(i, building) {
                var $building = $(building);
                var materials = $building.data('materials');

                var materialMatch = $.inArray(cardMaterial, materials) !== -1;
                var notComplete = !$building.data('complete');
                var roadMatch = hasRoad && $.inArray('Stone', materials) !== -1;
                var scriptoriumMatch = hasScriptorium && cardMaterial === 'Marble';
                var towerMatch = hasTower && (cardMaterial === 'Rubble');

                return notComplete &&
                        (materialMatch || roadMatch ||
                         scriptoriumMatch || towerMatch);
            });

            selBuilding = new Selectable($buildings);
            selBuilding.makeSelectN(1, function($selected) {
                var ident = $selected.data('ident');
                fsm.finish(ident, cardIdent, null);
            });

            $cancelBtn.show().prop('disabled', false).off('click').click(function() {
                fsm.cancel();
            });
        };

        fsm.onleaveSelectSite = function() {
            selBuilding.reset();
            selHand.reset();
            selSite.reset();
        };

        fsm.onenterFinish = function(event, from, to, card, building, site) {
            $dialog.text('Waiting...');
            actionCallback(card, building, site);
        };

        fsm.start();

        return;
        
    };

    AB.fountain = function(display, fountainCard, ootAllowed, hasRoad,
            hasTower, hasScriptorium,
            actionCallback)
    {
        var $dialog = display.dialog;

        var $sites = display.zoneCards('sites');
        var selSite = null;

        var selBuilding = null;

        var $skipBtn = display.button('skip');

        var cardName = Util.cardName(fountainCard);
        var cardProp = Util.cardProperties(cardName);
        var cardMaterial = cardProp.material;

        var fsm = FSM.create({
            initial: 'Start',

            events: [
                { name: 'start', from: 'Start', to: 'Select' },
                { name: 'finish', from: 'Select', to: 'Finish' },
            ]
        });

        fsm.onenterSelect = function() {

            var $sitesAllowed = $($sites).filter(function(i, site) {
                    var $site = $(site);
                    var siteAvail = $site.data('inTown') > 0 ||
                            (ootAllowed && $site.data('outOfTown') > 0);
                    var siteMatch = cardName === 'Statue' || 
                            $site.data('material') === cardProp.material;

                    return siteAvail && siteMatch;
            });

            selSite = new Selectable($sitesAllowed);
            selSite.makeSelectN(1, function($selected) {
                var siteName = $selected.data('material');
                fsm.finish(fountainCard, null, siteName);
            });

            var $buildings = display.buildings(AB.playerIndex).filter(
                    function(i, building) {
                        var $building = $(building);
                        var materials = $building.data('materials');

                        var materialMatch = $.inArray(cardMaterial, materials) !== -1;
                        var notComplete = !$building.data('complete');
                        var roadMatch = hasRoad && $.inArray('Stone', materials) !== -1;
                        var scriptoriumMatch = hasScriptorium && cardMaterial === 'Marble';
                        var towerMatch = hasTower && (cardMaterial === 'Rubble');

                        return notComplete &&
                                (materialMatch || roadMatch ||
                                 scriptoriumMatch || towerMatch);
                    });

            selBuilding = new Selectable($buildings);
            selBuilding.makeSelectN(1, function($selected) {
                var ident = $selected.data('ident');
                fsm.finish(ident, fountainCard, null);
            });

            $dialog.text('Use '+cardName+' in building or start a new building '+
                    'by clicking on a site. Skip action to draw it instead.');

            $skipBtn.show().prop('disabled', false).off('click').click(function() {
                fsm.finish(null, null, null);
            });
        };

        fsm.onleaveSelect = function() {
            selBuilding.reset();
            selSite.reset();
            $skipBtn.show().prop('disabled', true).off('click');
        };

        fsm.onenterFinish = function(event, from, to, card, building, site) {
            $dialog.text('Waiting...');
            actionCallback(card, building, site);
        };

        fsm.start();

        return;
    };

    AB.prison = function(display, actionCallback) {
        var $dialog = display.dialog;

        var selBuilding = null;

        var $skipBtn = display.button('skip');

        $skipBtn.show().prop('disabled', false).off('click').click(function() {
            selBuilding.reset();
            actionCallback(null);
        });

        $dialog.text('Choose opponent\'s building.');

        var $my_buildings = display.buildings(AB.playerIndex);
        var my_building_names = $my_buildings.map(function(i, building){
                var ident = $(building).data('ident');
                return Util.cardName(ident);
        }).get();

        var $buildings = $('.building').not(display.buildings(AB.playerIndex)).filter(
                function(i, building) {
            var $building = $(building);
            var name = Util.cardName($building.data('ident'));

            return $building.data('complete') && $.inArray(name, my_building_names) == -1;
        });

        selBuilding = new Selectable($buildings);
        selBuilding.makeSelectN(1, function($selected) {
            var ident = $selected.data('ident');
            actionCallback(ident);
            selBuilding.reset();
            $dialog.text('Waiting...');
        });

        return;
    };

    AB.stairway = function(display, hasRoad, hasTower, hasScriptorium,
            hasArchway, actionCallback)
    {
        var $dialog = display.dialog;

        var $stockpile = display.zoneCards('stockpile', AB.playerIndex);
        var selStockpile = new Selectable($stockpile);

        var $pool = display.zoneCards('pool');
        var selPool = new Selectable($pool);

        var selBuilding = null;

        var $cancelBtn = display.button('cancel');
        var $skipBtn = display.button('skip');

        var fromPool = false;

        var fsm = FSM.create({
            initial: 'Start',

            events: [
                { name: 'start', from: 'Start', to: 'SelectMaterial' },
                { name: 'material', from: 'SelectMaterial', to: 'SelectBuilding' },
                { name: 'building', from: 'SelectBuilding', to: 'Finish' },
                { name: 'cancel', from: 'SelectBuilding', to: 'SelectMaterial' },
            ]
        });

        fsm.onenterSelectMaterial = function() {
            if(hasArchway) {
                $dialog.text('Choose card in stockpile or pool '+
                        'to add to opponent\'s building.');
            } else {
                $dialog.text('Choose card in stockpile '+
                        'to add to opponent\'s building.');
            }

            selStockpile.makeSelectN(1, function($selected) {
                fsm.material();
            });

            if(hasArchway) {
                selPool.makeSelectN(1, function($selected) {
                    fromPool = true;
                    fsm.material();
                });
            }

            $skipBtn.show().prop('disabled', false).off('click').click(function() {
                selStockpile.reset();
                selPool.reset()
                actionCallback(null, null);
            });
        };

        fsm.onleaveSelectHand = function() {
            selStockpile.makeUnselectable();
            if(hasArchway) {selPool.makeUnselectable();}

            Util.off($skipBtn);
        };

        fsm.onenterSelectBuilding = function() {
            $dialog.text('Choose opponent\'s building.');

            var zone = fromPool ? selPool : selStockpile;

            var cardIdent = AB._extractCardId(zone);
            var cardName = Util.cardName(cardIdent);
            var cardProp = Util.cardProperties(cardName);
            var cardMaterial = cardProp.material;

            var $buildings = $('.building').not(display.buildings(AB.playerIndex)).filter(
                    function(i, building) {
                var $building = $(building);
                var materials = $building.data('materials');

                var materialMatch = $.inArray(cardMaterial, materials) !== -1;
                var complete = $building.data('complete');
                var roadMatch = hasRoad && $.inArray('Stone', materials) !== -1;
                var scriptoriumMatch = hasScriptorium && cardMaterial === 'Marble';
                var towerMatch = hasTower && (cardMaterial === 'Rubble');

                return complete &&
                        (materialMatch || roadMatch ||
                         scriptoriumMatch || towerMatch);
            });

            selBuilding = new Selectable($buildings);
            selBuilding.makeSelectN(1, function($selected) {
                var ident = $selected.data('ident');
                actionCallback(ident, cardIdent);
                fsm.finish();
            });

            $cancelBtn.show().prop('disabled', false).off('click').click(function() {
                fsm.cancel();
            });
        };

        fsm.onleaveSelectBuilding = function() {
            selBuilding.reset();
            selPool.reset();
            selStockpile.reset();
        };

        fsm.onenterFinish = function() {
            $dialog.text('Waiting...');
        };

        fsm.start();

        return;
    };


    AB.architect = function(display, ootAllowed, hasRoad, hasTower, hasScriptorium,
            hasArchway, actionCallback)
    {
        var $dialog = display.dialog;

        var $handcards = display.zoneCards('hand', AB.playerIndex).not('.jack');
        var selHand = new Selectable($handcards);

        var $stockpile = display.zoneCards('stockpile', AB.playerIndex);
        var selStockpile = new Selectable($stockpile);

        var $pool = display.zoneCards('pool');
        var selPool = new Selectable($pool);

        var selBuilding = null;

        var $sites = display.zoneCards('sites');
        var selSite = null;

        var $cancelBtn = display.button('cancel');
        var $skipBtn = display.button('skip');

        var fromPool = false;

        var fsm = FSM.create({
            initial: 'Start',

            events: [
                { name: 'start', from: 'Start', to: 'SelectHand' },
                { name: 'buildnew', from: 'SelectHand', to: 'SelectSite' },
                { name: 'add', from: 'SelectHand', to: 'SelectBuilding' },
                { name: 'cancel', from: 'SelectSite', to: 'SelectHand' },
                { name: 'cancel', from: 'SelectBuilding', to: 'SelectHand' },
                { name: 'finish', from: 'SelectSite', to: 'Finish' },
                { name: 'finish', from: 'SelectBuilding', to: 'Finish' },
            ]
        });

        fsm.onenterSelectHand = function() {
            if(hasArchway) {
                $dialog.text('Choose card in hand to start a new building or '+
                        'card in stockpile or pool to add to existing building.');
            } else {
                $dialog.text('Choose card in hand to start a new building or '+
                        'card in stockpile to add to existing building.');
            }


            selHand.makeSelectN(1, function($selected) {
                fsm.buildnew();
            });

            selStockpile.makeSelectN(1, function($selected) {
                fsm.add();
            });

            if(hasArchway) {
                selPool.makeSelectN(1, function($selected) {
                    fromPool = true;
                    fsm.add();
                });
            }

            $skipBtn.show().prop('disabled', false).off('click').click(function() {
                selHand.reset();
                selStockpile.reset();
                selPool.reset()
                actionCallback(null, null, null, false);
            });
        };

        fsm.onleaveSelectHand = function() {
            selHand.makeUnselectable();
            selStockpile.makeUnselectable();
            if(hasArchway) {selPool.makeUnselectable();}

            Util.off($skipBtn);
            $skipBtn.hide();
        };

        fsm.onenterSelectSite = function() {
            $dialog.text('Choose site to start a new building.');

            var cardIdent = AB._extractCardId(selHand);
            var cardName = Util.cardName(cardIdent);
            var cardProp = Util.cardProperties(cardName);
            var cardMaterial = cardProp.material;

            var $sitesAllowed = $(display.zoneCards('sites'))
                    .filter(function(i, site) {
                        var $site = $(site);
                        var siteAvail = $site.data('inTown') > 0 ||
                                (ootAllowed && $site.data('outOfTown') > 0);
                        var siteMatch = cardName === 'Statue' || 
                                $site.data('material') === cardProp.material;

                        return siteAvail && siteMatch;
            });

            selSite = new Selectable($sitesAllowed);
            selSite.makeSelectN(1, function($selected) {
                var siteName = $selected.data('material');
                actionCallback(cardIdent, null, siteName, false);
                fsm.finish();
            });

            $cancelBtn.show().prop('disabled', false).off('click').click(function() {
                fsm.cancel();
            });

        };

        fsm.onleaveSelectSite = function() {
            selHand.reset();
            selSite.reset();
            Util.off($skipBtn);
            $skipBtn.hide();
            Util.off($cancelBtn);
            $cancelBtn.hide();
        };

        fsm.onenterSelectBuilding = function() {
            $dialog.text('Choose building to add material to.');

            var zone = fromPool ? selPool : selStockpile;

            var cardIdent = AB._extractCardId(zone);
            var cardName = Util.cardName(cardIdent);
            var cardProp = Util.cardProperties(cardName);
            var cardMaterial = cardProp.material;

            var $buildings = display.buildings(AB.playerIndex).filter(
                    function(i, building) {
                var $building = $(building);
                var materials = $building.data('materials');

                var materialMatch = $.inArray(cardMaterial, materials) !== -1;
                var notComplete = !$building.data('complete');
                var roadMatch = hasRoad && $.inArray('Stone', materials) !== -1;
                var scriptoriumMatch = hasScriptorium && cardMaterial === 'Marble';
                var towerMatch = hasTower && cardMaterial === 'Rubble';

                return notComplete &&
                        (materialMatch || roadMatch ||
                         scriptoriumMatch || towerMatch);
            });

            selBuilding = new Selectable($buildings);
            selBuilding.makeSelectN(1, function($selected) {
                var ident = $selected.data('ident');
                actionCallback(ident, cardIdent, null, fromPool);
                fsm.finish();
            });

            $cancelBtn.show().prop('disabled', false).off('click').click(function() {
                fsm.cancel();
            });
        };

        fsm.onleaveSelectBuilding = function() {
            selBuilding.reset();
            selPool.reset();
            selStockpile.reset();
            Util.off($skipBtn);
            $skipBtn.hide();
            Util.off($cancelBtn);
            $cancelBtn.hide();
        };

        fsm.onenterFinish = function() {
            $dialog.text('Waiting...');
        };

        fsm.start();

        return;
        
    };

    return AB;
});
