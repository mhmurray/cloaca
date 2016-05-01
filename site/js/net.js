define(['sockjs', 'util'],
function(SockJS, Util) {
    var Net = {
        socket: null,
        user: null
    }

    Net.connect = function(url) {
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
            Net.sendAction(Net.user, Util.Action.REQGAMELIST);
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
        var s = {'user':Net.user, 'game':game_id, 'action':action, 'args':args};
        console.log('Sending action: ' + JSON.stringify(s));
        Net._sendString(JSON.stringify(s));    
    };

    return Net;
});
