#!/usr/bin/env python

""" Glory to Rome sim.
"""

from player import Player
from gtrutils import get_card_from_zone
from gamestate import GameState
import gtrutils
import card_manager 
from building import Building
import client2 as client

import collections
import logging
import pickle
import itertools
import time
import glob

lg = logging.getLogger('gtr')
# To set up logging, look at playgame.py

class StartOverException(Exception):
  pass

class CancelDialogException(Exception):
  pass

class Game(object):
  initial_pool_count = 5
  initial_jack_count = 6
  max_players = 5
  
  def __init__(self, game_state=None):
    self.game_state = game_state if game_state is not None else GameState()
    self.client_dict = {} # Dictionary of <name> : <Client()>
    logger = logging.getLogger('gtr')
    logger.addFilter(gtrutils.RoleColorFilter())
    logger.addFilter(gtrutils.MaterialColorFilter())

  def __repr__(self):
    rep=('Game(game_state={game_state!r})')
    return rep.format(game_state = self.game_state)

  def test_all_get_complete_building(self, building_name):
    from building import Building
    b = Building(
            building_name, 
            card_manager.get_material_of_card(building_name),
            [building_name]*card_manager.get_value_of_card(building_name),
            None, True)
    from copy import copy
    for p in self.game_state.players:
      p.buildings.append(copy(b))

  def test_all_get_incomplete_building(self, building_name):
    from building import Building
    b = Building(
            building_name, 
            card_manager.get_material_of_card(building_name),
            [building_name]*(card_manager.get_value_of_card(building_name)-1),
            None, False)
    from copy import copy
    for p in self.game_state.players:
      p.buildings.append(copy(b))

  def get_client(self, player_name):
    """ Returns the client object and updates the GameState to be current.
    """
    c = self.client_dict[player_name]
    c.game.game_state = self.game_state # Update client game state
    return c

  def add_player(self, name):
    self.game_state.find_or_add_player(name)
    if name not in self.client_dict:
      self.client_dict[name] = client.Client(name)

  def init_common_piles(self, n_players):
    lg.info('--> Initializing the game')

    self.init_library()
    first_player_index = self.init_pool(n_players)
    print 'Player {} goes first'.format(
        self.game_state.players[first_player_index].name)
    self.game_state.leader_index = first_player_index
    self.game_state.priority_index = first_player_index
    self.game_state.jack_pile.extend(['Jack'] * Game.initial_jack_count)
    self.init_foundations(n_players)

  def testing_init_piles(self, n_players):
    lg.info('--> Intializing for tests (Extra cards for everyone!)')

    cards=['Dock','Latrine','Storeroom','Atrium','Villa','Basilica']
    self.game_state.pool.extend(cards)
    for player in self.game_state.players:
      player.hand.extend(cards)
      player.hand.append('Jack')
      player.stockpile.extend(cards)
  
  def init_pool(self, n_players):
    """ Returns the index of the player that goes first. Fills the pool
    with one card per player, alphabetically first goes first. Resolves
    ties with more cards.
    """
    lg.info('--> Initializing the pool')
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
    lg.info('--> Initializing the foundations')
    n_out_of_town = 6 - n_players
    for material in card_manager.get_all_materials():
      self.game_state.in_town_foundations.extend([material]*n_players)
      self.game_state.out_of_town_foundations.extend([material]*n_out_of_town)

  def init_library(self):
    """ Starts with just a list of names for now.  """

    # read in card definitions from csv file:
    card_definitions_dict = card_manager.get_cards_dict_from_json_file()
    # the keys of the card dict are the card names:
    card_names = card_definitions_dict.keys()
    card_names.sort()

    self.game_state.library = []
    for card_name in card_names:
        
        card_count = card_manager.get_count_of_card(card_name)
        self.game_state.library.extend([card_name]*card_count)

    #self.game_state.library.sort()
    #print self.game_state.library
        
    lg.info('--> Initializing the library ({0} cards)'.format(
      len(self.game_state.library)))
    self.game_state.shuffle_library()

  def show_public_game_state(self):
    """ Prints the game state, showing only public information.

    This is the following: cards in the pool, # of cards in the library,
    # of jacks left, # of each foundation left, who's the leader, public
    player information.
    """

    gtrutils.print_header('Public game state', '+')

    # print leader and priority
    self.game_state.print_turn_info()

    # print pool. 
    pool_string = 'Pool: \n'
    pool_string += gtrutils.get_detailed_zone_summary(self.game_state.pool)
    lg.info(pool_string)
    
    # print exchange area. 
    try: 
      if self.game_state.exchange_area:
        exchange_string = 'Exchange area: \n'
        exchange_string += gtrutils.get_detailed_zone_summary(
          self.game_state.exchange_area)
        lg.info(exchange_string)
    except AttributeError: # backwards-compatibility for old games
      self.game_state.exchange_area = []
      
    # print N cards in library
    lg.info('Library : {0:d} cards'.format(len(self.game_state.library)))

    # print N jacks
    lg.info('Jacks : {0:d} cards'.format(len(self.game_state.jack_pile)))

    # print Foundations
    lg.info('Foundation materials:')
    foundation_string = '  In town: ' + gtrutils.get_short_zone_summary(
      self.game_state.in_town_foundations, 3)
    lg.info(foundation_string)
    foundation_string = '  Out of town: ' + gtrutils.get_short_zone_summary(
      self.game_state.out_of_town_foundations, 3)
    lg.info(foundation_string)

    print ''
    for player in self.game_state.players:
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

  def get_player_score(self, player):
    return self.get_buildings_score(player) + self.get_vault_score(player)

  def get_buildings_score(self, player):
    """ Add up the score from this players buildings.
    This includes the influence gained by sites, including payment
    from a Prison, and points from Statue and Wall.
    """
    influence_pts = player.get_influence_points()
    statue_pts = 0
    if self.player_has_active_building(player, 'Statue'):
      statue_pts = 3

    wall_pts = 0
    if self.player_has_active_building(player, 'Wall'):
      wall_pts = len(player.stockpile) // 2

    return influence_pts + statue_pts + wall_pts

  def get_vault_score(self, player):
    """ Examines all players' vaults to determine the vault
    score for each player, including the merchant bonuses.
    """
    bonuses = {}
    for player in self.game_state.players:
      bonuses[player.name] = []
    
    for material in card_manager.get_materials():
      # Set name to None if there's a tie, but maintain maximum
      name, maximum = None, 0
      for player in self.game_state.players:
        material_cards = filter(
            lambda x : card_manager.get_material_of_card(x) == material, player.vault)
        n = len(material_cards)
        if n > maximum:
          name = player.name
          maximum = n
        elif n == maximum:
          index = None
          maximum = n
      if name:
        bonuses[name].append(material)

    bonus_pts = 3*len(bonuses[player.name])

    card_pts = 0
    for card in player.vault:
      card_pts += card_manager.get_value_of_card(card)

    return card_pts + bonus_pts

    



  def get_clientele_limit(self, player):
    has_insula = self.player_has_active_building(player, 'Insula')
    has_aqueduct = self.player_has_active_building(player, 'Aqueduct')
    limit = player.get_influence_points()

    if has_insula: limit += 2
    if has_aqueduct: limit *= 2
    return limit

  def player_has_building(self, player, building):
    """ Checks if the player has the specific building object, not
    just a building of the same name.
    """
    return building in player.get_owned_buildings()

  def player_has_active_building(self, player, building):
    return building in self.get_active_building_names(player)

  def get_active_building_names(self, player):
    """ Returns a list of building names that are active for a player,
    taking the effect of the Stairway into account. See the 
    get_active_buildings() method for reference, but note that
    this method does not return duplicate names.
    """
    names = [b.foundation for b in self.get_active_buildings(player)]
    return list(set(names))

  def get_active_buildings(self, player):
    """ Returns a list of all Building objects that are active for a player.
    This may include buildings that belong to other players, in the case
    of the Stairway.

    The Player.get_active_buildings() method only accounts for buildings
    owned by the player. This ignores the case where a building owned 
    by another player may be Stairwayed, activating it for all players.

    Because mulitple players can have the same building stairwayed, this
    list might contain two or more buildings with the same foundation.
    """
    active_buildings = player.get_active_buildings()

    stairwayed_buildings = []
    for player in self.game_state.players:
      stairwayed_buildings.extend(player.get_stairwayed_buildings())

    return active_buildings + stairwayed_buildings

  def thinker_or_lead(self, player):
    lead_role = self.client_dict[player.name].ThinkerOrLeadDialog()
    if lead_role:
      # my_list[::-1] reverses the list
      for p in self.game_state.get_players_in_turn_order()[::-1]:
        self.game_state.stack.push_frame("perform_role_being_led", p)
      for p in self.game_state.get_following_players_in_order()[::-1]:
        self.game_state.stack.push_frame("follow_role_action", p)
      self.game_state.stack.push_frame("lead_role_action", player)

    else:
      self.game_state.stack.push_frame("perform_thinker_action", player)

  def process_stack_frame(self):
    if self.game_state.stack.stack:
      try:
        frame = self.game_state.stack.stack.pop()
      except IndexError:
        lg.info('Tried to pop from empty stack!')
        raise

      func = getattr(self,frame.function_name)
      func.__call__(*frame.entry_args)

  def run(self):
    """ Loop that keeps the game running.
    
    If the game is not started, push take_turn_stacked and run Game.pump()
    in an infinite loop.
    """
    if not self.game_state.is_started:
      leader = self.game_state.players[self.game_state.leader_index]
      self.game_state.stack.push_frame('take_turn_stacked', leader)

    while(True):
      self.pump()

  def load_game(self, log_file=None):
    """ Loads the game in log_file if specified.

    The default is to look in ./tmp for files like 'log_state_<timestamp>.log'
    """
    if log_file is None:
      log_file_prefix = 'tmp/log_state'
      log_files = glob.glob('{0}*.log'.format(log_file_prefix))
      log_files.sort()

    if not log_files:
      raise Exception('No saved games found in ' + log_file_prefix + '*')

    log_file_name = log_files[-1] # last element
    time_stamp = log_file_name.split('_')[-1].split('.')[0:1]
    time_stamp = '.'.join(time_stamp)
    asc_time = time.asctime(time.localtime(float(time_stamp)))
    lg.debug('Retrieving game state from {0}'.format(asc_time))

    self.get_previous_game_state(log_file_name)

    # After loading, print state since console will be empty
    self.show_public_game_state()
    self.print_complete_player_state(self.game_state.players[self.game_state.leader_index])

  def pump(self):
    self.process_stack_frame()
    self.save_game_state('tmp/log_state')

  def advance_turn(self):
    """ Moves the leader index, prints game state, saves, and pushes the next turn.
    """
    self.game_state.turn_number += 1
    self.game_state.increment_leader_index()
    leader_index = self.game_state.leader_index
    self.show_public_game_state()
    self.print_complete_player_state(self.game_state.players[leader_index])
    leader = self.game_state.players[leader_index]
    self.game_state.stack.push_frame('take_turn_stacked', leader)

  def take_turn_stacked(self, player):
    """
    Push ADVANCE_TURN frame.
    Push END_TURN frame.
    Push THINKER_OR_LEAD frame.
    """
    self.game_state.stack.push_frame("advance_turn")
    self.game_state.stack.push_frame("end_turn", player)
    self.game_state.stack.push_frame("thinker_or_lead", player)

  def post_game_state(self):
      save_game_state(self)

  def get_max_hand_size(self, player):
    max_hand_size = 5
    if self.player_has_active_building(player, 'Shrine'):
      max_hand_size += 2
    if self.player_has_active_building(player, 'Temple'):
      max_hand_size += 4

    return max_hand_size

  def perform_thinker_action(self, player):
    """
    1) If player has a Vomitorium, ask for discard.
    2) If player has a Latrine, and didn't use Vomitorium,
       ask for discard.
    3) Determine # cards that would be drawn. Check hand size,
       Temple, and Shrine. Also check if jacks are empty,
       and if drawing cards would end the game.
    3) Ask player for thinker type (jack or # cards)
    4) Draw cards for player.
    """
    client = self.get_client(player.name)
    if self.player_has_active_building(player, 'Vomitorium'):
      should_discard_all = client.UseVomitoriumDialog()
    else: should_discard_all = False

    if not should_discard_all and self.player_has_active_building(player, 'Latrine'):
      building = player.get_building('Latrine')
      latrine_card = client.UseLatrineDialog()
    else: latrine_card = None

    if latrine_card:
      self.game_state.discard_for_player(player, latrine_card)

    if should_discard_all:
      self.game_state.discard_all_for_player(player)
    
    client = self.get_client(player.name)
    thinker_type = client.ThinkerTypeDialog()
    if thinker_type == "Jack":
      self.game_state.draw_one_jack_for_player(player)
    if thinker_type == "Cards":
      self.game_state.thinker_for_cards(player, self.get_max_hand_size(player))
      if len(self.game_state.library) == 0:
        lg.info('The last Orders card has been drawn, Game Over.')
        end_game()

  def lead_role_action(self, leading_player):
    """
    1) Ask for cards used to lead
    2) Check legal leads using these cards (Palace, petition)
    3) Ask for role clarification if necessary
    4) Move cards to camp, set this turn's role that was led.
    """
    # This dialog checks that the cards used are legal
    client = self.get_client(leading_player.name)
    resp = client.LeadRoleDialog()
    role = resp[0]
    n_actions_total = resp[1]
    cards = resp[2:]
    self.game_state.role_led = role
    for c in cards:
      gtrutils.move_card(c, leading_player.hand, leading_player.camp)
      #leading_player.camp.append(leading_player.get_card_from_hand(c))
    leading_player.n_camp_actions = n_actions_total
    return role

  def follow_role_action(self, following_player, role=None):
    """
    1) Ask for cards used to follow
    2) Check for ambiguity in ways to follow (Crane, Palace, petition)
    3) Ask for clarification if necessary
    4) Move cards to camp
    """
    role = self.game_state.role_led
    client = self.get_client(following_player.name)
    # response could be None for thinker or [n_actions, card1, card2, ...]
    # for a role followed using petition, palace, etc.
    response = client.FollowRoleDialog()
    if response is None:
      print 'Follow role response is ' + str(response)
      self.game_state.stack.push_frame("perform_thinker_action", following_player)
    else:
      following_player.n_camp_actions = response[0]
      for c in response[1:]:
        following_player.camp.append(following_player.get_card_from_hand(c))

  def perform_role_being_led(self, player):
    """
    This is the main part of a player's turn. It figures how many actions
    the player gets from leading or following with a card (or cards).
    It then figures out how many clients get to perform their actions and
    activates them in turn. If the number of clients changes, it must be
    tracked here (eg. the first client finishes a Ludus Magna).
    1) Determine if the player gets to perform multiple actions (Palace)
    2) If the role is architect or craftsman, if the player is going
       to get multiples (Palace, clietele) or the have a Tower, set
       out_of_town_allowed=true
    3) While the player has actions {-->ACTION(perform_<role>_action)}
    4) Check how many clientele the player has (Stockpile, Ludus Magna).
    5) While the player has clientele actions { -->ACTION(perform_clientele_action) }
       Have to forward out_of_town_allowed.
    """
    # The clients are simple for Laborer, Merchant, and Legionary.
    # We can calculate how many actions you get before doing any of them.
    # Before all of them do the role that was led or followed
    role = self.game_state.role_led
    lg.info('Player {} is performing {}'.format(player.name, role))
    if role in ['Laborer', 'Merchant', 'Legionary']:
      has_cm = self.player_has_active_building(player, 'Circus Maximus')

      n_actions = player.get_n_clients(role, self.get_active_building_names(player))

      if player.is_following_or_leading():
        for i in range(player.n_camp_actions):
          self.perform_role_action(player, role, False)
        if has_cm : n_actions *= 2

      for i in range(n_actions):
        self.perform_clientele_action(player, role)


    # For Patron, anything is possible, since the Bath lets the player
    # perform arbitrary actions between Patron actions
    # For Craftsman and Architect, similarly, arbitrary things can happen
    # between actions as buildings are completed. Additionally, we need
    # to keep track of whether we have 2 Cra/Arch actions that can be used
    # to start a building out-of-town.
    # 
    # Things that can change the calculation of how many actions a player gets:
    #   1) Building a Circus Maximus - doubles unused clients
    #   2) Building a Ludus Magna - activates Merchant clients for other roles
    #
    # However note that clients that are new this turn *don't* get to perform
    # the action, regardless of how they were acquired.
    #
    # To handle this, we lock in the number of Patron and Merchant clients
    # at the beginning. Then we do all the real Patron-card client activations.
    # At that point we can check if there's a Ludus Magna, in which case we
    # do all the Merchant-card Patron actions.
    if role == 'Patron':
      n_patron = player.get_n_client_cards_of_role('Patron')
      n_merchant = player.get_n_client_cards_of_role('Merchant')

      if player.is_following_or_leading():
        # We can do extra palace actions successively, since
        # the number of them can't be changed.
        for i in range(player.n_camp_actions):
          self.perform_patron_action(player)
      
      patrons_used=0
      merchants_used=0

      while patrons_used < n_patron:
        self.perform_clientele_action(player, 'Patron')
        patrons_used += 1

      # Now if the player has build a Ludus Magna somehow, use the Merchants
      if self.player_has_active_building(player, 'Ludus Magna'):
        while merchants_used < n_merchant:
          self.perform_clientele_action(player, 'Patron')
          merchants_used += 1


    # Craftsman is similar to Patron, except that we need to check whether
    # we're allowed to out-of-town each action as we do it.
    # For the led role, we just check if there are any clients.
    # For the clients, we check if there are Craftsman yet to be used
    # then for the last guy, if there's a LM and a Merchant client.
    # If there's a CM, these checks only apply to the second action for
    # each client, since the first is always allowed to out-of-town.
    #
    # For the tower, we can always out-of-town, and used_oot should be
    # reset to zero after every call to perform_clientele_action()
    #
    # The same logic applies for architects, so we can combine the two.
    
    if role in ['Craftsman', 'Architect']:
      n_clients = player.get_n_client_cards_of_role(role)
      n_merchant = player.get_n_client_cards_of_role('Merchant')

      has_lm = self.player_has_active_building(player, 'Ludus Magna')
      has_tower = self.player_has_active_building(player, 'Tower')
      
      used_oot = False
      if player.is_following_or_leading():
        for i in range(player.n_camp_actions):
          if used_oot:
            used_oot = False
          else:
            can_oot = n_clients>0 or (i<player.n_camp_actions-1) or \
                      (has_lm and n_merchant > 0) or has_tower
            used_oot = self.perform_role_action(player, role, can_oot)
            if has_tower: used_oot = False

      clients_used = 0
      merchants_used = 0

      def check_merchants():
        has_lm = self.player_has_active_building(player, 'Ludus Magna')
        has_merchant = (n_merchant-merchants_used > 0)
        return has_lm and has_merchant

      while clients_used < n_clients:
        has_tower = self.player_has_active_building(player, 'Tower')
        can_oot = (n_clients - clients_used) > 1 or check_merchants() or has_tower
        used_oot = self.perform_clientele_action(player, role, can_oot, used_oot)
        if has_tower: used_oot = False

        clients_used += 1

      while check_merchants():
        has_tower = self.player_has_active_building(player, 'Tower')
        can_oot = (n_merchant - merchants_used) > 1
        used_oot = self.perform_clientele_action(player, role, can_oot, used_oot)
        if has_tower: used_oot = False

        merchants_used += 1


  def perform_clientele_action(self, player, role, out_of_town_allowed=False, out_of_town_used=False):
    """
    This function will activate one client. It makes two actions 
    if the player has a Circus Maximus. This function doesn't keep track
    of which clients have been used.
    1) -->ACTION(perform_<role>_action), forwarding out_of_town_allowed to architect/craftsman
    2) If the player has a Circus Maximus, do it again

    If out_of_town_allowed is True, there's another action after this one, so out_of_town_allowed
    is true for the last action we do here.

    We have to get the out_of_town_used input because this function handles the
    doubling by Circus Maximus, which means only the first of the doublet should
    be skipped due to out-of-town.
    
    We need to know if the last of the (possibly two) actions we do here is allowed
    to be out-of-town, so we take this input boolean as out_of_town_allowed. Of course,
    if we're doubling due to Circus Maximus, the first of this double is always
    allowed to out-of-town.

    Returns True if the last action was used to start an out-of-town site.
    """
    used_oot = out_of_town_used
    has_tower = self.player_has_active_building(player, 'Tower')
    if self.player_has_active_building(player, 'Circus Maximus'):
      if used_oot: used_oot = False
      else:
        used_oot = self.perform_role_action(player, role, True)
        if has_tower: used_oot = False

    if used_oot: used_oot = False
    else:
      used_oot = self.perform_role_action(player, role, out_of_town_allowed)
      if has_tower: used_oot = False

    return used_oot

  def perform_role_action(self, player, role, out_of_town_allowed):
    """ Multiplexer function for arbitrary roles. 
    Calls perform_<role>_action(), etc.

    It returns the value the role action returns. If this is a Craftsman
    or an Architect, it's whether or not the action was ued to start an
    out of town site. Otherwise it's False.
    """
    if role=='Patron':
      self.perform_patron_action(player)
      return False
    elif role=='Laborer':
      self.perform_laborer_action(player)
      return False
    elif role=='Architect':
      return self.perform_architect_action(player, out_of_town_allowed)
    elif role=='Craftsman':
      return self.perform_craftsman_action(player, out_of_town_allowed)
    elif role=='Legionary':
      self.perform_legionary_action(player)
      return False
    elif role=='Merchant':
      self.perform_merchant_action(player)
      return False
    else:
      raise Exception('Illegal role: {}'.format(role))

  def perform_laborer_action(self, player):
    """
    1) Ask for which card from the pool
    2) Move card from pool
    3) Check for Dock and ask for card from hand
    4) Move card from hand
    """
    has_dock = self.player_has_active_building(player, 'Dock')
    
    c = self.get_client(player.name)
    card_from_pool, card_from_hand = c.LaborerDialog()

    if card_from_hand and not has_dock:
      raise Exception('Illegal laborer from hand without Dock.')

    if card_from_pool:
      gtrutils.add_card_to_zone(
        gtrutils.get_card_from_zone(card_from_pool,self.game_state.pool),player.stockpile)
    if card_from_hand:
      gtrutils.add_card_to_zone(
        gtrutils.get_card_from_zone(card_from_hand,player.hand),player.stockpile)

  def perform_patron_action(self, player):
    """
    1) Abort if clientele full (Insula, Aqueduct)
    2) Ask for which card from pool
    3) Check for Bar and Aqueduct and 
    """
    # Bar, Aqueduct, Bath matter.
    # We don't have to check for these between each sub-action because it's not
    # possible for the state of buildings to change unless you've already built
    # a Bath. Also, building Bar after your patron from the pool doesn't let
    # you use the from-the-deck option.
    has_bar = self.player_has_active_building(player, 'Bar')
    has_aqueduct = self.player_has_active_building(player, 'Aqueduct')
    has_bath = self.player_has_active_building(player, 'Bath')

    client = self.get_client(player.name)

    if self.get_clientele_limit(player) - player.get_n_clients() > 0:
      card_from_pool = client.PatronFromPoolDialog()
      if card_from_pool:
        gtrutils.move_card(card_from_pool, self.game_state.pool, player.clientele)
        if has_bath:
          self.perform_role_action(player, card_manager.get_role_of_card(card_from_pool), False)

    client = self.get_client(player.name) # Do this to update client game state.

    if has_bar and self.get_clientele_limit(player) - player.get_n_clients() > 0:
      card_from_deck = client.PatronFromDeckDialog()
      if card_from_deck:
        card = self.game_state.draw_cards(1)[0]
        gtrutils.add_card_to_zone(card, player.clientele)
        if has_bath:
          self.perform_role_action(player, card_manager.get_role_of_card(card), False)

    client = self.get_client(player.name) # Do this to update client game state.

    if has_aqueduct and self.get_clientele_limit(player) - player.get_n_clients() > 0:
      card_from_hand = client.PatronFromHandDialog()
      if card_from_hand:
        gtrutils.move_card(card_from_hand, player.hand, player.clientele)
        if has_bath:
          self.perform_role_action(player, card_manager.get_role_of_card(card_from_hand), False)

  def check_building_start_legal(self, building, site):
    """ Checks if starting this building is legal. Accounts for Statue.

    The building parameter is just the name of the building,
    not the list structure used in Player.buildings.
    """
    if site is None or building is None: return False
    material = card_manager.get_material_of_card(building)
    return material == site or building == 'Statue'

  def check_building_add_legal(self, player, building_name, material_card):
    """ Checks if the specified player is allowed to add material
    to building. This accounts for the building material, the
    site material, a player's active Road, Scriptorium, and Tower.
    This does not handle Stairway, which is done in perform_architect_action().
    
    This checks if the material is legal, but not if the building is already
    finished or malformed (eg. no site, or no foundation).

    The building provided is the list structure used
    to represent buildings in Player.buildings, so the site
    is available from there.
    """
    if material_card is None or building_name is None:
      lg.warn('Illegal add: material=' + str(material_card) + '  building='+ building_name)
      return False
    has_tower = self.player_has_active_building(player, 'Tower')
    has_road = self.player_has_active_building(player, 'Road')
    has_scriptorium = self.player_has_active_building(player, 'Scriptorium')

    if building_name not in player.get_owned_building_names():
      lg.warn('Illegal build: {} doesn\'t own building {}'.format(player.name, building_name))
      return False

    building = player.get_building(building_name)

    # The sites are 'Wood', 'Concrete', etc.
    site_material = building.site
    foundation = building.foundation
    material = card_manager.get_material_of_card(material_card)

    foundation_material = card_manager.get_material_of_card(foundation)

    if has_tower and material == 'Rubble':
      return True
    elif has_scriptorium and material == 'Marble':
      return True
    elif has_road and (foundation_material == 'Stone' or site_material == 'Stone'):
      return True
    elif material == foundation_material or material == site_material:
      return True
    else:
      lg.warn('Illegal add, material ({0}) doesn\'t '.format(material) +
                   'match building material ({0}) '.format(foundation_material) +
                   'or site material ({0})'.format(site_material))
      return False

  
  def perform_craftsman_action(self, player, out_of_town_allowed):
    """
    Buildings that matter : Fountain, Tower, Road, Scriptorium.
    Also special case for Statue.

    Returns whether or not the out of town site was used.
    """
    # Buildings that matter:
    has_fountain = self.player_has_active_building(player, 'Fountain')
    has_tower = self.player_has_active_building(player, 'Tower')
    has_road = self.player_has_active_building(player, 'Road')
    has_scriptorium = self.player_has_active_building(player, 'Scriptorium')

    used_out_of_town = False
    building, material, site = (None, None, None)

    client = self.get_client(player.name)

    # Use fountain?
    if has_fountain and client.UseFountainDialog():
      card_from_deck = self.game_state.draw_cards(1)[0]
      player.add_cards_to_hand([card_from_deck])

      client = self.get_client(player.name)

      skip_action, building, material, site =\
        client.FountainDialog(card_from_deck, out_of_town_allowed)

      if skip_action:
        return False

    else:
      client = self.get_client(player.name)
      (building, material, site) = client.CraftsmanDialog(out_of_town_allowed)

    starting_new_building = site is not None
    already_owned = player.owns_building(building)
    start_okay = False if not site else \
      self.check_building_start_legal(building, site)
    add_okay = False if not material else \
      self.check_building_add_legal(player, building, material)
    if starting_new_building and already_owned:
      lg.warn(
        'Illegal build. {} is already owned by {} and cannot be started'
        .format(building, player.name))

    elif starting_new_building and start_okay and not already_owned:
      b = Building()
      b.foundation = gtrutils.get_card_from_zone(building, player.hand)
      if site in self.game_state.in_town_foundations:
        b.site = gtrutils.get_card_from_zone(site, self.game_state.in_town_foundations)
      elif out_of_town_allowed and site in self.game_state.out_of_town_foundations:
        b.site = gtrutils.get_card_from_zone(site, self.game_state.out_of_town_foundations)
        used_out_of_town = True
      elif not out_of_town_allowed and site in self.game_state.out_of_town_foundations:
        lg.warn(
            'Illegal build, not enough actions to build on out of town {} site'.format(site))
        return False
      else:
        lg.warn('Illegal build, site {} does not exist in- or out-of-town'.format(site))
        return False
      player.buildings.append(b)

    elif not starting_new_building and player.get_building(building).is_completed():
      lg.warn(
        'Illegal build. {} is already completed'.format(building))

    elif not starting_new_building and add_okay:
      b = player.get_building(building)
      gtrutils.move_card(material, player.hand, b.materials)
      completed = False
      if has_scriptorium and card_manager.get_material_of_card(material) == 'Marble':
        lg.info('Player {} completed building {} using Scriptorium'.format(
          player.name, str(building)))
        completed = True
      elif len(b.materials) == card_manager.get_value_of_material(b.site):
        lg.info('Player {} completed building {}'.format(player.name, str(building)))
        completed = True

      if completed:
        b.completed = True
        gtrutils.add_card_to_zone(b.site, player.influence)
        self.resolve_building(player, building)

    else:
      lg.warn('Illegal craftsman, building={}, site={}, material={}'.format(
                   building, site, material))
      return False

    return used_out_of_town
    

  def perform_legionary_action(self, player):
    """
    Buildings that matter: Bridge, Coliseum, Palisade, Wall
    1) Ask for card to show for demand
    2) Ask for affected players to give card of material, or say "Glory to Rome!"
    3) If player has coliseum, ask for affected players to select client to send to the lions.
    4) If player has bridge, ask affected players for material from stockpile
    """
    lg.info('=== Rome demands implementation! ===')
    lg.info('\n=== Glory to Rome! ===')

    # Buildings that matter:
    has_bridge = self.player_has_active_building(player, 'Bridge')
    has_coliseum = self.player_has_active_building(player, 'Coliseum')
    has_palisade = self.player_has_active_building(player, 'Palisade')
    has_wall = self.player_has_active_building(player, 'Wall')

    client = self.get_client(player.name)

    card_to_demand_material = client.LegionaryDialog()
    material = card_manager.get_material_of_card(card_to_demand_material)
    lg.info('Rome demands %s!!' % material)

    pass
    

  def perform_architect_action(self, player, out_of_town_allowed):
    """
    Performs ArchitectDialog, then StairwayDialog if the player
    has an active stairway.

    out_of_town_allowed is indicated by the caller if this architect would
    be stacked up with another, so that an out-of-town site may be used.
    In that case, this will return an indication and the caller can nix the
    next architect action.
    1) Ask for building to start or material to add. (Archway, Stairway)
    2) If out_of_town_allowed is false, don't allow out of town, otherwise
       start the out-of-town site and return the indicator.
    3) Check legality of material, building + site.
    4) Place material or building -->ACTION(place_material) -->ACTION(start_building)

    Returns whether or not the out of town site was used.

    Buildings that matter : Archway, Tower, Road, Scriptorium, Villa, Stairway
    Also special case for Statue.

    Returns whether or not the out of town site was used.
    """
    # Buildings that matter:
    has_archway = self.player_has_active_building(player, 'Archway')
    has_tower = self.player_has_active_building(player, 'Tower')
    has_road = self.player_has_active_building(player, 'Road')
    has_scriptorium = self.player_has_active_building(player, 'Scriptorium')
    has_stairway = self.player_has_active_building(player, 'Stairway')

    used_out_of_town = False
    building, material, site = (None, None, None)

    client = self.get_client(player.name)
    (building, material, site, from_pool) = client.ArchitectDialog(out_of_town_allowed)

    if building is None and site is None and material is None:
      lg.info('Skipped architect action.')
    else:
      starting_new_building = site is not None
      already_owned = player.owns_building(building)
      start_okay = False if not site else \
        self.check_building_start_legal(building, site)
      add_okay = False if not material else \
        self.check_building_add_legal(player, building, material)

      if starting_new_building and already_owned:
        lg.warn(
          'Illegal build. {} is already owned by {} and cannot be started'
          .format(building, player.name))

      elif starting_new_building and start_okay and not already_owned:
        b = Building()
        b.foundation = gtrutils.get_card_from_zone(building, player.hand)
        if site in self.game_state.in_town_foundations:
          b.site = gtrutils.get_card_from_zone(site, self.game_state.in_town_foundations)
        elif site in self.game_state.out_of_town_foundations:
          b.site = gtrutils.get_card_from_zone(site, self.game_state.out_of_town_foundations)
          used_out_of_town = True
        else:
          lg.warn('Illegal build, site {} does not exist in- or out-of-town'.format(site))
          return False
        player.buildings.append(b)

      elif not starting_new_building and player.get_building(building).is_completed():
        lg.warn(
          'Illegal build. {} is already completed'.format(building))

      elif not starting_new_building and add_okay:
        b = player.get_building(building)
        material_zone = self.game_state.pool if from_pool else player.stockpile
        gtrutils.move_card(material, material_zone, b.materials)
        completed = False
        if has_scriptorium and card_manager.get_material_of_card(material) == 'Marble':
          lg.info('Player {} completed building {} using Scriptorium'.format(
            player.name, building,foundation))
          completed = True
        elif building == 'Villa':
          lg.info(
            'Player {} completed Villa with one material using Architect'.format(player.name))
          completed = True
        elif len(b.materials) == card_manager.get_value_of_material(b.site):
          lg.info('Player {} completed building {}'.format(player.name, str(b)))
          completed = True

        if completed:
          b.completed = True
          gtrutils.add_card_to_zone(b.site, player.influence)
          self.resolve_building(player, building)

      else:
        lg.warn('Illegal Architect, building={}, site={}, material={}'.format(
                     building, site, material))
        lg.warn('  add_okay='+str(add_okay)+'  start_okay='+str(start_okay))
        return False

    if has_stairway:
      client = self.get_client(player.name)
      building, material, from_pool = client.StairwayDialog()
      if building is not None and material is not None:
        other_player = [p for p in self.game_state.players
                        if building in p.buildings][0]
        material_zone = self.game_state.pool if from_pool else player.stockpile
        lg.info(
          'Player {} used Stairway to add a material to player {}\'s {}, ' +
          'activating its function for all players'.format(
          player.name, other_player.name, str(building)))
        gtrutils.move_card(material, material_zone, building.stairway_materials)

    return used_out_of_town


  def perform_merchant_action(self, player):
    """
    Do we log materials? We should in case the display messes up,
    but maybe only until end of turn.
    1) Abort if vault full. Also between each step here. (Market)
    2) Ask player to select material from Stockpile. Reveal and place in vault.
    3) If Basilica, ask player to select from hand. No reveal and vault.
    4) If Atrium, ask player to select top of deck. No reveal and vault.
    """
    vault_limit = player.get_influence_points()
    if self.player_has_active_building(player, 'Market'): card_limit += 2

    card_limit = vault_limit - len(player.vault)

    has_atrium = self.player_has_active_building(player, 'Atrium')
    has_basilica = self.player_has_active_building(player, 'Basilica')

    merchant_allowed = (card_limit>0) \
      and (has_atrium or len(player.stockpile)>0 or (has_basilica and len(player.hand)>0))

    if merchant_allowed:
      client = self.get_client(player.name)
      # card_from_deck is a boolean. The others are actual card names.
      card_from_stockpile, card_from_hand, card_from_deck = client.MerchantDialog()

      if card_from_stockpile:
        gtrutils.add_card_to_zone(
          gtrutils.get_card_from_zone(card_from_stockpile, player.stockpile), player.vault)
      if card_from_hand:
        gtrutils.add_card_to_zone(
          gtrutils.get_card_from_zone(card_from_hand, player.hand), player.vault)
      if card_from_deck:
        gtrutils.add_card_to_zone(self.game_state.draw_cards(1)[0], player.vault)

  def kids_in_pool(self, player):
    """
    Place cards in camp into the pool.
    1) If Sewer, ask to move cards into stockpile.
    2) If dropping a Jack, ask players_with_senate in order.
    """
    lg.info('\n ==== KIDS IN POOL ====\n')
    print 'Players in turn order ' + str(self.game_state.get_players_in_turn_order())
    for player in self.game_state.get_players_in_turn_order():
      player_index = self.game_state.players.index(player)
      other_players_in_order = self.game_state.get_players_in_turn_order(player_index)
      other_players_in_order.pop(0)

      players_with_senate = [p for p in other_players_in_order 
                             if self.player_has_active_building(p, 'Senate')]
      
      has_sewer = self.player_has_active_building(player, 'Sewer') 
      if has_sewer:
        client = self.get_client(player.name)
        cards = client.UseSewerDialog()
        for card in cards:
          gtrutils.move_card(card, player.camp, player.stockpile)

      print('Camp = ' + str(player.camp))
      for card in player.camp:
        if card is 'Jack':
          for senate_player in players_with_senate:
            client = self.get_client(senate_player.name)
            if client.UseSenateDialog():
              gtr_utils.move_card(card, player.camp, senate_player.hand)
              break
        else:
          lg.info('Moving card {} from camp to pool'.format(card))
          gtrutils.move_card(card, player.camp, self.game_state.pool)

  def end_turn(self, player):
    """
    Ask for Academy thinker. Need to figure out whether or not Senate goes first.
    1) Find players_with_senate
    2) --> kids_in_pool(player)
    """
    self.kids_in_pool(player)
    has_academy = self.player_has_active_building(player, 'Academy') 

    if has_academy and player.performed_craftsman:
      client = self.get_client(player.name)
      client.ThinkerTypeDialog()
    
    player.performed_craftsman = False
    player.n_camp_actions = 0

  def end_game(self):
    """ The game is over. This determines a winner.
    """
    lg.info('      =================  ')
    lg.info('   ====== GAME OVER =====')
    lg.info('      =================  ')
    lg.info('  The only winner is Rome.')
    lg.info('  Glory to Rome!')
    lg.info('\n')
    for p in self.game_state.players:
      lg.info('Score for player {} : {}'.format(p.name, self.get_player_score(p)))
    lg.info('\n')
    raise Exception('Game over.')

  def add_material_to_building(self, player, material, source, building):
    """
    Adds a material to a building and checks if the building is complete
    The caller should make sure it's legal.
    1) Add material to building, indicate Stairway separately.
    2) If building is completed, trigger resolve_<building> action
    """
    pass

  def resolve_building(self, player, building):
    """ Switch on completed building to resolve the "On Completion" effects.
    """
    if str(building) == 'Catacomb':
      self.end_game()
    elif str(building) == 'Foundry':
      n = player.get_influence_points()
      for i in range(n):
          lg.info(
              'Foundry: Performing Laborer {}/{} for player {}'.format(i+1,n,player.name))
          self.perform_laborer_action(player)
    elif str(building) == 'Garden':
      n = player.get_influence_points()
      for i in range(n):
          lg.info(
              'Garden: Performing Patron {}/{} for player {}'.format(i+1,n,player.name))
          self.perform_patron_action(player)
    elif str(building) == 'School':
      n = player.get_influence_points()
      for i in range(n):
          lg.info(
              'School: Performing Thinker {}/{} for player {}'.format(i+1,n,player.name))
          self.perform_thinker_action(player)
    elif str(building) == 'Amphitheatre':
      n = player.get_influence_points()
      for i in range(n):
          lg.info(
              'Amphitheatre: Performing Craftsman {}/{} for player {}'.format(i+1,n,player.name))
          self.perform_craftsman_action(player)

  def save_game_state(self, log_file_prefix='log_state'):
    """
    Save game state to file
    """
    # get the current time, in seconds 
    time_stamp = time.time()
    self.game_state.time_stamp = time_stamp
    file_name = '{0}_{1}.log'.format(log_file_prefix, time_stamp)
    log_file = file(file_name, 'w')
    pickle.dump(self.game_state, log_file)
    log_file.close()

  def get_previous_game_state(self, log_file_name):
    """
    Return saved game state from file
    """
    log_file = file(log_file_name, 'r')
    game_state = pickle.load(log_file)
    log_file.close()
    self.game_state = game_state
    lg.info('Loaded game state.')
    return game_state

# vim: ts=8:sts=2:sw=2:et
