"""A class to represent the state of a game on the server.
"""

class GameRecord(object):
    """A record suitable for sending over the network to describe games.
    """

    def __init__(self, game_id, players, started, host):
        self.game_id = game_id
        self.players = players
        self.started = started
        self.host = host

    def __str__(self):
        s = ('Game {0!s}  Host: {1!s}  Started: {2!s}  Players: {3!s}'
            ).format(self.game_id, self.host, self.started, self.host)
            
        return s

    def __repr__(self):
        return ('GameRecord({game_id:d}, {players!s}, {started!s}, {host:d})'
                ).format(**self.__dict__)
