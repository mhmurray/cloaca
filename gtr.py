#!/usr/bin/env python

""" Glory to Rome sim.
"""

from player import Player
from gtrutils import get_card_from_zone
from gamestate import GameState
import gtrutils
import card_manager 
from building import Building

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

class Game:
  initial_pool_count = 5
  initial_jack_count = 6
  max_players = 5
  
  def __init__(self, game_state=None):
    self.game_state = game_state if game_state is not None else GameState()
    logger = logging.getLogger('gtr')
    logger.addFilter(gtrutils.RoleColorFilter())
    logger.addFilter(gtrutils.MaterialColorFilter())

  def __repr__(self):
    rep=('Game(game_state={game_state!r})')
    return rep.format(game_state = self.game_state)

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

  def take_turn(self, player):
    """
    !!! This no longer used after implementing take_turn_stacked !!!
    1) Ask for thinker or lead
    2) -->ACTION(thinker), -->ACTION(lead_role)
    """
    lead_role = self.ThinkerOrLeadDialog(player)
    if lead_role:
      role = self.lead_role_action(player)
      for p in self.game_state.get_following_players_in_order():
        self.follow_role_action(p, role)

      self.perform_role_being_led(player)
      for p in self.game_state.get_following_players_in_order():
        self.perform_role_being_led(p)
    else:
      self.perform_thinker_action(player)
      
    self.end_turn(player)

  def thinker_or_lead(self, player):
    lead_role = self.ThinkerOrLeadDialog(player)
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
      frame = self.game_state.stack.stack.pop()
      func = getattr(self,frame.function_name)
      func.__call__(*frame.entry_args)

  def run(self, load_state = False):
    """ Loop that keeps the game running.
    
    If load_state is True, we load the old state and start running.
    The stack should never be empty, but we might load in the middle
    of a turn, which means we haven't printed the game state. Print
    it again, maybe redundantly.
    """
    if load_state:
      self.get_previous_game_state('tmp/log_state')
      self.show_public_game_state()
      self.print_complete_player_state(self.game_state.players[self.game_state.leader_index])
    else:
      leader = self.game_state.players[self.game_state.leader_index]
      self.game_state.stack.push_frame('take_turn_stacked', leader)

    while(self.game_state.stack.stack):
      self.save_game_state('tmp/log_state')
      self.process_stack_frame()

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
    Push END_TURN frame.
    Push THINKER_OR_LEAD frame.
    Yield.
    """
    self.game_state.stack.push_frame("advance_turn")
    self.game_state.stack.push_frame("end_turn", player)
    self.game_state.stack.push_frame("thinker_or_lead", player)

  def ThinkerOrLeadDialog(self, player):
    """ Asks whether the player wants to think or lead at the start of their
    turn.

    Returns True if 'Lead' is chosen, False if 'Thinker'.
    """
    lg.info('Start of {}\'s turn: Thinker or Lead?'.format(player.name))

    choices = ['Thinker', 'Lead']
    index = self.choices_dialog(choices, 'Select one.')
    return index==1

  def UseLatrineDialog(self, player):
    """ Asks which card, if any, the player wishes to use with the 
    Latrine before thinking.
    """
    lg.info('Choose a card to discard with the Latrine.')

    sorted_hand = sorted(player.hand)
    card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]
    card_choices.insert(0, 'Skip discard')
    index = self.choices_dialog(card_choices, 'Select a card to discard')

    if index == 0:
      return None
    else:
      return sorted_hand[index-1]

  def UseVomitoriumDialog(self, player):
    """ Asks if the player wants to discard their hand with the Vomitorium.

    Returns True if player uses the Vomitorium, False otherwise.
    """
    lg.info('Discard hand with Vomitorium?')

    choices = ['Discard all', 'Skip Vomitorium']
    index = self.choices_dialog(choices)

    return index == 0

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
    if self.player_has_active_building(player, 'Vomitorium'):
      should_discard_all = self.UseVomitoriumDialog(player)
    else: should_discard_all = False

    if not should_discard_all and self.player_has_active_building(player, 'Latrine'):
      building = player.get_building('Latrine')
      latrine_card = self.UseLatrineDialog(player)
    else: latrine_card = None

    if latrine_card:
      self.game_state.discard_for_player(player, latrine_card)

    if should_discard_all:
      self.game_state.discard_all_for_player(player)
    
    thinker_type = self.ThinkerTypeDialog(player)
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
    resp = self.LeadRoleDialog(self.game_state, leading_player)
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
    # response could be None for thinker or [n_actions, card1, card2, ...]
    # for a role followed using petition, palace, etc.
    response = self.FollowRoleDialog(following_player, role)
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
    
    card_from_pool, card_from_hand = self.LaborerDialog(player, has_dock)

    if card_from_pool:
      gtrutils.add_card_to_zone(
        gtrutils.get_card_from_zone(card_from_pool,self.game_state.pool),player.stockpile)
    if card_from_hand:
      gtrutils.add_card_to_zone(
        gtrutils.get_card_from_zone(card_from_hand,player.hand),player.stockpile)

  def PatronFromPoolDialog(self, player):
    card_from_pool = None
    sorted_pool = sorted(self.game_state.pool)

    if len(sorted_pool):
      lg.info('Performing Patron, choose a client from pool (Clientele {}/{})'.format(
        str(player.get_n_clients()),str(self.get_clientele_limit(player))))
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_pool]
      card_choices.insert(0,'Skip this action')

      card_index = self.choices_dialog(card_choices, 'Select a card to take into your clientele')
      if card_index > 0:
        card_from_pool = sorted_pool[card_index-1]

    return card_from_pool

  def PatronFromDeckDialog(self, player):
    lg.info(
      'Performing Patron. Do you wish to take a client from the deck? (Clientele {}/{})'.format(
      str(player.get_n_clients()),str(self.get_clientele_limit(player))))
    choices = ['Yes','No']
    return self.choices_dialog(choices) == 0

  def PatronFromHandDialog(self, player):
    card_from_hand = None
    sorted_hand = sorted([card for card in player.hand if card != 'Jack'])

    if len(sorted_hand):
      lg.info('Performing Patron, choose a client from hand (Clientele {}/{})'.format(
        str(player.get_n_clients()),str(self.get_clientele_limit(player))))
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]
      card_choices.insert(0,'Skip this action')

      card_index = self.choices_dialog(card_choices, 'Select a card to take into your clientele')
      if card_index > 0:
        card_from_hand = sorted_hand[card_index-1]

    return card_from_hand

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

    if self.get_clientele_limit(player) - player.get_n_clients() > 0:
      card_from_pool = self.PatronFromPoolDialog(player)
      if card_from_pool:
        gtrutils.move_card(card_from_pool, self.game_state.pool, player.clientele)
        if has_bath:
          self.perform_role_action(player, card_manager.get_role_of_card(card_from_pool), False)

    if has_bar and self.get_clientele_limit(player) - player.get_n_clients() > 0:
      card_from_deck = self.PatronFromDeckDialog(player)
      if card_from_deck:
        card = self.game_state.draw_cards(1)
        gtrutils.add_card_to_zone(card, player.clientele)
        if has_bath:
          self.perform_role_action(player, card_manager.get_role_of_card(card), False)

    if has_aqueduct and self.get_clientele_limit(player) - player.get_n_clients() > 0:
      card_from_hand = self.PatronFromHandDialog(player)
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

  def UseFountainDialog(self, player):
    choices = ['Use Fountain, drawing from deck', 'Don\'t use Fountain, play from hand']
    choice_index = choices_dialog(choices, 'Do you wish to use your Fountain?')
    return choice_index == 0

  def FountainDialog(self, player, card_from_deck, out_of_town_allowed):
    """ The Fountain allows you to draw a card from the deck, then
    choose whether to use the card with a craftsman action. The player
    is allowed to just keep (draw) the card.
    
    This function returns a tuple (skip, building, material, site),
    with the following elements:
      1) Whether the player skips the action or not (drawing the card)
      2) The building to be started or added to
      3) The material to be added to an incomplete building
      4) The site to start a building on.

    The material will always be the Fountain card, and the building might be.
    """
    # TODO: Could check if it's even possible to use the card
    skip, building, material, site = (False, None, None, None)

    material_of_card = card_manager.get_material_of_card(card_from_deck)
    
    card_choices = \
      [str(b) for b in player.get_incomplete_buildings()
      if self.check_building_add_legal(player, str(b), card_from_deck)]

    if not player.owns_building(card_from_deck):
      card_choices.insert(0, 'Start {} buidling'.format(card_from_deck))

    if len(card_choices) == 0:
      lg.warn('Can\'t use {} with a craftsman action'.format(card_from_deck))
      return (True, None, None, None)

    lg.info('Performing Craftsman with {}, choose a building option:'
                 .format(card_from_deck))

    choices = ['Use {} to start or add to a building'.format(card_from_deck),
               'Don\'t play card, draw and skip action instead.']
    choice_index = self.choices_dialog(choices)

    if choice_index == 1:
      lg.info('Skipping Craftsman action and drawing card')
      return (True, None, None, None)

    card_index = self.choices_dialog(card_choices, 'Select a building option')
    if card_index == 0: # Starting a new building
      building = card_from_deck

      if building == 'Statue':
        sites = card_manager.get_all_materials()
        site_index = choices_dialog(sites)
        site = sites[site_index]
      else:
        site = card_manager.get_material_of_card(building)

    else: # Adding to a building from hand
      building = card_choices[card_index-1]
      material = card_from_deck

    return False, building, material, site
  
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

    # Use fountain?
    if has_fountain and self.UseFountainDialog(player):
      card_from_deck = self.game_state.draw_cards(1)
      player.add_cards_to_hand([card_from_deck])

      skip_action, building, material, site =\
        self.FountainDialog(player, card_from_deck, out_of_town_allowed)

      if skip_action:
        return False

    else:
      (building, material, site) = self.CraftsmanDialog(player, out_of_town_allowed)

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
    
  def LegionaryDialog(self, player):
    lg.info('Card to use for legionary:')
    hand = player.hand
    sorted_hand = sorted(hand)
    card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]

    card_index = self.choices_dialog(card_choices, 
        'Select a card to use to demand material')
    card_from_hand = sorted_hand[card_index]

    lg.info('Using card %s' % gtrutils.get_detailed_card_summary(card_from_hand))
    return card_from_hand
        

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

    card_to_demand_material = self.LegionaryDialog(player)
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

    (building, material, site, from_pool) = self.ArchitectDialog(player, out_of_town_allowed)

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
      building, material, from_pool = self.StairwayDialog(player)
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
      # card_from_deck is a boolean. The others are actual card names.
      card_from_stockpile, card_from_hand, card_from_deck = \
        self.MerchantDialog(player, has_atrium, has_basilica, card_limit)

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
        cards = self.UseSewerDialog(player)
        for card in cards:
          gtrutils.move_card(card, player.camp, player.stockpile)

      print('Camp = ' + str(player.camp))
      for card in player.camp:
        if card is 'Jack':
          for senate_player in players_with_senate:
            if self.UseSenateDialog(senate_player, player):
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
      self.ThinkerTypeDialog(player)
    
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

  def get_previous_game_state(self, log_file_prefix='log_state'):
    """
    Return saved game state from file
    """
    log_files = glob.glob('{0}*.log'.format(log_file_prefix))
    log_files.sort()
    #for log_file in log_files: # print all log file names, for debugging
    #  lg.debug(log_file)

    if not log_files:
      return None

    log_file_name = log_files[-1] # last element
    time_stamp = log_file_name.split('_')[-1].split('.')[0:1]
    time_stamp = '.'.join(time_stamp)
    asc_time = time.asctime(time.localtime(float(time_stamp)))
    #lg.debug('Retrieving game state from {0}'.format(asc_time))

    log_file = file(log_file_name, 'r')
    game_state = pickle.load(log_file)
    log_file.close()
    self.game_state = game_state
    lg.info('Loaded game state.')
    return game_state

  def print_selections(self, choices_list, selectable):
    """ Prints [%d] <selection> for each element in choices_list
    if the corresponding entry in selectable is True.
    """
    i_choice = 1
    for choice, select in itertools.izip_longest(choices_list, selectable,
                                                 fillvalue=True):
      if select:
        lg.info('  [{0:2d}] {1}'.format(i_choice, choice))
        i_choice+=1
      else:
        lg.info('       {0}'.format(choice))

  def choices_dialog(self, choices_list, 
                     prompt='Please make a selection',
                     selectable=None):
    """ Returns the index in the choices_list selected by the user or
    raises a StartOverException or a CancelDialogExeption.
    
    The <selectable> parameter is a list of booleans of the same
    length as choices_list, indicating whether the item is a valid
    selection. If None or unspecified, all items are selectable.
    If the list is shorter than choices_list, additional True elements
    are added to match length.
    """

    if selectable is None:
      selectable = [True] * len(choices_list)
    
    # Match length
    selectable += [True]*(len(choices_list) - len(selectable))

    self.print_selections(choices_list, selectable)

    selectable_choices = list(itertools.compress(choices_list, selectable))
    n_valid_selections = len(selectable_choices)
    
    while True:
      prompt_str = '--> {0} [1-{1}] ([q]uit, [s]tart over, [w]izard): '
      response_str = raw_input(prompt_str.format(prompt, n_valid_selections))
      if response_str in ['s', 'start over']: raise StartOverException
      elif response_str in ['q', 'quit']: raise CancelDialogException
      elif response_str in ['w', 'wizard']:
        print ' !!! Current stack state: !!! '
        def anon(x): print str(x)
        map(anon, self.game_state.stack.stack[::-1])
        print ' !!!                      !!! '


      try:
        response_int = int(response_str)
      except:
        lg.info('your response was {0!s}... try again'.format(response_str))
        continue
      if response_int <= n_valid_selections and response_int > 0:
        # return the index in the choices_list, 0 indexed
        index = choices_list.index(selectable_choices[response_int-1])
        return index
      else:
        lg.info('Invalid selection ({0}). Please enter a number between '
                '1 and {1}'.format(response_int, n_valid_selections))


  def ThinkerTypeDialog(self, player):
    """ Returns 'Jack' or 'Cards' for which type of thinker to
    perform.
    """
    lg.info('Thinker:')
    lg.info('[1] Jack')
    n_possible_cards = self.get_max_hand_size(player) - len(player.hand)
    if n_possible_cards < 1: n_possible_cards = 1
    lg.info('[2] Fill up from library ({0} cards)'.format(n_possible_cards))
    while True:
      response_str = raw_input('--> Your choice ([q]uit, [s]tart over): ')
      if response_str in ['s', 'start over']: continue
      elif response_str in ['q', 'quit']: return ('','','')
      try:
        response_int = int(response_str)
        if response_int == 1:
          return 'Jack'
        elif response_int == 2:
          return 'Cards'
        else:
          lg.info('your response was {0!s}... try again'.format(response_str))
          continue
        lg.info(player.describe_hand_private())
        save_game_state(game_state)
        break
      except:
        lg.info('your response was {0!s}... try again'.format(response_str))

  def UseSewerDialog(self, player):
    done=False
    cards_to_move=[]
    choices=['All', 'None']
    choices.extend([gtrutils.get_detailed_card_summary(card) 
                    for card in player.camp if card is not 'Jack'])
    while not done:
      lg.info('Do you wish to use your Sewer?')

      card_index = self.choices_dialog(choices, 'Select a card to take into your stockpile')
      if card_index == 0:
        cards_to_move.extend(choices[2:])
      elif card_index > 1:
        cards_to_move.append(choices.pop(card_index))
      else:
        done=True
    
    return cards_to_move

  def UseSenateDialog(self, senate_player, jack_player):
    lg.info('Do you wish to use your Senate?')
    choices=['Yes','No']
    index = self.choices_dialog(choices, 'Select one')
    return index == 0

  def LaborerDialog(self, player, has_dock):
    """ Prompts for which card to get from the pool and hand for a Laborer
    action.
    """
    card_from_pool, card_from_hand = (None,None)

    sorted_pool = sorted(self.game_state.pool)
    if len(sorted_pool) > 0:
      lg.info('Performing Laborer, choose a card from the pool:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_pool]
      card_choices.insert(0,'Skip this action')

      card_index = self.choices_dialog(card_choices, 'Select a card to take into your stockpile')
      if card_index > 0:
        card_from_pool = sorted_pool[card_index-1]

    sorted_hand = sorted([card for card in player.hand if card != 'Jack'])
    if has_dock and len(sorted_hand) > 0:
      lg.info('Choose a card from your hand:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]
      card_choices.insert(0,'Skip this action')

      card_index = self.choices_dialog(card_choices, 'Select a card to take into your stockpile')
      if card_index > 0:
        card_from_hand = sorted_hand[card_index-1]

    return (card_from_pool, card_from_hand)


  def StairwayDialog(self, player):
    """
    Asks the player if they wish to use the Stairway and returns the 
    building to add to, the material to add, and whether to take from the pool.
    """
    possible_buildings = [(p, b) for p in self.game_state.players
                          for b in p.get_completed_buildings()
                          if p is not player
                          ]
    possible_buildings = sorted(possible_buildings, None, lambda x: x[0].name.lower() + str(x[1]).lower())
    lg.info('Use Stairway?')
    building_names = [p.name + '\'s ' + str(b) for (p,b) in possible_buildings]
    choices = sorted(building_names)
    choices.insert(0, 'Don\'t use Stairway')
    choice_index = self.choices_dialog(choices, 'Select option for Stairway')
    
    building, material, from_pool = None, None, False
    if choice_index != 0:
      other_player, building = possible_buildings[choice_index-1]
      
      has_archway = self.player_has_active_building(player, 'Archway')
      
      sorted_stockpile = sorted(player.stockpile)
      lg.info('Choose a material to add from your stockpile:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_stockpile]

      if has_archway:
        sorted_pool = sorted(self.game_state.pool)
        pool_choices = ['[POOL]' + gtrutils.get_detailed_card_summary(card) for card in sorted_pool]
        card_choices.extend(pool_choices)

      card_index = self.choices_dialog(card_choices, 'Select a material to add')

      if card_index >= len(sorted_stockpile):
        from_pool = True
        material = sorted_pool[card_index - len(sorted_stockpile)]
      else:
        material = sorted_stockpile[card_index]

    return building, material, from_pool

  def ArchitectDialog(self, player, out_of_town_allowed):
    """ Returns (building, material, site, from_pool) to be built.

    If the action is to be skipped, returns None, None, None
    """
    building, material, site, from_pool = None, None, None, False

    lg.info('Performing Architect, choose a building option:')
    card_choices = sorted(player.get_incomplete_building_names())
    card_choices.insert(0, 'Start a new buidling')
    card_choices.insert(0, 'Skip action')

    card_index = self.choices_dialog(card_choices, 'Select a building option')
    if card_index == 1: # Starting a new building
      sorted_hand = sorted(player.hand)
      lg.info('Choose a building to start from your hand:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]

      card_index = self.choices_dialog(card_choices, 'Select a building to start')
      building = sorted_hand[card_index]

      if building == 'Statue':
        sites = card_manager.get_all_materials()
        site_index = choices_dialog(sites)
        site = sites[site_index]
      else:
        site = card_manager.get_material_of_card(building)

    elif card_index > 1: # Adding to a building from stockpile
      building = card_choices[card_index]
      
      has_archway = self.player_has_active_building(player, 'Archway')
      
      sorted_stockpile = sorted(player.stockpile)
      lg.info('Choose a material to add from your stockpile:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_stockpile]

      if has_archway:
        sorted_pool = sorted(self.game_state.pool)
        pool_choices = ['[POOL]' + gtrutils.get_detailed_card_summary(card) for card in sorted_pool]
        card_choices.extend(pool_choices)

      card_index = self.choices_dialog(card_choices, 'Select a material to add')

      if card_index >= len(sorted_stockpile):
        from_pool = True
        material = sorted_pool[card_index - len(sorted_stockpile)]
      else:
        material = sorted_stockpile[card_index]

    return building, material, site, from_pool


  def CraftsmanDialog(self, player, out_of_town_allowed):
    """ Returns (building, material, site) to be built.
    """
    building, material, site = None, None, None

    lg.info('Performing Craftsman, choose a building option:')
    card_choices = player.get_incomplete_building_names()
    card_choices.insert(0, 'Start a new buidling')

    card_index = self.choices_dialog(card_choices, 'Select a building option')
    if card_index == 0: # Starting a new building
      sorted_hand = sorted(player.hand)
      lg.info('Choose a building to start from your hand:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]

      card_index = self.choices_dialog(card_choices, 'Select a building to start')
      building = sorted_hand[card_index]

      if building == 'Statue':
        sites = card_manager.get_all_materials()
        site_index = choices_dialog(sites)
        site = sites[site_index]
      else:
        site = card_manager.get_material_of_card(building)

    else: # Adding to a building from hand
      building = card_choices[card_index]
      
      sorted_hand = sorted(player.hand)
      lg.info('Choose a material to add from your hand:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]

      card_index = self.choices_dialog(card_choices, 'Select a material to add')
      material = sorted_hand[card_index]

    return building, material, site

  def MerchantDialog(self, player, has_atrium, has_basilica, card_limit):
    """ Prompts for which card to get from the pool and hand for a Laborer
    action.

    There are flags for the player having an Basilica or Atrium. These
    cause the dialog to prompt for card from the hand or replace the 
    normal merchant action with a draw from the deck.

    There is a parameter that specifies the card limit for the vault. This
    is the number of slots left in the vault.
    """
    card_from_stockpile, card_from_hand, card_from_deck  = (None,None,False)

    sorted_stockpile = sorted(player.stockpile)
    if len(sorted_stockpile) > 0 or has_atrium:
      lg.info('Performing Merchant, choose a card from stockpile (Vault {}/{})'.format(
        str(len(player.vault)),str(len(player.vault)+card_limit)))
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_stockpile]
      card_choices.insert(0,'Skip this action')
      card_choices.insert(1,'Take card from top of deck')

      card_index = self.choices_dialog(card_choices, 'Select a card to take into your vault')
      if card_index == 1:
        card_from_deck = True
        card_limit -= 1 
      elif card_index > 1:
        card_from_stockpile = sorted_stockpile[card_index-2]
        card_limit -= 1

    sorted_hand = sorted([card for card in player.hand if card != 'Jack'])
    if card_limit>0 and has_basilica and len(sorted_hand)>0:
      lg.info('Choose a card from your hand:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]
      card_choices.insert(0,'Skip this action')

      card_index = self.choices_dialog(card_choices, 'Select a card to take into your vault')
      if card_index > 0:
        card_from_hand = sorted_hand[card_index-1]

    return (card_from_stockpile, card_from_hand, card_from_deck)

  def SelectRoleDialog(self, player, role=None, unselectable=None,
                       other_options=None):
    """ Selects a card or cards to be used as a role for leading or following
    from the player's hand.

    The <role> parameter specifies a role that has been pre-selected - for 
    instance if this is interacting with a player following a role.

    The <unselectable> parameter is a list of cards that cannot be
    selected. These are matched against the corresponding card in player.hand.
    If the parameter is None or unspecified, the whole hand is selectable.

    The <other_options> parameter adds additional selection options at the end
    of the list. For instance, 'Thinker' or 'End selections'. These options will
    be returned verbatim in the list of cards selected.

    Allows selection of a Jack, but doesn't determine which role it represents.
    Allows petition if enough cards of the same role are available.
    Returns a list of cards selected.
    
    The caller must then determine the role intended. For a single Orders card,
    this is easy, but for a petition (length(response) > 1) or Jack, an
    additional dialog is required.
    """
    sorted_cards = sorted(player.hand, card_manager.cmp_jacks_first)
    cards_used = list(unselectable) if unselectable else [] # make a copy
    selectable = [] # list of booleans to filter with choices_dialog()
    for card in sorted_cards:
      if card in cards_used:
        selectable.append(False)
        cards_used.remove(card)
      elif card == 'Jack':
        selectable.append(True)
      elif role is not None and card_manager.get_role_of_card(card) != role:
        selectable.append(False)
      else:
        selectable.append(True)

    card_choices = [gtrutils.get_detailed_card_summary(card)\
                    for card in sorted_cards]

    petition_count = 2 if self.player_has_active_building(player, 'Circus') else 3
    hand_cpy = list(player.hand)
    if unselectable is not None:
      for card in unselectable:
        if card in hand_cpy:
          hand_cpy.remove(card)
    non_jack_hand = filter(lambda x:x!='Jack', hand_cpy)
    hand_roles = map(card_manager.get_role_of_card, non_jack_hand)
    role_counts = collections.Counter(hand_roles)
    possible_petitions = [role for (role,count) in role_counts.items()
                          if count>=petition_count]

    # Always have Petition on the list, but don't allow selection if not
    # enough pairs/triplets.
    card_choices.append('Petition')
    if len(possible_petitions) < 1:
      selectable.append(False)

    if other_options:
      card_choices.extend(other_options)

    card_index = self.choices_dialog(card_choices, 'Select a card', selectable)

    if card_index == card_choices.index('Petition'):
      cards_selected = self.PetitionDialog(player, petition_count, unselectable)
    elif card_index > len(sorted_cards):
      cards_selected = [card_choices[card_index]] # This is one of the 'other options'
    else:
      cards_selected = [sorted_cards[card_index]]

    return cards_selected

  def LeadRoleDialog(self, game_state, player):
    """ Players can only lead from their hands to their camp. 
    Returns a list of [<role>, <n_actions>, <card1>, <card2>, ...] where <role> is
    the role being led and the remainder of the list
    are the card or cards used to lead.
    The item <n_actions> is usually 1, but could be larger for players
    with a Palace.
    This is usually only one card, but petitioning allows the player
    to use 3 cards as a jack.
    Raises a StartOverException if the user enters the Start Over option
    or if the user attempts an illegal action (petition without the needed
    multiple of a single role).
    """
    has_palace = self.player_has_active_building(player, 'Palace') 

    role_led, n_actions, cards_led = None, 0, []

    lg.info('Lead a role. Choose the card:')
    cards_selected = self.SelectRoleDialog(player)

    if(len(cards_selected) > 1 or cards_selected[0] == 'Jack'):
      role_index = self.choices_dialog(
        card_manager.get_all_roles(), 'Select a role for Jack (or Petition)')
      role_led = card_manager.get_all_roles()[role_index]
    else:
      role_led = card_manager.get_role_of_card(cards_selected[0])

    # Now that a role has been selected, use the Palace to add more actions
    n_actions = 1
    if has_palace:
      while True:
        lg.info('Using Palace to perform additional actions. # Actions = ' + str(n_actions))
        lg.info('     using cards: {1!s}'.format(n_actions, cards_selected))
        unselectable = list(cards_selected)
        
        quit_opt = 'Skip further Palace actions'
        cards = self.SelectRoleDialog(player, role_led, unselectable,
                                      other_options=[quit_opt])
        if cards[0] == quit_opt:
          break
        n_actions += 1
        cards_selected += cards

    return [role_led, n_actions] + cards_selected

  def PetitionDialog(self, player, petition_count, unselectable = None):
    """
    Returns a list of cards used to petition.

    Palace has been incorporated elsewhere. The _RoleDialog methods need to 
    return [role, n_actions, cards...]
    """
    non_jack_hand = filter(lambda x:x!='Jack', player.hand)
    hand_roles = map(card_manager.get_role_of_card, non_jack_hand)
    role_counts = collections.Counter(hand_roles)
    possible_petitions = [role for (role,count) in role_counts.items()
                          if count>=petition_count]

    if len(possible_petitions) < 1:
      lg.info('Petitioning requires {0} cards of the same role'.format(petition_count))
      raise StartOverException

    def get_allowed_cards(cards, petition_role, cards_used=[], unselectable = None):
      selectable = []
      cards_used_cpy = list(cards_used)
      unselectable_cpy = [] if unselectable is None else list(unselectable)
      if len(cards_used)>0:
        card_manager.get_role_of_card(cards_used[0])
      for card in cards:
        if card == 'Jack':
          selectable.append(False)
        elif card in unselectable_cpy:
          selectable.append(False)
          unselectable_cpy.remove(card)
        elif card in cards_used_cpy:
          selectable.append(False)
          cards_used_cpy.remove(card)
        else:
          role = card_manager.get_role_of_card(card)
          if petition_role is not None and petition_role != role:
            selectable.append(False)
          elif role_counts[role] < petition_count:
            selectable.append(False)
          else:
            selectable.append(True)

      return selectable

    cards_to_petition = []
    petition_cards = list(player.hand)
    the_petition_role = None

    # Get first petition card, then filter out the roles that don't match
    for i in range(0, petition_count):
      selectable = get_allowed_cards(petition_cards, the_petition_role, cards_to_petition, unselectable)
      card_index = self.choices_dialog(petition_cards, 
        "Select {0:d} cards to use for petition".format(petition_count - len(cards_to_petition)),
        selectable)
      cards_to_petition.append(petition_cards[card_index])

      if len(cards_to_petition) == 1:
        the_petition_role = card_manager.get_role_of_card(cards_to_petition[0])

    return cards_to_petition

  def FollowRoleDialog(self, player, role_led):
    """ Players can only lead or follow from their hands to their camp. 
    Returns a list of [<n_actions>, <card1>, <card2>, ...] where these
    are the card or cards used to follow.
    This is usually only one card, but petitioning allows the player
    to use 3 cards as a jack.
    The first list element, <n_actions> is usually 1, but a Palace allows
    following for multiple actions.
    Raises a StartOverException if the user enters the Start Over option
    or if the user attempts an illegal action (petition without the needed
    multiple of a single role).
    """
    has_palace = self.player_has_active_building(player, 'Palace') 

    n_actions, cards_played = 0, []

    lg.info('Follow {}: choose the card:'.format(role_led))
    thinker_opt = 'Thinker'
    cards_selected = self.SelectRoleDialog(player, role_led, None, [thinker_opt])

    if cards_selected[0] == thinker_opt:
      return None

    n_actions = 1
    if has_palace:
      while True:
        lg.info('Using Palace to perform additional actions. # Actions = ' + str(n_actions))
        lg.info('     using cards: {1!s}'.format(n_actions, cards_selected))
        unselectable = list(cards_selected)
        quit_opt = 'Skip further Palace actions'
        cards = self.SelectRoleDialog(player, role_led, unselectable,
                                      other_options=[quit_opt])
        if cards[0] == quit_opt:
          break
        n_actions += 1
        cards_selected += cards

    return [n_actions] + cards_selected

# vim: ts=8:sts=2:sw=2:et
