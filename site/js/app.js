define(['jquery', 'jqueryui', 'sockjs', 'util', 'display', 'action_builder', 'games', 'fsm', 'game', 'net'],
function($, _, SockJS, Util, Display, AB, Games, FSM, Game, Net){
    var App = {
        game_id: null,
        playerIndex: null,
        fsm: null
    }

    App.fsm = FSM.create({
        initial: 'Loading',

        events: [
            { name: 'loaded', from: 'Loading', to: 'MainMenu' },
            { name: 'join', from: 'Loading', to: 'MainMenu' },
            ]
    });

    App.initialize = function(){
        var tabs = $('#tabs').tabs({
            active: 0, // Default to game list
        });

        var heading = $('<div/>').attr('id', 'heading');
        var $gloryTitle = $('<span/>').text('Glory to Rome').addClass('title');
        var socketStatus = $('<span/>').text('Connecting...').addClass('status');
        heading.append($gloryTitle).append(socketStatus);

        $('#page-wrapper').before(heading);

        Games.user = 'a';
        //Games.user = $('#player-select').val();

        // Create a new WebSocket.
        Net.user = Games.user;
        Net.connect('http://localhost:5000/hello/');

        function sendAction(game_id, action, args) {
            return Net.sendAction(game_id, action, args);
        }

        // Get references to elements on the page.
        var form = document.getElementById('message-form');
        var messageField = document.getElementById('custom-action');
        var gameList = document.getElementById('gamelist');
        var newGameBtn = document.getElementById('creategame');
        var refreshBtn = document.getElementById('refresh');

        refreshBtn.onclick = function() {
            sendAction(0, Util.Action.REQGAMELIST);
        };

        newGameBtn.onclick = function() {
            console.log('create new game');
            sendAction(0, Util.Action.REQCREATEGAME);
        };
        
        // Split string, but only n times. Rest of string as last array element.
        function splitWithTail(str, delim, count){
          var parts = str.split(delim);
          var tail = parts.slice(count).join(delim);
          var result = parts.slice(0,count);
          result.push(tail);
          return result;
        };

        function update_game_list(json_list) {
            // The args is a json formated list of GameRecord dicts, with
            // keys game_id and players.

            list = JSON.parse(json_list);
            gameList.innerHTML = '';
            for(var i=0; i<list.length; ++i) {
                var game_id = list[i].game_id;
                var players = list[i].players;
                Games.records[game_id] = {
                    id: game_id,
                    players: players
                };

                function join(num) {
                    return function() {
                        console.log('join'+num);
                        sendAction(0, Util.Action.REQJOINGAME, [num]);
                    };
                };
                function start(num) {
                    return function() {
                        console.log('start'+num);
                        sendAction(num, Util.Action.REQSTARTGAME);
                    };
                };

                var gamelist = $('#gamelist');
                var $li = $('<li/>', {
                    
                    class:'received',
                    id: 'game-rec-'+game_id,
                });
                var $joinbtn = $('<button/>', {
                    text: 'Join',
                    id: 'join-btn-'+game_id,
                    class:'submit',
                    click: join(game_id)
                });
                var $startbtn = $('<button/>', {
                    text: 'Start',
                    id: 'start-btn-'+game_id,
                    class:'submit',
                    click: start(game_id)
                });
                $li.append($('<span/>').text('Game '+game_id))
                        .append('Players: '+players.join(', ')).addClass('game-listing');
                gamelist.append($li);
                $li.append($joinbtn);
                $li.append($startbtn);
            }
        };

        function update_game_state(game_id, gameState) {
            var game = Games.games[game_id];
            game.updateState(JSON.parse(gameState));
        };
        
        // Handle messages sent by the server.
        Net.socket.onmessage = function(event) {
            var message = event.data;

            // Parse NetString : <length>:<str>,
            var msg = (splitWithTail(message, ':', 1)[1]).slice(0,-1);

            var dict = JSON.parse(msg);
            var action = dict['action'];
            var args = dict['args'];
            
            if (action == Util.Action.GAMESTATE) {
                var game_id = parseInt(args[0]);
                update_game_state(game_id, args[1]);
            } else if (action == Util.Action.GAMELIST) {
                update_game_list(args);
            } else if (action == Util.Action.CREATEGAME) {
                console.log('Received CREATEGAME');
                sendAction(0, Util.Action.REQGAMELIST);
            } else if (action == Util.Action.JOINGAME) {
                console.log('Received JOINGAME');
                var game_id = parseInt(args[0]);
                App.game_id = game_id;
                sendAction(0, Util.Action.REQGAMELIST);
            } else if (action == Util.Action.STARTGAME) {
                console.log('Received STARTGAME');
                var id = parseInt(args);
                if(id in Games.games) {
                    console.log('Game '+id+' already started.');
                } else {
                    console.log('Starting game ' + id);
                    var game = new Game(Games.records[id], Games.user);
                    Games.games[id] = game;
                    game.initialize();
                    var tabs = $('#tabs').tabs('refresh');
                    tabs.tabs('option', 'active', -1); // switch to new tab.
                }
            }

        };


        // Send a message when the form is submitted.
        form.onsubmit = function(e) {
            e.preventDefault();

            // Retrieve the message from the textarea.
            var message = messageField.value;
            var obj = JSON.parse(message);
            var game = obj['game'];
            var action = obj['action'];
            var args = obj['args'];

            // Send the message through the WebSocket.
            sendAction(game, action, args);

            // Clear out the message field.
            // messageField.value = '6:a,0,32,';

            return false;
        };

    }

    return App;
});
