define(['jquery', 'jqueryui', 'fsm', 'util', 'selectable'],
function($, _, FSM, Util, Selectable){
    var mod = {
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

    mod.laborer = function(display, hasDock, actionCallback) {
        var ip = mod.playerIndex+1;
        var $poolpick = null;
        var $handpick = null;
        var $pool = display.zoneCards('pool');
        var $handcards = display.zoneCards('hand', ip).not('.jack');
        var $dialog = display.dialog;
        var $okBtn = display.button('ok');
        var $skipBtn = display.button('skip');

        if(hasDock) {
            $dialog.text('Select card from pool and/or hand.');
        } else { 
            $dialog.text('Select card from pool.');
        }

        var selPool = new Selectable($pool);
        selPool.makeSelectN(1);
        if(hasDock) {
            var selHand = new Selectable($handcards);
            selHand.makeSelectN(1);
        }
        $okBtn.show().prop('disabled', false).click(function(e) {
            $poolpicks = selPool.selected();
            var frompool = $poolpicks.length 
                    ? Util.extractCardIds($poolpicks)[0]
                    : null;
            selPool.reset();

            var fromhand = null;
            if(hasDock) {
                $handpicks = selHand.selected();
                fromhand = $handpicks.length
                        ? Util.extractCardIds($handpicks)[0]
                        : null;
                selHand.reset();
            }

            actionCallback(fromhand, frompool);
        });

        return;
    };
    
    mod.patronFromPool = function(display, actionCallback) {
        var ip = mod.playerIndex+1;
        var $pool = display.zoneCards('pool');
        var $dialog = display.dialog;
        var $skipBtn = display.button('skip');

        $dialog.text('Select client from pool.');

        var sel = new Selectable($pool);
        sel.makeSelectN(1, function($selected) {
            var selection = Util.extractCardIds($selected)[0];

            sel.reset();
            actionCallback(selection);
        });

        $skipBtn.show().prop('disabled', false).click(function(e) {
            sel.reset();
            actionCallback(null);
        });

        return;
    };
    
    mod.patronFromHand = function(display, actionCallback) {
        var ip = mod.playerIndex+1;
        var $hand = display.zoneCards('hand', ip).not('.jack');
        var $dialog = display.dialog;
        var $skipBtn = display.button('skip');

        $dialog.text('Select client from hand.');

        var sel = new Selectable($hand);
        sel.makeSelectN(1, function($selected) {
            var selection = Util.extractCardIds($selected)[0];

            sel.reset();
            actionCallback(selection);
        });

        $skipBtn.show().prop('disabled', false).click(function(e) {
            sel.reset();
            actionCallback(null);
        });

        return;
    };

    mod.useLatrine = function(display, actionCallback) {
        var ip = mod.playerIndex+1;
        var $hand = display.zoneCards('hand', ip).not('.jack');
        var $dialog = display.dialog;
        var $skipBtn = display.button('skip');

        $dialog.text('Use latrine? Select card from hand.');

        var sel = new Selectable($hand);
        sel.makeSelectN(1, function($selected) {
            var selection = Util.extractCardIds($selected)[0];

            sel.reset();
            actionCallback(selection);
        });

        $skipBtn.show().prop('disabled', false).click(function(e) {
            sel.reset();
            actionCallback(null);
        });

        return;
    };
    
    mod.useSewer = function(display, actionCallback) {
        var ip = mod.playerIndex+1;
        var $camp = $('#p'+ip+'-camp> .card').not('.jack');
        var $dialog = display.dialog;
        var $skipBtn = display.button('skip');
        var $okBtn = display.button('ok');

        $dialog.text('Select cards to move from Camp to Stockpile with Sewer.');

        var sel = new Selectable($camp);
        sel.makeSelectAny();

        $skipBtn.show().prop('disabled', false).click(function(e) {
            sel.reset();
            actionCallback([null]);
        });

        $okBtn.prop('disabled', false).click(function(e) {
            var card_ids = Util.extractCardIds(sel.selected());
            sel.reset();
            actionCallback(card_ids);
        });

        return;
    };
    
    mod.legionary = function(display, count, actionCallback) {
        var ip = mod.playerIndex+1;
        var $hand = display.zoneCards('hand', ip).not('.jack');
        var $dialog = display.dialog;
        var $skipBtn = display.button('skip');

        $dialog.text('Reveal cards for Legionary or skip remaining actions.');

        var sel = new Selectable($hand);
        function finished($selected) {
            var cards = Util.extractCardIds($selected);

            sel.reset();
            actionCallback(cards);
        };

        sel.makeSelectN(count, finished);

        $skipBtn.show().prop('disabled', false).click(function(e) {
            var $selected = sel.selected();
            finished($selected);
        });

        return;
    };
    
    mod.giveCards = function(display, materials, hasBridge,
            hasColiseum, immune, actionCallback)
    {

        var ip = mod.playerIndex+1;
        var $hand = display.zoneCards('hand', ip).not('.jack');
        var $dialog = display.dialog;
        var $gloryBtn = display.button('glory');

        $dialog.text('Rome demands ' + materials.join(', ')+'!');

        function gloryButton() {
            $gloryBtn.show().prop('disabled', false).click(function(e) {
                actionCallback([]);
            });
        };

        if(immune) { gloryButton(); return; }

        materialCounts = {Rubble: 0, Wood: 0, Concrete: 0, Brick: 0, Stone: 0, Marble: 0};
        materials.forEach(function(item) {
                materialCounts[item]+=1;
        });

        var cards = [];
        var selections = {};

        for(var m in materialCounts) {
            var $cards = $hand.filter('.'+m.toLowerCase());
            materialCounts[m] = Math.min(materialCounts[m], $cards.length);
            var count = materialCounts[m];
            if(count) {
                var s = new Selectable($cards);
                s.makeSelectN(count, function($selected) {
                    // Check if all Selectables are done. Return if not.
                    for(var mat in selections) {
                        var selectable = selections[mat];
                        if(selectable.selected().length !== materialCounts[mat]) {
                            return;
                        }
                    }
                    // If done, accumulate cards from all and reset them.
                    for(var mat in selections) {
                        var selection = selections[mat];
                        cards.push.apply(cards,Util.extractCardIds(selection.selected()));
                        selection.reset();
                    }
                    actionCallback(cards);
                });
                selections[m] = s;
            }
        }

        // If we don't have any of the materials, no Selectables will be made.
        if(Object.keys(selections).length == 0) {
            gloryButton();
        }

        return;
    };

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
     *          [{text: 'Yes', return: true},
     *           {text: 'No', return: false}
     *           ], actionCallbackFunction);
     */
    mod.singleChoice = function(display, dialog, choices, actionCallback) {
        var ip = mod.playerIndex+1;
        var $dialog = display.dialog.text(dialog);

        var choiceButtons = display.choiceBtns;

        $.each(choices, function(i, item) {
            choiceButtons.append($('<button/>').click(function(e) {
                actionCallback(item.return);
                choiceButtons.children('button').prop('disabled', true);
                choiceButtons.empty();
            }).text(item.text));
        });

        return;
    };
        
    mod.merchant = function(display, hasBasilica, hasAtrium, actionCallback) {
        var ip = mod.playerIndex+1;

        var $stockpile = display.zoneCards('stockpile', ip);
        var $handcards = display.zoneCards('hand', ip).not('.jack');
        var $dialog = display.dialog;
        var $okBtn = display.button('ok');

        if(hasAtrium && hasBasilica) {
            $dialog.text('Select card from stockpile or deck, and one from your hand.');
        } else if(hasAtrium) { 
            $dialog.text('Select card from stockpile or deck.');
        } else if(hasBasilica) { 
            $dialog.text('Select card from stockpile and/or hand.');
        } else { 
            $dialog.text('Select card from stockpile.');
        }

        if(hasAtrium) {
            $stockpile.extend(display.deck);
        }
        var selStockpile = new Selectable($stockpile);
        selStockpile.makeSelectN(1);

        if(hasBasilica) {
            var selHand = new Selectable($handcards);
            selHand.makeSelectN(1);
        }

        $okBtn.show().prop('disabled', false).click(function(event) {
            var $stockpilePick = selStockpile.selected();

            var fromStockpile = null;
            var fromDeck = false;
            if($stockpilePick.length) {
                fromDeck = $stockpilePick[0].id === 'deck';

                if(!fromDeck) {
                    fromStockpile = Util.extractCardIds($stockpilePick)[0];
                }
            } else {
                fromStockpile = null;
            }
            selStockpile.reset();

            var fromHand = null;
            if(hasBasilica) {
                var $handPick = selHand.selected();
                fromHand = $handPick.length
                        ? Util.extractCards($handPick)[0]
                        : null;
                selHand.reset();

            }

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
    mod.leadRole = function(display, hasPalace, petitionMin,
            petitionMax, actionCallback)
    {
        var $dialog = display.dialog;
        var ip = mod.playerIndex+1;

        var $handcards = display.zoneCards('hand', ip);
        var selHand = new Selectable($handcards);

        var $handNoJacks = $($handcards).not('.jack');
        var selHandNoJacks = new Selectable($handNoJacks);

        var role = null;
        var $roleBtns = display.roleButtons();
        var selRole = new Selectable($roleBtns);

        var $cancelBtn = display.button('cancel');
        var $okBtn = display.button('ok');
        var $petitionBtn = display.button('petition');

        var $deck = display.deck;
        var $jacks = display.jacks;
        var $lead = display.button('lead-role');

        var fsm = FSM.create({
            initial: 'Start',

            events: [
                { name: 'start', from: 'Start', to: 'ThinkerOrLead' },
                { name: 'lead', from: 'ThinkerOrLead', to: 'SelectingCards' },
                { name: 'think', from: 'ThinkerOrLead', to: 'Thinker' },
                { name: 'orders', from: 'SelectingCards', to: 'HaveRole' },
                { name: 'cancel', from: 'SelectingCards', to: 'ThinkerOrLead' },
                { name: 'jack', from: 'SelectingCards', to: 'JackRole' },
                { name: 'petition', from: 'SelectingCards', to: 'PetitionFirst' },
                { name: 'first', from: 'PetitionFirst', to: 'PetitionRest' },
                { name: 'cancel', from: 'PetitionFirst', to: 'SelectingCards' },
                { name: 'cancel', from: 'PetitionRest', to: 'PetitionFirst' },
                { name: 'petition', from: 'PetitionRest', to: 'PetitionRole' },
                { name: 'role', from: 'PetitionRole', to: 'HaveRole' },
                { name: 'cancel', from: 'PetitionRole', to: 'SelectingCards' },
                { name: 'role', from: 'JackRole', to: 'HaveRole' },
                { name: 'cancel', from: 'JackRole', to: 'SelectingCards' },
                { name: 'nopalace', from: 'HaveRole', to: 'Finish' },
            /*
                { name: 'palace', from: 'haverole', to: 'palace' },
                { name: 'petition', from: 'selectingcards', to: 'petition' },
                { name: 'done', from: 'petition', to: 'petitionrole' },
                { name: 'role', from: 'petitionrole', to: 'palace' },
                { name: 'orders', from: 'palace', to: 'palace' },
                { name: 'jack', from: 'palace', to: 'palacejackrole' },
                { name: 'petition', from: 'palace', to: 'palacepetition' },
                { name: 'done', from: 'palacepetition', to: 'palace' }
            */
            ]
        });

        fsm.onenterThinkerOrLead = function() {
            $dialog.text('Thinker or lead a role?');

            if($jacks.data('nCards') > 0) {
                $jacks.addClass('selectable');
                $jacks.off('click').one('click', function(ev) {
                    actionCallback(Util.Action.THINKERTYPE, [true]);
                    fsm.think();
                });
            }

            $deck.addClass('selectable');
            $deck.off('click').one('click', function(ev) {
                actionCallback(Util.Action.THINKERTYPE, [false]);
                fsm.think();
            });

            $lead.show().prop('disabled', false).one('click', function(ev) {
                fsm.lead();
            });
        };

        fsm.onleaveThinkerOrLead = function() {
            Util.off($lead, $deck, $jacks);
            $jacks.removeClass('selectable');
            $deck.removeClass('selectable');
        };

        fsm.onenterSelectingCards = function() {
            $dialog.text('Select a card to lead.');

            $cancelBtn.show().prop('disabled', false).one('click', function(event) {
                selHand.reset();
                fsm.cancel();
            });

            $petitionBtn.show().prop('disabled', false).one('click', function(event) {
                fsm.petition();
            });
            
            selHand.makeSelectN(1, function($selected) {
                selHand.makeUnselectable();
                var $card = $selected.eq(0);
                var cardName = Util.extractCardNames($selected)[0];
                if(cardName == 'Jack') {
                    fsm.jack();
                } else {
                    role = Util.extractCardProperties($selected)[0].role;
                    fsm.orders();
                }
            });
        };

        fsm.onleaveSelectingCards = function() {
            Util.off($cancelBtn, $petitionBtn);
        };

        fsm.onenterJackRole = function() {
            $dialog.text('Pick role for Jack.');

            $cancelBtn.show().prop('disabled', false).one('click', function(event) {
                selRole.reset();
                selHand.reset();
                fsm.cancel();
            });

            $roleBtns.show().prop('disabled', false);
            selRole.makeSelectN(1, function($selected) {
                selRole.makeUnselectable();
                role = $selected.eq(0).data('role');
                fsm.role();
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

            $cancelBtn.show().prop('disabled', false).one('click', function(ev) {
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

            $cancelBtn.show().prop('disabled', false).one('click', function(ev) {
                selHand.reset();
                fsm.cancel();
            });

            $okBtn.show().prop('disabled', false).on('click', function(ev) {
                var $selected = selHand.selected();
                if($selected.length < petitionMin) {
                    $dialog.text('Not enough cards. Pick at least ' +
                        petitionMin + ' cards for petition');
                } else {
                    selHand.makeUnselectable();
                    fsm.petition();
                }
            });
        };

        fsm.onleavePetitionRest = function() {
            Util.off($cancelBtn, $okBtn);
        };

        fsm.onenterPetitionRole = function() {
            $dialog.text('Pick role for Petition.');

            $cancelBtn.prop('disabled', false).one('click', function(event) {
                selRole.reset();
                selHand.reset();
                fsm.cancel();
            });

            $roleBtns.show().prop('disabled', false);
            selRole.makeSelectN(1, function($selected) {
                selRole.makeUnselectable();
                role = $selected.eq(0).data('role');
                fsm.role();
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

        fsm.onenterFinish = function() {
            var card_ids = Util.extractCardIds(selHand.selected());
            actionCallback(Util.Action.LEADROLE, [role, 1].concat(card_ids));

            selRole.reset();
            selHand.reset();
        };

        fsm.start();

        return;
    };

    mod.followRole = function(display, role, hasPalace, petitionMin,
            petitionMax, actionCallback)
    {
        var materialLed = Util.roleToMaterial(role);
        var $dialog = display.dialog;
        var ip = mod.playerIndex+1;

        var $hand = display.zoneCards('hand', ip).not('.jack');
        var selHand = new Selectable($hand);
        var $matchingHand = display.zoneCards('hand', ip).filter(
                '.'+materialLed.toLowerCase()+',.jack');
        var selMatching = new Selectable($matchingHand);

        var $cancelBtn = display.button('cancel');
        var $okBtn = display.button('ok');
        var $petitionBtn = display.button('petition');

        var $piles = display.decks;
        var $deck = display.deck;
        var $jacks = display.jacks;

        var fsm = FSM.create({
            initial: 'Start',

            events: [
                { name: 'start', from: 'Start', to: 'SelectingCards' },
                { name: 'follow', from: 'SelectingCards', to: 'HaveFirst' },
                { name: 'think', from: 'SelectingCards', to: 'Thinker' },
                { name: 'petition', from: 'SelectingCards', to: 'PetitionFirst' },
                { name: 'first', from: 'PetitionFirst', to: 'PetitionRest' },
                { name: 'cancel', from: 'PetitionFirst', to: 'SelectingCards' },
                { name: 'cancel', from: 'PetitionRest', to: 'PetitionFirst' },
                { name: 'petition', from: 'PetitionRest', to: 'HaveFirst' },
                { name: 'nopalace', from: 'HaveFirst', to: 'Finish' },
            /*
                { name: 'palace', from: 'haverole', to: 'palace' },
                { name: 'petition', from: 'selectingcards', to: 'petition' },
                { name: 'done', from: 'petition', to: 'petitionrole' },
                { name: 'role', from: 'petitionrole', to: 'palace' },
                { name: 'orders', from: 'palace', to: 'palace' },
                { name: 'jack', from: 'palace', to: 'palacejackrole' },
                { name: 'petition', from: 'palace', to: 'palacepetition' },
                { name: 'done', from: 'palacepetition', to: 'palace' }
            */
            ]
        });

        fsm.onenterSelectingCards = function() {
            display.dialog.text('Thinker or follow '+role+'?');

            if($jacks.data('nCards') > 0) {
                $jacks.addClass('selectable');
                $jacks.one('click', function(ev) {
                    actionCallback(Util.Action.FOLLOWROLE, [true, 0, null]);
                    actionCallback(Util.Action.THINKERTYPE, [true]);
                    fsm.think();
                });
            }

            $deck.addClass('selectable');
            $deck.one('click', function(ev) {
                actionCallback(Util.Action.FOLLOWROLE, [true, 0, null]);
                actionCallback(Util.Action.THINKERTYPE, [false]);
                fsm.think();
            });

            $petitionBtn.show().prop('disabled', false).one('click', function(event) {
                fsm.petition();
            });
            
            selMatching.makeSelectN(1, function($selected) {
                selMatching.makeUnselectable();
                var $card = $selected.eq(0);
                fsm.follow();
            });
        };

        fsm.onleaveSelectingCards = function() {
            Util.off($deck, $jacks, $petitionBtn);
            $jacks.removeClass('selectable');
            $deck.removeClass('selectable');
        };

        fsm.onenterPetitionFirst = function() {
            $dialog.text('Pick at least '+petitionMin+' cards for petition');

            selMatching.reset();
            selHand.reset();
            selHand.makeSelectN(1, function($selected) {
                fsm.first($selected);
            });

            $cancelBtn.show().prop('disabled', false).one('click', function(ev) {
                selHand.reset();
                fsm.cancel();
            });
        };

        fsm.onleavePetitionFirst = function() {
            Util.off($cancelBtn);
        };

        fsm.onenterPetitionRest = function($selected) {
            $dialog.text('Pick at least '+petitionMin+' cards for petition');

            selHand.reset();
            selHand.makeSelectN(petitionMax);
            $selected.each(function(i, el) {
                selHand.select($(el));
            });

            $cancelBtn.show().prop('disabled', false).on('click', function(ev) {
                selHand.reset();
                fsm.cancel();
            });

            $okBtn.show().prop('disabled', false).on('click', function(ev) {
                var $selected = selHand.selected();
                if($selected.length < petitionMin) {
                    $dialog.text('Not enough cards. Pick at least ' +
                        petitionMin + ' cards for petition');
                } else {
                    selHand.makeUnselectable();
                    fsm.petition();
                }
            });
        };

        fsm.onleavePetitionRest = function() {
            Util.off($cancelBtn, $okBtn);
        };

        fsm.onenterHaveFirst = function() {
            if(hasPalace) {
                fsm.palace();
            } else {
                fsm.nopalace();
            }
        };

        fsm.onenterFinish = function() {
            var petition_ids = Util.extractCardIds(selHand.selected());
            var card_ids = Util.extractCardIds(selMatching.selected());
            console.log('card ids: ' + card_ids);
            console.log('petition ids: ' + petition_ids);

            selHand.reset();
            selMatching.reset();

            actionCallback(Util.Action.FOLLOWROLE, [false, 1].concat(card_ids).concat(petition_ids));
        };

        fsm.start();

        return;
    };

    mod.craftsman = function(display, ootAllowed, hasRoad, hasTower, hasScriptorium,
            actionCallback)
    {
        var $dialog = display.dialog;
        var ip = mod.playerIndex+1;

        var $handcards = display.zoneCards('hand', ip).not('.jack');
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

            $skipBtn.show().prop('disabled', false).off('click').click(function(event) {
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

            var cardIdent = Util.extractCardIds(selHand.selected())[0];
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

            var $buildings = $('#p'+ip+'-buildings > .building').filter(
                    function(i, building) {
                var $building = $(building);
                var materials = $building.data('materials');

                var materialMatch = $.inArray(cardMaterial, materials)>-1;
                var notComplete = !$building.data('complete');
                var roadMatch = hasRoad && $.inArray('Stone', materials)>-1;
                var scriptoriumMatch = hasScriptorium && $.inArray('Marble', materials)>-1;
                var towerMatch = cardMaterial === 'Rubble';

                console.log(notComplete &&
                        (materialMatch || roadMatch ||
                         scriptoriumMatch || towerMatch));
                return notComplete &&
                        (materialMatch || roadMatch ||
                         scriptoriumMatch || towerMatch);
            });

            selBuilding = new Selectable($buildings);
            selBuilding.makeSelectN(1, function($selected) {
                var ident = $selected.data('ident');
                fsm.finish(ident, cardIdent, null);
            });

            $cancelBtn.show().prop('disabled', false).off('click').click(function(event) {
                fsm.cancel();
            });
        };

        fsm.onleaveSelectSite = function() {
            console.dir(selSite.selected());
            selBuilding.reset();
            selHand.reset();
            selSite.reset();
            //TODO: the sites don't actually lose the selected class, even though reset is called.
        };

        fsm.onenterFinish = function(event, from, to, card, building, site) {
            $dialog.text('Waiting...');
            actionCallback(card, building, site);
        };

        fsm.start();

        return;
        
    };

    mod.architect = function(display, ootAllowed, hasRoad, hasTower, hasScriptorium,
            hasArchway, actionCallback)
    {
        var $dialog = display.dialog;
        var ip = mod.playerIndex+1;

        var $handcards = display.zoneCards('hand', ip).not('.jack');
        var selHand = new Selectable($handcards);

        var $stockpile = display.zoneCards('stockpile', ip);
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

            $skipBtn.show().prop('disabled', false).off('click').click(function(event) {
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
        };

        fsm.onenterSelectSite = function() {
            $dialog.text('Choose site to start a new building.');

            var cardIdent = Util.extractCardIds(selHand.selected())[0];
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
        };

        fsm.onleaveSelectSite = function() {
            selHand.reset();
            selSite.reset();
        };

        fsm.onenterSelectBuilding = function() {
            $dialog.text('Choose building to add material to.');

            var $card;
            if(fromPool) {
                $card = selPool.selected();
            } else {
                $card = selStockpile.selected();
            }

            var cardIdent = Util.extractCardIds($card)[0];
            var cardName = Util.cardName(cardIdent);
            var cardProp = Util.cardProperties(cardName);
            var cardMaterial = cardProp.material;

            var $buildings = $('#p'+ip+'-buildings > .building').filter(
                    function(i, building) {
                var $building = $(building);
                var materials = $building.data('materials');

                var materialMatch = $.inArray(cardMaterial, materials) !== -1;
                var notComplete = !$building.data('complete');
                var roadMatch = hasRoad && $.inArray('Stone', materials);
                var scriptoriumMatch = hasScriptorium && $.inArray('Marble', materials);
                var towerMatch = cardMaterial === 'Rubble';

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

            $cancelBtn.show().prop('disabled', false).off('click').click(function(event) {
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

    return mod;
});
