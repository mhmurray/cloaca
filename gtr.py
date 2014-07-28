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
    if thinker:
      perform_thinker_action(player)
      end_turn()
    else:
      role = self.lead_role_action(player)
      for p in get_other_players():
        self.follow_role_action(p, role)

      perform_role_being_led(player)
      for p in get_following_players():
        self.perform_role_being_led(p)

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
      game_state.discard_all_for_player(thinking_player)
    
    if latrine_card:
      game_state.discard_for_player(latrine_card)

    thinker_type = self.ThinkerTypeDialog()
    if thinker_type == "Jack":
      game_state.draw_one_jack_for_player(thinking_player)
    if thinker_type == "Cards":
      game_state.thinker_fillup_for_player(thinking_player)

  def lead_role_action(self, leading_player):
    """
    1) Ask for cards used to lead
    2) Check legal leads using these cards (Palace, petition)
    3) Ask for role clarification if necessary
    4) Move cards to camp, set this turn's role that was led.
    """
    # This dialog checks that the cards used are legal
    resp = self.LeadOrRoleDialog(leading_player)
    role = resp[0]
    cards = resp[1:]
    self.game_state.role_led = role
    for c in cards:
      leading_player.camp.append(leading_player.get_card_from_hand(c))

  def follow_role_action(self, following_player, role):
    """
    1) Ask for cards used to follow
    2) Check for ambiguity in ways to follow (Crane, Palace, petition)
    3) Ask for clarification if necessary
    4) Move cards to camp
    """
    cards = self.FollowRoleDialog(following_player, role)
    for c in cards:
      following_player.camp.append(leading_player.get_card_from_hand(c))

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
    pass

  def perform_clientele_action(self, player, role, out_of_town_allowed):
    """
    This function will activate one client. It makes two actions 
    if the player has a Circus Maximus. This function doesn't keep track
    of which clients have been used.
    1) -->ACTION(perform_<role>_action), forwarding out_of_town_allowed to architect/craftsman
    1) If the player has a Circus Maximus, do it again
    """
    pass


  def perform_laborer_action(self, player):
    """
    1) Ask for which card from the pool
    2) Move card from pool
    3) Check for Dock and ask for card from hand
    4) Move card from hand
    """
    pass

  def peform_patron_action(self, player):
    """
    1) Abort if clientele full (Insula, Aqueduct)
    2) Ask for which card from pool
    3) Check for Bar and Aqueduct and 
    """
    pass

  def peform_craftsman_action(self, player, out_of_town_allowed):
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

  def peform_legionary_action(self, player, affected_players):
    """
    affected_players must be determined by the caller, accounting for Pallisade, Wall, Bridge
    1) Ask for card to show for demand
    2) Ask for affected players to give card of material, or say "Glory to Rome!"
    3) If player has coliseum, ask for affected players to select client to send to the lions.
    4) If player has bridge, ask affected players for material from stockpile
    """
    pass

  def peform_architect_action(self, player, out_of_town_allowed):
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

  def peform_merchant_action(self, player):
    """
    Do we log materials? We should in case the display messes up,
    but maybe only until end of turn.
    1) Abort if vault full. Also between each step here. (Market)
    2) Ask player to select material from Stockpile. Reveal and place in vault.
    3) If Basilica, ask player to select from hand. No reveal and vault.
    4) If Atrium, ask player to select top of deck. No reveal and vault.
    """
    pass

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

  def choices_dialog(self, choices_list, 
                     prompt = 'Please make a selection'):
    """ Returns the index in the choices_list selected by the user or
    raises a StartOverException or a CancelDialogExeption. """

    print_selections(choices_list)
    
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


  def ThinkerTypeDialog(game_state, player):
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


  def LeadRoleDialog(game_state, player):
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

  def FollowRoleDialog(game_state, player, role_led):
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
    logging.info('Follow {}: choose the card:'.format(role))
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
