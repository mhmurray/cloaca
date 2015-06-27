#!/usr/bin/env python

""" Provides the GameState class, which is the physical representation
of the game. The only rules enforced are physical - such as failing to
draw a card from an empty pile.
"""

import gtrutils
from gtrutils import get_card_from_zone
from player import Player
from building import Building
import random
import logging

import stack

lg = logging.getLogger('gtr')

class GameState:
    """ Contains the current game state. The methods of this class
    represent physical changes to the game state. It's kind of like
    an API to be manipulated by an entity that enforces the rules.
    The only rules enforced by the GameState object are physical,
    such as failing to draw a card from an empty stack.
    """

    def __init__(self, players=None, jack_pile=None, library=None, pool=None,
                 in_town_foundations=None, out_of_town_foundations=None,
                 card_definitions_dict=None, time_stamp=None,
                 exchange_area=None, my_stack=None):
        self.players = []
        if players:
            for player in players: self.find_or_add_player(player)
        self.leader_index = None
        self.turn_number = 0
        self.is_decision_phase = True # 2 phases: decision, action
        self.do_respond_to_legionary = False
        self.is_role_led = False
        self.role_led = None
        self.active_player = None
        self.slave_player = None
        self.priority_index = None
        self.turn_index = 0
        self.jack_pile = jack_pile or []
        self.library = library or []
        self.pool = pool or []
        self.exchange_area = exchange_area or []
        self.in_town_foundations = in_town_foundations or []
        self.out_of_town_foundations = out_of_town_foundations or []
        self.oot_allowed = False
        self.used_oot = False
        self.is_started = False
        self.time_stamp = time_stamp
        self.stack = my_stack if my_stack else stack.Stack()
        self.legionary_count = 0
        self.legionary_index = 0
        self.legionary_resp_indices = []
        self.kip_index = 0
        self.senate_resp_indices = []
        self.expected_action = None

    def __repr__(self):
        rep = ('GameState(players={players!r}, leader={leader!r}, '
               'priority={priority!r}, jack_pile={jack_pile!r}, '
               'library={library!r}, '
               'in_town_foundations={in_town_foundations!r}'
               'out_of_town_foundations={out_of_town_foundations!r})'
               )
        return rep.format(
            players=self.players,
            leader=self.leader_index,
            priority= self.priority_index,
            jack_pile=self.jack_pile,
            library=self.library,
            in_town_foundations=self.in_town_foundations,
            out_of_town_foundations=self.out_of_town_foundations,
        )

    def privatize(self):
        """ Changes card names to 'Card' in order to represent a game
        where we don't have complete information. This is the case
        when this object is used in the client to track the
        server game state, for instance.
        """
        self.library = ['Card']*len(self.library)

        for p in self.players:

            if p is not self.slave_player:
                p.vault = ['Card']*len(p.vault)
                p.hand = [c if c == 'Jack' else 'Card' for c in p.hand ]
                p.fountain_card = 'Card' if p.fountain_Card else None

    def increment_priority_index(self):
        prev_index = self.priority_index
        self.priority_index = self.priority_index + 1
        if self.priority_index >= self.get_n_players():
            self.priority_index = 0
        lg.debug(
          'priority index changed from {0} to {1}; turn {2}'.format(
            prev_index,
            self.priority_index,
            self.turn_index,
        ))

    def increment_leader_index(self):
        prev_index = self.leader_index
        self.leader_index = self.leader_index + 1
        if self.leader_index >= self.get_n_players():
            self.leader_index = 0
            self.turn_index = self.turn_index + 1
        lg.debug('leader index changed from {0} to {1}'.format(prev_index,
        self.leader_index))

    def print_turn_info(self):
        lg.info('--> Turn {0} | leader: {1} | priority: {2}'.format(
          self.turn_index,
          self.players[self.leader_index].name,
          self.players[self.priority_index].name,
        ))

    def get_n_players(self):
        return len(self.players)

    def get_current_player(self):
        return self.players[self.leader_index]

    def get_active_player_index(self):
        return self.players.index(self.active_player)

    def get_following_players_in_order(self):
        """ Returns a list of players in turn order starting with
        the next player after the leader, and ending with the player
        before the leader. This is get_all_players_in_turn_order()
        with the leader removed.
        """
        n = self.leader_index
        return self.players[n+1:] + self.players[:n]

    def get_players_in_turn_order(self, start_player=None):
        """ Returns a list of players in turn order
        starting with start_player or the leader it's None.
        """
        n = self.players.index(start_player) if start_player else self.leader_index
        return self.players[n:] + self.players[:n]

    def get_player_indices_in_turn_order(self, start_player=None):
        """ Returns a list of player indices in turn order
        starting with start_player or the leader it's None.
        """
        n = self.players.index(start_player) if start_player else self.leader_index
        r = range(len(self.players))
        return r[n:] + r[:n]

    def thinker_fillup_for_player(self, player, max_hand_size):
        n_cards = max_hand_size - len(player.hand)
        lg.debug(
            'Adding {0} cards to {1}\'s hand'.format(n_cards, player.name))
        player.add_cards_to_hand(self.draw_cards(n_cards))

    def thinker_for_cards(self, player, max_hand_size):
        n_cards = max_hand_size - len(player.hand)
        if n_cards < 1: n_cards = 1
        lg.debug(
            'Adding {0} cards to {1}\'s hand'.format(n_cards, player.name))
        player.add_cards_to_hand(self.draw_cards(n_cards))

    def draw_one_card_for_player(self, player):
        player.add_cards_to_hand(self.draw_cards(1))

    def draw_one_jack_for_player(self, player):
        player.add_cards_to_hand([self.draw_jack()])

    def discard_for_player(self, player, card):
        if card not in player.hand:
            raise Exception('Card {} not found in hand.'.format(card))

        self.pool.append(player.get_card_from_hand(card))

    def discard_all_for_player(self, player):
        cards_to_discard = list(player.hand)
        for card in cards_to_discard:
            self.pool.append(player.get_card_from_hand(card))

    def find_player_index(self, player_name):
        """ Finds the index of a named player, otherwise creates a new
        Player object with the given name, appending it to the list of
        players. """
        players_match = filter(lambda x : x.name==player_name, self.players)
        if len(players_match) > 1:
            lg.critical(
              'Fatal error! Two instances of player {0}.'.format(players_match[0].name))
            raise Exception('Cannot have two players with the same name.')
        elif len(players_match) == 1:
            lg.info('Found existing player {0}.'.format(players_match[0].name))
            player_index = self.players.index(players_match[0])
            return player_index
        else:
            return None

    def find_or_add_player(self, player_name):
        """ Finds the index of a named player, otherwise creates a new
        Player object with the given name, appending it to the list of
        players. """
        players_match = filter(lambda x : x.name==player_name, self.players)
        if len(players_match) > 1:
            lg.critical(
              'Fatal error! Two instances of player {0}.'.format(players_match[0].name))
            raise Exception('Cannot create two players with the same name.')
        elif len(players_match) == 1:
            lg.info('Found existing player {0}.'.format(players_match[0].name))
            player_index = self.players.index(players_match[0])
        else:
            lg.info('Adding player {0}.'.format(player_name))
            self.players.append(Player(player_name))
            player_index = len(self.players) - 1
        return player_index

    def find_player(self, name):
        """ Gets the Player object corresponding to the specified player name.
        """
        return filter(lambda x: x.name==name, self.players)[0]

    def init_player(self, player):
        player.add_cards_to_hand([self.draw_jack()]) # takes a list of cards
        self.thinker_fillup_for_player(player, 5)

    def init_players(self):
        lg.info('--> Initializing players')
        for player in self.players:
            self.init_player(player)

    def testing_init_player(self, player):
        player.add_cards_to_hand([self.draw_jack()]) # takes a list of cards
        self.thinker_fillup_for_player(player, 5)
        player.stockpile.extend(['Forum','Insula','Catacomb','Foundry','Circus','Storeroom'])

    def testing_init_players(self):
        lg.info('--> Initializing players')
        for player in self.players:
            self.testing_init_player(player)

    def add_cards_to_pool(self, cards):
        self.pool.extend(cards)

    def get_card_from_pool(self, card):
        return get_card_from_zone(card, self.pool)

    def add_cards_to_exchange_area(self, card):
        self.exchange_area.extend(cards)

    def get_card_from_exchange_area(self, card):
        return get_card_from_zone(card, self.exchange_area)

    def draw_jack(self):
        return self.jack_pile.pop()

    def draw_cards(self, n_cards):
        cards = []
        for i in range(0, n_cards):
            cards.append(self.library.pop())
        return cards

    def shuffle_library(self):
        """ Shuffles the library.

        random.shuffle has a finite period, which is apparently 2**19937-1.
        This means lists of length >~ 2080 will not get a completely random
        shuffle. See the SO question
          http://stackoverflow.com/questions/3062741/maximal-length-of-list-to-shuffle-with-python-random-shuffle
        """
        random.shuffle(self.library)

    def pass_priority(self):
        self.priority_index += 1;
        while self.priority_index >= len(self.players):
            self.priority_index -= len(self.players)

    def show_public_game_state(self):
        """ Prints the game state, showing only public information.

        This is the following: cards in the pool, # of cards in the library,
        # of jacks left, # of each foundation left, who's the leader, public
        player information.
        """

        gtrutils.print_header('Public game state', '+')

        # print leader and priority
        self.print_turn_info()

        # print pool.
        pool_string = 'Pool: \n'
        pool_string += gtrutils.get_detailed_zone_summary(self.pool)
        lg.info(pool_string)

        # print exchange area.
        try:
            if self.exchange_area:
                exchange_string = 'Exchange area: \n'
                exchange_string += gtrutils.get_detailed_zone_summary(
                  self.exchange_area)
                lg.info(exchange_string)
        except AttributeError: # backwards-compatibility for old games
            self.exchange_area = []

        # print N cards in library
        lg.info('Library : {0:d} cards'.format(len(self.library)))

        # print N jacks
        lg.info('Jacks : {0:d} cards'.format(len(self.jack_pile)))

        # print Foundations
        lg.info('Foundation materials:')
        foundation_string = '  In town: ' + gtrutils.get_short_zone_summary(
          self.in_town_foundations, 3)
        lg.info(foundation_string)
        foundation_string = '  Out of town: ' + gtrutils.get_short_zone_summary(
          self.out_of_town_foundations, 3)
        lg.info(foundation_string)

        print ''
        for player in self.players:
            self.print_public_player_state(player)
            #self.print_complete_player_state(player)
            print ''


    def print_public_player_state(self, player):
        """ Prints a player's public information.

        This is the following: Card in camp (if existing), clientele, influence,
        number of cards in vault, stockpile, number of cards/jacks in hand,
        buildings built, buildings under construction and stage of completion.
        """
        # name
        lg.info('--> Player {0} public state:'.format(player.name))

        # hand
        lg.info(player.describe_hand_public())

        # Vault
        if len(player.vault) > 0:
            lg.info(player.describe_vault_public())

        # influence
        if player.influence:
            lg.info(player.describe_influence())

        # clientele
        if len(player.clientele) > 0:
            lg.info(player.describe_clientele())

        # Stockpile
        if len(player.stockpile) > 0:
            lg.info(player.describe_stockpile())

        # Buildings
        if len(player.buildings) > 0:
            # be sure there is at least one non-empty site
            for building in player.buildings:
                if building:
                    lg.info(player.describe_buildings())
                    break


        # Camp
        if len(player.camp) > 0:
            lg.info(player.describe_camp())

        # Revealed cards
        try:
            if len(player.revealed) > 0:
                lg.info(player.describe_revealed())
        except AttributeError:
            player.revealed = []


    def print_complete_player_state(self, player):
        """ Prints a player's information, public or not.

        This is the following: Card in camp (if existing), clientele, influence,
        cards in vault, stockpile, cards in hand,
        buildings built, buildings under construction and stage of completion.
        """
        # print name
        lg.info('--> Player {} complete state:'.format(player.name))

        # print hand
        lg.info(player.describe_hand_private())

        # print Vault
        if len(player.vault) > 0:
            lg.info(player.describe_vault_public())

        # print clientele
        if len(player.clientele) > 0:
            lg.info(player.describe_clientele())

        # print Stockpile
        if len(player.stockpile) > 0:
            lg.info(player.describe_stockpile())

        # print Buildings
        if len(player.buildings) > 0:
            # be sure there is at least one non-empty site
            for building in player.buildings:
                if building:
                    lg.info(player.describe_buildings())
                    break


if __name__ == '__main__':


    test = GameState()
    print test
