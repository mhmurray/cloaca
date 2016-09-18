define(['util', 'fsm'],
function(Util, FSM) {
    var Net = {
        socket: null,
        user: null
    }

    Net.connect = function(url, onopen, onmessage) {
        Net.socket = new WebSocket(url);

        // Handle any errors that occur.
        Net.socket.onerror = function(error) {
            console.log('WebSocket Error: ' + error);
        };

        // Show a connected message when the WebSocket is opened.
        Net.socket.onopen = function(event) {
            var socketStatus = $('.status');
            socketStatus.text('Connected.');
            socketStatus.removeClass('closed').addClass('open');

            onopen();
        };
        
        // Split string, but only n times. Rest of string as last array element.
        function splitWithTail(str, delim, count){
          var parts = str.split(delim);
          var tail = parts.slice(count).join(delim);
          var result = parts.slice(0,count);
          result.push(tail);
          return result;
        };

        Net.socket.onmessage = function(event) {
            var message = event.data;

            // Parse NetString : <length>:<str>,
            //var msg = (splitWithTail(message, ':', 1)[1]).slice(0,-1);
            var msg = message;

            var dict = JSON.parse(msg);
            console.log('Received', dict);

            var game = dict['game']
            var action = dict['action']['action'];
            var args = dict['action']['args'];

            onmessage(game, action, args);
        };
        
        // Show a disconnected message when the WebSocket is closed.
        Net.socket.onclose = function(event) {
            var socketStatus = $('.status');
            socketStatus.text('Disconnected from WebSocket.');
            socketStatus.removeClass('open').addClass('closed');
        };
        
        // Close the WebSocket connection when the close button is clicked.
        var closeBtn = document.getElementById('close');
        closeBtn.onclick = function(e) {
            e.preventDefault();

            // Close the WebSocket.
            socket.close();

            return false;
        };

        return;
    };

    Net._sendString = function(s) {
        //Net.socket.send(s.length+':'+s+',');
        Net.socket.send(s);
    };

    Net.sendAction = function(game_id, number, action, args=[]) {
        var s = {'game':game_id, 'number':number, 'action':{'action':action, 'args':args}};
        console.log('Sending action: ' + JSON.stringify(s));
        Net._sendString(JSON.stringify(s));
    };

    // Send a list of game commands. Argument is list of lists with the 
    // same arguments as sendAction.
    Net.sendActions = function(commands) {
        var l = [];
        for(var i=0; i<commands.length; i++) {
            var c = commands[i];
            var s = {'game':c[0], 'number':c[1], 'action':{'action':c[2], 'args':c[3]}};
            l.push(s);
        }

        var json = JSON.stringify(l);
        console.log('Sending actions: ' + json);
        Net._sendString(json);
    };

    return Net;
});
