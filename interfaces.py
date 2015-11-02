from zope.interface import Interface, implements


class IGTRService(Interface):

    def get_game_list():
        """Return a list of GameRecord objects describing all games.
        """

    def submit_action(user, game, action):
        """Submit a GameAction to the server
        """

    def get_game_state(user, game):
        """Get the GameState object as viewed by user, formatted
        as a pickled string"""

    def join_game(user, game):
        """Join a game.
        """

    def create_game(user, game):
        """Create game.
        """

    def start_game(user, game):
        """Request that a game starts.
        """


class IGTRFactory(Interface):

    def submit_action(user, game, action):
        """Submit a GameAction"""

    def get_game_state(user, game):
        """Get the GameState object as viewed by user, formatted
        as a pickled string"""

    def join_game(user, game):
        """Join an existing game"""

    def start_game(user, game):
        """Start a game once there are 2 or more players"""

    def get_game_list():
        """Get list of games"""

    def create_game(user):
        """Create new game (return game id?)"""

