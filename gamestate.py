#!/usr/bin/env python

""" Provides the GameState class, which is the physical representation
of the game. The only rules enforced are physical - such as failing to
draw a card from an empty pile. 
"""

from gtrutils import get_card_from_zone
from player import Player
from building import Building
import random
import logging


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
               exchange_area=None):
    self.players = []
    if players:
        for player in players: self.find_or_add_player(player)
    self.leader_index = None
    self.is_decision_phase = True # 2 phases: decision, action
    self.do_respond_to_legionary = False
    self.is_role_led = False
    self.role_led = None
    self.priority_index = None
    self.turn_index = 0
    self.jack_pile = jack_pile or []
    self.library = library or []
    self.pool = pool or []
    self.exchange_area = exchange_area or []
    self.in_town_foundations = in_town_foundations or []
    self.out_of_town_foundations = out_of_town_foundations or []
    self.is_started = False
    self.time_stamp = time_stamp

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

  def increment_priority_index(self):
      prev_index = self.priority_index
      self.priority_index = self.priority_index + 1
      if self.priority_index >= self.get_n_players():
        self.priority_index = 0
      logging.debug(
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
      logging.debug('leader index changed from {0} to {1}'.format(prev_index,
      self.leader_index))

  def print_turn_info(self):
      logging.info('--> Turn {0} | leader: {1} | priority: {2}'.format(
        self.turn_index, 
        self.players[self.leader_index].name,
        self.players[self.priority_index].name,
      )) 

  def get_n_players(self):
      return len(self.players)

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
      n = start_player or self.leader_index
      return self.players[n:] + self.players[:n]

  def thinker_fillup_for_player(self, player, max_hand_size):
    n_cards = max_hand_size - len(player.hand)
    logging.debug(
        'Adding {0} cards to {1}\'s hand'.format(n_cards, player.name))
    player.add_cards_to_hand(self.draw_cards(n_cards))

  def thinker_for_cards(self, player, max_hand_size):
    n_cards = max_hand_size - len(player.hand)
    if n_cards < 1: n_cards = 1
    logging.debug(
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

  def find_or_add_player(self, player_name):
    """ Finds the index of a named player, otherwise creates a new
    Player object with the given name, appending it to the list of 
    players. """
    players_match = filter(lambda x : x.name==player_name, self.players)
    if len(players_match) > 1:
      logging.critical(
        'Fatal error! Two instances of player {0}.'.format(players_match[0].name))
      raise Exception('Cannot create two players with the same name.')
    elif len(players_match) == 1:
      logging.info('Found existing player {0}.'.format(players_match[0].name))
      player_index = self.players.index(players_match[0])
    else:
      logging.info('Adding player {0}.'.format(player_name))
      self.players.append(Player(player_name))
      player_index = len(self.players) - 1
    return player_index
  
  def init_player(self, player):
    player.add_cards_to_hand([self.draw_jack()]) # takes a list of cards
    self.thinker_fillup_for_player(player, 5)

  def init_players(self):
    logging.info('--> Initializing players')
    for player in self.players:
      self.init_player(player)
    
  def testing_init_player(self, player):
    player.add_cards_to_hand([self.draw_jack()]) # takes a list of cards
    self.thinker_fillup_for_player(player, 5)
    player.buildings.append(Building('Tower','Concrete', ['Senate'],[],False))
    player.buildings.append(Building('Atrium','Brick'))
    player.buildings.append(Building('Catacomb','Stone',['Villa','Villa']))

  def testing_init_players(self):
    logging.info('--> Initializing players')
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


if __name__ == '__main__':

    
  test = GameState()
  print test

