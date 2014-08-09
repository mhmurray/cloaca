#!/usr/bin/env python

""" Glory to Rome sim.

"""

from player import Player
from gtrutils import get_card_from_zone
from gamestate import GameState
import gtrutils
import card_manager 

import collections
import logging
import pickle

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
    logger = logging.getLogger()
    logger.addFilter(gtrutils.RoleColorFilter())
    logger.addFilter(gtrutils.MaterialColorFilter())

  def __repr__(self):
    rep=('Game(game_state={game_state!r})')
    return rep.format(game_state = self.game_state)

  def init_common_piles(self, n_players):
    logging.info('--> Initializing the game')

    self.init_library()
    first_player_index = self.init_pool(n_players)
    print 'Player {} goes first'.format(
        self.game_state.players[first_player_index].name)
    self.game_state.leader_index = first_player_index
    self.game_state.priority_index = first_player_index
    self.game_state.jack_pile.extend(['Jack'] * Game.initial_jack_count)
    self.init_foundations(n_players)
  
  def init_pool(self, n_players):
    """ Returns the index of the player that goes first. Fills the pool
    with one card per player, alphabetically first goes first. Resolves
    ties with more cards.
    """
    logging.info('--> Initializing the pool')
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
    logging.info('--> Initializing the foundations')
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
        
    logging.info('--> Initializing the library ({0} cards)'.format(
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
    logging.info(pool_string)
    
    # print exchange area. 
    try: 
      if self.game_state.exchange_area:
        exchange_string = 'Exchange area: \n'
        exchange_string += gtrutils.get_detailed_zone_summary(
          self.game_state.exchange_area)
        logging.info(exchange_string)
    except AttributeError: # backwards-compatibility for old games
      self.game_state.exchange_area = []
      
    # print N cards in library
    print 'Library : {0:d} cards'.format(len(self.game_state.library))

    # print N jacks
    print 'Jacks : {0:d} cards'.format(len(self.game_state.jack_pile))

    # print Foundations
    logging.info('Foundation materials:')
    foundation_string = '  In town: ' + gtrutils.get_short_zone_summary(
      self.game_state.in_town_foundations, 3)
    logging.info(foundation_string)
    foundation_string = '  Out of town: ' + gtrutils.get_short_zone_summary(
      self.game_state.out_of_town_foundations, 3)
    logging.info(foundation_string)

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
    logging.info('--> Player {0} public state:'.format(player.name))

    # hand
    logging.info(player.describe_hand_public())
    
    # Vault
    if len(player.vault) > 0:
      logging.info(player.describe_vault_public())

    # influence
    if player.influence:
      logging.info(player.describe_influence())

    # clientele
    if len(player.clientele) > 0:
      logging.info(player.describe_clientele())

    # Stockpile
    if len(player.stockpile) > 0:
      logging.info(player.describe_stockpile())

    # Buildings
    if len(player.buildings) > 0:
      # be sure there is at least one non-empty site
      for building in player.buildings:
          if building:
              logging.info(player.describe_buildings())
              break


    # Camp
    if len(player.camp) > 0:
      logging.info(player.describe_camp())

    # Revealed cards
    try:
      if len(player.revealed) > 0:
        logging.info(player.describe_revealed())
    except AttributeError:
      player.revealed = []


  def print_complete_player_state(self, player):
    """ Prints a player's information, public or not.

    This is the following: Card in camp (if existing), clientele, influence,
    cards in vault, stockpile, cards in hand,
    buildings built, buildings under construction and stage of completion.
    """
    # print name
    logging.info('--> Player {0} complete state:'.format(player.name))

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
      # be sure there is at least one non-empty site
      for building in player.buildings:
          if building:
              print player.describe_buildings()
              break

  def take_turn(self, player):
    """
    1) Ask for thinker or lead
    2) -->ACTION(thinker), -->ACTION(lead_role)
    """
    lead_role = self.ThinkerOrLeadDialog(player)
    if lead_role:
      role = self.lead_role_action(player)
      for p in self.game_state.get_following_players_in_order():
        self.follow_role_action(p, role)

      self.perform_role_being_led(player,)
      for p in self.game_state.get_following_players_in_order():
        self.perform_role_being_led(p)
    else:
      self.perform_thinker_action(player)
      self.end_turn(player)

  def ThinkerOrLeadDialog(self, player):
    """ Asks whether the player wants to think or lead at the start of their
    turn.
    """
    logging.info('Start of {}\'s turn: Thinker or Lead?'.format(player.name))

    choices = ['Thinker', 'Lead']
    index = self.choices_dialog(choices, 'Select one.')
    return index==1

  def post_game_state(self):
      save_game_state(self)

  def perform_thinker_action(self, thinking_player):
    """
    1) If thinking_player has a Latrine, ask for discard.
    2) If thinking_player has a Vomitorium, ask for discard.
    3) Determine # cards that would be drawn. Check hand size,
       Temple, and Shrine. Also check if jacks are empty,
       and if drawing cards would end the game.
    3) Ask thinking_player for thinker type (jack or # cards)
    4) Draw cards for player.
    """
    # still doesn't check for stairway-activated buildings
    if "Latrine" in thinking_player.get_active_buildings():
      latrine_card = client.UseLatrineDialog(thinking_player)
    else: latrine_card = None

    if "Vomitorium" in thinking_player.get_active_buildings():
      should_discard = client.UseVomitoriumDialog(thinking_player)
    else: should_discard_all = False

    if should_discard_all:
      self.game_state.discard_all_for_player(thinking_player)
    
    if latrine_card:
      self.game_state.discard_for_player(latrine_card)

    thinker_type = self.ThinkerTypeDialog(thinking_player)
    if thinker_type == "Jack":
      self.game_state.draw_one_jack_for_player(thinking_player)
    if thinker_type == "Cards":
      self.game_state.thinker_fillup_for_player(thinking_player)

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
    cards = resp[1:]
    self.game_state.role_led = role
    for c in cards:
      leading_player.camp.append(leading_player.get_card_from_hand(c))
    return role

  def follow_role_action(self, following_player, role):
    """
    1) Ask for cards used to follow
    2) Check for ambiguity in ways to follow (Crane, Palace, petition)
    3) Ask for clarification if necessary
    4) Move cards to camp
    """
    cards = self.FollowRoleDialog(following_player, role)
    for c in cards:
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
    # Skip the whole palace thing.
    
    # The clients are simple for Laborer, Merchant, and Legionary.
    # We can calculate how many actions you get before doing any of them.
    # Before all of them do the role that was led or followed
    role = self.game_state.role_led
    logging.info('Player {} is performing {}'.format(player.name, role))
    if role in ['Laborer', 'Merchant', 'Legionary']:
      has_cm = 'Circus Maximus' in player.get_active_buildings()

      n_actions = player.get_n_clients(role)

      if player.is_following_or_leading():
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
    #
    
    if role == 'Patron':
      n_patron = player.get_n_client_cards_of_role('Patron')
      n_merchant = player.get_n_client_cards_of_role('Merchant')

      if player.is_following_or_leading():
        self.perform_patron_action(player)
      
      patrons_used=0
      merchants_used=0

      while patrons_used < n_patron:
        self.perform_clientele_action(player, 'Patron')
        patrons_used += 1

      # Now if the player has build a Ludus Magna somehow, use the Merchants
      if 'Ludus Magna' in player.get_active_buildings():
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
    # The same logic applies for architects, so we can combine the two.
    
    if role in ['Craftsman', 'Architect']:
      n_clients = player.get_n_client_cards_of_role(role)
      n_merchant = player.get_n_client_cards_of_role('Merchant')

      has_lm = 'Ludus Magna' in player.get_active_buildings()
      
      used_oot = False
      if player.is_following_or_leading():
        can_oot = n_clients > 0 or (has_lm and n_merchant > 0)
        used_oot = self.perform_role_action(player, role, can_oot)

      clients_used = 0
      merchants_used = 0

      def check_merchants():
        has_lm = 'Ludus Magna' in player.get_active_buildings()
        has_merchant = (n_merchants-merchants_used > 0)
        return has_lm and has_merchant

      while clients_used < n_clients:
        can_oot = (n_clients - clients_used) > 1 or check_merchants()
        used_oot = self.perform_clientele_action(player, role, can_oot, used_oot)

        clients_used += 1

      while check_merchants():
        can_oot = (n_merchants - merchants_used) > 1
        used_oot = self.perform_clientele_action(player, role, can_oot, used_oot)

        merchants_used += 1

    #ugh! done. Probably should test this one.


  def perform_clientele_action(self, player, role, out_of_town_allowed=False, out_of_town_used=False):
    """
    This function will activate one client. It makes two actions 
    if the player has a Circus Maximus. This function doesn't keep track
    of which clients have been used.
    1) -->ACTION(perform_<role>_action), forwarding out_of_town_allowed to architect/craftsman
    2) If the player has a Circus Maximus, do it again

    If out_of_town_allowed is True, there's another action after this one, so out_of_town_allowed
    is true for the last action we do here.

    Returns True if the last action was used to start an out-of-town site.
    """
    used_oot = out_of_town_used
    if 'Circus Maximus' in player.get_active_buildings():
      if used_oot: used_oot = False
      else:
        used_oot = self.perform_role_action(player, role, out_of_town_allowed)

    if used_oot: used_oot = False
    else:
      used_oot = self.perform_clientele_action(player, role, out_of_town_allowed)

    return used_oot

  def perform_role_action(self, player, role, out_of_town_allowed):
    """ Multiplexer function for arbitrary roles. 
    Calls perform_<role>_action(), etc.

    It returns the value the role action returns. If this is a Craftsman
    or an Architect, it's whether or not the action was ued to start an
    out of town site. Otherwise it's None.
    """
    if role=='Patron':
      self.perform_patron_action(player)
      return False
    elif role=='Laborer':
      self.perform_laborer_action(player)
      return False
    elif role=='Architect':
      return self.perform_architect_action(player)
    elif role=='Craftsman':
      return self.perform_craftsman_action(player)
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
    has_dock = 'Dock' in player.get_active_buildings()
    
    card_from_pool, card_from_hand = self.LaborerDialog(player, has_dock)

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
    pass

  def perform_craftsman_action(self, player, out_of_town_allowed):
    """
    out_of_town_allowed is indicated by the caller if this craftsman would
    be stacked up with another, so that an out-of-town site may be used.
    In that case, this will return an indication and the caller can nix the
    next craftsman action.
    1) Ask for building to start or material to add.
    2) If out_of_town_allowed is false, don't allow out of town, otherwise
       start the out-of-town site and return the indicator.
    3) Check legality of material, building + site.
    4) Place material or building -->ACTION(place_material) -->ACTION(start_building)
    5) Mark flag for "performed craftsman this turn" for Academy
    """
    pass

  def perform_legionary_action(self, player, affected_players):
    """
    affected_players must be determined by the caller, accounting for Pallisade, Wall, Bridge
    1) Ask for card to show for demand
    2) Ask for affected players to give card of material, or say "Glory to Rome!"
    3) If player has coliseum, ask for affected players to select client to send to the lions.
    4) If player has bridge, ask affected players for material from stockpile
    """
    pass

  def perform_architect_action(self, player, out_of_town_allowed):
    """
    out_of_town_allowed is indicated by the caller if this architect would
    be stacked up with another, so that an out-of-town site may be used.
    In that case, this will return an indication and the caller can nix the
    next architect action.
    1) Ask for building to start or material to add. (Archway, Stairway)
    2) If out_of_town_allowed is false, don't allow out of town, otherwise
       start the out-of-town site and return the indicator.
    3) Check legality of material, building + site.
    4) Place material or building -->ACTION(place_material) -->ACTION(start_building)
    """
    pass

  def perform_merchant_action(self, player):
    """
    Do we log materials? We should in case the display messes up,
    but maybe only until end of turn.
    1) Abort if vault full. Also between each step here. (Market)
    2) Ask player to select material from Stockpile. Reveal and place in vault.
    3) If Basilica, ask player to select from hand. No reveal and vault.
    4) If Atrium, ask player to select top of deck. No reveal and vault.
    """
    vault_limit = player.get_influence()
    if 'Market' in player.get_active_buildings(): card_limit += 2

    card_limit = vault_limit - len(player.vault)

    has_atrium = 'Atrium' in player.get_active_buildings()
    has_basilica = 'Basilica' in player.get_active_buildings()

    merchant_allowed = (card_limit>0) \
      and (has_atrium or len(player.stockpile)>0 or (has_basilica and len(player.hand)>0))

    if merchant_allowed:
      # card_from_deck is a boolean. The others are actual card names.
      card_from_stockpile, card_from_hand, card_from_deck = \
        self.MerchantDialog(self.game_state, player, has_atrium, has_basilica, card_limit)

      if card_from_stockpile:
        gtrutils.add_card_to_zone(
          gtrutils.get_card_from_zone(card_from_stockpile, player.stockpile), player.vault)
      if card_from_hand:
        gtrutils.add_card_to_zone(
          gtrutils.get_card_from_zone(card_from_hand, player.hand), player.vault)
      if card_from_deck:
        gtrutils.add_card_to_zone(self.game_state.draw_cards(1), player.vault)

  def kids_in_pool(self, player, players_with_senate):
    """
    Place cards in camp into the pool.
    1) If Sewer, ask to move cards into stockpile.
    2) If dropping a Jack, ask players_with_senate in order.
    """
    pass

  def end_turn(self, player):
    """
    Ask for Academy thinker. Need to figure out whether or not Senate goes first.
    1) Find players_with_senate
    2) --> kids_in_pool(player, players_with_senate)
    """
    pass

  def add_material_to_building(self, player, material, source, building):
    """
    Adds a material to a building and checks if the building is complete
    The caller should make sure it's legal.
    1) Add material to building, indicate Stairway separately.
    2) If building is completed, trigger resolve_<building> action
    """
    pass

  def resolve_building(self, player, building):
    """ Placeholder for all building resolutions
    """
    pass

  def save_game_state(self, log_file_prefix='log_state'):
    """
    Save game state to file
    """
    # get the current time, in seconds 
    time_stamp = time.time()
    self.game_state.time_stamp = time_stamp
    file_name = '{0}_{1}.log'.format(log_file_prefix, time_stamp)
    log_file = file(file_name, 'w')
    pickle.dump(game_state, log_file)
    log_file.close()

  def get_previous_game_state(self, log_file_prefix='log_state'):
    """
    Return saved game state from file
    """
    log_files = glob.glob('{0}*.log'.format(log_file_prefix))
    log_files.sort()
    #for log_file in log_files: # print all log file names, for debugging
    #  logging.debug(log_file)

    if not log_files:
      return None

    log_file_name = log_files[-1] # last element
    time_stamp = log_file_name.split('_')[-1].split('.')[0:1]
    time_stamp = '.'.join(time_stamp)
    asc_time = time.asctime(time.localtime(float(time_stamp)))
    #logging.debug('Retrieving game state from {0}'.format(asc_time))

    log_file = file(log_file_name, 'r')
    game_state = pickle.load(log_file)
    log_file.close()
    self.game_state = game_state
    return game_state

  def print_selections(self, choices_list):
    for i, choice in enumerate(choices_list):
      logging.info('  [{0}] {1}'.format(i+1, choice))

  def choices_dialog(self, choices_list, 
                     prompt = 'Please make a selection'):
    """ Returns the index in the choices_list selected by the user or
    raises a StartOverException or a CancelDialogExeption. """

    self.print_selections(choices_list)
    
    while True:
      prompt_str = '--> {0} [1-{1}] ([q]uit, [s]tart over): '
      response_str = raw_input(prompt_str.format(prompt, len(choices_list)))
      if response_str in ['s', 'start over']: raise StartOverException
      elif response_str in ['q', 'quit']: raise CancelDialogException
      try:
        response_int = int(response_str)
      except:
        logging.info('your response was {0!s}... try again'.format(response_str))
        continue
      if response_int <= len(choices_list) and response_int > 0:
        # return the 0-indexed choice
        return response_int-1
      else:
        logging.info('Invalid selection ({0}). Please enter a number between 1 and {1}'.format(response_int, len(choices_list)))


  def ThinkerTypeDialog(self, player):
    """ Returns 'Jack' or 'Cards' for which type of thinker to
    perform.
    """
    logging.info('Thinker:')
    logging.info('[1] Jack')
    n_possible_cards = player.get_n_possible_thinker_cards()
    logging.info('[2] Fill up from library ({0} cards)'.format(n_possible_cards))
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
          logging.info('your response was {0!s}... try again'.format(response_str))
          continue
        logging.info(player.describe_hand_private())
        save_game_state(game_state)
        break
      except:
        logging.info('your response was {0!s}... try again'.format(response_str))

  def LaborerDialog(self, player, has_dock):
    """ Prompts for which card to get from the pool and hand for a Laborer
    action.
    """
    card_from_pool, card_from_hand = (None,None)

    sorted_pool = sorted(self.game_state.pool)
    if len(sorted_pool) > 0:
      logging.info('Performing Laborer, choose a card from the pool:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_pool]
      card_choices.insert(0,'Skip this action')

      card_index = self.choices_dialog(card_choices, 'Select a card to take into your stockpile')
      if card_index > 0:
        card_from_pool = sorted_pool[card_index-1]

    sorted_hand = sorted([card for card in player.hand if card != 'Jack'])
    if has_dock and len(sorted_hand) > 0:
      logging.info('Choose a card from your hand:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]
      card_choices.insert(0,'Skip this action')

      card_index = self.choices_dialog(card_choices, 'Select a card to take into your stockpile')
      if card_index > 0:
        card_from_hand = sorted_hand[card_index-1]

    return (card_from_pool, card_from_hand)

  def MerchantDialog(game_state, player, has_atrium, has_basilica, card_limit):
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
      logging.info('Performing Merchant, choose a card from stockpile (Vault {}/{})'.format(
        str(len(player.vault)-card_limit),str(len(player.vault))))
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
      logging.info('Choose a card from your hand:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]
      card_choices.insert(0,'Skip this action')

      card_index = self.choices_dialog(card_choices, 'Select a card to take into your vault')
      if card_index > 0:
        card_from_hand = sorted_hand[card_index-1]

    return (card_from_stockpile, card_from_hand, card_from_deck)

  def LeadRoleDialog(self, game_state, player):
    """ Players can only lead from their hands to their camp. 
    Returns a list of [<role>, <card1>, <card2>, ...] where <role> is
    the role being led and the remainder of the list
    are the card or cards used to lead.
    This is usually only one card, but petitioning allows the player
    to use 3 cards as a jack.
    Raises a StartOverException if the user enters the Start Over option
    or if the user attempts an illegal action (petition without the needed
    multiple of a single role).
    """
    # Choose the role card
    logging.info('Lead or Follow a role: choose the card:')
    hand = player.hand
    sorted_hand = sorted(hand)
    card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]
    card_choices.append('Petition')

    card_index = self.choices_dialog(card_choices, 'Select a card to lead/follow')

    role_index = -1
    # If it's a jack, figure out what role it needs to be
    if card_choices[card_index] == 'Jack':
      role_index = self.choices_dialog(
        card_manager.get_all_roles(), 'Select a role for the Jack')
      return [card_manager.get_all_roles()[role_index], 'Jack']

    elif card_index == card_choices.index('Petition'):
      # check if petition is possible
      petition_count = 2 if 'Circus' in player.get_active_buildings() else 3
      non_jack_hand = filter(lambda x:x!='Jack', hand)
      hand_roles = map(card_manager.get_role_of_card, non_jack_hand)
      role_counts = collections.Counter(hand_roles)
      possible_petitions = [role for (role,count) in role_counts.items()
                            if count>=petition_count]

      if len(possible_petitions) < 1:
        logging.info('Petitioning requires {0} cards of the same role'.format(petition_count))
        raise StartOverException

      # Petition can be used for any role
      role_index = self.choices_dialog(
        card_manager.get_all_roles(), 'Select a role to petition')
      petition_role = card_manager.get_all_roles()[role_index]

      # Determine which cards will be used to petition
      cards_to_petition = []
      petition_cards = filter(
        lambda x : role_counts[card_manager.get_role_of_card(x)] >= petition_count, non_jack_hand)
      # Get first petition card, then filter out the roles that don't match
      for i in range(0, petition_count):
        card_index = self.choices_dialog(petition_cards, 
          "Select {0:d} cards to use for petition".format(petition_count - len(cards_to_petition)))
        cards_to_petition.append(petition_cards.pop(card_index))

        if len(cards_to_petition) == 1:
          def roles_match_petition(card): 
            return card_manager.get_role_of_card(card) == \
                      card_manager.get_role_of_card(cards_to_petition[0])
          
          petition_cards = filter(roles_match_petition, petition_cards)

      ret_value = [petition_role]
      ret_value.extend(cards_to_petition)
      return ret_value

    else:
      card = sorted_hand[card_index]
      return [card_manager.get_role_of_card(card), card]

  def FollowRoleDialog(self, player, role_led):
    """ Players can only lead or follow from their hands to their camp. 
    Returns a list of [<card1>, <card2>, ...] where these
    are the card or cards used to follow.
    This is usually only one card, but petitioning allows the player
    to use 3 cards as a jack.
    Raises a StartOverException if the user enters the Start Over option
    or if the user attempts an illegal action (petition without the needed
    multiple of a single role).
    """
    # Choose the role card
    logging.info('Follow {}: choose the card:'.format(role_led))
    hand = player.hand
    sorted_hand = sorted(hand)
    card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]
    card_choices.append('Petition')

    card_index = self.choices_dialog(card_choices, 'Select a card to follow with')

    if card_choices[card_index] == 'Jack':
      return ['Jack']

    elif card_index == card_choices.index('Petition'):
      # check if petition is possible
      petition_count = 2 if 'Circus' in player.get_active_buildings() else 3
      non_jack_hand = filter(lambda x:x!='Jack', hand)
      hand_roles = map(card_manager.get_role_of_card, non_jack_hand)
      role_counts = collections.Counter(hand_roles)
      possible_petitions = [role for (role,count) in role_counts.items()
                            if count>=petition_count]

      if len(possible_petitions) < 1:
        logging.info('Petitioning requires {0} cards of the same role'.format(petition_count))
        raise StartOverException

      # Determine which cards will be used to petition
      cards_to_petition = []
      petition_cards = filter(
        lambda x : role_counts[card_manager.get_role_of_card(x)] >= petition_count, non_jack_hand)
      # Get first petition card, then filter out the roles that don't match
      for i in range(0, petition_count):
        card_index = self.choices_dialog(petition_cards, 
          "Select {0:d} cards to use for petition".format(petition_count - len(cards_to_petition)))
        cards_to_petition.append(petition_cards.pop(card_index))

        if len(cards_to_petition) == 1:
          def roles_match_petition(card): 
            return card_manager.get_role_of_card(card) == \
                      card_manager.get_role_of_card(cards_to_petition[0])
          
          petition_cards = filter(roles_match_petition, petition_cards)

      return cards_to_petition

    else:
      card = sorted_hand[card_index]
      return [card]

# vim: ts=8:sts=2:sw=2:et
