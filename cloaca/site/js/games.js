define([],
function() {
    var Games = {
        // List of games we have joined. Each is an object 
        //      {
        //          id: game_id,
        //          players: players
        //          gs: game state
        //          display: Game object
        //      }.
        games: {},

        // In-memory representation of the server's list of games.
        // This has the same structure as the list returned
        // with the GAMELIST server message, but they are keyed
        // by the game_id.
        records: {},

        // Our username.
        user: null
    };

    return Games;
});
