""" Provides the GameState class, which is the physical representation
of the game. The only rules enforced are physical - such as failing to
draw a card from an empty pile.
"""

import gtrutils
from error import GTRError
from player import Player
from building import Building
import random
import logging
import card_manager
from collections import Counter
from zone import Zone
from card import Card

import stack

lg = logging.getLogger(__name__)

class GameState(object):
    """Data object containing the state of a game.
    """

    def __init__(self):
        self.players = []
        self.leader_index = None
        self.turn_number = 0
        self.is_role_led = False
        self.role_led = None
        self.active_player = None
        self.turn_index = 0
        self.jacks = Zone()
        self.library = Zone()
        self.pool = Zone()
        self.in_town_sites = []
        self.out_of_town_sites = []
        self.oot_allowed = False
        self.used_oot = False
        self.stack = stack.Stack()
        self.legionary_count = 0
        self.legionary_index = 0
        self.legionary_resp_indices = []
        self.kip_index = 0
        self.senate_resp_indices = []
        self.expected_action = None
        self.game_id = 0
        self.host = None

        self.game_log = []

    active_player_index = property(lambda self : self.players.index(self.active_player))
    leader = property(lambda self : self.players[self.leader_index])
    is_started = property(lambda self : self.turn_number > 0)

    def __repr__(self):
        rep = ('GameState(players={players!r}, leader={leader!r}, '
               'jacks={jacks!r}, '
               'library={library!r}, '
               'in_town_sites={in_town_sites!r},'
               'out_of_town_sites={out_of_town_sites!r})'
               )
        return rep.format(
            players=self.players,
            leader=self.leader_index,
            jacks=self.jacks,
            library=self.library,
            in_town_sites=self.in_town_sites,
            out_of_town_sites=self.out_of_town_sites,
        )

    def privatize(self, player_name):
        """Changes card names to 'Card' in order to represent a game
        visible by player_name. This hides the library, vault, and other
        players' hands, as well as the revealed card for a Fountain.

        This does not hide Jacks in hand.
        """
        self.library.set_content([Card(-1)]*len(self.library))

        for p in self.players:
            p.vault.set_content([Card(-1)]*len(p.vault))

            if p.name != player_name:
                p.hand.set_content([c if c.name == 'Jack' else Card(-1) for c in p.hand ])
                p.fountain_card = Card(-1) if p.fountain_card else None

    def increment_leader_index(self):
        prev_index = self.leader_index
        self.leader_index = self.leader_index + 1
        if self.leader_index >= len(self.players):
            self.leader_index = 0
            self.turn_index = self.turn_index + 1
        lg.debug('leader index changed from {0} to {1}'.format(prev_index,
        self.leader_index))

    def following_players_in_order(self):
        """Return a list of players in turn order starting with
        the next player after the leader, and ending with the player
        before the leader. This is players_in_turn_order()
        with the leader removed.
        """
        n = self.leader_index
        return self.players[n+1:] + self.players[:n]

    def players_in_turn_order(self, start_player=None):
        """ Returns a list of players in turn order
        starting with start_player or the leader it's None.
        """
        n = self.players.index(start_player) if start_player else self.leader_index
        return self.players[n:] + self.players[:n]

    def thinker_for_cards(self, player, max_hand_size):
        n_cards = max_hand_size - len(player.hand)
        if n_cards < 1: n_cards = 1
        lg.debug(
            'Adding {0} cards to {1}\'s hand'.format(n_cards, player.name))
        player.hand.extend(self.draw_cards(n_cards))

    def draw_jack_for_player(self, player):
        player.hand.append(self.draw_jack())

    def discard_for_player(self, player, card):
        player.hand.move_card(card, self.pool)

    def discard_all_for_player(self, player):
        cards_to_discard = list(player.hand)
        for card in cards_to_discard:
            player.hand.move_card(card, self.pool)

    def find_player_index(self, player_name):
        """Finds the index of a named player.
        """
        players_match = [i for i,p in enumerate(self.players)
                         if p.name==player_name]
        return players_match[0] if len(players_match) else None

    def find_player(self, name):
        """Return the Player object with the specified name or None if no
        such player is in the game.
        """
        players_match = filter(lambda x : x.name == name, self.players)
        return players_match[0] if len(players_match) else None

    def init_player_hands(self):
        lg.info('Initializing {0} players.'.format(len(self.players)))
        for player in self.players:
            self.draw_jack_for_player(player)
            self.thinker_for_cards(player, 5)

    def draw_jack(self):
        try:
            c = self.jacks.pop()
        except IndexError:
            raise GTRError('Jack pile is empty.')

        return c

    def draw_cards(self, n_cards):
        cards = []
        for i in range(0, n_cards):
            cards.append(self.library.pop(0))
        return cards

    def shuffle_library(self):
        """ Shuffles the library.

        random.shuffle has a finite period, which is apparently 2**19937-1.
        This means lists of length >~ 2080 will not get a completely random
        shuffle. See the SO question
          http://stackoverflow.com/questions/3062741/maximal-length-of-list-to-shuffle-with-python-random-shuffle
        """
        random.shuffle(self.library.cards)

    def log(self, msg):
        """Logs a game message. These are a record of the progress of the
        game, not, eg. error messages meant for the player.
        """
        self.game_log.append(msg)
