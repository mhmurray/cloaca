define(['util', 'jquery', 'jqueryui'],
function(Util, $, _){
    var display = {
    };

    display.updateGameState = function(obj) {
        display.id = obj.game_id;
        display.is_started = obj.is_started;
        display.turn_number = obj.turn_number;
        display.library = obj.library.cards;
        display.players = obj.players;
        display.leader_index = obj.leader_index;
        display.leader = display.players[display.leader_index];
        display.expected_action = obj.expected_action;
        console.log('Expected action: ' + display.expected_action);
    

        function createCardZone(zoneId, title, cards) {
            var $zone = Util.makeCardZone(zoneId, title);
            var $cardList = $zone.children('.card-container');
            for(var j=0; j<cards.length; j++) {
                $cardList.append(Util.makeCard(cards[j].ident));
            }
            return $zone;
        };


        $('#pool').parent().remove();
        var $pool = createCardZone('pool', 'Pool', obj.pool.cards);
        $('#gamestate-wrapper > ul').after($pool);


        var $players = $('#player-info');
        $players.empty();
        for(var i=0; i<display.players.length; i++) {
            var ip = i+1;
            var $p = $('<div />', {id:'player'+ip, class:'player-box'}).appendTo($players);
            $p.html('<b>Player '+(ip)+'</b>');

            $p.append(createCardZone(
                        'p'+ip+'-hand',
                        'Hand',
                        display.players[i].hand.cards));
            $p.append(createCardZone(
                        'p'+ip+'-camp',
                        'Camp',
                        display.players[i].camp.cards));
            $p.append(createCardZone(
                        'p'+ip+'-stockpile',
                        'Stockpile',
                        display.players[i].stockpile.cards));
            $p.append(createCardZone(
                        'p'+ip+'-vault',
                        'Vault',
                        display.players[i].vault.cards));
            $p.append(createCardZone(
                        'p'+ip+'-clientele',
                        'Clientele',
                        display.players[i].clientele.cards));
        }

        $list = $('#gamestate-list');
        $list.empty();
        $list.append($('<li/>', {
            class: "received",
            text: 'Game '+display.id+'   Turn #'+display.turn_number+'   Leader: '+display.leader['name']
        }));
        $list.append($('<li/>', {
            class: "received",
            text: 'Library: ' + display.library.length + ' cards.'
        }));

        $gameLog = $('#game-log').html(obj.game_log.join('<br>'));
        $gameLog[0].scrollTop = $gameLog[0].scrollHeight;
                        
        $('#gamestate-wrapper').show();

        $('.card-container').sortable({
            tolerance: 'intersect',
            //connectWith: $('.card-container') // Drag-and-drop
        });
        $('.card-container').disableSelection();


    };

    return display;
});
