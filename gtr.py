"""Provides the Game class, which has little state of its own,
but provides the methods for game flow control.
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
import message

lg = logging.getLogger('gtr')
# To set up logging, look at playgame.py

class Game(object):
    initial_pool_count = 5
    initial_jack_count = 6
    max_players = 5

    def __init__(self, game_state=None):
        self.game_state = game_state if game_state is not None else GameState()
        self.client_dict = {} # Dictionary of <name> : <Client()>
        self.slave = False

        logger = logging.getLogger('gtr')
        logger.addFilter(gtrutils.RoleColorFilter())
        logger.addFilter(gtrutils.MaterialColorFilter())

    def __repr__(self):
        rep=('Game(game_state={game_state!r})')
        return rep.format(game_state = self.game_state)

    def start_game(self):
        self.init_common_piles(len(self.game_state.players))
        self.game_state.init_players()
        self.game_state.stack.push_frame('take_turn_stacked', self.game_state.active_player)
        self.game_state.is_started = True
        self.pump()

    def expected_action(self):
        return self.game_state.expected_action

    def test_set_n_in_town(self, n_sites):
        self.game_state.in_town_foundations = []
        for material in card_manager.get_all_materials():
            self.game_state.in_town_foundations.extend([material]*n_sites)

    def test_set_n_out_of_town(self, n_sites):
        self.game_state.out_of_town_foundations = []
        for material in card_manager.get_all_materials():
            self.game_state.out_of_town_foundations.extend([material]*n_sites)

    def test_all_get_client(self, client_card):
        for p in self.game_state.players:
            p.clientele.append(client_card)

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
        first_player_name = self.game_state.players[first_player_index].name
        lg.info('Player {} goes first'.format(first_player_name))

        self.game_state.active_player = self.game_state.players[first_player_index]
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

    def handle_thinkerorlead(self, a):
        do_thinker = a.args[0]
        p = self.game_state.get_current_player()

        if not do_thinker:
            # my_list[::-1] reverses the list
            for p in self.game_state.get_players_in_turn_order()[::-1]:
                self.game_state.stack.push_frame("perform_role_being_led", p)
            for p in self.game_state.get_following_players_in_order()[::-1]:
                self.game_state.stack.push_frame("follow_role_action", p)
            self.game_state.stack.push_frame("lead_role_action")

        else:
            self.game_state.stack.push_frame("perform_thinker_action", p)

        self.pump()


    def thinker_or_lead(self, player):
        self.game_state.active_player = player
        self.game_state.expected_action = message.THINKERORLEAD
        return


    def process_stack_frame(self):
        if self.game_state.stack.stack:
            try:
                frame = self.game_state.stack.stack.pop()
            except IndexError:
                lg.info('Tried to pop from empty stack!')
                raise

            lg.debug('Pop stack frame: ' + str(frame))
            #print 'Pop stack frame: ' + str(frame)

            func = getattr(self, frame.function_name)
            func.__call__(*frame.args)

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
        #self.save_game_state('tmp/log_state')

    def advance_turn(self):
        """ Moves the leader index, prints game state, saves, and pushes the next turn.
        """
        self.game_state.turn_number += 1
        self.game_state.increment_leader_index()
        leader_index = self.game_state.leader_index
        #self.show_public_game_state()
        #self.print_complete_player_state(self.game_state.players[leader_index])
        leader = self.game_state.players[leader_index]
        self.game_state.stack.push_frame('take_turn_stacked', leader)
        self.pump()

    def take_turn_stacked(self, player):
        """
        Push ADVANCE_TURN frame.
        Push END_TURN frame.
        Push THINKER_OR_LEAD frame.
        """
        self.game_state.stack.push_frame("advance_turn")
        self.game_state.stack.push_frame("end_turn")
        self.game_state.stack.push_frame("kids_in_pool")
        self.game_state.stack.push_frame("thinker_or_lead", player)
        self.pump()

    def post_game_state(self):
        save_game_state(self)

    def get_max_hand_size(self, player):
        max_hand_size = 5
        if self.player_has_active_building(player, 'Shrine'):
            max_hand_size += 2
        if self.player_has_active_building(player, 'Temple'):
            max_hand_size += 4

        return max_hand_size

    def perform_optional_thinker_action(self, player):
        """ Thinker using Academy at the end of turn in which player used Craftsman.

        This thinker is optional, unlike perform_thinker_action().
        """
        self.game_state.expected_action = message.SKIPTHINKER
        return

    def handle_skipthinker(self, a):
        skip = a.args[0]

        if skip:
            self.pump()

        else:
            perform_thinker_action(self.game_state.get_current_player())


    def perform_thinker_action(self, player):
        """ Entry point for the stack frame that performs one thinker action.
        """
        if self.player_has_active_building(player, 'Vomitorium'):
            self.game_state.active_player = player
            self.game_state.expected_action = message.USEVOMITORIUM

        else:
            a = message.GameAction(message.USEVOMITORIUM, False)
            self.handle_usevomitorium(a)


    def handle_usevomitorium(self, a):
        """ Handle using a Vomitorium to discard hand.

        This is either called on a client response, or directly
        from perform_craftsman if the player doesn't have a Vomitorium.

        If the player doesn't have a latrine or the vomitorium is used,
        call handle_uselatrine() to skip the latrine usage.
        Otherwise, ask for latrine use and return.
        """
        p = self.game_state.get_current_player()

        do_discard = a.args[0]
        if do_discard:
            self.game_state.discard_all_for_player(p)
            a = message.GameAction(message.USELATRINE, None)
            self.handle_uselatrine(a)

        elif self.player_has_active_building(p, 'Latrine'):
            self.game_state.active_player = p
            self.game_state.expected_action = message.USELATRINE

        else:
            a = message.GameAction(message.USELATRINE, None)
            self.handle_uselatrine(a)


    def handle_uselatrine(self, a):
        p = self.game_state.active_player
        latrine_card = a.args[0]

        if latrine_card is not None:
            self.game_state.discard_for_player(p, latrine_card)

        self.game_state.active_player = p
        self.game_state.expected_action = message.THINKERTYPE


    def handle_thinkertype(self, a):
        p = self.game_state.active_player
        for_jack = a.args[0]

        if for_jack:
            self.game_state.draw_one_jack_for_player(p)
        else:
            self.game_state.thinker_for_cards(p, self.get_max_hand_size(p))
            if len(self.game_state.library) == 0:
                lg.info('The last Orders card has been drawn, Game Over.')
                end_game()

        self.pump()


    def lead_role_action(self):
        """ Entry point for the lead role stack frame.
        """
        self.game_state.active_player = self.game_state.get_current_player()
        self.game_state.expected_action = message.LEADROLE


    def handle_leadrole(self, a):
        p = self.game_state.get_current_player()

        role, n_actions = a.args[0:2]
        cards = a.args[2:]

        self.game_state.role_led = role
        p.n_camp_actions = n_actions
        for c in cards:
            gtrutils.move_card(c, p.hand, p.camp)

        self.pump()


    def follow_role_action(self, player):
        self.game_state.active_player = player
        self.game_state.expected_action = message.FOLLOWROLE


    def handle_followrole(self, a):
        think, n_actions = a.args[0], a.args[1]
        cards = a.args[2:]

        p = self.game_state.active_player

        if think:
            p.n_camp_actions = 0
            self.game_state.stack.push_frame("perform_thinker_action", p)
        else:
            p.n_camp_actions = n_actions
            for c in cards:
                gtrutils.move_card(c, p.hand, p.camp)

        self.pump()


    def perform_role_being_led(self, player):
        """
        Stack up all Merchants then clients of the appropriate role.
        The function perform_clientele_action(), called in one of these frames,
        skips if it's a Merchant and player doesn't have Ludus Magna.
        Then checks if leading or following and has Circus Maximus. If so,
        stack up two actions, otherwise, stack one.
        Examine the stack. If there are two perform_craftsman() (or Arch)
        actions on top, set the flag "out of town allowed".
        Also, if there's a perform_craftsman on top of a perform_clientele_action()
        (and we're leading craftsman), set "out of town allowed".
        """
        role = self.game_state.role_led
        lg.info('Player {} is performing {}'.format(player.name, role))

        n_merchants = player.get_n_clients('Merchant')
        n_role = player.get_n_clients(role)

        if role != 'Merchant':
            for _ in range(n_merchants):
                self.game_state.stack.push_frame('perform_clientele_action', player, 'Merchant')

        for _ in range(n_role):
            self.game_state.stack.push_frame('perform_clientele_action', player, role)

        for _ in range(player.n_camp_actions):
            self.game_state.stack.push_frame('perform_role_action', player, role)

        self.pump()


    def perform_clientele_action(self, player, role):
        role_led = self.game_state.role_led
        has_ludus = self.player_has_active_building(player, 'Ludus Magnus')
        has_cm = self.player_has_active_building(player, 'Circus Maximus')
        is_leading_or_following = player.is_following_or_leading()


        # Only do these if the player has an active Ludus Magnus
        if role == 'Merchant' and role_led != 'Merchant':
            if has_ludus:
                self.game_state.stack.push_frame('perform_role_action', player, role_led)
                if has_cm and is_leading_or_following:
                    self.game_state.stack.push_frame('perform_role_action', player, role_led)
            # Skip Merchant if that's not the role being led and no Ludus
        else:
            # Do these for everyone
            self.game_state.stack.push_frame('perform_role_action', player, role)
            if has_cm and is_leading_or_following:
                self.game_state.stack.push_frame('perform_role_action', player, role)

        self.pump()


    def perform_role_action(self, player, role):
        """ Multiplexer function for arbitrary roles.

        Calls perform_<role>_action(), etc.

        This also handles the GameState.oot_used flag. The flag indicates that
        a Craftsman or Architect started a building on an out-of-town site.
        This will skip the action if the player doesn't have a tower.
        """
        has_tower = self.player_has_active_building(player, 'Tower')
        used_oot = self.game_state.used_oot

        self.game_state.used_oot = False
        if not used_oot or (used_oot and has_tower):
            if role=='Patron':
                self.perform_patron_action(player)
            elif role=='Laborer':
                self.perform_laborer_action(player)
            elif role=='Architect':
                self.perform_architect_action(player)
            elif role=='Craftsman':
                self.perform_craftsman_action(player)
            elif role=='Legionary':
                self.perform_legionary_action(player)
            elif role=='Merchant':
                self.perform_merchant_action(player)
            else:
                raise Exception('Illegal role: {}'.format(role))

        else:
            self.pump()


    def perform_laborer_action(self, player):
        self.game_state.active_player = player
        self.game_state.expected_action = message.LABORER


    def handle_laborer(self, a):
        card_from_hand, card_from_pool = a.args[0:2]

        p = self.game_state.active_player

        if card_from_pool:
            gtrutils.move_card(card_from_pool, self.game_state.pool, p.stockpile)
        if card_from_hand:
            gtrutils.move_card(card_from_hand, p.hand, p.stockpile)

        self.pump()


    def perform_patron_action(self, player):
        has_bar = self.player_has_active_building(player, 'Bar')
        has_aqueduct = self.player_has_active_building(player, 'Aqueduct')

        if has_bar and has_aqueduct:
            # All patron stack frames will be pushed by handle_baroraqueduct
            self.game_state.expected_action = message.BARORAQUEDUCT

        else:
            if has_bar:
                self.game_state.stack.push_frame('perform_patron_from_deck', player)
            if has_aqueduct:
                self.game_state.stack.push_frame('perform_patron_from_hand', player)

            self.game_state.stack.push_frame('perform_patron_from_pool', player)

            self.pump()


    def handle_baroraqueduct(self, a):
        bar_first = a.args[0]

        p = self.game_state.active_player

        if bar_first:
            self.game_state.stack.push_frame('perform_patron_from_deck', p)
            self.game_state.stack.push_frame('perform_patron_from_hand', p)
        else:
            self.game_state.stack.push_frame('perform_patron_from_hand', p)
            self.game_state.stack.push_frame('perform_patron_from_deck', p)

        self.game_state.stack.push_frame('perform_patron_from_pool', p)

        self.pump()


    def perform_patron_from_pool(self, player):
        self.game_state.active_player = player
        self.game_state.expected_action = message.PATRONFROMPOOL


    def handle_patronfrompool(self, a):
        card = a.args[0]

        p = self.game_state.active_player

        if card:
            gtrutils.move_card(card, self.game_state.pool, p.clientele)
            if self.player_has_active_building(p, 'Bath'):
                role = card_manager.get_role_of_card(card)
                #TODO: Does Ludus Magna help with Bath. What about Circus Maximus?
                self.game_state.stack.push_frame('perform_role_action', p, role)

        self.pump()


    def perform_patron_from_deck(self, player):
        self.game_state.active_player = player
        self.game_state.expected_action = message.PATRONFROMDECK


    def handle_patronfromdeck(self, a):
        do_patron = a.args[0]

        p = self.game_state.active_player

        if do_patron:
            card = self.game_state.draw_cards(1)[0]
            gtrutils.add_card_to_zone(card, p.clientele)
            if self.player_has_active_building(p, 'Bath'):
                role = card_manager.get_role_of_card(card)
                #TODO: Does Ludus Magna help with Bath. What about Circus Maximus?
                self.game_state.stack.push_frame('perform_role_action', p, role)

        self.pump()


    def perform_patron_from_hand(self, player):
        self.game_state.active_player = player
        self.game_state.expected_action = message.PATRONFROMHAND


    def handle_patronfromhand(self, a):
        card = a.args[0]

        p = self.game_state.active_player

        if card:
            gtrutils.move_card(card, p.hand, p.clientele)
            if self.player_has_active_building(p, 'Bath'):
                role = card_manager.get_role_of_card(card)
                #TODO: Does Ludus Magna help with Bath. What about Circus Maximus?
                self.game_state.stack.push_frame('perform_role_action', p, role)

        self.pump()


    def check_building_start_legal(self, player, building, site):
        """ Checks if starting this building is legal. Accounts for Statue.

        The building parameter is just the name of the building.
        """
        if site is None or building is None:
            return False
        if player.owns_building(building):
            return False

        material = card_manager.get_material_of_card(building)

        return material == site or building == 'Statue'

    def check_building_add_legal(self, player, building_name, material_card):
        """ Checks if the specified player is allowed to add material
        to building. This accounts for the building material, the
        site material, a player's active Road, Scriptorium, and Tower.
        This does not handle Stairway, which is done in perform_architect_action().

        This checks if the material is legal, but not if the building is already
        finished or malformed (eg. no site, or no foundation).
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


    def perform_craftsman_action(self, player):
        self.game_state.active_player = player
        if self.player_has_active_building(player, 'Fountain'):
            self.game_state.expected_action = message.USEFOUNTAIN
        else:
            a = message.GameAction(message.USEFOUNTAIN, False)
            self.handle_usefountain(a)


    def perform_architect_action(self, player):
        self.game_state.active_player = player
        self.game_state.expected_action = message.ARCHITECT


    def handle_usefountain(self, a):
        # TODO: Does the handle_fountain need to be different than
        # handle_craftsman? We could just check if we're Fountain-ing.
        use_fountain = a.args[0]

        p = self.game_state.active_player

        if use_fountain:
            player.fountain_card = self.game_state.draw_cards(1)[0]
            self.game_state.expected_action = message.FOUNTAIN
        else:
            self.game_state.expected_action = message.CRAFTSMAN


    def handle_fountain(self, a):
        skip, building, material, site = a.args

        p = self.game_state.active_player

        fountain_card = p.fountain_card
        p.add_cards_to_hand([p.fountain_card])
        p.fountain_card = None

        if not skip:
            self.construct(p, building, material, site)

        self.pump()


    def construct(self, player, foundation, material, site):
        """ Handles building construction without validity checking.

        Does not move the material or building card. This function's
        caller must grab them.

        If the site is not None, construct the specified building on it.
        If it's out of town, set the GameState.used_oot flag.
        (The perform_role_action() function consumes this flag.)

        Else, if the site is None, add the material to the building.
        """
        start_building = site is not None

        if start_building:
            # assert(check_building_start_legal(player, foundation, site))
            is_oot = site not in self.game_state.in_town_foundations

            if is_oot:
                sites = self.game_state.out_of_town_foundations
                self.game_state.used_oot = is_oot
            else:
                sites = self.game_state.in_town_foundations

            site_card = gtrutils.get_card_from_zone(site, sites)
            foundation_card = gtrutils.get_card_from_zone(foundation, player.hand)
            player.buildings.append(Building(foundation_card, site_card))

        else:
            # assert(check_building_add_legal(player, building, material))
            has_scriptorium = self.player_has_active_building(player, 'Scriptorium')

            b = player.get_building(foundation)
            b.add_material(material)

            completed = False
            if has_scriptorium and card_manager.get_material_of_card(material) == 'Marble':
                lg.info('Player {} completed building {} using Scriptorium'.format(
                  player.name, str(b)))
                completed = True
            elif len(b.materials) == card_manager.get_value_of_material(b.site):
                lg.info('Player {} completed building {}'.format(player.name, str(b)))
                completed = True

            if completed:
                b.completed = True
                gtrutils.add_card_to_zone(b.site, player.influence)
                self.resolve_building(player, b)


    def handle_craftsman(self, a):
        foundation, material, site = a.args

        p = self.game_state.active_player

        if foundation is None or (material is None and site is None):
            self.pump()

        else:
            m = None
            if material is not None:
                m = gtrutils.get_card_from_zone(material, p.hand)

            lg.debug('Construct building: {0}, {1}, {2}, {3}'.format(str(p),str(foundation), m, site))
            self.construct(p, foundation, m, site)
            self.pump()


    def handle_architect(self, a):
        """ Skip the action by making building = None
        """
        foundation, material, site, from_pool = a.args

        p = self.game_state.active_player

        if foundation is not None:
            m = None
            if material is not None:
                if from_pool:
                    m = gtrutils.get_card_from_zone(material, self.game_state.pool)
                else:
                    m = gtrutils.get_card_from_zone(material, p.stockpile)

            lg.debug('Construct building: {0!s}, {1!s}, {2}, {3}'.format(p,foundation, m, site))
            self.construct(p, foundation, m, site)

        else:
            has_stairway = self.player_has_active_building(p, 'Stairway')
            if has_stairway:
                self.game_state.expected_action = STAIRWAY
                return

        self.pump()


    def handle_stairway(self, a):
        """ Handles a Stairway move.

        If player, building, or material is None, skip the action.
        """
        player, foundation, material, from_pool = a.args

        if player is None or foundation is None or material is None:
            self.pump()

        p = self.game_state.active_player

        b = player.get_building(foundation)
        zone = self.game_state.pool if from_pool else p.stockpile

        lg.info(
          'Player {0} used Stairway to add a material to player {1}\'s {2}, '
          .format( p.name, player.name, str(b)) +
          'activating its function for all players')

        gtrutils.move_card(material, zone, b.stairway_materials)

        self.pump()


    def perform_legionary_action(self, player):
        """ Legionary actions are processed all at once. For example, if
        you have 2 Legionary clients and are leading Legionary, you reveal
        three orders cards to demand. Here, this means we have to consolidate
        all Legionary actions on the stack into one.

        The stack may contain any of these frames that we must consider
          - perform_role_action(player, 'Legionary')
          - perform_clientele_action(player, 'Legionary')
          - perform_clientele_action(player, 'Merchant')

        Nothing about the active player's buildings can change via a Legionary
        action, so we can evaluate the Circus Maximus and Ludus Magna on the
        listed stack frames.
        """
        self.game_state.active_player = player

        has_ludus = self.player_has_active_building(player, 'Ludus Magnus')
        has_cm = self.player_has_active_building(player, 'Circus Maximus')
        is_leading_or_following = player.is_following_or_leading()
        role_led = self.game_state.role_led

        self.game_state.legionary_count = 1

        # Traverse the stack, remove Legionary frames and increment legionary count
        for f in self.game_state.stack.stack[::-1]:
            if not len(f.args) or f.args[0] != player:
                break

            if f.function_name == 'perform_role_action' and f.args[1] == 'Legionary':
                self.game_state.legionary_count += 1
                self.game_state.stack.remove(f)

            elif f.function_name == 'perform_clientele_action':
                role = f.args[1]

                if role == 'Legionary' or (has_ludus and role == 'Merchant'):
                    self.game_state.legionary_count += 1
                    if has_cm and role_led == 'Legionary' and is_following_or_leading:
                        self.game_state.legionary_count += 1

                    self.game_state.stack.remove(f)

            else:
                break

        # Player can infer the legionary count
        self.game_state.expected_action = message.LEGIONARY


    def handle_legionary(self, a):
        cards = a.args

        p = self.game_state.active_player

        # Player.revealed isn't a zone, but a list of revealed cards in the hand
        # so the cards are not removed from the players hand
        p.revealed.extend(cards)

        # Get cards from pool
        for card in cards:
            mat = card_manager.get_material_of_card(card)
            for _c in self.game_state.pool:
                if card_manager.get_material_of_card(_c) == mat:
                    gtrutils.move_card(_c, self.game_state.pool, p.stockpile)


        # Get cards from other players
        n = len(self.game_state.players)
        p_index = self.game_state.players.index(p)

        self.game_state.legionary_index = p_index

        has_bridge = self.player_has_active_building(p, 'Bridge')

        if has_bridge:
            r = range(n)
            indices = r[n+1:] + r[:n]
        else:
            indices = [(self.game_state.legionary_index + 1) % n]
            if n > 2:
                indices.append((self.game_state.legionary_index - 1) % n)

        self.game_state.legionary_resp_indices = indices

        self.game_state.active_player = self.game_state.players[indices[0]]
        self.game_state.expected_action = message.GIVECARDS


    def handle_givecards(self, a):
        cards = a.args

        p = self.game_state.active_player

        leg_p = self.game_state.players[self.game_state.legionary_index]

        has_bridge = self.player_has_active_building(leg_p, 'Bridge')
        has_coliseum = self.player_has_active_building(leg_p, 'Coliseum')

        has_wall = self.player_has_active_building(p, 'Wall')
        has_palisade = self.player_has_active_building(p, 'Palisade')

        is_immune = has_wall or (has_palisade and not has_bridge)

        if not is_immune:
            self.move_legionary_cards(p, leg_p, cards, has_bridge, has_coliseum)

        self.game_state.legionary_resp_indices.pop(0)
        if len(self.game_state.legionary_resp_indices):
            next_index = self.game_state.legionary_resp_indices[0]

            self.active_player = self.game_state.players[next_index]
            self.game_state.expected_action = message.GIVECARDS

        else:
            self.pump()


    def move_legionary_cards(self, p, leg_p, cards, has_bridge, has_coliseum):
        """ Moves the cards from p's zones according to leg_p's revealed
        cards and the flags for Bridge and Coliseum.

        The cards provided should be in order, lose from hand, then stockpile,
        then clientele
        """
        rev_cards = leg_p.revealed
        given_cards = list(cards)
        c2m = card_manager.get_material_of_card

        for c in leg_p.revealed:
            mat = c2m(c)
            matched_cards = [card for card in p.hand if c2m(card) == mat]
            for given_card in given_cards:
                if given_card in matched_cards:
                    gtrutils.move_card(given_card, p.hand, leg_p.stockpile)
                    given_cards.remove(given_card)
                    break

        if has_bridge:
            for c in leg_p.revealed:
                mat = c2m(c)
                matched_cards = [card for card in p.stockpile if c2m(card) == mat]
                for given_card in given_cards:
                    if given_card in matched_cards:
                        gtrutils.move_card(given_card, p.stockpile, leg_p.stockpile)
                        given_cards.remove(given_card)
                        break

        if has_coliseum:
            for c in leg_p.revealed:
                mat = c2m(c)
                matched_cards = [card for card in p.clientele if c2m(card) == mat]
                for given_card in given_cards:
                    if given_card in matched_cards:
                        gtrutils.move_card(given_card, p.clientele, leg_p.vault)
                        given_cards.remove(given_card)
                        break


    def perform_merchant_action(self, player):
        self.game_state.active_player = player
        self.game_state.expected_action = message.MERCHANT


    def handle_merchant(self, a):
        stockpile_card, hand_card, from_deck = a.args

        p = self.game_state.active_player

        if stockpile_card:
            gtrutils.move_card(stockpile_card, p.stockpile, p.vault)

        if hand_card:
            gtrutils.move_card(hand_card, p.hand, p.vault)

        if from_deck:
            gtrutils.add_card_to_zone(self.game_state.draw_cards(1)[0], player.vault)

        self.pump()


    def kids_in_pool(self):
        """ Place cards in camp into the pool.
        1) If Sewer, ask to move cards into stockpile.
        2) If dropping a Jack, ask players_with_senate in order.
        """
        lg.info('\n ==== KIDS IN POOL ====\n')

        self.do_kids_in_pool(self.game_state.get_current_player())


    def do_kids_in_pool(self, p):
        p_index = self.game_state.players.index(p)
        self.game_state.kip_index = p_index

        p_in_order = self.game_state.get_players_in_turn_order(p)
        p_in_order.pop(0) # skip this player

        indices = []
        for _p in p_in_order:
            if self.player_has_active_building(_p, 'Senate'):
                indices.append(self.game_state.players.index(_p))

        self.game_state.senate_resp_indices = indices

        self.do_senate()


    def do_senate(self):
        if self.game_state.senate_resp_indices:
            self.game_state.expected_action = message.USESENATE
            return

        else:
            p = self.game_state.players[self.game_state.kip_index]
            if self.player_has_active_building(p, 'Sewer'):
                self.game_state.expected_action = message.USESEWER
                return

            else:
                self.handle_usesewer(message.GameAction(message.USESEWER, None))


    def handle_usesenate(self, a):
        take_jack = a.args[0]
        p_index = self.game_state.senate_resp_indices.pop(0)
        p_kip = self.game_state.players[self.game_state.kip_index]

        if take_jack:
            p = self.game_state.players[p_index]
            gtrutils.move_card('Jack', p_kip.camp, p.hand)

            self.game_state.senate_resp_indices = []

        self.do_senate()


    def handle_usesewer(self, a):
        cards = a.args
        p = self.game_state.players[self.game_state.kip_index]

        if cards[0] is not None:
            for c in cards:
                if c == 'Jack':
                    raise Exception('Can\'t move Jacks with Sewer')
                gtrutils.move_card(c, p.camp, p.stockpile)

        for c in p.camp:
            if c == 'Jack':
                gtrutils.move_card(c, p.camp, self.game_state.jack_pile)
            else:
                gtrutils.move_card(c, p.camp, self.game_state.pool)

        kip_next = (self.game_state.kip_index + 1) % len(self.game_state.players)

        if kip_next == self.game_state.leader_index:
            self.pump()

        else:
            self.do_kids_in_pool(self.game_state.players[kip_next])


    def end_turn(self):
        # players in reverse order
        players = self.game_state.get_players_in_turn_order()[::-1]

        for p in players:
            self.game_state.stack.push_frame('do_end_turn', p)

        self.pump()


    def do_end_turn(self, p):
        has_academy = self.player_has_active_building(p, 'Academy')

        p.revealed = []
        p.n_camp_actions = 0

        if p.performed_craftsman and has_academy:
            p.peformed_craftsman = False
            self.perform_optional_thinker(p)

        self.pump()


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


    def resolve_building(self, player, building_obj):
        """ Switch on completed building to resolve the "On Completion" effects.
        """
        if str(building_obj) == 'Catacomb':
            self.end_game()
        elif str(building_obj) == 'Foundry':
            n = player.get_influence_points()

            msg = 'Foundry: Performing {} Laborer actions for player {}'
            lg.info(msg.format(n, player.name))

            for _ in range(n):
                self.game_state.stack.push_frame('perform_laborer_action', player)

        elif str(building_obj) == 'Garden':
            n = player.get_influence_points()

            msg = 'Garden: Performing {} Patron actions for player {}'
            lg.info(msg.format(n,player.name))

            for _ in range(n):
                self.game_state.stack.push_frame('perform_patron_action', player)

        elif str(building_obj) == 'School':
            n = player.get_influence_points()

            msg = 'School: Performing {} Thinker actions for player {}'
            lg.info(msg,format(n, player.name))

            for _ in range(n):
                self.game_state.stack.push_frame('perform_optional_thinker_action', player)

        elif str(building_obj) == 'Amphitheatre':
            n = player.get_influence_points()

            msg = 'Amphitheatre: Performing {} Craftsman actions for player {}'
            lg.info(msg.format(n, player.name))

            for _ in range(n):
                self.game_state.stack.push_frame('perform_craftsman_action', player)

        self.pump()


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


    def handle(self, a):
        """ Switchyard to handle game actions.
        """
        lg.info('Handling action: ' + repr(a))
        if a.action != self.expected_action():
            raise Exception('Expected GameAction type: ' + str(self.expected_action())
                + ', Got :' + repr(a))

        method_name = 'handle_' + str(a)

        try:
            method = getattr(self, method_name)
        except AttributeError:
            raise Exception('Unhandled GameAction type: ' + str(a.action))
        else:
            method.__call__(a)
            self.game_state.game_id += 1
