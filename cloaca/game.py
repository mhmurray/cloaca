from cloaca.player import Player
import cloaca.gtrutils as gtrutils
from cloaca.building import Building
from cloaca.card import Card
from cloaca.zone import Zone
from cloaca.error import GTRError, GameOver
import cloaca.stack
import cloaca.card_manager as cm

import random
import copy
from collections import Counter
import logging
import message
from datetime import datetime
import itertools

lg = logging.getLogger(__name__)
lg.addHandler(logging.NullHandler())

class Game(object):
    """Controls the operation of a single game.

    The game_state attribute stores all the information about an ongoing game
    in the GameState class. The methods here handle GameAction inputs from
    players and manipulation of the game state.

    Game.add_player(uid, username) adds a player with the User id and their
    username.

    Game.start() starts the game, dealing cards to each player, setting up
    the game components, and queueing up the first turn.

    Game.controlled_start() is a way to start the game useful for testing. See
    the function docs.

    Game.handle(game_action) takes a GameAction object as user input and executes
    the subsequent game rules. It raises a GTRError if there is any trouble
    performing the action.
    
    """
    _initial_jack_count = 6

    leader = property(lambda self : self.players[self.leader_index])
    started = property(lambda self : self.turn_number > 0)
    finished = property(lambda self : self.winners is not None)

    def __init__(self, game_id=0, players=None, leader_index=None,
            turn_number=0, role_led=None, active_player_index=None,
            jacks=None, library=None, pool=None, in_town_sites=None,
            out_of_town_sites=None, oot_allowed=False, used_oot=False,
            stack=None, legionary_count=0, legionary_player_index=None,
            expected_action=None, host='', winners=None, action_number=0,
            current_frame=None, game_log=None):
        """
        Initialize Game object. Summary of arguments:

            game_id -- (int) unique game number
            players -- (list of Player objects)
            leader_index -- (int) index of current leader or None.
            turn_number -- (int)
            role_led -- (string) Role led or None (e.g. 'Craftsman')
            active_player_index -- (int) index of active player or None
            jacks -- (iterable of Card objects)
            library -- (iterable of Card objects)
            pool -- (iterable of Card objects)
            in_town_sites -- (iterable of strings) sites are strings,
                e.g. ['Rubble', 'Rubble', 'Brick']
            out_of_town_sites -- (iterable of strings) sites are strings,
                e.g. ['Rubble', 'Rubble', 'Brick']
            oot_allowed -- (boolean) out-of-town construction is allowed
                by the next building action
            used_oot -- (boolean) used out-of-town construction in the last
                building action
            stack -- (Stack object) stack of Frames objects for pending actions
            legionary_count -- (int) count of number of Legionary actions
                the active player is responding to
            legionary_player_index -- (int) index of player demanding with Legionary.
            expected_action -- (int) message.GameAction index of expected action
                by active player, or None.
            host -- (str) user name of game host
            winners -- (iterable of Player objects) players that have won the game
                or empty list
            action_number -- (int) number of actions that have been executed this game
            current_frame -- (Frame object) Frame that is currently being executed
            game_log -- (list of strings) log messages as list of string
        """
        self.game_id = game_id
        self.players = [] if players is None else players
        self.leader_index = leader_index
        self.turn_number = turn_number
        self.role_led = role_led
        self.active_player_index = active_player_index
        self.jacks = Zone([] if jacks is None else jacks, name='jacks')
        self.library = Zone([] if library is None else library, name='library')
        self.pool = Zone([] if pool is None else pool, name='pool')
        self.in_town_sites = [] if in_town_sites is None else in_town_sites
        self.out_of_town_sites = [] if out_of_town_sites is None else out_of_town_sites
        self.oot_allowed = oot_allowed
        self.used_oot = used_oot
        self.stack = cloaca.stack.Stack() if stack is None else stack
        self.legionary_count = legionary_count
        self.legionary_player_index = legionary_player_index
        self.expected_action = expected_action
        self.host = '' if host is None else host
        self.winners = [] if winners is None else winners
        self.action_number = action_number

        # Keep track of currently-executing stack frame.
        self._current_frame = current_frame

        self.game_log = [] if game_log is None else game_log

    @property
    def active_player(self):
        return self.players[self.active_player_index]

    @active_player.setter
    def active_player(self, player):
        self.active_player_index = self.players.index(player)

    @property
    def legionary_player(self):
        return self.players[self.legionary_player_index]

    @legionary_player.setter
    def legionary_player(self, player):
        self.legionary_player_index = self.players.index(player)

    def start(self):
        if self.started:
            raise GTRError('Game has already started.')

        self._init_common_piles(len(self.players))
        self._init_player_hands()
        self.stack.push_frame('_take_turn_stacked', self.active_player)
        self.turn_number = 1

        self._log('Starting game.')
        self._log('Turn {0}: {1}'
            .format(self.turn_number,
                    self.leader.name))

        self._pump()

    def controlled_start(self):
        """Start the game with modified, deterministic rules.

        The first player in the list goes first, cards are not
        dealt into the pool. Both players start with empty hands.

        The deck of Orders cards is still random, however.
        """
        if self.started:
            raise GTRError('Game has already started.')

        self._init_library()

        self.active_player = self.players[0]
        self.leader_index = 0

        self.jacks.set_content([Card(i) for i in range(Game._initial_jack_count)])
        self._init_sites(len(self.players))

        self.stack.push_frame('_take_turn_stacked', self.active_player)
        self.turn_number = 1

        self._log('Starting game.')
        self._log('Turn {0}: {1}'
            .format(self.turn_number,
                    self.leader.name))

        self._pump()

    def add_player(self, uid, name):
        """Adds a player to the game. Raises GTRError if game is started,
        full, or player already is in the game.
        """
        if self._find_player(name) is not None:
            raise GTRError('Cannot add player to same game twice: {0}'
                    .format(name))

        if self.started:
            raise GTRError('Cannot add player after game start.')

        n = len(self.players)
        if n >= 5:
            raise GTRError('Maximum players reached for this game {0}/{0}'
                    .format(n))

        lg.debug('Adding player {0}.'.format(name))

        self.players.append(Player(uid, name))
        self._log('{0} has joined the game.'.format(name))

    def handle(self, a):
        """ Switchyard to handle game actions.
        """
        lg.debug('Handling action: ' + repr(a))
        if a.action != self.expected_action:
            raise GTRError('Expected GameAction type: ' + str(self.expected_action)
                + ', got: ' + repr(a))

        method_name = '_handle_' + str(a)

        try:
            method = getattr(self, method_name)
        except AttributeError:
            raise GTRError('Unhandled GameAction type: ' + str(a.action))
        else:
            # TODO: We should catch this in GTRServer where it calls this.
            # The server class can decide what to do with illegal actions.
            try:
                method(a)
            except GTRError as e:
                lg.debug('Error handling action: '+e.message)
                raise


    def privatized_game_state_copy(self, player_name):
        """Change card names to 'Card' in order to represent a game
        visible by player_name. Hide the library, vault, and other
        players' hands, as well as the revealed card for a Fountain.

        Do not hide Jacks in hand.
        
        Don't hide anything if the game is over.

        Return a new game state object
        """
        gs = copy.deepcopy(self)

        if self.winners is None or not len(self.winners):

            gs.library.set_content([Card(-1)]*len(gs.library))

            for p in gs.players:
                p.vault.set_content([Card(-1)]*len(p.vault))

                if p.name != player_name:
                    p.hand.set_content(sorted(
                            [c if c.name == 'Jack' else Card(-1) for c in p.hand],
                            cmp=cm.cmp_jacks_first_alphabetical_by_material))

                    p.fountain_card = Card(-1) if p.fountain_card else None
                    p.revealed.set_content([cm.get_card(c.name) for c in p.revealed])
                    p.prev_revealed.set_content([cm.get_card(c.name) for c in p.prev_revealed])

        return gs

    def find_player_index(self, player_name):
        """Finds the index of a named player.
        """
        players_match = [i for i,p in enumerate(self.players)
                         if p.name==player_name]
        return players_match[0] if len(players_match) else None

    def _find_players_building(self, foundation):
        """Return (player, building) with specified foundation Card.
        """
        for p in self.players:
            try:
                b = p.get_building(foundation)
            except GTRError:
                continue
            else:
                return p, b

        return None, None

    def _find_player(self, name):
        """Return the Player object with the specified name or None if no
        such player is in the game.
        """
        players_match = filter(lambda x : x.name == name, self.players)
        return players_match[0] if len(players_match) else None

    def _increment_leader_index(self):
        prev_index = self.leader_index
        self.leader_index = self.leader_index + 1
        if self.leader_index >= len(self.players):
            self.leader_index = 0
        lg.debug('Leader index changed from {0} to {1}'.format(prev_index,
        self.leader_index))

    def _following_players_in_order(self):
        """Return a list of players in turn order starting with
        the next player after the leader, and ending with the player
        before the leader. This is players_in_turn_order()
        with the leader removed.
        """
        n = self.leader_index
        return self.players[n+1:] + self.players[:n]

    def _players_in_turn_order(self, start_player=None):
        """ Returns a list of players in turn order
        starting with start_player or the leader it's None.
        """
        n = self.players.index(start_player) \
            if start_player else self.leader_index

        return self.players[n:] + self.players[:n]

    def _init_common_piles(self, n_players):
        self._log('Initializing the game')

        self._init_library()
        first_player_index = self._init_pool(n_players)

        self.active_player = self.players[first_player_index]
        self.leader_index = first_player_index
        self.jacks = Zone([Card(i) for i in range(Game._initial_jack_count)])
        self._init_sites(n_players)

    def _init_pool(self, n_players):
        """Deals one card to each player and place the cards in the pool.

        Return the player index that goes first.
        """
        all_cards = Zone()
        has_winner = False
        player_indices = range(n_players)
        while not has_winner:
            # Make list of (player, card) pairs
            cards = [(i,self._draw_cards(1)[0]) for i in player_indices]
            first = min(cards, key=lambda x : x[1])
            player_indices = [c[0] for c in cards if c[1].name == first[1].name]
            all_cards.extend([c[1] for c in cards])

            s = ' '.join(['{0} reveals {1!s}.'.format(self.players[i].name, card)
                         for i, card in cards])
            self._log(s)

            if len(player_indices)==1:
                has_winner = True
                self._log('{0} plays first.'.format(self.players[player_indices[0]].name))
            else:
                self._log('Deal more cards into pool to break tie.')

        self.pool.extend(all_cards)
        return player_indices[0]

    def _init_sites(self, n_players):
        n_out_of_town = 6 - n_players
        for material in cm.get_all_materials():
            self.in_town_sites.extend([material]*n_players)
            self.out_of_town_sites.extend([material]*n_out_of_town)

    def _init_library(self):
        """Initializes the library as a list of Card objects
        """
        self.library.set_content(cm.get_orders_card_set())
        self._shuffle_library()

    def _init_player_hands(self):
        lg.info('Initializing {0} players.'.format(len(self.players)))
        for player in self.players:
            self._draw_jack_for_player(player)
            self._thinker_for_cards(player, 5)

    def _shuffle_library(self):
        """ Shuffles the library.

        random.shuffle has a finite period, which is apparently 2**19937-1.
        This means lists of length >~ 2080 will not get a completely random
        shuffle. See the SO question
          http://stackoverflow.com/questions/3062741/maximal-length-of-list-to-shuffle-with-python-random-shuffle
        """
        random.shuffle(self.library.cards)

    def _player_score(self, player):
        return self._buildings_score(player) + self._vault_score(player)

    def _buildings_score(self, player):
        """ Add up the score from this players buildings.
        This includes the influence gained by sites, including payment
        from a Prison, and points from Statue and Wall.
        """
        influence_pts = player.influence_points
        statue_pts = 0
        if self._player_has_active_building(player, 'Statue'):
            statue_pts = 3

        wall_pts = 0
        if self._player_has_active_building(player, 'Wall'):
            wall_pts = len(player.stockpile) // 2

        return influence_pts + statue_pts + wall_pts

    def _vault_score(self, player):
        """ Examines all players' vaults to determine the vault
        score for each player, including the merchant bonuses.
        """
        bonuses = {}
        for a_player in self.players:
            bonuses[a_player.name] = []

        for material in cm.get_materials():
            # Set name to None if there's a tie, but maintain maximum
            name, maximum = None, 0
            for a_player in self.players:
                material_cards = filter(
                    lambda c : c.material == material, a_player.vault)
                n = len(material_cards)
                if n > maximum:
                    name = a_player.name
                    maximum = n
                elif n == maximum:
                    name = None
                    maximum = n
            if name:
                bonuses[name].append(material)

        bonus_pts = 3*len(bonuses[player.name])

        card_pts = 0
        for card in player.vault:
            card_pts += card.value

        return card_pts + bonus_pts

    def _clientele_limit(self, player):
        has_insula = self._player_has_active_building(player, 'Insula')
        has_aqueduct = self._player_has_active_building(player, 'Aqueduct')
        limit = player.influence_points

        if has_insula: limit += 2
        if has_aqueduct: limit *= 2
        return limit

    def _vault_limit(self, player):
        has_market = self._player_has_active_building(player, 'Market')
        limit = player.influence_points

        if has_market: limit += 2
        return limit

    def _player_has_active_building(self, player, building):
        """True if the building is active for the player.

        Args:
        player -- Player object
        building -- string
        """
        return building in self._active_building_names(player)

    def _active_building_names(self, player):
        """Returns a list of building names that are active for a player,
        taking the effect of the Stairway into account. See the
        _active_buildings(player) method for reference, but note that
        this method does not return duplicate names.
        """

        names = map(str, self._active_buildings(player))
        return list(set(names))

    def _active_buildings(self, player):
        """Returns a list of all Building objects that are active for a player.

        This includes:
            - Complete buildings owned by this player.
            - Incomplete Marble buildings owned by this player if Gate is active.
            - Complete buildings owned by other players if they have been
            stairwayed. 

        First we build a list of buildings active because of the stairway.
        Next, add complete buildings owned by the player.
        Finally, add in incomplete marble buildings owned by the player.

        Since multiple players can have a building with a Stairway activation,
        this list might contain buildings with the same name.
        """
        _active_buildings = player.complete_buildings
        for player_ in self.players:
            _active_buildings.extend(player_.stairwayed_buildings)

        b = next( (b for b in _active_buildings if b.foundation.name == 'Gate'), None)
        if b is not None:
            incomplete_marble = [b for b in player.incomplete_buildings if
                                 b.composed_of('Marble')]
            _active_buildings.extend(incomplete_marble)

        return _active_buildings


    def _await_action(self, action, active_player):
        """Sets the game in a state to await a call to handle()
        for the active_player and the specific action. 
        Increments the Game.action_number, so this must be used for
        all cases where we're waiting for a player.
        
        For example:

            self._await_action(message.GIVECARDS, player)

        This exists because these are frequently placed on the stack,
        requiring a function.
        """
        self.expected_action = action
        self.active_player = active_player
        self.action_number += 1


    def _handle_thinkerorlead(self, a):
        do_thinker = a.args[0]

        if not do_thinker:
            # my_list[::-1] reverses the list
            for p in self._players_in_turn_order()[::-1]:
                self.stack.push_frame("_perform_role_being_led", p)
            for p in self._following_players_in_order()[::-1]:
                self.stack.push_frame("_await_action", message.FOLLOWROLE, p)
            self.stack.push_frame("_await_action", message.LEADROLE, self.leader)

        else:
            self.stack.push_frame("_perform_thinker_action", self.leader)

        self._pump()

    def _thinker_for_cards(self, player, max_hand_size):
        n_cards = max_hand_size - len(player.hand)
        if n_cards < 1: n_cards = 1
        lg.debug(
            'Adding {0} cards to {1}\'s hand'.format(n_cards, player.name))
        drawn_cards = self._draw_cards(n_cards)
        player.hand.extend(drawn_cards)
        return len(drawn_cards)

    def _draw_jack_for_player(self, player):
        player.hand.append(self._draw_jack())

    def _discard_for_player(self, player, card):
        if card.name == 'Jack':
            player.hand.move_card(card, self.jacks)
        else:
            player.hand.move_card(card, self.pool)

    def _discard_all_for_player(self, player):
        # Make copy of hand because we're modifying it.
        for card in list(player.hand):
            self._discard_for_player(player, card)

    def _draw_jack(self):
        try:
            c = self.jacks.pop()
        except IndexError:
            raise GTRError('Jack pile is empty.')

        return c

    def _draw_cards(self, n_cards):
        """Draws up to n_cards, less if the deck doesn't have that many cards.
        """
        cards = []
        for i in range(0, n_cards):
            try:
                card = self.library.pop(0)
            except IndexError:
                break
            else:
                cards.append(card)

        return cards

    def _log(self, msg):
        """Logs the message in the GameState log roll.
        """
        time = datetime.now().time().strftime('%H:%M:%S ')
        self.game_log.append(time+msg)
        lg.debug(time+msg)

    def _pump(self):
        """Pop the top frame from the stack into self._current_frame
        and execute the function.
        """
        if self.stack.stack:
            try:
                self._current_frame = self.stack.stack.pop()
            except IndexError:
                lg.warning('Tried to pop from empty stack!')
                raise

            lg.debug('Execute next stack frame: ' + repr(self._current_frame))

            func = getattr(self, self._current_frame.function_name)
            func.__call__(*self._current_frame.args)

    def _advance_turn(self):
        """Advance turn and leader markers.
        """
        self.turn_number += 1
        self._increment_leader_index()
        leader_index = self.leader_index
        leader = self.players[leader_index]
        self.stack.push_frame('_take_turn_stacked', leader)

        self._log('Turn {0}: {1}'.format(self.turn_number, leader.name))

        self._pump()

    def _take_turn_stacked(self, player):
        """
        Push ADVANCE_TURN frame.
        Push END_TURN frame.
        Push THINKER_OR_LEAD frame.
        """
        self.stack.push_frame("_advance_turn")
        self.stack.push_frame("_end_turn")
        self.stack.push_frame("_kids_in_pool")
        self.stack.push_frame("_await_action", message.THINKERORLEAD, player)

        self._pump()

    def _max_hand_size(self, player):
        max_hand_size = 5
        if self._player_has_active_building(player, 'Shrine'):
            max_hand_size += 2
        if self._player_has_active_building(player, 'Temple'):
            max_hand_size += 4

        return max_hand_size


    def _handle_skipthinker(self, a):
        skip = a.args[0]

        p = self.active_player

        if skip:
            self._log('{0} skips thinker action.'.format(p.name))
            self._pump()

        else:
            self._perform_thinker_action(self.leader)


    def _perform_thinker_action(self, player):
        """ Entry point for the stack frame that performs one thinker action.
        """
        if self._player_has_active_building(player, 'Vomitorium'):
            self._await_action(message.USEVOMITORIUM, player)

        else:
            a = message.GameAction(message.USEVOMITORIUM, False)
            self._handle_usevomitorium(a)


    def _handle_usevomitorium(self, a):
        """ Handle using a Vomitorium to discard hand.

        This is either called on a client response, or directly
        from perform_craftsman if the player doesn't have a Vomitorium.

        If the player doesn't have a latrine or the vomitorium is used,
        call _handle_uselatrine() to skip the latrine usage.
        Otherwise, ask for latrine use and return.
        """
        p = self.active_player

        do_discard = a.args[0]
        if do_discard:
            self._log('{0} discards their entire hand with Vomitorium: {1}.'
                .format(p.name, ', '.join(map(str, p.hand))))

            self._discard_all_for_player(p)
            a = message.GameAction(message.USELATRINE, None)
            self._handle_uselatrine(a)

        elif self._player_has_active_building(p, 'Latrine'):
            self._await_action(message.USELATRINE, p)

        else:
            a = message.GameAction(message.USELATRINE, None)
            self._handle_uselatrine(a)


    def _handle_uselatrine(self, a):
        p = self.active_player
        latrine_card = a.args[0]

        if latrine_card is not None:
            self._discard_for_player(p, latrine_card)
            self._log('{0} discards {1} using Latrine.'
                .format(p.name, latrine_card))

        self._await_action(message.THINKERTYPE, p)


    def _handle_thinkertype(self, a):
        p = self.active_player
        for_jack = a.args[0]

        is_leader = p == self.leader

        if for_jack:
            self._draw_jack_for_player(p)

            if is_leader:
                self._log('{0} thinks for a Jack.'.format(p.name))
            else:
                self._log('{0} thinks for a Jack instead of following.'.format(p.name))

        else:
            n_cards = self._thinker_for_cards(p, self._max_hand_size(p))

            #n_cards = max(1, self._max_hand_size(p) - len(p.hand))
            noun = 'cards' if n_cards > 1 else 'card'

            if is_leader:
                self._log('{0} thinks for {1} {2}.'.format(p.name, n_cards, noun))
            else:
                self._log('{0} thinks for {1} {2} instead of following.'
                    .format(p.name, n_cards, noun))

            self._check_library_empty()

        self._pump()


    def _check_library_empty(self):
        """Calls _end_game() if the library is empty.
        """
        if len(self.library) == 0:
            self._log('The last Orders card has been drawn from the deck. Game Over.')
            self._end_game()
            


    def _handle_leadrole(self, a):
        p = self.leader

        role, n_actions = a.args[0:2]
        cards = a.args[2:]

        # This will raise GTRError if the cards don't check out.
        self._check_action_units(p, role, n_actions, cards)

        if not p.hand.contains(cards):
            raise GTRError('Cards specified to lead role not in hand: {0}.'
                .format(', '.join(map(str, cards))))

        self.role_led = role
        p.n_camp_actions = n_actions
        for c in cards:
            p.hand.move_card(c, p.camp)

        if n_actions > 1:
            self._log('{0} leads {1} for {2} actions using: {3}'
                    .format(p.name, role, n_actions, ', '.join(map(str, cards))))
        else:
            self._log('{0} leads {1} using: {2}'
                    .format(p.name, role, ', '.join(map(str, cards))))

        self._pump()


    def _check_action_units(self, player, role_led, n_actions, cards):
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
        
        has_palace = self._player_has_active_building(player, 'Palace')
        has_circus = self._player_has_active_building(player, 'Circus')

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
        if not gtrutils.check_petition_combos(n_left, n_on, n_off_list,
                has_circus, True):
            raise invalid_combo_error
        

    def _handle_followrole(self, a):
        n_actions = a.args[0]
        cards = a.args[1:]

        p = self.active_player

        think = n_actions == 0

        if think and len(cards)>0:
            raise GTRError('Thinker (n_actions == 0) requested but cards received ({0}).'
                    .format(', '.join(map(str, cards))))

        if think:
            p.n_camp_actions = 0
            self.stack.push_frame("_perform_thinker_action", p)
        else:
            # This will raise GTRError if the cards don't check out.
            self._check_action_units(p, self.role_led, n_actions, cards)

            # Check if cards exist in hand
            if not p.hand.contains(cards):
                raise GTRError('Not all cards specified exist in hand.')

            p.n_camp_actions = n_actions
            for c in cards:
                p.hand.move_card(c, p.camp)

            if n_actions > 1:
                self._log('{0} follows for {1} actions using: {2}'
                        .format(p.name, n_actions, ', '.join(map(str, cards))))
            else:
                self._log('{0} follows using: {1}'
                        .format(p.name, ', '.join(map(str, cards))))

        self._pump()


    def _player_client_count(self, player, role):
        """Return the number of active clients this player has of the specified
        role, accounting for Storeroom, but not Ludus Magna.

        This does not count doubling of clientele actions with Circus Maximus, 
        since the number of *clients* is returned, not the number of *client actions*.

        If role is None, return the size of clientele.
        """
        if role is None:
            n_clients = len(player.clientele)
        elif role == 'Laborer' and self._player_has_active_building(player, 'Storeroom'):
            n_clients = len(player.clientele)
        else:
            n_clients = len(filter(lambda c: c.role == role, player.clientele))

            # Ludus Magna adds to any non-Merchant count.
#            if role != 'Merchant' and self._player_has_active_building(player, 'Ludus Magna'):
#                n_clients += len(filter(lambda c: c.role == 'Merchant', player.clientele))

        return n_clients



    def _perform_role_being_led(self, player):
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
        role = self.role_led
        self._log('{0} is performing {1}'.format(player.name, role))

        # Reset used_oot flag. It can linger if prev. player started oot with Tower.
        self.used_oot = False

        n_merchants = self._player_client_count(player, 'Merchant')
        n_role = self._player_client_count(player, role)

        if role != 'Merchant':
            for _ in range(n_merchants):
                self.stack.push_frame('_perform_clientele_action', player, 'Merchant')

        for _ in range(n_role):
            self.stack.push_frame('_perform_clientele_action', player, role)

        for _ in range(player.n_camp_actions):
            self.stack.push_frame('_perform_role_action', player, role)

        self._pump()


    def _perform_clientele_action(self, player, role):
        role_led = self.role_led
        has_ludus = self._player_has_active_building(player, 'Ludus Magna')
        has_cm = self._player_has_active_building(player, 'Circus Maximus')
        is_leading_or_following = player.is_following_or_leading


        if role == 'Merchant' and role_led != 'Merchant':
            if has_ludus:
                self.stack.push_frame('_perform_role_action', player, role_led)
                if has_cm and is_leading_or_following:
                    self.stack.push_frame('_perform_role_action', player, role_led)
            # Skip Merchant if that's not the role being led and no Ludus
        else:
            self.stack.push_frame('_perform_role_action', player, role)
            if has_cm and is_leading_or_following:
                self.stack.push_frame('_perform_role_action', player, role)

        self._pump()


    def _check_oot_allowed(self, player):
        """Checks if the player can start a site out of town. Here are the
        conditions for oot being allowed:

            - There is another perform_role_action stack frame below this with the
            same player.

            - A perform_clientele_action frame of the same role and player.

            - A perform_clientele_action frame of same player, and role Merchant
            and we have a Ludus Magna.

            - We have a Tower.

        This checks the top stack frame, so call this after popping the action
        in which you want to know if out-of-town is allowed.

        Returns True if starting out of town is allowed, False otherwise.
        """
        if self._player_has_active_building(player, 'Tower'):
            return True

        has_ludus = self._player_has_active_building(player, 'Ludus Magna')

        current_function = self._current_frame.function_name
        if current_function != '_perform_role_action':
            lg.warning('Called _check_oot_allowed during action: {0}'
                    .format(current_function))
            return False

        current_player = self._current_frame.args[0]
        if current_player.name != player.name:
            lg.warning('Called _check_oot_allowed for wrong player.')
            return False

        current_role = self._current_frame.args[1]

        f = self.stack.stack[-1]

        # Args are (player, role)
        if f.function_name == '_perform_role_action':
            p, role = f.args

            if p.name == player.name and role == current_role:
                return True

        if f.function_name == '_perform_clientele_action':
            p, role = f.args

            if p.name == player.name and \
                    ((role=='Merchant' and has_ludus) or role == current_role):
                return True

        return False


    def _perform_role_action(self, player, role):
        """Multiplexer function for arbitrary roles.

        Calls perform_<role>_action(), etc.

        This also handles the GameState.oot_used flag. The flag indicates that
        a Craftsman or Architect started a building on an out-of-town site.
        This will skip the action if the player doesn't have a tower.
        """
        has_tower = self._player_has_active_building(player, 'Tower')
        used_oot = self.used_oot

        self.used_oot = False
        if not used_oot or (used_oot and has_tower):

            self.oot_allowed = self._check_oot_allowed(player)

            if role=='Patron':
                self._perform_patron_action(player)
            elif role=='Laborer':
                self._await_action(message.LABORER, player)
                return
            elif role=='Architect':
                self._await_action(message.ARCHITECT, player)
                return
            elif role=='Craftsman':
                self._perform_craftsman_action(player)
            elif role=='Legionary':
                self._perform_legionary_action(player)
            elif role=='Merchant':
                self._await_action(message.MERCHANT, player)

            else:
                raise ValueError('Illegal role: {0}'.format(role))

        else:
            self._pump()


    def _handle_laborer(self, a):
        cards = a.args

        p = self.active_player

        hand_cards = [c for c in cards if c in p.hand]
        pool_cards = [c for c in cards if c in self.pool]

        if len(hand_cards)>1:
            raise GTRError('Received too many cards from {0}\'s hand ({1})'
                       .format(p.name, ', '.join(map(str, hand_cards))))

        if len(pool_cards)>1:
            raise GTRError('Received too many cards from the pool ({0})'
                       .format(', '.join(map(str, hand_cards))))

        if len(cards) > len(hand_cards) + len(pool_cards):
            raise GTRError('Received cards not in pool or hand.')

        pool_c = pool_cards[0] if pool_cards else None
        hand_c = hand_cards[0] if hand_cards else None

        if pool_c is not None and pool_c not in self.pool:
            raise GTRError('Tried to move non-existent card {0} from pool'
                       .format(pool_c))

        if hand_c is not None and hand_c not in p.hand:
            raise GTRError('Tried to move non-existent card {0} from hand'
                       .format(hand_c))

        if hand_c is not None and not self._player_has_active_building(p, 'Dock'):
            raise GTRError('Tried to Laborer from hand without Dock.');

        if pool_c:
            self.pool.move_card(pool_c, p.stockpile)
        if hand_c:
            p.hand.move_card(hand_c, p.stockpile)

        if hand_c:
            self._log('{0} performs Laborer from pool: {1} and hand: {2}.'
                    .format(p.name, pool_c, hand_c))
        else:
            self._log('{0} performs Laborer from pool: {1}'
                    .format(p.name, pool_c))

        self._pump()


    def _perform_patron_action(self, player):
        has_bar = self._player_has_active_building(player, 'Bar')
        has_aqueduct = self._player_has_active_building(player, 'Aqueduct')

        if has_bar and has_aqueduct:
            self.stack.push_frame('_await_action', message.BARORAQUEDUCT, player)

        else:
            if has_bar:
                self.stack.push_frame('_await_action', message.PATRONFROMDECK, player)
            if has_aqueduct:
                self.stack.push_frame('_await_action', message.PATRONFROMHAND, player)

        self._await_action(message.PATRONFROMPOOL, player)


    def _handle_baroraqueduct(self, a):
        bar_first = a.args[0]

        p = self.active_player

        if bar_first:
            self.stack.push_frame('_await_action', message.PATRONFROMHAND, p)
            self.stack.push_frame('_await_action', message.PATRONFROMDECK, p)
        else:
            self.stack.push_frame('_await_action', message.PATRONFROMDECK, p)
            self.stack.push_frame('_await_action', message.PATRONFROMHAND, p)

        self._pump()


    def _handle_patronfrompool(self, a):
        try:
            card = a.args[0]
        except IndexError:
            card = None

        p = self.active_player

        if card is not None:
            if len(p.clientele) >= self._clientele_limit(p):
                raise GTRError(p.name + ' has no room in clientele')

            self.pool.move_card(card, p.clientele)
            self._check_library_empty()

            if self._player_has_active_building(p, 'Bath'):
                #TODO: Does Ludus Magna help with Bath. What about Circus Maximus?
                self.stack.push_frame('_perform_role_action', p, card.role)
                self._log(
                    '{0} performs Patron, hiring {1} from pool and performing {2} using Bath.'
                    .format(p.name, card, card.role))

            else:
                self._log(
                    '{0} performs Patron, hiring {1} from pool.'
                    .format(p.name, card))

            self._check_forum()

        self._pump()


    def _handle_patronfromdeck(self, a):
        do_patron = a.args[0]

        p = self.active_player

        if do_patron:
            if len(p.clientele) >= self._clientele_limit(p):
                raise GTRError(p.name + ' has no room in clientele')

            card = self._draw_cards(1)[0]
            gtrutils.add_card_to_zone(card, p.clientele)

            if self._player_has_active_building(p, 'Bath'):
                #TODO: Does Ludus Magna help with Bath. What about Circus Maximus?
                self.stack.push_frame('_perform_role_action', p, card.role)
                self._log(
                    '{0} performs Patron, hiring {1} from deck and performing {2} using Bath.'
                    .format(p.name, card, card.role))

            else:
                self._log(
                    '{0} performs Patron, hiring {1} from deck.'
                    .format(p.name, card))

            self._check_forum()
            self._check_library_empty()

        self._pump()


    def _handle_patronfromhand(self, a):
        try:
            card = a.args[0]
        except IndexError:
            card = None

        p = self.active_player

        if card is not None:
            if len(p.clientele) >= self._clientele_limit(p):
                raise GTRError(p.name + ' has no room in clientele')

            p.hand.move_card(card, p.clientele)

            if self._player_has_active_building(p, 'Bath'):
                #TODO: Does Ludus Magna help with Bath. What about Circus Maximus?
                self.stack.push_frame('_perform_role_action', p, card.role)
                self._log(
                    '{0} performs Patron, hiring {1} from hand and performing {2} using Bath.'
                    .format(p.name, card, card.role))

            else:
                self._log(
                    '{0} performs Patron, hiring {1} from hand.'
                    .format(p.name, card))

            self._check_forum()

        self._pump()


    def _check_forum(self):
        """Checks all players for a Forum win. It's possible for multiple players
        to have a Forum win if it's Stairway, so we have to check everyone.
        """
        forum_winners = []
        for p in self.players:
            if self._player_has_active_building(p, 'Forum'):
                has_ludus = self._player_has_active_building(p, 'Ludus Magna')
                has_storeroom = self._player_has_active_building(p, 'Storeroom')

                # With a ludus, the extra Merchants count for missing roles.
                extra_merchant_count = 0
                roles = set()
                for c in p.clientele:
                    if c.role not in roles:
                        roles.add(c.role)
                    elif c.role == 'Merchant':
                        extra_merchant_count += 1
                    elif has_storeroom:
                        roles.add('Laborer')


                ludus_win = has_ludus and (len(roles) + extra_merchant_count) >= 6
                normal_win = len(roles) >= 6

                # We might have an extra merchant and no Ludus. That Merchant
                # should count with Storeroom
                storeroom_win = has_storeroom and \
                        (len(roles) + (1 if extra_merchant_count > 0 else 0)) >=6 

                if ludus_win or normal_win or storeroom_win:
                    forum_winners.append(p)

        if forum_winners:
            self._forum_win(forum_winners)


    def _check_building_start_legal(self, player, building, site):
        """ Checks if starting this building is legal. Accounts for Statue.
        The building parameter is just the name of the building.

        Raises GTRError if building start is illegal.
        """
        if site is None or building is None:
            raise GTRError('Illegal building / site ({0!s}/{1})'
                .format(building, site))

        if player.owns_building(building):
            raise GTRError('{0} already owns {1!s}.'.format(player.name, building))

        if site not in self.out_of_town_sites:
            raise GTRError('No {0} sites left, including out of town'
                .format(site))

        if site not in self.in_town_sites and \
                not self.oot_allowed:
            raise GTRError('Starting an out of town building is not allowed.')

        if not (building.material == site or building.name == 'Statue'):
            raise GTRError('Illegal building/site combination ({0!s}/{1}).'
                .format(building, site))

    def _check_building_add_legal(self, player, building, material_card):
        """ Checks if the specified player is allowed to add material
        to building. This accounts for the building material, the
        site material, a player's active Road, Scriptorium, and Tower.
        This does not handle Stairway, which is done in _perform_architect_action().

        This checks if the material is legal, but not if the building is already
        finished or malformed (eg. no site, or no foundation).

        Returns if the material add is allowed, and raises GTRError if not.
        """
        if material_card is None or building is None:
            raise GTRError('Illegal add: material={0!s} building={1!s}'
                .format(material_card, building_card))

        has_tower = self._player_has_active_building(player, 'Tower')
        has_road = self._player_has_active_building(player, 'Road')
        has_scriptorium = self._player_has_active_building(player, 'Scriptorium')

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


    def _perform_craftsman_action(self, player):
        self.active_player = player
        if self._player_has_active_building(player, 'Fountain'):
            self._await_action(message.USEFOUNTAIN, player)
        else:
            a = message.GameAction(message.USEFOUNTAIN, False)
            self._handle_usefountain(a)


    def _handle_usefountain(self, a):
        use_fountain = a.args[0]

        p = self.active_player

        if use_fountain:
            # Fountain allows the last card of the deck to be used, so 
            # check_library_empty is in _handle_fountain().
            p.fountain_card = self._draw_cards(1)[0]
            self._log('{0} looks at a card with Fountain.'
                .format(p.name))

            self._await_action(message.FOUNTAIN, p)

        else:
            self._await_action(message.CRAFTSMAN, p)


    def _handle_fountain(self, a):
        building, material, site = a.args

        skip = building is None

        p = self.active_player

        fountain_card = p.fountain_card

        if skip:
            self._log('{0} skips Fountain, drawing the card.'
                .format(p.name))
            p.hand.append(p.fountain_card)
            p.fountain_card = None
        else:
            # Construct moves the fountain card to foundation or materials and
            # sets player.fountain_card to None
            b = self._construct(p, building, material, site, None, fountain=True)
            self._log('{0} performs Craftsman using {1} with Fountain.'
                    .format(p.name, fountain_card.name))
            self._log_construct(p, building, material, site, ' using Fountain card')

            if b.complete:
                self._log('{0} completed.'.format(str(b)))
                self._resolve_building(p, b)

        self._check_library_empty()

        self._pump()


    def _log_construct(self, player, building, material, site, material_source=''):
        """Logs a _construct call, checking the site to see if this was a building
        start or an addition to a building. This can be used for Craftsman or
        Architect. An additional string material_source can be provided to indicate
        where the material card came from, eg. ' from hand'.

        Checks GameState.used_oot to log if the site was out-of-town.
        """

        if site is None:
            self._log('{0} adds {1} as material to {2}{3}.'
                .format(player.name, material, building, material_source))
        elif self.used_oot:
            self._log('{0} starts {1} on a {2} site, out of town.'
                .format(player.name, building, site))
        else:
            self._log('{0} starts {1} on a {2} site.'
                .format(player.name, building, site))


    def _construct(self, player, foundation, material, site, material_zone, fountain=False):
        """Handles building construction with validity checking.

        Does not move the material or building card. This function's
        caller must grab them.

        If the site is not None, _construct the specified building on it.
        If it's out of town, set the Game.used_oot flag.
        (The perform_role_action() function consumes this flag.)

        Else, if the site is None, add the material to the building.

        If the fountain flag is True, then material_zone is ignored, and the card
        is taken from player.fountain_card, which is set to None if the operation
        succeeds.

        Returns the modified building.
        """
        start_building = site is not None

        if start_building:

            # raises if start is illegal
            self._check_building_start_legal(player, foundation, site)

            is_oot = site not in self.in_town_sites

            # TODO: These errors are all checked in check_building_start
            if player.owns_building(foundation):
                raise GTRError('{0} already has a {1!s}'
                    .format(player.name, foundation))

            if is_oot:
                sites = self.out_of_town_sites
                if site not in sites:
                    raise GTRError('{0} not available out of town.'.format(site))
            else:
                sites = self.in_town_sites
                if site not in sites:
                    raise GTRError('{0} not available in town.'.format(site))

            if fountain:
                if foundation != player.fountain_card:
                    raise GTRError('{0!s} is not {1}\'s Fountain card.'
                        .format(foundation, player.name))
            else:
                if foundation not in player.hand:
                    raise GTRError('{0!s} card not in {1}\'s hand.'
                        .format(foundation, player.name))

            site_card = gtrutils.get_card_from_zone(site, sites)
            if fountain:
                foundation_card = player.fountain_card
                player.fountain_card = None
            else:
                foundation_card = player.hand.pop(player.hand.index(foundation))

            b = Building(foundation_card, site_card)
            player.buildings.append(b)

            self.used_oot = is_oot

            # Check Forum before ending the game via sites, since starting a Forum
            # on the last in-town site with an active Gate and all client roles is
            # a win.
            self._check_forum()

            if len(self.in_town_sites) == 0:
                self._end_game()

            return b

        else:
            # This raises if the add is not legal
            self._check_building_add_legal(player, foundation, material)

            # Both these raise if the card/building isn't found
            b = player.get_building(foundation)
            if b.complete:
                raise GTRError('Cannot add to {0!s} because it is already complete.'
                    .format(foundation))

            # Raises if material doesn't exist
            if fountain:
                b.materials.append(player.fountain_card)
                player.fountain_card = None
            else:
                material_zone.move_card(material, b.materials)

            has_scriptorium = self._player_has_active_building(player, 'Scriptorium')

            complete = False
            if has_scriptorium and material.material == 'Marble':
                self._log('{0} completed building {1} using Scriptorium'.format(
                  player.name, str(b)))
                complete = True
           
            elif len(b.materials) == cm.get_value_of_material(b.site):
                self._log('{0} completed building {1}'.format(player.name, str(b)))
                complete = True
            
            # This is an Architect action if the material comes from the stockpile.
            elif material_zone is player.stockpile and foundation.name == 'Villa':
                self._log('{0} completed Villa with one material '
                        'using Architect.'
                        .format(player.name))
                complete = True


            if complete:
                b.complete = True
                gtrutils.add_card_to_zone(b.site, player.influence)

            return b


    def _handle_craftsman(self, a):
        foundation, material, site = a.args

        p = self.active_player

        if foundation is None or (material is None and site is None):
            self._log('{0} skips Craftsman action.'.format(p.name))
            self._pump()

        else:
            b = self._construct(p, foundation, material, site, p.hand)
            self._log('{0} performs Craftsman.'.format(p.name))
            self._log_construct(p, foundation, material, site, ' from hand')

            if b.complete:
                lg.debug('{0} completes {1!s}'.format(p.name, b))
                self._log('{0} completed.'.format(str(b)))
                self._resolve_building(p, b)

            p.performed_craftsman = True

            self._pump()


    def _handle_architect(self, a):
        """Skip the action by making foundation = None.
        """
        foundation, material, site = a.args

        p = self.active_player

        if foundation:
            if material is None:
                material_zone, s = None, ''
            else:
                if material in self.pool:
                    material_zone, s = self.pool, ' from pool'
                else:
                    material_zone, s = p.stockpile, ' from stockpile'

            b = self._construct(p, foundation, material, site, material_zone)
            self._log('{0} performs Architect.'.format(p.name))
            self._log_construct(p, foundation, material, site, s)

            # In case Stairway is completed, check after construct()
            has_stairway = self._player_has_active_building(p, 'Stairway')
            if has_stairway:
                self.stack.push_frame('_await_action', message.STAIRWAY, p)

            if b.complete:
                self._log('{0} completed'.format(str(b)))
                self._resolve_building(p, b)

        else:
            self._log('{0} skips Architect action.'.format(p.name))

            # Skipping architect still allows Stairway
            has_stairway = self._player_has_active_building(p, 'Stairway')
            if has_stairway:
                self.stack.push_frame('_await_action', message.STAIRWAY, p)

        self._pump()


    def _handle_stairway(self, a):
        """ Handles a Stairway move.

        If player, building, or material is None, skip the action.
        player_name is ignored.
        """
        foundation, material = a.args

        p = self.active_player

        if foundation is None or material is None:
            self._log('{0} skips Stairway.'.format(p.name))

        else:
            player, b = self._find_players_building(foundation)
            if b is None or p is None:
                raise GTRError('Building named for Stairway addition not found: {0}'
                        .format(foundation.name))

            if not b.complete:
                raise GTRError('Cannot use Stairway on incomplete building.')

            from_pool = material in self.pool

            zone = self.pool if from_pool else p.stockpile

            zone.move_card(material, b.stairway_materials)

            if from_pool:
                self._log('{0} uses Stairway to add {1} from the pool to {2}\'s {3}.' 
                    .format(p.name, material, player.name, foundation))
            else:
                self._log('{0} uses Stairway to add {1} to {2}\'s {3}.' 
                    .format(p.name, material, player.name, foundation))

            self._check_forum()

        self._pump()


    def _perform_legionary_action(self, player):
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

        However, if this legionary is the product of a Patron action hiring a
        Legionary client, and the next stack frame is a Merchant while we have
        a Ludus Magna, this should not combine into two Legionary actions.
        This is easiest to achieve by checking that Legionary is the led role
        before combining Merchants.
        """
        self.active_player = player

        has_ludus = self._player_has_active_building(player, 'Ludus Magna')
        has_cm = self._player_has_active_building(player, 'Circus Maximus')
        is_following_or_leading = player.is_following_or_leading
        role_led = self.role_led

        self.legionary_count = 1

        # Traverse the stack, remove Legionary frames and increment legionary count
        for f in self.stack.stack[::-1]:
            if not len(f.args) or f.args[0] != player:
                break

            if f.function_name == '_perform_role_action' and f.args[1] == 'Legionary':
                self.legionary_count += 1
                self.stack.remove(f)

            elif f.function_name == '_perform_clientele_action':
                role = f.args[1]

                legionary_led = self.role_led == 'Legionary'
                if role == 'Legionary' or (has_ludus and role == 'Merchant' and legionary_led):
                    self.legionary_count += 1
                    if has_cm and role_led == 'Legionary' and is_following_or_leading:
                        self.legionary_count += 1

                    self.stack.remove(f)

            else:
                break

        self._await_action(message.LEGIONARY, player)


    def _handle_legionary(self, a):
        cards = a.args

        if len([c for c in cards if c.name == 'Jack']):
            raise GTRError('Cannot demand material with Jack.')

        p = self.active_player
        hand = Zone([c for c in p.hand if c.name !='Jack'])
        if not hand.contains(cards):
            raise GTRError('Demanding with cards not in hand: {0}.'
                    .format(', '.join(map(str,cards))))

        if len(cards) > self.legionary_count:
            raise GTRError('Too many cards specified for Legionary demand: {0} '
                    '({1:d} allowed)'
                    .format(', '.join(map(str,cards)), self.legionary_count))

        cards_in_revealed = p.prev_revealed.intersection(cards)
        if len(cards_in_revealed):
            raise GTRError('Cannot use card for Legionary twice in one turn: {0}.'
                    .format(', '.join(map(str,cards_in_revealed.elements()))))

        for c in p.prev_revealed:
            try:
                hand.cards.remove(c)
            except ValueError:
                pass # Possible that card is no longer in hand

        p.revealed.set_content(hand.get_cards(cards))
        p.prev_revealed.extend(p.revealed)

        revealed_materials = [c.material for c in p.revealed]

        if len(revealed_materials) == 0:
            self._log('{0} skips legionary.'.format(p.name))
            self._pump()
            return
        else:
            self._log('Rome demands {0}! (revealing {1})'
                .format(', '.join(revealed_materials), 
                    ', '.join(map(str, p.revealed))))

            # Get cards from other players, but only neighbors without Bridge.

            has_bridge = self._player_has_active_building(p, 'Bridge')

            if len(self.players) > 3 and not has_bridge:
                players_turn_order = self._players_in_turn_order(p) 
                responding_players = players_turn_order[1], players_turn_order[-1]

            else:
                responding_players = self._players_in_turn_order(p)
                responding_players.pop(0)

            for player in responding_players[::-1]:
                self.stack.push_frame('_await_action', message.GIVECARDS, player)
                    
            self.legionary_player = p
            self._await_action(message.TAKEPOOLCARDS, p)


    def _handle_takepoolcards(self, a):
        pool_cards = a.args

        revealed_materials = [c.material for c in self.active_player.revealed]

        pool_matches = [c for c in pool_cards if c in self.pool]
        if len(pool_matches) < len(pool_cards):
            raise GTRError('Cards specified that aren\'t in pool ({0}).'
                    .format(', '.join(map(str, pool_matches))))

        for c in pool_matches:
            self.pool.move_card(c, self.legionary_player.stockpile)

        if pool_matches:
            self._log('{0} collected {1} from the pool.'
                .format(self.legionary_player.name,
                    ', '.join([c.material for c in pool_matches])))

        self._pump()


    def _handle_givecards(self, a):
        """Handle action that gives cards for Legionary. Cards from stockpile
        (Bridge) or clientele (Coliseum) must also be specified If the player
        is immune because of a Wall or Palisade, they need not provide cards
        from stockpile or clientele.
        """
        cards = a.args

        p = self.active_player

        leg_p = self.legionary_player

        has_bridge = self._player_has_active_building(leg_p, 'Bridge')
        has_coliseum = self._player_has_active_building(leg_p, 'Coliseum')

        has_wall = self._player_has_active_building(p, 'Wall')
        has_palisade = self._player_has_active_building(p, 'Palisade')

        is_immune = has_wall or (has_palisade and not has_bridge)

        self._move_legionary_cards(p, leg_p, cards, is_immune,
                has_bridge, has_coliseum)

        self._pump()


    def _move_legionary_cards(self, p, leg_p, cards, immune, has_bridge, has_coliseum):
        """Moves the cards from p's zones according to leg_p's revealed
        cards and the flags for Bridge and Coliseum.
        """
        cards_in_hand = [c for c in cards if c in p.hand]
        cards_in_stockpile = [c for c in cards if c in p.stockpile]
        cards_in_clientele = [c for c in cards if c in p.clientele]

        if cards_in_stockpile and not has_bridge:
            raise GTRError('Cannot give cards from stockpile if '
                    'Legionary leader ({0}) has no Bridge ({1}).'
                    .format(self.legionary_player.name,
                        ', '.join(map(str, cards_in_stockpile))))

        if cards_in_clientele and not has_coliseum:
            raise GTRError('Cannot give cards from clientele if '
                    'Legionary leader has no Coliseum ({0}).'
                    .format(', '.join(map(str, cards_in_clientele))))

        if (len(cards_in_hand)+len(cards_in_stockpile)+
                len(cards_in_clientele)) < len(cards):
            raise GTRError('Cards given that aren\'t in '
                    'stockpile, hand, or clientele ({0}).'
                    .format(', '.join(map(str, cards))))

        def legionary_zone(demanded, given, zone):
            """Check cards from zone that are both demanded
            and given. Raise GTRError if the cards aren't in
            the zone, are given but not demanded, or are demanded
            and not given but are in the zone.
            """
            # Check that all required cards were offered.
            demanded_mats = Counter([c.material for c in demanded])
            given_mats = Counter([c.material for c in given])
            zone_mats = Counter([c.material for c in zone])

            unmatched_mats = demanded_mats - given_mats
            extra_mats = given_mats - demanded_mats
            remaining_mats = zone_mats - given_mats
            ungiven_mats = unmatched_mats & remaining_mats # intersection

            if len(extra_mats):
                lg.debug('Too many cards given : ' + str(extra_mats))
                raise GTRError('Extra cards given for Legionary.')

            if len(ungiven_mats) and not immune:
                lg.debug('Require more cards : ' + str(ungiven_mats))
                raise GTRError('Not enough cards given for Legionary.')

            return given

        hand_cards_to_move = legionary_zone(
                leg_p.revealed, cards_in_hand, p.hand)
        if has_bridge:
            stockpile_cards_to_move = legionary_zone(
                    leg_p.revealed, cards_in_stockpile, p.stockpile)
        else:
            stockpile_cards_to_move = []

        if has_coliseum:
            clientele_cards_to_move = legionary_zone(
                    leg_p.revealed, cards_in_clientele, p.clientele)
        else:
            clientele_cards_to_move = []

        if hand_cards_to_move or stockpile_cards_to_move or \
                clientele_cards_to_move:
            if len(hand_cards_to_move):
                self._log('{0} gives {1} from their hand.'
                        .format(p.name,
                            ', '.join(map(str, hand_cards_to_move))))
            if len(stockpile_cards_to_move):
                self._log('{0} gives {1} from their stockpile.'
                        .format(p.name,
                            ', '.join(map(str, stockpile_cards_to_move))))
            if len(clientele_cards_to_move):
                self._log('{0} feeds {1} to the lions.'
                        .format(p.name,
                            ', '.join(map(str, clientele_cards_to_move))))
        else:
            self._log('{0}: "Glory to Rome!"'.format(p.name))

        for c in hand_cards_to_move:
            p.hand.move_card(c, leg_p.stockpile)

        for c in stockpile_cards_to_move:
            p.stockpile.move_card(c, leg_p.stockpile)

        # Don't move cards if leg. player would go over vault limit.
        # Instead, mark the cards as given, then wait for a TAKECLIENTS action.
        vault_space = self._vault_limit(leg_p)-len(leg_p.vault)
        if vault_space > 0:
            if vault_space >= len(clientele_cards_to_move):
                for c in clientele_cards_to_move:
                    p.clientele.move_card(c, leg_p.vault)
            else:
                p.clients_given.set_content(clientele_cards_to_move)
                self.stack.push_frame('_await_action', message.TAKECLIENTS, leg_p)



    def _handle_takeclients(self, a):
        clients = a.args

        p = self.active_player
        victim = next((p for p in self.players if len(p.clients_given)), None)
        if victim is None:
            raise GTRError('Received TAKECLIENTS without victim.')

        extra_taken = [c for c in clients if c not in victim.clients_given]
        if len(extra_taken):
            raise GTRError('Clients picked that were not given: {0}'
                    .format(', '.join(map(str, extra_taken))))

        vault_space = self._vault_limit(p)-len(p.vault)
        if len(clients) != vault_space:
            raise GTRError('Must take exactly {0:d} clients.'
                    .format(vault_space))

        for c in clients:
           victim.clientele.move_card(c, p.vault)

        victim.clients_given.set_content([])

        self._log('{0} chooses clients from {1}: {2}'
                .format(p.name, victim.name, ', '.join(map(str, clients))))


        self._pump()


    def _handle_merchant(self, a):
        from_deck = a.args[0]
        cards = a.args[1:]

        p = self.active_player

        stockpile_cards = [c for c in cards if c in p.stockpile]
        hand_cards = [c for c in cards if c in p.hand]

        if len(hand_cards)>1:
            raise GTRError('Received too many cards from {0}\'s hand ({1})'
                       .format(p.name, ', '.join(map(str, hand_cards))))

        if len(stockpile_cards)>1:
            raise GTRError('Received too many cards from {0}\'s stockpile ({1})'
                       .format(p.name, ', '.join(map(str, stockpile_cards))))

        if len(cards) > len(hand_cards) + len(stockpile_cards):
            raise GTRError('Received cards not in stockpile or hand.')

        stockpile_card = stockpile_cards[0] if stockpile_cards else None
        hand_card = hand_cards[0] if hand_cards else None


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

        if n_cards + len(p.vault) > self._vault_limit(p):
            raise GTRError('Not enough room in {0}\'s vault for {1:d} additional cards. (Limit {2:d} more.)'
                .format(p.name, n_cards, self._vault_limit(p)-len(p.vault)))

        # If the Atrium card from the deck is the last Orders card, then the
        # game is over and the Basilica doesn't function.
        game_will_end = from_deck and len(self.library) == 1

        if stockpile_card:
            p.stockpile.move_card(stockpile_card, p.vault)

        if from_deck:
            gtrutils.add_card_to_zone(self._draw_cards(1)[0], p.vault)

        if hand_card and not game_will_end:
            p.hand.move_card(hand_card, p.vault)

        hand_log = hand_card and not game_will_end

        # Logging
        if stockpile_card:
            self._log(('{0} performs Merchant, selling a {1!s} from the stockpile'
                      + (' and a card from their hand.' if hand_log else '.'))
                      .format(p.name, stockpile_card))
        elif from_deck:
            self._log(('{0} performs Merchant, selling a card from the deck'
                      + (' and a card from their hand.' if hand_log else '.'))
                      .format(p.name))
        elif hand_log:
            self._log('{0} performs Merchant, selling a card from their hand.'
                .format(p.name))
        else:
            self._log('{0} skips Merchant action.'.format(p.name))

        self._check_library_empty()

        self._pump()


    def _kids_in_pool(self):
        """Place cards in camp into the pool.
        """
        self._log('Kids in the pool.')
        for p in self._players_in_turn_order()[::-1]:
            self.stack.push_frame('_do_kids_in_pool', p)

        for p in self._players_in_turn_order()[::-1]:
            if self._player_has_active_building(p, 'Senate'):
                self.stack.push_frame('_do_senate', p)

        self._pump()


    def _do_senate(self, p):
        """Wait for a USESENATE action from player if opponent has Jack.
        """
        other_players = self._players_in_turn_order(p)
        other_players.pop(0)

        has_jack = next((True for pl in other_players if 'Jack' in pl.camp), False)
        if has_jack:
            self._await_action(message.USESENATE, p)
        else:
            self._pump()


    def _do_kids_in_pool(self, p):
        if self._player_has_active_building(p, 'Sewer') and \
                next(itertools.ifilter(lambda c: c.name != 'Jack', p.camp), None) is not None:
            self._await_action(message.USESEWER, p)

        else:
            self.active_player = p
            self._handle_usesewer(message.GameAction(message.USESEWER))


    def _handle_usesenate(self, a):
        jacks = a.args
        p = self.active_player

        jacks_in_camps = [] # list of (player, jack) tuples

        players = self._players_in_turn_order(p)
        players.pop(0)

        for player in players:
            camp_jacks = [j for j in jacks if j in player.camp]
            for j in camp_jacks:
                jacks_in_camps.append( (player, j) )

        if len(jacks) > len(jacks_in_camps):
            raise GTRError('Too many Jacks specified with Senate ({0:d}).'
                    .format(len(jacks)))
        else:
            for player, jack in jacks_in_camps:
                self._log('{0} takes {1}\'s Jack with Senate.'
                        .format(p.name, player.name))
                player.camp.move_card(jack, p.hand)

        if self._player_has_active_building(p, 'Sewer'):
            self._await_action(message.USESEWER, p)

        self._pump()


    def _handle_usesewer(self, a):
        cards = a.args
        p = self.active_player

        for c in cards:
            if c.name == 'Jack':
                raise GTRError('Can\'t move Jacks with Sewer')
            elif c not in p.camp:
                raise GTRError('Card not in camp for use with Sewer ({0})'
                        .format(c.name))

        for c in cards:
            p.camp.move_card(c, p.stockpile)

        if len(cards):
            self._log('{0} flushes cards down the Sewer: {1}'
                    .format(p.name, ', '.join(map(str, cards))))

        for c in p.camp.cards[:]: # Copy since we're removing
            if c.name == 'Jack':
                p.camp.move_card(c, self.jacks)
            else:
                p.camp.move_card(c, self.pool)

        self._pump()


    def _handle_prison(self, a):
        building = a.args[0]
        player = self.active_player

        if building is None:
            self._log('{0} doesn\'t steal anything with Prison, keeping the '
                    'influence points.'
                    .format(player.name))
        else:
            p, b = self._find_players_building(building)
            if p is None or b is None:
                raise GTRError('Building chosen for Prison doesn\'t exist: {0}'
                        .format(building.name))

            if not b.complete:
                raise GTRError('Cannot use Prison on incomplete building.')

            else:
                i = p.buildings.index(b)
                player.buildings.append(p.buildings.pop(i))
                
                i = player.influence.index('Stone')
                p.influence.append(player.influence.pop(i))

                self._log('{0} steals {1}\'s {2} with Prison.'
                        .format(player.name, p.name, str(b)))

                self._resolve_building(player, b)

        self._pump()


    def _end_turn(self):
        """Clean up Game flags and push a _do_end_turn for each player.
        """
        self.role_led = None
        self.legionary_count = None
        self.legionary_player_index = None
        self.used_oot = False
        self.oot_allowed = False

        players = self._players_in_turn_order()[::-1]

        for p in players:
            self.stack.push_frame('_do_end_turn', p)

        self._pump()


    def _do_end_turn(self, p):
        """Run Academy for each player, and cleans up Player flags.
        """
        has_academy = self._player_has_active_building(p, 'Academy')

        p.revealed.set_content([])
        p.prev_revealed.set_content([])
        p.n_camp_actions = 0

        if p.performed_craftsman and has_academy:
            self.stack.push_frame('_await_action', message.SKIPTHINKER, p)

        p.performed_craftsman = False

        self._pump()


    def _calc_winners(self, players=None):
        """Calculate the winners using score and cards in hand among
        the specified players. If players isn't specified, all players
        are considered.
        """
        if players is None:
            players = self.players

        if len(players) <= 1:
            return players

        max_score = self._player_score(players[0])
        winners = [players[0]]

        for p in players[1:]:
            score = self._player_score(p)

            if score > max_score:
                max_score = score
                winners = [p]

            elif score == max_score:
                winners.append(p)

        if len(winners) > 1:

            max_hand = len(winners[0].hand)
            real_winners =  [winners[0]]

            for p in winners[1:]:
                hand = len(p.hand)

                if hand > max_hand:
                    max_hand = hand
                    real_winners = [p]

                elif hand == max_hand:
                    real_winners.append(p)

            return real_winners

        else:
            return winners




    def _end_game(self):
        """The game is over. This determines a winner.
        """
        for p in self.players:
            self._log('{0} scores {1}'.format(p.name, self._player_score(p)))
        lg.info('\n')

        winners = self._calc_winners()
        if len(winners) == 1:
            self._log('{0} has won the game with {1} points.'
                    .format(winners[0].name, self._player_score(winners[0])))
        elif len(winners) > 1:
            self._log('There is a TIE between players ' +
                    ', '.join([p.name for p in winners[:-1]]) + 
                    ' and {0} with {1} points.'
                    .format(winners[-1].name, self._player_score(winners[-1])))

        self._log('Game over. Glory to Rome!')
        self.winners = winners

        raise GameOver()


    def _forum_win(self, winners):
        """All players in winners have an active Forum with all client roles.

        If there are multiple players with a winning Forum, the tie is broken
        by scoring those players normally.

        Return a list of winning players
        """
        if len(winners) < 1:
            raise GTRError('No Forum winners specified')
        elif len(winners) == 1:
            real_winners = winners
        else:
            real_winners = self._calc_winners(winners)

        if len(real_winners) == 1:
            self._log('{0} has won the game by building a Forum ({1} points).'
                    .format(winners[0].name, self._player_score(winners[0])))
        elif len(winners) > 1:
            self._log('There is a TIE between players {0}'
                    ', all of whom have built a Forum and have {1} points.'
                    .format(', '.join([p.name for p in real_winners]),
                        self._player_score(real_winners[0])))

        self._log('Game over. Glory to Rome!')
        self.winners = real_winners

        raise GameOver()


    def _resolve_building(self, player, building_obj):
        """Switch on completed building to resolve the "On Completion" effects.
        """
        if str(building_obj) == 'Catacomb':
            self._log('{0} completed Catacomb, ending the game immediately.'
                .format(player.name))

            self._end_game()

        elif str(building_obj) == 'Foundry':
            n = player.influence_points

            self._log('{0} completed Foundry, performing {1} Laborer actions.'
                .format(player.name, n))

            for _ in range(n):
                self.stack.push_frame('_perform_role_action', player, 'Laborer')

        elif str(building_obj) == 'Garden':
            n = player.influence_points

            self._log('{0} completed Garden, performing {1} Patron actions.'
                .format(player.name, n))

            for _ in range(n):
                self.stack.push_frame('_perform_patron_action', player)

        elif str(building_obj) == 'School':
            n = player.influence_points

            self._log('{0} completed School, think {1} times.'
                .format(player.name, n))

            for _ in range(n):
                self.stack.push_frame('_await_action', message.SKIPTHINKER, player)

        elif str(building_obj) == 'Amphitheatre':
            n = player.influence_points

            self._log('{0} completed Amphitheatre, performing {1} Craftsman actions.'
                .format(player.name, n))

            for _ in range(n):
                self.stack.push_frame('_perform_role_action', player, 'Craftsman')

        elif str(building_obj) == 'Prison':
            self.stack.push_frame('_await_action', message.PRISON, player)

        elif str(building_obj) in ('Forum', 'Ludus Magna', 'Gate', 'Storeroom'):
            self._check_forum()


