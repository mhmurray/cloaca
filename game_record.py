"""A class to represent the state of a game on the server.
"""

class GameRecord(object):
    """A record suitable for sending over the network to describe games.
    """

    def __init__(self, game_id, players):
        self.game_id = game_id
        self.players = players

    def __str__(self):
        s = 'Game ' + str(self.game_id) + '  Players: ' + ', '.join(self.players)
        return s

    def __repr__(self):
        return 'GameRecord({0:d}, {1!s})'.format(self.game_id, self.players)


