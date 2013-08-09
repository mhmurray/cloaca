#!/usr/bin/env python

""" Glory to Rome sim.

"""

from player import Player
from gtrutils import _get_card_from_zone
from gamestate import GameState
import collections

class Game:
  initial_pool_count = 5
  initial_jack_count = 6
  max_players = 5
  
  def __init__(self, game_state=None):
    self.game_state = game_state if game_state is not None else GameState()
    self.leader = None
    self.priority = None

  def __repr__(self):
    rep=('Game(game_state={game_state!r})')
    return rep.format(game_state = self.game_state)

  def init_common_piles(self, n_players):
    self.init_library()
    first_player = self.init_pool(n_players)
    print 'Player {} goes first'.format(self.game_state.players[first_player].name)
    self.leader = first_player
    self.priority = first_player
    self.game_state.jack_pile.extend(['Jack'] * Game.initial_jack_count)
    self.init_foundations(n_players)
  
  def init_pool(self, n_players):
    """ Returns the index of the player that goes first. Fills the pool
    with one card per player, alphabetically first goes first. Resolves
    ties with more cards.
    """
    player_cards = [""]*n_players
    all_cards_drawn = []
    has_winner = False
    winner = None
    while not has_winner:
      # Draw new cards for winners, or everyone in the first round
      for i,card in enumerate(player_cards):
        if card is None: continue
        player_cards[i] = self.game_state.draw_cards(1)[0]
        all_cards_drawn.append(player_cards[i])
      # Winnow player_cards to only have the alphabetically first cards
      winning_card = min( [c for c in player_cards if c is not None])
      has_winner = player_cards.count(winning_card) == 1
      if has_winner: winner = player_cards.index(winning_card)
      # Set all players' cards to None if they aren't winners
      player_cards = map(lambda c : c if c==winning_card else None, player_cards)

    self.game_state.pool.extend(all_cards_drawn)
    return winner
    

  def init_foundations(self, n_players):
    for key in self.game_state.foundations:
      # name is 'Rubble', etc. Foundation name is 'Rubble Foundation'.
      self.game_state.foundations[key] = [key + ' Foundation'] * n_players

  def init_library(self):
    """ Starts with a minimal set of cards. They're just a list of names
    for now.
    """
    initial_cards = [
      'Latrine', 'Vomitorium', 'Colisseum', 'Statue', 'Pallisade', 'Atrium'
      ]
    self.game_state.library = initial_cards * 5
    self.game_state.shuffle_library()

  def show_public_game_state(self):
    """ Prints the game state, showing only public information.

    This is the following: cards in the pool, # of cards in the library,
    # of jacks left, # of each foundation left, who's the leader, public
    player information.
    """
    # print leader and priority
    print 'Leader : {0},   Priority : {1}'.format(self.leader, self.priority)

    # print pool. Counter counts multiplicities for us.
    counter = collections.Counter(self.game_state.pool)
    pool_string = 'Pool: '
    for card, count in counter.items():
      pool_string += '{0}[{1:d}], '.format(card[:4], count)
    pool_string.rstrip(', ')
    print pool_string
    
    # print N cards in library
    print 'Library : {0:d} cards'.format(len(self.game_state.library))

    # print N jacks
    print 'Jacks : {0:d} cards'.format(len(self.game_state.jack_pile))

    # print Foundations
    foundation_string = 'Foundations: '
    for name, card_list in self.game_state.foundations.items():
      foundation_string += '{0}[{1:d}], '.format(name, len(card_list))
    foundation_string.rstrip(', ')
    print foundation_string

    print ''
    for player in self.game_state.players:
      #self.print_public_player_state(player)
      self.print_complete_player_state(player)
      print ''

  def print_public_player_state(self, player):
    """ Prints a player's public information.

    This is the following: Card in camp (if existing), clientele, influence,
    number of cards in vault, stockpile, number of cards/jacks in hand, 
    buildings built, buildings under construction and stage of completion.
    """
    # print name
    print 'Player {0} :'.format(player.name)

    # print hand
    print player.describe_hand_public()
    
    # print Vault
    if len(player.vault) > 0:
      print player.describe_vault_public()

    # print clientele
    if len(player.clientele) > 0:
      print player.describe_clientele()

    # print Stockpile
    if len(player.stockpile) > 0:
      print player.describe_stockpile()

    # print Buildings
    if len(player.buildings) > 0:
      print player.describe_buildings()


  def print_complete_player_state(self, player):
    """ Prints a player's information, public or not.

    This is the following: Card in camp (if existing), clientele, influence,
    cards in vault, stockpile, cards in hand,
    buildings built, buildings under construction and stage of completion.
    """
    # print name
    print 'Player {0} :'.format(player.name)

    # print hand
    print player.describe_hand_private()
    
    # print Vault
    if len(player.vault) > 0:
      print player.describe_vault_public()

    # print clientele
    if len(player.clientele) > 0:
      print player.describe_clientele()

    # print Stockpile
    if len(player.stockpile) > 0:
      print player.describe_stockpile()

    # print Buildings
    if len(player.buildings) > 0:
      print player.describe_buildings()

class Card:
  def __init__(self, name=None, material=None, value=None, role=None):
    self.name = name or ''
    self.short_name = name[:4] if name else ''
    self.material = material
    self.value = value or 0
    self.role = role

  def __repr__(self):
    rep=('Card(name={name!r}, material={material!r}, '
         'value={value!r}, role={role!r})')
    return rep.format(name=self.name, material=self.material,
      value=self.value, role=self.role)

  def __str__(self):
    return self.name

