define(['jquery', 'jqueryui', 'fsm', 'util', 'zone'],
function($, _, FSM, Util, Zone){
    var mod = {
        playerIndex: null
    };

    mod.laborer = function(hasDock, actionCallback) {
        var ip = mod.playerIndex+1;
        var $poolpick = null;
        var $handpick = null;
        var $poolcards = $('#pool > .card');
        var $handcards = $('#p'+ip+'-hand > .card').not('.jack');
        var $dialog = $('#dialog');
        var $skipbtn = $('#skip-btn');
        var $okbtn = $('#ok-btn');

        if(hasDock) {
            $dialog.text('Select card from pool and/or hand.');
        } else { 
            $dialog.text('Select card from pool.');
        }

        var zhand = new Zone($handcards);
        var zpool = new Zone($poolcards);
        zhand.makeSelectN(1);
        zpool.makeSelectN(1);
        $okbtn.prop('disabled', false);
        $okbtn.click(function(event) {
            $poolpicks = zpool.selected();
            $handpicks = zhand.selected();

            var frompool = $poolpicks.length ? parseInt($poolpicks[0].id.replace('card', '')) : 'None';
            var fromhand = $handpicks.length ? parseInt($handpicks[0].id.replace('card', '')) : 'None';

            zhand.reset();
            zpool.reset();

            actionCallback(fromhand, frompool);
        });

        return;


        var fsm = FSM.create({
            initial: 'start',

            events: [
                { name: 'start', from: 'start', to: 'noselection' },
                { name: 'pickpool', from: 'noselection', to: 'poolselected' },
                { name: 'pickhand', from: 'noselection', to: 'handselected' },
                { name: 'pickhand', from: 'poolselected', to: 'bothselected' },
                { name: 'pickpool', from: 'handselected', to: 'bothselected' },
                { name: 'skip', from: 'noselection', to: 'bothselected' }
            ],
        });
        
        
        // Enter LABORER
        //  disable all;
        //      hand = Zone('#p1-hand > .card');
        //      hand.reset();
        //      pool = Zone('#pool > .card');
        //      pool.reset();
        //  enable "select one" on pool cards, with "de-selection"
        //      pool.selectOne(de-selection=true))
        //  if dock enable "select one" on non-jack hand cards with "de-selection"
        //      hand.selectOne(de-selection=true)
        //      // We press the okay button to select, so we don't need 
        //      // callbacks on selection.
        //
        //  enable okay button --> finish selection
        //      okay.enable();
        //      okay.onclick() {
        //          handcard, poolcard = hand.selection[0], zone.selection[0];
        //          hand.reset(); pool.reset();

        fsm.onenternoselection = function(event, from, to) {
            
            $poolcards.addClass('selectable');
            $poolcards.click(function(ev) {
                var $card = $(ev.target);
                $card.addClass('selected');

                fsm.pickpool($card);
            });

            if(hasDock) {
                $handcards.addClass('selectable');

                $handcards.click(function(ev) {
                    var $card = $(ev.target);
                    $card.addClass('selected');

                    fsm.pickhand($card);
                });
            }

            $skipbtn.prop('disabled', false);
            $skipbtn.click(function() {
                fsm.skip();
            });

        };

        fsm.onleavenoselection = function() {
            $skipbtn.off('click');
        };

        fsm.onenterpoolselected = function(event, from, to, $card) {
            $poolpick = $card;
            if(!hasDock) {
                fsm.pickhand(null);
            } else {
                $dialog.text('Selected ' + $card.text() + ' from pool. Select card from hand.')
                $poolcards.not($card).removeClass('selectable');
                $poolcards.off('click');
                // pickhand onclick should still work for hand cards.
                
                // Could add click() for selected card to unpick.

                $skipbtn.click(function() {
                    fsm.pickhand(null);
                });
            }
        };

        fsm.onleavepoolselected = function() {
            $skipbtn.off('click');
        };

        fsm.onenterhandselected = function(event, from, to, $card) {
            $handpick = $card;
            $dialog.text('Selected ' + $card.text() + ' from hand. Select card from pool.')
            $handcards.not($card).removeClass('selectable');
            $handcards.off('click');
            // pickpool onclick should still work for hand cards.
            
            // Could add click() for selected card to unpick.

            $skipbtn.click(function() {
                fsm.pickpool(null);
            });
        };

        fsm.onleavehandselected = function() {
            $skipbtn.off('click');
        };

        fsm.onenterbothselected = function(event, from, to, $card) {
            if(event == 'pickpool') {
                $poolpick = $card;
            } else if(event == 'pickhand') {
                $handpick = $card;
            }
            frompool = $poolpick ? parseInt($poolpick[0].id.replace('card', '')) : 'None';
            fromhand = $handpick ? parseInt($handpick[0].id.replace('card', '')) : 'None';
            $poolcards.off('click');
            $handcards.off('click');
            $poolcards.removeClass('selectable selected');
            $handcards.removeClass('selectable selected');

            actionCallback(fromhand, frompool);
        };

        return fsm;
    };

    mod.leadrole = function(petitionCount, hasPalace, actionCallback) {
        var $dialog = $('#dialog');
        var ip = mod.playerIndex+1;
        var $handcards = $('#p'+ip+'-hand > .card');
        console.log('getting handcards : ' +'#p'+ip+'-hand > .card');
        var role = null;

        var fsm = FSM.create({
            initial: 'start',

            events: [
                { name: 'start', from: 'start', to: 'selectcard' },
                { name: 'orders', from: 'selectcard', to: 'palace' },
                { name: 'jack', from: 'selectcard', to: 'jackrole' },
                { name: 'role', from: 'jackrole', to: 'palace' },
                { name: 'nopalace', from: 'palace', to: 'finish' },
                { name: 'petition', from: 'selectcard', to: 'petition' },
                { name: 'done', from: 'petition', to: 'petitionrole' },
                { name: 'role', from: 'petitionrole', to: 'palace' },
                { name: 'orders', from: 'palace', to: 'palace' },
                { name: 'jack', from: 'palace', to: 'palacejackrole' },
                { name: 'petition', from: 'palace', to: 'palacepetition' },
                { name: 'done', from: 'palacepetition', to: 'palace' }
            ]
        });

        fsm.onenterselectcard = function(event, from, to, args) {
            $dialog.text('Select a card to lead.');
            $('#dialog-wrapper > button').prop('disable', true);
            
            $handcards.click(function(ev) {
                var $card = $(ev.target);
                $card.addClass('selected');
                if($card.text() == 'Jack') {
                    fsm.jack($card);
                } else {
                    var ident = parseInt($card[0].id.replace('card',''));
                    role = Util.cardProperties(ident).role;
                    fsm.orders($card);
                }
            });
        };

        fsm.onleaveselectcard = function(event, from, to, args) {
            $handcards.removeClass('selectable');
            $handcards.off('click');
        };

        fsm.onenterjackrole = function(event, from, to, args) {
            console.log('Selected Jack card, pick role now.');
            $dialog.text('Pick role for Jack.');
            $rolebtns = $('#role-select > button');
            $rolebtns.prop('disabled', false);
            $rolebtns.click(function(ev) {
                var $btn = $(ev.target);
                var role_ = $btn[0].id.replace('select-','');
                // Capitalize first letter
                role = role_.charAt(0).toUpperCase() + role_.slice(1);
                fsm.role();
            });
        };

        fsm.onleavejackrole = function(event, from, to, args) {
            $rolebtns = $('#role-select > button');
            $rolebtns.prop('disabled', true);
            $rolebtns.off('click');
        };

        fsm.onenterpalace = function(event, from, to, args) {
            if(!hasPalace) {
                fsm.nopalace();
            } else {
                alert('Palace not implemented');
            }
        };

        fsm.onenterfinish = function(event, from, to, args) {
            var $cards = $('#p'+ip+'-hand > .card.selected');
            var $card_ids = $cards.map(function(i) {return this.id;});
            var card_idents = $.map($card_ids.get(), function(id) {
                var ident = parseInt(id.replace('card',''));
                return ident;
            });

            actionCallback(role, 1, card_idents);

        };
        return fsm;
    };

    return mod;
});
