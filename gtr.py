"""Provides the Game class, which has little state of its own,
but provides the methods for game flow control.
"""

from player import Player
from gtrutils import get_card_from_zone
from gamestate import GameState
import gtrutils
from gtrutils import GTRError, check_petition_combos
import card_manager as cm
from building import Building
from card import Card
from zone import Zone
#import client2 as client

from collections import Counter
import logging
import pickle
import itertools
import time
import glob
import message
from itertools import product
from datetime import datetime

lg = logging.getLogger('gtr')
logging.basicConfig()
lg.setLevel(logging.INFO)
#lg.setLevel(logging.DEBUG)

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

        self.log('Starting game.')
        self.log('Turn {0}: {1}'
            .format(self.game_state.turn_number,
                    self.game_state.get_current_player().name))

        self.pump()

    def expected_action(self):
        return self.game_state.expected_action


    def get_client(self, player_name):
        """ Returns the client object and updates the GameState to be current.
        """
        c = self.client_dict[player_name]
        c.game.game_state = self.game_state # Update client game state
        return c

    def add_player(self, name):
        self.game_state.find_or_add_player(name)

        self.log('{0} has joined the game.'.format(name))

    def init_common_piles(self, n_players):
        self.log('Initializing the game')

        self.init_library()
        first_player_index = self.init_pool(n_players)

        self.game_state.active_player = self.game_state.players[first_player_index]
        self.game_state.leader_index = first_player_index
        self.game_state.priority_index = first_player_index
        self.game_state.jack_pile = Zone([Card(i) for i in range(Game.initial_jack_count)])
        self.init_sites(n_players)


    def init_pool(self, n_players):
        """Deals one card to each player and place the cards in the pool.

        Return the player index that goes first.
        """
        all_cards = Zone()
        has_winner = False
        players = range(n_players)
        while not has_winner:
            # Make list of (player, card) pairs
            cards = [(i,self.game_state.draw_cards(1)[0]) for i in players]
            first = min(cards, key=lambda x : x[1])
            players = [c[0] for c in cards if c[1].name == first[1].name]
            all_cards.extend([c[1] for c in cards])

            s = ''.join(['{0} reveals {1!s}. '.format(self.game_state.players[i].name, card)
                         for i, card in cards])
            self.log(s)

            if len(players)==1:
                has_winner = True
                self.log('{0} plays first.'.format(self.game_state.players[0].name))
            else:
                self.log('Deal more cards into pool to break tie.')

        self.game_state.pool.extend(all_cards)
        return players[0]

    def init_sites(self, n_players):
        n_out_of_town = 6 - n_players
        for material in cm.get_all_materials():
            self.game_state.in_town_foundations.extend([material]*n_players)
            self.game_state.out_of_town_foundations.extend([material]*n_out_of_town)

    def init_library(self):
        """Initializes the library as a list of Card objects
        """
        self.game_state.library = Zone(cm.get_orders_card_set())
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

        for material in cm.get_materials():
            # Set name to None if there's a tie, but maintain maximum
            name, maximum = None, 0
            for player in self.game_state.players:
                material_cards = filter(
                    lambda c : c.material == material, player.vault)
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
            card_pts += card.value

        return card_pts + bonus_pts


    def get_clientele_limit(self, player):
        has_insula = self.player_has_active_building(player, 'Insula')
        has_aqueduct = self.player_has_active_building(player, 'Aqueduct')
        limit = player.get_influence_points()

        if has_insula: limit += 2
        if has_aqueduct: limit *= 2
        return limit

    def get_vault_limit(self, player):
        has_market = self.player_has_active_building(player, 'Market')
        limit = player.get_influence_points()

        if has_market: limit += 2
        return limit

    def player_has_building(self, player, building):
        """Checks if the player has the specific building object, not
        just a building of the same name.

        Args:
        building -- Building object
        """
        return building in player.get_owned_buildings()

    def player_has_active_building(self, player, building):
        """True if the building is active for the player.

        Args:
        player -- Player object
        building -- string
        """
        return building in self.get_active_building_names(player)

    def get_active_building_names(self, player):
        """ Returns a list of building names that are active for a player,
        taking the effect of the Stairway into account. See the
        get_active_buildings() method for reference, but note that
        this method does not return duplicate names.
        """
        names = map(str, self.get_active_buildings(player))
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
                lg.warning('Tried to pop from empty stack!')
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

    def log(self, msg):
        """Logs the message in the GameState log roll.
        """
        time = datetime.now().time().strftime('%H:%M:%S ')
        self.game_state.log(time+msg)

    def pump(self):
        self.process_stack_frame()

    def advance_turn(self):
        """ Moves the leader index, prints game state, saves, and pushes the next turn.
        """
        self.game_state.turn_number += 1
        self.game_state.increment_leader_index()
        leader_index = self.game_state.leader_index
        leader = self.game_state.players[leader_index]
        self.game_state.stack.push_frame('take_turn_stacked', leader)

        self.log('Turn {0}: {1}'.format(self.game_state.turn_number, leader.name))

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

        p = self.game_state.active_player

        if skip:
            self.log('{0} skips thinker with Academy'.format(p.name))
            self.pump()

        else:
            self.log('{0} thinks at the end of turn with Academy'.format(p.name))
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
            self.log('{0} discards their entire hand with Vomitorium: {1}.'
                .format(p.name, ', '.join(p.hand)))

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
            self.log('{0} discards {1} using Latrine.'
                .format(p.name, latrine_card))

        self.game_state.active_player = p
        self.game_state.expected_action = message.THINKERTYPE


    def handle_thinkertype(self, a):
        p = self.game_state.active_player
        for_jack = a.args[0]

        is_leader = p == self.game_state.get_current_player()

        if for_jack:
            self.game_state.draw_one_jack_for_player(p)

            if is_leader:
                self.log('{0} thinks for a Jack.'.format(p.name))
            else:
                self.log('{0} thinks for a Jack instead of following.'.format(p.name))

        else:
            self.game_state.thinker_for_cards(p, self.get_max_hand_size(p))

            n_cards = max(1, self.get_max_hand_size(p) - len(p.hand))
            noun = 'cards' if n_cards > 1 else 'card'

            if is_leader:
                self.log('{0} thinks for {1} {2}.'.format(p.name, n_cards, noun))
            else:
                self.log('{0} thinks for {1} {2} instead of following.'
                    .format(p.name, n_cards, noun))

            if len(self.game_state.library) == 0:
                self.log('{0} has drawn the last Orders card. Game Over.'.format(p.name))
                self.end_game()

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

        # This will raise GTRError if the cards don't check out.
        self.check_action_units(p, role, n_actions, cards)

        if not p.hand.contains(cards):
            raise GTRError('Cards specified to lead role not in hand: {0}.'
                .format(', '.join(map(str, cards))))

        self.game_state.role_led = role
        p.n_camp_actions = n_actions
        for c in cards:
            gtrutils.move_card(c, p.hand, p.camp)

        if n_actions > 1:
            self.log('{0} leads {1} for {2} actions using: {3}'
                    .format(p.name, role, n_actions, ', '.join(map(str, cards))))
        else:
            self.log('{0} leads {1} using: {2}'
                    .format(p.name, role, ', '.join(map(str, cards))))

        self.pump()


    def follow_role_action(self, player):
        self.game_state.active_player = player
        self.game_state.expected_action = message.FOLLOWROLE


    def check_action_units(self, player, role_led, n_actions, cards):
        """Checks the action units provided to lead or follow
        a role, possibly multiple times via Palace, to be sure
        the combination of cards is legal for n_actions.
        This checks indirectly if the following role is the same
        as the led role, since, eg. a single Laborer card won't 
        work for a Patron lead.

        This will raise on the following conditions:

            1) n_actions <= 0
            2) n_actions > 1 and player doesn't have palace.
            3) # of Jacks in cards > n_actions
            4) The combination of orders cards can't be used to Petition
               for n_actions actions (if the player has a Palace).

        Raises GTRError if the combination is not legal.
        """
        # Action unit can be one of the following:
        #   1) Single Card of role_led
        #   2) Single Jack
        #   3) Petition of three cards of any one role (including
        #      role_led)
        #   4) Petition of two cards of any one role (including
        #      role_led) if player has Circus
        
        has_palace = self.player_has_active_building(player, 'Palace')
        has_circus = self.player_has_active_building(player, 'Circus')

        if n_actions <= 0:
            raise GTRError('Cannot follow with 0 actions.')

        if not has_palace and n_actions > 1:
            raise GTRError(
                    'Cannot follow with more than 1 action without a Palace.')

        n_left = n_actions
        n_jacks = 0
        for c in cards:
            if c.name == 'Jack': n_jacks += 1

        role_counter = Counter([c.role for c in cards if c.name != 'Jack'])
        
        # Subtract off Jacks and actions one-for-one. Determine number of
        # cards on-role and off-role for the role that was led.
        n_left -= n_jacks

        n_on = role_counter[role_led]

        n_off_list = []
        for role in cm.get_all_roles():
            if role != role_led:
                n_off_list.append(role_counter[role])

        invalid_combo_error = GTRError(
                'Invalid n_actions (' + str(n_actions) + \
                ') for the combination of cards passed (' + \
                ', '.join(map(str, cards)) + ')')

        # If n_left is < 0 now we have too many Jacks.
        if n_left < 0:
            raise invalid_combo_error

        # This will allow n_left = n_on = 0 and n_off = []
        if not check_petition_combos(n_left, n_on, n_off_list, has_circus, True):
            raise invalid_combo_error
        

    def handle_followrole(self, a):
        think, n_actions = a.args[0], a.args[1]
        cards = a.args[2:]

        p = self.game_state.active_player

        if think:
            p.n_camp_actions = 0
            self.game_state.stack.push_frame("perform_thinker_action", p)
        else:
            # This will raise GTRError if the cards don't check out.
            self.check_action_units(p, self.game_state.role_led, n_actions, cards)

            # Check if cards exist in hand
            if not p.hand.contains(cards):
                raise GTRError('Not all cards specified exist in hand.')

            p.n_camp_actions = n_actions
            for c in cards:
                p.hand.move_card(c, p.camp)

            if n_actions > 1:
                self.log('{0} follows for {1} actions using: {2}'
                        .format(p.name, n_actions, ', '.join(map(str, cards))))
            else:
                self.log('{0} follows using: {1}'
                        .format(p.name, ', '.join(map(str, cards))))

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
        self.log('Player {} is performing {}'.format(player.name, role))

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


    def check_oot_allowed(self, player):
        """Checks if the player can start a site out of town. Here are the
        conditions for oot being allowed.

        There is another perform_role_action stack frame below this with the
        same player.

        A perform_clientele_action frame of the same role and player.

        A perform_clientele_action frame of same player, and role Merchant
        and we have a Ludus Magnus.

        We have a Tower.

        This checks the top stack frame, so call this after popping the action
        in which you want to know if out-of-town is allowed.

        Returns True if starting out of town is allowed, False otherwise.
        """
        if self.player_has_active_building(player, 'Tower'):
            return True

        has_ludus = self.player_has_active_building(player, 'Ludus Magnus')

        f = self.game_state.stack.stack[-1]

        # Args are (player, role)
        if f.function_name == 'perform_role_action':
            p, role = f.args

            if p.name == player.name and role == self.game_state.role_led:
                return True

        if f.function_name == 'perform_clientele_action':
            p, role = f.args

            if p.name == player.name and \
                    ((role=='Merchant' and has_ludus) or role == self.game_state.role_led):
                return True

        return False

    def perform_role_action(self, player, role):
        """Multiplexer function for arbitrary roles.

        Calls perform_<role>_action(), etc.

        This also handles the GameState.oot_used flag. The flag indicates that
        a Craftsman or Architect started a building on an out-of-town site.
        This will skip the action if the player doesn't have a tower.
        """
        has_tower = self.player_has_active_building(player, 'Tower')
        used_oot = self.game_state.used_oot

        self.game_state.used_oot = False
        if not used_oot or (used_oot and has_tower):

            self.game_state.oot_allowed = self.check_oot_allowed(player)

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
        hand_c, pool_c = a.args[0:2]

        p = self.game_state.active_player

        if pool_c and pool_c not in self.game_state.pool:
            raise GTRError('Tried to move non-existent card {0} from pool'
                       .format(pool_c))

        if hand_c and hand_c not in p.hand:
            raise GTRError('Tried to move non-existent card {0} from hand'
                       .format(hand_c))

        if pool_c:
            gtrutils.move_card(pool_c, self.game_state.pool, p.stockpile)
        if hand_c:
            gtrutils.move_card(hand_c, p.hand, p.stockpile)

        if hand_c:
            self.log('{0} performs Laborer from pool: {1} and hand: {2}.'
                    .format(p.name, pool_c, hand_c))
        else:
            self.log('{0} performs Laborer from pool: {1}'
                    .format(p.name, pool_c))

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
        if len(p.clientele) >= self.get_clientele_limit(p):
            raise GTRError('Player ' + p.name + ' has no room in clientele')

        if card:
            gtrutils.move_card(card, self.game_state.pool, p.clientele)

            if self.player_has_active_building(p, 'Bath'):
                role = cm.get_role_of_card(card)
                #TODO: Does Ludus Magna help with Bath. What about Circus Maximus?
                self.game_state.stack.push_frame('perform_role_action', p, role)
                self.log(
                    '{0} performs Patron, hiring {1} from pool and performing {2} using Bath.'
                    .format(p.name, card, role))

            else:
                self.log(
                    '{0} performs Patron, hiring {1} from pool.'
                    .format(p.name, card))

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
                role = cm.get_role_of_card(card)
                #TODO: Does Ludus Magna help with Bath. What about Circus Maximus?
                self.game_state.stack.push_frame('perform_role_action', p, role)
                self.log(
                    '{0} performs Patron, hiring {1} from deck and performing {2} using Bath.'
                    .format(p.name, card, role))

            else:
                self.log(
                    '{0} performs Patron, hiring {1} from deck.'
                    .format(p.name, card))

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
                role = cm.get_role_of_card(card)
                #TODO: Does Ludus Magna help with Bath. What about Circus Maximus?
                self.game_state.stack.push_frame('perform_role_action', p, role)
                self.log(
                    '{0} performs Patron, hiring {1} from hand and performing {2} using Bath.'
                    .format(p.name, card, role))

            else:
                self.log(
                    '{0} performs Patron, hiring {1} from hand.'
                    .format(p.name, card))

        self.pump()


    def check_building_start_legal(self, player, building, site):
        """ Checks if starting this building is legal. Accounts for Statue.
        The building parameter is just the name of the building.

        Raises GTRError if building start is illegal.
        """
        if site is None or building is None:
            raise GTRError('Illegal building / site ({0!s}/{1})'
                .format(building, site))

        if player.owns_building(building):
            raise GTRError('Player already owns {0!s}.'.format(building))

        if site not in self.game_state.out_of_town_foundations:
            raise GTRError('No {0} sites left, including out of town'
                .format(site))

        if site not in self.game_state.in_town_foundations and \
                not self.game_state.oot_allowed:
            raise GTRError('Starting an out of town building is not allowed.')

        if not (building.material == site or building.name == 'Statue'):
            raise GTRError('Illegal building/site combination ({0!s}/{1}).'
                .format(building, site))

    def check_building_add_legal(self, player, building, material_card):
        """ Checks if the specified player is allowed to add material
        to building. This accounts for the building material, the
        site material, a player's active Road, Scriptorium, and Tower.
        This does not handle Stairway, which is done in perform_architect_action().

        This checks if the material is legal, but not if the building is already
        finished or malformed (eg. no site, or no foundation).

        Returns if the material add is allowed, and raises GTRError if not.
        """
        if material_card is None or building is None:
            raise GTRError('Illegal add: material={0!s} building={1!s}'
                .format(material_card, building_card))

        has_tower = self.player_has_active_building(player, 'Tower')
        has_road = self.player_has_active_building(player, 'Road')
        has_scriptorium = self.player_has_active_building(player, 'Scriptorium')

        # This raises GTRError if building doesn't exist
        building = player.get_building(building)

        # The sites are 'Wood', 'Concrete', etc.
        site_mat = building.site
        material = material_card.material
        found_mat = building.foundation.material

        if (has_tower and material == 'Rubble') or \
               (has_scriptorium and material == 'Marble') or \
               (has_road and (found_mat == 'Stone' or site_mat == 'Stone')) or \
               (material == found_mat or material == site_mat):
           return
        else:
            raise GTRError(
                    'Illegal add, material ({0!s}) doesn\'t match building '
                    'material ({1!s}) or site material ({2!s})'
                    .format(material, found_mat, site_mat))


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
            p.fountain_card = self.game_state.draw_cards(1)[0]
            self.game_state.expected_action = message.FOUNTAIN
            self.log('{0} reveals {1} with Fountain.'
                .format(p.name, p.fountain_card))

        else:
            self.game_state.expected_action = message.CRAFTSMAN


    def handle_fountain(self, a):
        skip, building, material, site = a.args

        p = self.game_state.active_player

        fountain_card = p.fountain_card
        p.add_cards_to_hand([p.fountain_card])
        p.fountain_card = None

        if skip:
            self.log('{0} skips Fountain, drawing {1}.'
                .format(p.name, fountain_card))
        else:
            b = self.construct(p, building, material, site, p.hand)
            self.log('{0} performs Craftsman using card revealed with Fountain.')
            self.log_construct(p, building, material, site, ' using Fountain card')

            if b.complete:
                self.log('{0} completed.'.format(str(b)))
                self.resolve_building(p, b)

        self.pump()


    def log_construct(self, player, building, material, site, material_source=''):
        """Logs a construct call, checking the site to see if this was a building
        start or an addition to a building. This can be used for Craftsman or
        Architect. An additional string material_source can be provided to indicate
        where the material card came from, eg. ' from hand'.

        Checks GameState.used_oot to log if the site was out-of-town.
        """

        if site is None:
            self.log('{0} adds {1} as material to {2}{3}.'
                .format(player.name, material, building, material_source))
        elif self.game_state.used_oot:
            self.log('{0} starts {1} on a {2} site, out of town.'
                .format(player.name, building, site))
        else:
            self.log('{0} starts {1} on a {2} site.'
                .format(player.name, building, site))


    def construct(self, player, foundation, material, site, material_zone):
        """ Handles building construction with validity checking.

        Does not move the material or building card. This function's
        caller must grab them.

        If the site is not None, construct the specified building on it.
        If it's out of town, set the GameState.used_oot flag.
        (The perform_role_action() function consumes this flag.)

        Else, if the site is None, add the material to the building.

        Returns the modified building.
        """
        start_building = site is not None

        if start_building:

            # raises if start is illegal
            self.check_building_start_legal(player, foundation, site)

            is_oot = site not in self.game_state.in_town_foundations

            if player.owns_building(foundation):
                raise GTRError('{0} already has a {1!s}'
                    .format(player.name, foundation))

            if is_oot:
                sites = self.game_state.out_of_town_foundations
                if site not in sites:
                    raise GTRError('{0} not available out of town.'.format(site))
            else:
                sites = self.game_state.in_town_foundations
                if site not in sites:
                    raise GTRError('{0} not available in town.'.format(site))

            if foundation not in player.hand:
                raise GTRError('{0!s} card not in {1}\'s hand.'
                    .format(foundation, player.name))

            site_card = gtrutils.get_card_from_zone(site, sites)
            foundation_card = player.hand.pop(player.hand.index(foundation))
            b = Building(foundation_card, site_card)
            player.buildings.append(b)

            self.game_state.used_oot = is_oot

            if len(self.game_state.in_town_foundations) == 0:
                self.end_game()

            return b

        else:
            # This raises if the add is not legal
            self.check_building_add_legal(player, foundation, material)

            # Both these raise if the card/building isn't found
            b = player.get_building(foundation)
            if b.complete:
                raise GTRError('Cannot add to {0!s} because it is already complete.'
                    .format(foundation))

            # Raises if material doesn't exist
            #m = gtrutils.get_card_from_zone(material, material_zone)
            material_zone.move_card(material, b.materials)

            #b.add_material(m)

            has_scriptorium = self.player_has_active_building(player, 'Scriptorium')

            complete = False
            if has_scriptorium and cm.get_material_of_card(m) == 'Marble':
                self.log('Player {} completed building {} using Scriptorium'.format(
                  player.name, str(b)))
                complete = True
            elif len(b.materials) == cm.get_value_of_material(b.site):
                self.log('Player {} completed building {}'.format(player.name, str(b)))
                complete = True

            if complete:
                b.complete = True
                gtrutils.add_card_to_zone(b.site, player.influence)

            return b


    def handle_craftsman(self, a):
        foundation, material, site = a.args

        p = self.game_state.active_player

        if foundation is None or (material is None and site is None):
            self.pump()

        else:
            b = self.construct(p, foundation, material, site, p.hand)
            self.log('{0} performs Craftsman.'.format(p.name))
            self.log_construct(p, foundation, material, site, ' from hand')

            if b.complete:
                self.log('{0} completed.'.format(str(b)))
                self.resolve_building(p, b)

            self.pump()


    def handle_architect(self, a):
        """Skip the action by making foundation = None.
        """
        foundation, material, site, from_pool = a.args

        p = self.game_state.active_player

        if foundation:
            if from_pool:
                material_zone, s = self.game_state.pool, ' from pool'
            else:
                material_zone, s = p.stockpile, ' from stockpile'

            b = self.construct(p, foundation, material, site, material_zone)
            self.log('{0} performs Architect.'.format(p.name))
            self.log_construct(p, foundation, material, site, s)

            if b.complete:
                self.log('{0} completed'.format(str(b)))
                self.resolve_building(p, b)

        else:
            self.log('{0} skips Architect action.'.format(p.name))

        has_stairway = self.player_has_active_building(p, 'Stairway')
        if has_stairway:
            self.game_state.expected_action = message.STAIRWAY
            return

        self.pump()


    def handle_stairway(self, a):
        """ Handles a Stairway move.

        If player, building, or material is None, skip the action.
        """
        player, foundation, material, from_pool = a.args

        p = self.game_state.active_player

        if player is None or foundation is None or material is None:
            self.log('{0} chooses to skip use of Stairway.'.format(p.name))
            self.pump()

        b = player.get_building(foundation)
        zone = self.game_state.pool if from_pool else p.stockpile

        gtrutils.move_card(material, zone, b.stairway_materials)

        if from_pool:
            self.log('{0} uses Stairway to add {1} from the pool to {2}\'s {3}.' 
                .format(p.name, material, player.name, foundation))
        else:
            self.log('{0} uses Stairway to add {1} to {2}\'s {3}.' 
                .format(p.name, material, player.name, foundation))

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

        if len([c for c in cards if c.name == 'Jack']):
            raise GTRError('Cannot demand material with Jack.')

        p = self.game_state.active_player

        if not p.hand.contains(cards):
            raise GTRError('Demanding with cards not in hand: {0}.'
                .format(', '.join(map(str,cards))))


        # Player.revealed isn't a zone, but a list of revealed cards in the hand
        # so the cards are not removed from the players hand
        p.revealed.extend(p.hand.get_cards(cards))

        revealed_materials = [c.material for c in  p.revealed]

        self.log('Rome demands {0}! (revealing {1})'
            .format(', '.join(revealed_materials), 
                ', '.join(map(str,p.revealed))))

        # Get cards from pool
        pool_cards = []
        for card in cards:
            for _c in self.game_state.pool:
                if _c.material == card.material:
                    gtrutils.move_card(_c, self.game_state.pool, p.stockpile)
                    pool_cards.append(_c)

        if pool_cards:
            self.log('{0} collected {1} from the pool.'
                .format(p.name, ', '.join([c.material for c in  pool_cards])))


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
        lg.debug('Received GIVECARDS(' + ','.join(map(str, cards))+')')

        p = self.game_state.active_player

        leg_p = self.game_state.players[self.game_state.legionary_index]

        has_bridge = self.player_has_active_building(leg_p, 'Bridge')
        has_coliseum = self.player_has_active_building(leg_p, 'Coliseum')

        has_wall = self.player_has_active_building(p, 'Wall')
        has_palisade = self.player_has_active_building(p, 'Palisade')

        is_immune = has_wall or (has_palisade and not has_bridge)

        if is_immune:
            self.log('{0} is immune to legionary.'.format(p.name))
        else:
            self.move_legionary_cards(p, leg_p, cards, has_bridge, has_coliseum)

        self.game_state.legionary_resp_indices.pop(0)
        if len(self.game_state.legionary_resp_indices):
            lg.debug('Waiting on next player to respond to legionary.')
            next_index = self.game_state.legionary_resp_indices[0]

            self.active_player = self.game_state.players[next_index]
            self.game_state.expected_action = message.GIVECARDS

        else:
            lg.debug('All players have responded to legionary.')
            self.pump()


    def move_legionary_cards(self, p, leg_p, cards, has_bridge, has_coliseum):
        """ Moves the cards from p's zones according to leg_p's revealed
        cards and the flags for Bridge and Coliseum.

        The cards provided should be in order, lose from hand, then stockpile,
        then clientele
        """
        rev_cards = leg_p.revealed
        given_cards = list(cards)
        c2m = cm.get_material_of_card

        lg.debug('Moving cards for legionary. Revealed: ' + str(rev_cards) +
                ' Given: ' + str(given_cards))

        cards_moved_from_hand = [] # for logging

        # Check that all required cards were offered.
        revealed = Counter([c.material for c in rev_cards])
        given = Counter([c.material for c in given_cards])
        hand = Counter([c.material for c in p.hand])

        unmatched = revealed - given
        extras = given - revealed
        ungiven = unmatched & hand # Set intersection

        if len(extras):
            raise GTRError('Extra cards given for legionary.')

        if len(ungiven):
            raise GTRError('Not enough cards given for legionary.')

        for c in given_cards:
            gtrutils.move_card(c, p.hand, leg_p.stockpile)

        self.log('{0} gives cards from their hand: {1}'
            .format(p.name, ', '.join(map(str, given_cards))))

        stockpile_copy = list(p.stockpile)
        cards_moved_from_stockpile = []
        if has_bridge:
            for c in leg_p.revealed:
                for card in stockpile_copy:
                    if c2m(card) == c2m(c):
                        cards_moved_from_stockpile.append(card)
                        stockpile_copy.remove(card)
                        break

            for c in cards_moved_from_stockpile:
                gtrutils.move_card(given_card, p.stockpile, leg_p.stockpile)

            self.log('{0} gives cards from their stockpile: {1}'
                .format(p.name, ', '.join(cards_moved_from_stockpile)))

        clientele_copy = list(p.clientele)
        cards_moved_from_clientele = []
        if has_coliseum:
            for c in leg_p.revealed:
                for card in clientele_copy:
                    if c2m(card) == c2m(c):
                        cards_moved_from_clientele.append(card)
                        clientele_copy.remove(given_card)
                        break

            for c in cards_moved_from_clientele:
                gtrutils.move_card(given_card, p.clientele, leg_p.vault)

            self.log('{0} feeds clientele to the lions: {1}'
                .format(p.name, ', '.join(cards_moved_from_clientele)))


    def perform_merchant_action(self, player):
        self.game_state.active_player = player
        self.game_state.expected_action = message.MERCHANT


    def handle_merchant(self, a):
        stockpile_card, hand_card, from_deck = a.args

        p = self.game_state.active_player

        if stockpile_card and stockpile_card not in p.stockpile:
            raise GTRError('Card {0!s} not found in {1}\'s stockpile.'
                .format(stockpile_card, p.name))

        if hand_card and hand_card not in p.hand:
            raise GTRError('Card {0!s} not found in {1}\'s hand.'
                .format(hand_card, p.name))

        if stockpile_card and from_deck:
            raise GTRError('Can\'t merchant from deck and from stockpile.')

        n_cards = int(stockpile_card is not None) + \
                  int(hand_card is not None) + \
                  int(from_deck)

        if n_cards + len(p.vault) > self.get_vault_limit(p):
            raise GTRError('Not enough room in {0}\'s vault for {1:d} cards.'
                .format(p.name, n_cards))

        if stockpile_card:
            gtrutils.move_card(stockpile_card, p.stockpile, p.vault)

        if hand_card:
            gtrutils.move_card(hand_card, p.hand, p.vault)

        if from_deck:
            gtrutils.add_card_to_zone(self.game_state.draw_cards(1)[0], player.vault)

        # Logging
        if stockpile_card:
            self.log(('{0} performs Merchant, selling a {1!s} from the stockpile'
                      + ' and a card from their hand.' if hand_card else '.')
                      .format(p.name, stockpile_card))
        elif from_deck:
            self.log(('{0} performs Merchant, selling a card from the deck'
                      + ' and a card from their hand.' if hand_card else '.')
                      .format(p.name))
        elif hand_card:
            self.log('{0} performs Merchant, selling a card from their hand.'
                .format(p.name))
        else:
            self.log('{0} skips Merchant action.')

        self.pump()


    def kids_in_pool(self):
        """ Place cards in camp into the pool.
        1) If Sewer, ask to move cards into stockpile.
        2) If dropping a Jack, ask players_with_senate in order.
        """
        self.log('Kids in the pool.')
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

            self.log('{0} takes {1}\'s Jack with Senate.'
                .format(p.name, p_kip.name))

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

            self.log('{0} flushes cards down the Sewer: {1}'
                .format(p.name, ', '.join(cards)))

        for c in p.camp:
            if c.name == 'Jack':
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
        self.log('Game over.')
        for p in self.game_state.players:
            lg.info('Score for player {} : {}'.format(p.name, self.get_player_score(p)))
            self.log('Score for player {} : {}'.format(p.name, self.get_player_score(p)))
        lg.info('\n')
        raise GTRError('Game over.')


    def resolve_building(self, player, building_obj):
        """Switch on completed building to resolve the "On Completion" effects.
        """
        if str(building_obj) == 'Catacomb':
            self.log('{0} completed Catacomb, ending the game immediately.'
                .format(player.name))

            self.end_game()

        elif str(building_obj) == 'Foundry':
            n = player.get_influence_points()

            self.log('{0} completed Foundry, performing {1} Laborer actions.'
                .format(player.name, n))

            for _ in range(n):
                self.game_state.stack.push_frame('perform_laborer_action', player)

        elif str(building_obj) == 'Garden':
            n = player.get_influence_points()

            self.log('{0} completed Garden, performing {1} Patron actions.'
                .format(player.name, n))

            for _ in range(n):
                self.game_state.stack.push_frame('perform_patron_action', player)

        elif str(building_obj) == 'School':
            n = player.get_influence_points()

            self.log('{0} completed School, think {1} times.'
                .format(player.name, n))

            for _ in range(n):
                self.game_state.stack.push_frame('perform_optional_thinker_action', player)

        elif str(building_obj) == 'Amphitheatre':
            n = player.get_influence_points()

            self.log('{0} completed Amphitheatre, performing {1} Craftsman actions.'
                .format(player.name, n))

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
        lg.debug('Loaded game state.')
        return game_state


    def handle(self, a):
        """ Switchyard to handle game actions.
        """
        lg.debug('Handling action: ' + repr(a))
        if a.action != self.expected_action():
            raise Exception('Expected GameAction type: ' + str(self.expected_action())
                + ', got: ' + repr(a))

        method_name = 'handle_' + str(a)

        try:
            method = getattr(self, method_name)
        except AttributeError:
            raise Exception('Unhandled GameAction type: ' + str(a.action))
        else:
            # TODO: We should catch this in GTRServer where it calls this.
            # The server class can decide what to do with illegal actions.
            try:
                method(a)
            except GTRError as e:
                lg.debug('Error handling action')
                lg.debug(str(e))
                return

            self.game_state.game_id += 1
