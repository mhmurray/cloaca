import gtrutils
import card_manager 
import gtr
from building import Building
from gamestate import GameState

import collections
import logging
import pickle
import itertools
import time
import glob

lg = logging.getLogger('gtr')

class StartOverException(Exception):
  pass

class CancelDialogException(Exception):
  pass

class Client(object):
  """ Rather than interact with the player via the command line and stdout,
  this client is broken out with an interface for each of the game decisions
  a player must make.
  
  The client needs a model of the game state to be able
  to create appropriate dialogs/gui. For a simplistic start, this game model
  is a copy of the official Game object, which is really just a copy of the
  GameState object. The final version will update known game information with
  notifications of other players' moves from the server.

  The _Dialog() methods mostly shouldn't have arguments,
  maybe with the exception for building actions (out-of-town).
  """
  
  def __init__(self, name):
    self.game = gtr.Game()
    self.game.game_state = None
    self.name = name

  def get_player(self):
    for p in self.game.game_state.players:
      if p.name == self.name:
        return p

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
        map(anon, self.game.game_state.stack.stack[::-1])
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

  def ThinkerOrLeadDialog(self):
    """ Asks whether the player wants to think or lead at the start of their
    turn.

    Returns True if 'Lead' is chosen, False if 'Thinker'.
    """
    lg.info('Start of {}\'s turn: Thinker or Lead?'.format(self.name))

    choices = ['Thinker', 'Lead']
    index = self.choices_dialog(choices, 'Select one.')
    return index==1

  def UseLatrineDialog(self):
    """ Asks which card, if any, the player wishes to use with the 
    Latrine before thinking.
    """
    lg.info('Choose a card to discard with the Latrine.')

    sorted_hand = sorted(self.get_player().hand)
    card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]
    card_choices.insert(0, 'Skip discard')
    index = self.choices_dialog(card_choices, 'Select a card to discard')

    if index == 0:
      return None
    else:
      return sorted_hand[index-1]

  def UseVomitoriumDialog(self):
    """ Asks if the player wants to discard their hand with the Vomitorium.

    Returns True if player uses the Vomitorium, False otherwise.
    """
    lg.info('Discard hand with Vomitorium?')

    choices = ['Discard all', 'Skip Vomitorium']
    index = self.choices_dialog(choices)

    return index == 0

  def PatronFromPoolDialog(self):
    p = self.get_player()

    card_from_pool = None
    sorted_pool = sorted(self.game.game_state.pool)

    if len(sorted_pool):
      lg.info('Performing Patron, choose a client from pool (Clientele {}/{})'.format(
        str(p.get_n_clients()), str(self.game.get_clientele_limit(p))))
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_pool]
      card_choices.insert(0,'Skip this action')

      card_index = self.choices_dialog(card_choices, 'Select a card to take into your clientele')
      if card_index > 0:
        card_from_pool = sorted_pool[card_index-1]

    return card_from_pool

  def PatronFromDeckDialog(self):
    p = self.get_player()
    lg.info(
      'Performing Patron. Do you wish to take a client from the deck? (Clientele {}/{})'.format(
      str(p.get_n_clients()), str(self.game.get_clientele_limit(p))))
    choices = ['Yes','No']
    return self.choices_dialog(choices) == 0

  def PatronFromHandDialog(self):
    p = self.get_player()

    card_from_hand = None
    sorted_hand = sorted([card for card in p.hand if card != 'Jack'])

    if len(sorted_hand):
      lg.info('Performing Patron, choose a client from hand (Clientele {}/{})'.format(
        str(p.get_n_clients()),str(self.game.get_clientele_limit(p))))
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]
      card_choices.insert(0,'Skip this action')

      card_index = self.choices_dialog(card_choices, 'Select a card to take into your clientele')
      if card_index > 0:
        card_from_hand = sorted_hand[card_index-1]

    return card_from_hand

  def UseFountainDialog(self):
    choices = ['Use Fountain, drawing from deck', 'Don\'t use Fountain, play from hand']
    choice_index = self.choices_dialog(choices, 'Do you wish to use your Fountain?')
    return choice_index == 0

  def FountainDialog(self):
    """ The Fountain allows you to draw a card from the deck, then
    choose whether to use the card with a craftsman action. The player
    is allowed to just keep (draw) the card.
    
    This function returns a tuple (skip, building, material, site),
    with the following elements:
      1) Whether the player skips the action or not (drawing the card)
      2) The building to be started or added to
      3) The material to be added to an incomplete building
      4) The site to start a building on.

    The material will always be the Fountain card or None, and the building might be
    the Fountain card.
    """
    p = self.get_player()

    skip, building, material, site = (False, None, None, None)

    material_of_card = card_manager.get_material_of_card(p.fountain_card)
    
    card_choices = \
      [str(b) for b in p.get_incomplete_buildings()
      if self.game.check_building_add_legal(p, str(b), p.fountain_card)]

    if not p.owns_building(p.fountain_card):
      card_choices.insert(0, 'Start {} buidling'.format(p.fountain_card))

    if len(card_choices) == 0:
      lg.warn('Can\'t use {} with a craftsman action'.format(p.fountain_card))
      return (True, None, None, None)

    lg.info('Performing Craftsman with {}, choose a building option:'
                 .format(p.fountain_card))

    choices = ['Use {} to start or add to a building'.format(p.fountain_card),
               'Don\'t play card, draw and skip action instead.']
    choice_index = self.choices_dialog(choices)

    if choice_index == 1:
      lg.info('Skipping Craftsman action and drawing card')
      return (True, None, None, None)

    card_index = self.choices_dialog(card_choices, 'Select a building option')
    if card_index == 0: # Starting a new building
      building = p.fountain_card

      if building == 'Statue':
        sites = card_manager.get_all_materials()
        site_index = self.choices_dialog(sites)
        site = sites[site_index]
      else:
        site = card_manager.get_material_of_card(building)

    else: # Adding to a building from hand
      building = card_choices[card_index-1]
      material = p.fountain_card

    return False, building, material, site

  def LegionaryDialog(self):
    p = self.get_player()
    lg.info('Card to use for legionary:')
    hand = p.hand
    sorted_hand = sorted(hand)
    card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]

    card_index = self.choices_dialog(card_choices, 
        'Select a card to use to demand material')
    card_from_hand = sorted_hand[card_index]

    lg.info('Using card %s' % gtrutils.get_detailed_card_summary(card_from_hand))
    return card_from_hand
        
  def ThinkerTypeDialog(self):
    """ Returns True if think for Jack, False for think for cards, None to skip.
    """
    lg.info('Thinker for Jack or cards?')
    p = self.get_player()
    n_possible_cards = max(self.game.get_max_hand_size(p) - len(p.hand), 1)
    choices = ['Jack',
               'Fill up from library ({0} cards)'.format(n_possible_cards),
               'Skip thinker']
    index = self.choices_dialog(choices)

    return (True, False, None)[index]

  def UseSewerDialog(self):
    p = self.get_player()
    done=False
    cards_to_move=[]
    choices=['All', 'None']
    choices.extend([gtrutils.get_detailed_card_summary(card) 
                    for card in p.camp if card is not 'Jack'])
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

  def UseSenateDialog(self):
    lg.info('Do you wish to use your Senate?')
    choices=['Yes','No']
    index = self.choices_dialog(choices, 'Select one')
    return index == 0

  def LaborerDialog(self):
    """ Returns (card_from_pool, card_from_hand).
    """
    card_from_pool, card_from_hand = (None,None)

    player = self.get_player()

    has_dock = self.game.player_has_active_building(player, 'Dock')

    sorted_pool = sorted(self.game.game_state.pool)
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

  def StairwayDialog(self):
    """
    Asks the player if they wish to use the Stairway and returns
    
    (player, building, material, from_pool)

    player: the player that owns the building
    building: the name (string) of the building
    material: name of the material card to use
    from_pool: bool to use the Archway to take from the pool
    """
    p = self.get_player()
    possible_buildings = [(pl, b) for pl in self.game.game_state.players
                          for b in pl.get_completed_buildings()
                          if pl is not p
                          ]
    possible_buildings = sorted(possible_buildings, None, lambda x: x[0].name.lower() + str(x[1]).lower())
    lg.info('Use Stairway?')
    building_names = [pl.name + '\'s ' + str(b) for (pl,b) in possible_buildings]
    choices = sorted(building_names)
    choices.insert(0, 'Don\'t use Stairway')
    choice_index = self.choices_dialog(choices, 'Select option for Stairway')
    
    player_name, building_name, material, from_pool = None, None, None, False
    if choice_index != 0:
      player, building = possible_buildings[choice_index-1]
      player_name = player.name
      building_name = building.foundation
      
      has_archway = self.game.player_has_active_building(p, 'Archway')
      
      sorted_stockpile = sorted(p.stockpile)
      lg.info('Choose a material to add from your stockpile:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_stockpile]

      if has_archway:
        sorted_pool = sorted(self.game.game_state.pool)
        pool_choices = ['[POOL]' + gtrutils.get_detailed_card_summary(card) for card in sorted_pool]
        card_choices.extend(pool_choices)

      card_index = self.choices_dialog(card_choices, 'Select a material to add')

      if card_index >= len(sorted_stockpile):
        from_pool = True
        material = sorted_pool[card_index - len(sorted_stockpile)]
      else:
        material = sorted_stockpile[card_index]

    return player_name, building_name, material, from_pool

  def ArchitectDialog(self):
    """ Returns (building, material, site, from_pool) to be built.

    If the action is to be skipped, returns None, None, None
    """
    building, material, site, from_pool = None, None, None, False
    p = self.get_player()

    lg.info('Performing Architect, choose a building option:')
    card_choices = sorted(p.get_incomplete_building_names())
    card_choices.insert(0, 'Start a new buidling')
    card_choices.insert(0, 'Skip action')

    card_index = self.choices_dialog(card_choices, 'Select a building option')
    if card_index == 1: # Starting a new building
      sorted_hand = sorted(p.hand)
      lg.info('Choose a building to start from your hand:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]

      card_index = self.choices_dialog(card_choices, 'Select a building to start')
      building = sorted_hand[card_index]

      if building == 'Statue':
        sites = card_manager.get_all_materials()
        site_index = self.choices_dialog(sites)
        site = sites[site_index]
      else:
        site = card_manager.get_material_of_card(building)

    elif card_index > 1: # Adding to a building from stockpile
      building = card_choices[card_index]
      
      has_archway = self.game.player_has_active_building(p, 'Archway')
      
      sorted_stockpile = sorted(p.stockpile)
      lg.info('Choose a material to add from your stockpile:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_stockpile]

      if has_archway:
        sorted_pool = sorted(self.game.game_state.pool)
        pool_choices = ['[POOL]' + gtrutils.get_detailed_card_summary(card) for card in sorted_pool]
        card_choices.extend(pool_choices)

      card_index = self.choices_dialog(card_choices, 'Select a material to add')

      if card_index >= len(sorted_stockpile):
        from_pool = True
        material = sorted_pool[card_index - len(sorted_stockpile)]
      else:
        material = sorted_stockpile[card_index]

    return building, material, site, from_pool

  def CraftsmanDialog(self):
    """ Returns (building, material, site) to be built.
    """
    p = self.get_player()
    building, material, site = None, None, None

    lg.info('Performing Craftsman, choose a building option:')
    card_choices = p.get_incomplete_building_names()
    card_choices.insert(0, 'Start a new buidling')

    card_index = self.choices_dialog(card_choices, 'Select a building option')
    if card_index == 0: # Starting a new building
      sorted_hand = sorted(p.hand)
      lg.info('Choose a building to start from your hand:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]

      card_index = self.choices_dialog(card_choices, 'Select a building to start')
      building = sorted_hand[card_index]

      if building == 'Statue':
        sites = card_manager.get_all_materials()
        site_index = self.choices_dialog(sites)
        site = sites[site_index]
      else:
        site = card_manager.get_material_of_card(building)

    else: # Adding to a building from hand
      building = card_choices[card_index]
      
      sorted_hand = sorted(p.hand)
      lg.info('Choose a material to add from your hand:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]

      card_index = self.choices_dialog(card_choices, 'Select a material to add')
      material = sorted_hand[card_index]

    return building, material, site

  def MerchantDialog(self):
    """ Prompts for which card to get from the pool and hand for a Laborer
    action.

    There are flags for the player having an Basilica or Atrium. These
    cause the dialog to prompt for card from the hand or replace the 
    normal merchant action with a draw from the deck.

    There is a parameter that specifies the card limit for the vault. This
    is the number of slots left in the vault.
    """
    p = self.get_player()

    vault_limit = p.get_influence_points()

    card_limit = vault_limit - len(p.vault)
    if self.game.player_has_active_building(p, 'Market'): card_limit += 2

    has_atrium = self.game.player_has_active_building(p, 'Atrium')
    has_basilica = self.game.player_has_active_building(p, 'Basilica')

    card_from_stockpile, card_from_hand, card_from_deck  = (None,None,False)

    sorted_stockpile = sorted(player.stockpile)
    if len(sorted_stockpile) > 0 or has_atrium:
      lg.info('Performing Merchant, choose a card from stockpile (Vault {}/{})'.format(
        str(len(p.vault)), str(card_limit)))
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

    sorted_hand = sorted([card for card in p.hand if card != 'Jack'])
    if card_limit>0 and has_basilica and len(sorted_hand)>0:
      lg.info('Choose a card from your hand:')
      card_choices = [gtrutils.get_detailed_card_summary(card) for card in sorted_hand]
      card_choices.insert(0,'Skip this action')

      card_index = self.choices_dialog(card_choices, 'Select a card to take into your vault')
      if card_index > 0:
        card_from_hand = sorted_hand[card_index-1]

    return (card_from_stockpile, card_from_hand, card_from_deck)

  def SelectRoleDialog(self, role=None, unselectable=None,
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
    p = self.get_player()
    sorted_cards = sorted(p.hand, card_manager.cmp_jacks_first)
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

    petition_count = 2 if self.game.player_has_active_building(p, 'Circus') else 3
    hand_cpy = list(p.hand)
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
      cards_selected = self.PetitionDialog(unselectable)
    elif card_index > len(sorted_cards):
      cards_selected = [card_choices[card_index]] # This is one of the 'other options'
    else:
      cards_selected = [sorted_cards[card_index]]

    return cards_selected


  def LeadRoleDialog(self):
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
    p = self.get_player()
    has_palace = self.game.player_has_active_building(p, 'Palace') 

    role_led, n_actions, cards_led = None, 0, []

    lg.info('Lead a role. Choose the card:')
    cards_selected = self.SelectRoleDialog()

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
        cards = self.SelectRoleDialog(role_led, unselectable,
                                      other_options=[quit_opt])
        if cards[0] == quit_opt:
          break
        n_actions += 1
        cards_selected += cards

    return [role_led, n_actions] + cards_selected


  def PetitionDialog(self, unselectable = None):
    """
    Returns a list of cards used to petition.

    Palace has been incorporated elsewhere. The _RoleDialog methods need to 
    return [role, n_actions, cards...]
    """
    p = self.get_player()
    petition_count = 2 if self.game.player_has_active_building(p, 'Circus') else 3
    non_jack_hand = filter(lambda x:x!='Jack', p.hand)
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
    petition_cards = list(p.hand)
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

  def FollowRoleDialog(self):
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
    p = self.get_player()

    role_led = self.game.game_state.role_led
    has_palace = self.game.player_has_active_building(p, 'Palace') 

    n_actions, cards_played = 0, []

    lg.info('Follow {}: choose the card:'.format(role_led))
    thinker_opt = 'Thinker'
    cards_selected = self.SelectRoleDialog(role_led, None, [thinker_opt])

    if cards_selected[0] == thinker_opt:
      return None

    n_actions = 1
    if has_palace:
      while True:
        lg.info('Using Palace to perform additional actions. # Actions = ' + str(n_actions))
        lg.info('     using cards: {1!s}'.format(n_actions, cards_selected))
        unselectable = list(cards_selected)
        quit_opt = 'Skip further Palace actions'
        cards = self.SelectRoleDialog(role_led, unselectable,
                                      other_options=[quit_opt])
        if cards[0] == quit_opt:
          break
        n_actions += 1
        cards_selected += cards

    return [n_actions] + cards_selected

# vim: ts=8:sts=2:sw=2:et
