define(['sockjs', 'util', 'fsm', 'jscookie'],
function(SockJS, Util, FSM, Cookies) {
    var Net = {
        socket: null,
        user: null
    }

    Net.connect = function(url, onopen, onmessage) {
        Net.socket = SockJS(url);

        // Handle any errors that occur.
        Net.socket.onerror = function(error) {
            console.log('WebSocket Error: ' + error);
        };

        // Show a connected message when the WebSocket is opened.
        Net.socket.onopen = function(event) {
            var socketStatus = $('.status');
            socketStatus.text('Connected.');
            socketStatus.removeClass('closed').addClass('open');

            uid = Cookies.get('TWISTED_SESSION');
            console.log('Read TWISTED_SESSION cookie:', uid);

            console.log('Try to read invalid cookie');
            console.log(Cookies.get('NotARealCookie'));

            if(uid !== null) {
                Net.sendAction(0, Util.Action.LOGIN, [uid]);
            }

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
            var msg = (splitWithTail(message, ':', 1)[1]).slice(0,-1);

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
        Net.socket.send(s.length+':'+s+',');
    };

    Net.sendAction = function(game_id, action, args=[]) {
        var s = {'game':game_id, 'action':{'action':action, 'args':args}};
        console.log('Sending action: ' + JSON.stringify(s));
        Net._sendString(JSON.stringify(s));
    };

    return Net;
});
