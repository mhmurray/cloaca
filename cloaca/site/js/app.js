define(['jquery', 'jqueryui', 'sockjs', 'util', 'display', 'games', 'fsm', 'game', 'net'],
function($, _, SockJS, Util, Display, Games, FSM, Game, Net){
    var App = {
        game_id: null,
        playerIndex: null,
    };

    App.initialize = function(){
        // The relative URL to the websocket is stored in an invisible
        // HTML element.
        var ws_uri_path = $('#ws-uri').attr('href');
        var ws_proto = 'wss:';
        if(location.protocol == 'http:') {
            ws_proto = 'ws:';
        }
        var ws_uri = ws_proto+'//'+location.host + ws_uri_path;

        var tabs = $('#tabs').tabs({
            active: 0, // Default to game list
        });

        var heading = $('<div/>').attr('id', 'heading');
        var $gloryTitle = $('<span/>').text('Glory to Rome').addClass('title');
        var socketStatus = $('<span/>').text('Connecting...').addClass('status');
        heading.append($gloryTitle).append(socketStatus);

        $('#page-wrapper').before(heading);

        $('#error-container').hide();
        $('#error-dialog > .close').click(function(e) {
            $('#error-container').hide();
        });

        function displayError(message) { 
            var $list = $('#error-dialog > ul').append($('<li/>', {text: message}));
            $('#error-container').show();
            $list[0].scrollTop = $list[0].scrollHeight;
        }

        // Handle messages sent by the server.
        function handleCommand(game, action, args) {
            
            if (action == Util.Action.GAMESTATE) {
                update_game_state(game, JSON.parse(args[0]));

            } else if (action == Util.Action.GAMELIST) {
                update_game_list(args);

            } else if (action == Util.Action.CREATEGAME) {
                console.log('Received CREATEGAME');
                sendAction(0, null, Util.Action.REQGAMELIST);

            } else if (action == Util.Action.JOINGAME) {
                console.log('Received JOINGAME');
                App.game_id = game;
                sendAction(0, null, Util.Action.REQGAMELIST);

            } else if (action == Util.Action.STARTGAME) {
                console.log('Received STARTGAME');
                if(game in Games.games) {
                    console.log('Game '+game+' already started.');
                } else {
                    console.log('Starting game ' + game);
                    var game_obj = new Game(Games.records[game], Games.user);
                    Games.games[game] = game_obj;
                    game_obj.initialize();
                    var tabs = $('#tabs').tabs('refresh');
                    tabs.tabs('option', 'active', -1); // switch to new tab.
                }
            } else if (action == Util.Action.SERVERERROR) {
                var message = args[0];
                displayError(message);
            }
        };

        var loginSM = FSM.create({
            initial: 'Start',

            events: [
                { name: 'start', from: 'Start', to: 'LoggedOut' },
                { name: 'login', from: 'LoggedOut', to: 'LoggedIn' },
                { name: 'logout', from: 'LoggedIn', to: 'LoggedOut' },
                ]
        });

        loginSM.onafterstart = function() {
            // Check if already logged in
            username = $('#the_username').text();
            game_id = parseInt($('#the_game_id').text());
            loginSM.login(username, game_id)
            /*$.get('user', {}, function(data, status) {
                if(data !== '') {
                    loginSM.login(data);
                }
            });
            */
        };

        loginSM.onenterLoggedIn = function(event, from, to, user, game_id) {
            //$('#username').addClass('open').text(user);
            $('#username').addClass('open');
            $('#login-status').removeClass('closed').text('Logged in as ');
            $('#login-form').hide();
            $('#logout-btn').show();
            Games.user = user;
            Net.user = user;
            Net.connect(ws_uri, function() {
                Net.sendAction(game_id, null, Util.Action.REQGAMESTATE);
            }, handleCommand);
        };

        loginSM.onenterLoggedOut = function(event, from, to) {
            $('#username').removeClass('open').text('');
            $('#login-status').removeClass('open').addClass('closed').text('Not logged in.');
            $('#login-form').show();
            $('#logout-btn').hide();
            Games.user = undefined;
            Net.user = undefined;
            if(Net.socket !== null) {
                Net.socket.close();
            }
        };

        loginSM.start();

        var $loginForm = $('#login-form');
        $loginForm.submit(function(e) {
            e.preventDefault();

            var user = $('#login-text').val();

            $.post('login', {user: user}, function(data, status) {
                if(data === user) {
                    loginSM.login(data);
                } else {
                    console.error('Failed login:', user);
                }
            });
        });

        var logoutBtn = $('#logout-btn');
        logoutBtn.click(function(e) {
            $.get('logout', {}, function(data, status) {
                loginSM.logout();
            });
        });

        function sendAction(game_id, number, action, args) {
            return Net.sendAction(game_id, number, action, args);
        }

        // Get references to elements on the page.
        var form = document.getElementById('message-form');
        var messageField = document.getElementById('custom-action');
        var gameList = document.getElementById('gamelist');
        var newGameBtn = document.getElementById('creategame');
        var refreshBtn = document.getElementById('refresh');

        refreshBtn.onclick = function() {
            sendAction(0, null, Util.Action.REQGAMELIST);
        };

        newGameBtn.onclick = function() {
            console.log('create new game');
            sendAction(0, null, Util.Action.REQCREATEGAME);
        };
        

        function update_game_list(json_list) {
            // The args is a json formated list of GameRecord dicts, with
            // keys game_id and players.

            var list = JSON.parse(json_list);
            gameList.innerHTML = '';

            function join(num) {
                return function() {
                    console.log('join'+num);
                    sendAction(num, null, Util.Action.REQJOINGAME);
                };
            };
            function start(num) {
                return function() {
                    console.log('start'+num);
                    sendAction(num, null, Util.Action.REQSTARTGAME);
                };
            };

            var gamesJoined = [];

            for(var i=0; i<list.length; ++i) {
                console.log(list[i]);
                var game_id = parseInt(list[i].game_id);
                var players = list[i].players;
                var isStarted = list[i].started;
                var host = list[i].host
                Games.records[game_id] = {
                    id: game_id,
                    players: players
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
                var text = 'Game '+game_id;
                if(isStarted) {
                    text+= ' (in progress...)';
                } else {
                    text+= ' (not started)';
                }

                $li.append($('<span/>').text(text))
                        .append('Players: '+players.join(', ')).addClass('game-listing');
                gamelist.append($li);
                $li.append($joinbtn);
                $li.append($startbtn);

                if(players.indexOf(Games.user) > -1) {
                    if(isStarted) {
                        gamesJoined.push(game_id);
                    }
                }
            }

            gamesJoined.sort(function(a,b) {return a-b;});
            for(var i=0; i<gamesJoined.length; i++) {
                var _id = gamesJoined[i];
                if(!(_id in Games.games)){
                    console.log('Resuming game', game_id);
                    var game_obj = new Game(Games.records[_id], Games.user);
                    Games.games[_id] = game_obj;
                    game_obj.initialize();
                    var tabs = $('#tabs').tabs('refresh');
                    tabs.tabs('option', 'active', -1); // switch to new tab.
                    sendAction(_id, null, Util.Action.REQGAMESTATE);
                }
            }
        };

        function update_game_state(game_id, gameState) {
            console.dir(gameState);
            if(!(game_id in Games.games)) {
                players = [];
                for(var i=0; i<gameState.players.length; i++) {
                    players.push(gameState.players[i].name);
                }

                var game_obj = new Game(game_id, players);
                Games.games[game_id] = game_obj;
                game_obj.initialize();
                var tabs = $('#tabs').tabs('refresh');
                tabs.tabs('option', 'active', -1); // switch to new tab.
            }

            var game = Games.games[game_id];
            game.updateState(gameState);
        };
        
        // Send a message when the form is submitted.
        form.onsubmit = function(e) {
            e.preventDefault();

            // Retrieve the message from the textarea.
            var message = messageField.value;
            var obj = JSON.parse(message);
            var game = obj['game'];
            var number = obj['number'];
            var action = obj['action'];
            var args = obj['args'];

            // Send the message through the WebSocket.
            sendAction(game, number, action, args);

            // Clear out the message field.
            // messageField.value = '6:a,0,32,';

            return false;
        };

    }

    return App;
});
