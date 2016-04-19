define(['jquery', 'jqueryui', 'sockjs', 'util', 'display', 'action_builder', 'game'],
function($, _, SockJS, Util, Display, AB, Game){
    var App = {
        game_id: null,
        username: 'user',
        playerIndex: null
        
    }

    App.initialize = function(){

        // Get references to elements on the page.
        var form = document.getElementById('message-form');
        var messageField = document.getElementById('custom-action');
        var gameList = document.getElementById('gamelist');
        var gameState = document.getElementById('gamestate');
        var socketStatus = document.getElementById('status');
        var closeBtn = document.getElementById('close');
        var refreshBtn = document.getElementById('refresh');
        var newGameBtn = document.getElementById('creategame');

        App.username = $('#player-select').val();
        function get_player() {
            return App.username;
        }

        // Create a new WebSocket.
        //var socket = new sockjs.SockJS('http://localhost:5000/hello/');
        var socket = SockJS('http://localhost:5000/hello/');


        function sendString(s) {
            socket.send(s.length+':'+s+',');
        };

        function sendAction(game_id, action, args=[]) {
            var p = get_player();
            var s = {'user':p, 'game':game_id, 'action':action, 'args':args};
            console.log('Sending action: ' + JSON.stringify(s));
            sendString(JSON.stringify(s));    
        };

        refreshBtn.onclick = function() {
            sendAction(App.game_id, Util.Action.REQGAMELIST);
        };

        newGameBtn.onclick = function() {
            console.log('create new game');
            sendAction(App.game_id, Util.Action.REQCREATEGAME);
        };

        $('#lead-role').click(function(ev) {
            console.log('Creating lead-role FSM');
            var petitionCount = 3;
            var hasPalace = false;
            var fsm = AB.leadrole(3, hasPalace, function(role, n_actions, cards) {
                sendAction(App.game_id, Util.Action.THINKERORLEAD, [false]);

                var args = [role, n_actions].concat(cards);
                sendAction(App.game_id, Util.Action.LEADROLE, args);
            });

            fsm.start();

        });

        $('#think-jack').click(function() {
            sendAction(App.game_id, Util.Action.THINKERORLEAD, ['True']);
            sendAction(App.game_id, Util.Action.THINKERTYPE, ['True']);
        });

        $('#think-orders').click(function() {
            sendAction(App.game_id, Util.Action.THINKERORLEAD, ['True']);
            sendAction(App.game_id, Util.Action.THINKERTYPE, ['False']);
        });

        $('#game-refresh-btn').click(function() {
            console.log('Refresh game ' + App.game_id);
            sendAction(App.game_id, Util.Action.REQGAMESTATE);
        });

        // Handle any errors that occur.
        socket.onerror = function(error) {
            console.log('WebSocket Error: ' + error);
        };


        // Show a connected message when the WebSocket is opened.
        socket.onopen = function(event) {
            socketStatus.innerHTML = 'Connected.';
            socketStatus.className = 'open';
            sendAction(App.game_id, Util.Action.REQGAMELIST);
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
                    id: 'game-rec-'+i,
                });
                var $joinbtn = $('<button/>', {
                    text: 'Join',
                    id: 'join-btn-'+i,
                    class:'submit',
                    click: join(i)
                });
                var $startbtn = $('<button/>', {
                    text: 'Start',
                    id: 'start-btn-'+i,
                    class:'submit',
                    click: start(i)
                });
                $li.append($('<span/>').text('Game '+i)).append('Players: '+list[i]['players'].join(', '));
                gamelist.append($li);
                $li.append($joinbtn);
                $li.append($startbtn);
            }
        };

        function update_game_state(args) {
            // the game state will be null if the game isn't started
            var gs = JSON.parse(args);
            if (!gs) {
                console.log("Game not started yet.");
                return;
            }
            var player_index = null;
            for(var i=0; i<gs.players.length; i++) {
                if(gs.players[i].name == App.username) {
                    player_index = i;
                }
            }

            Game.games[gs.game_id] = {
                gameState: gs,
                playerIndex: player_index
            };

            App.game_id = gs.game_id;
            App.playerIndex = player_index;
            AB.playerIndex = player_index;

            Display.updateGameState(gs);

            $('#thinker-commands > button').prop('disabled', true);
            $('#ok-cancel-btns > button').prop('disabled', true);
            $('#role-select > button').prop('disabled', true);

            if(gs.expected_action == Util.Action.THINKERORLEAD) {
                $('#thinker-commands > button').prop('disabled', false);
                $('#dialog').text('Thinker or lead a role?');

            } else if (gs.expected_action == Util.Action.LABORER) {
                console.log('Creating Laborer FSM');
                var hasDock = false;
                AB.laborer(hasDock, function(hand_card, pool_card) {
                    sendAction(App.game_id, Util.Action.LABORER, [hand_card, pool_card]);
                });
            }

            current_game_id = Display.game_id;
        };


        // Handle messages sent by the server.
        socket.onmessage = function(event) {
            var message = event.data;
            /*
            messagesList.innerHTML += '<li class="received"><span>Received:</span>' +
                                       message + '</li>';
            */

            // Parse NetString : <length>:<str>,
            var msg = (splitWithTail(message, ':', 1)[1]).slice(0,-1);
            //console.log('msg = ' + msg);

            var dict = JSON.parse(msg);
            var action = dict['action'];
            var args = dict['args'];
            
            if (action == Util.Action.GAMESTATE) {
                console.log('Received GAMESTATE');
                update_game_state(args);
            } else if (action == Util.Action.GAMELIST) {
                console.log('Received GAMELIST');
                update_game_list(args);
            } else if (action == Util.Action.CREATEGAME) {
                console.log('Received CREATEGAME');
                sendAction(App.game_id, Util.Action.REQGAMELIST);
            } else if (action == Util.Action.JOINGAME) {
                console.log('Received JOINGAME');
                var game_id = parseInt(args[0]);
                App.game_id = game_id;
                Game.games[game_id] = {gs: null};
                sendAction(App.game_id, Util.Action.REQGAMELIST);
            }

        };


        // Show a disconnected message when the WebSocket is closed.
        socket.onclose = function(event) {
            socketStatus.innerHTML = 'Disconnected from WebSocket.';
            socketStatus.className = 'closed';
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

        // Close the WebSocket connection when the close button is clicked.
        closeBtn.onclick = function(e) {
            e.preventDefault();

            // Close the WebSocket.
            socket.close();

            return false;
        };

    }

    return App;
});
