#!/usr/bin/env python

""" Provides the GameState class, which is the physical representation
of the game. The only rules enforced are physical - such as failing to
draw a card from an empty pile. 
"""

from gtrutils import get_card_from_zone
from player import Player
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
               foundations=None, card_definitions_dict=None, time_stamp=None):
    self.players = []
    if players:
        for player in players: self.add_player(player)
    self.leader_index = None
    self.priority_index = None
    self.turn_index = 0
    self.jack_pile = jack_pile or []
    self.library = library or []
    self.pool = pool or []
    self.foundations = foundations
    if self.foundations is None:
      self.foundations = {
        'Rubble'  : [],
        'Wood'    : [],
        'Cement'  : [],
        'Brick'   : [],
        'Stone'   : [],
        'Marble'  : [],
        }
    self.is_started = False
    self.time_stamp = time_stamp

  def __repr__(self):
    rep = ('GameState(players={players!r}, leader={leader!r}, '
           'priority={priority!r}, jack_pile={jack_pile!r}, '
           'library={library!r}, foundations={foundations!r})'
           )
    return rep.format(
        players=self.players, 
        leader=self.leader_index,
        priority= self.priority_index,
        jack_pile=self.jack_pile,
        library=self.library, 
        foundations=self.foundations
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

  def thinker_fillup_for_player(self, player):
    n_cards = player.get_max_hand_size() - len(player.hand)
    player.add_cards_to_hand(self.draw_cards(n_cards))

  def draw_one_card_for_player(self, player):
    player.add_cards_to_hand(self.draw_cards(1))

  def draw_one_jack_for_player(self, player):
    player.add_cards_to_hand([self.draw_jack()])

  def add_player(self, player):
    """ Adds a player, which is of class Player. Returns index of player. """
    self.players.append(player)
    player_index = len(self.players) - 1
    return player_index
  
  def init_player(self, player):
    player.add_cards_to_hand([self.draw_jack()]) # takes a list of cards
    self.thinker_fillup_for_player(player)

  def init_players(self):
    logging.info('--> Initializing players')
    for player in self.players: self.init_player(player)
    
  def add_cards_to_pool(self, cards):
    self.pool.extend(cards)

  def get_card_from_pool(self, card):
    return get_card_from_zone(card, pool)
    
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
      http://stackoverflow.com/questions/3062741/
      maximal-length-of-list-to-shuffle-with-python-random-shuffle
    """
    random.shuffle(self.library)
    
  def pass_priority(self):
    self.priority_index += 1;
    while self.priority_index >= len(self.players):
      self.priority_index -= len(self.players)


if __name__ == '__main__':

    
  test = GameState()
  print test

