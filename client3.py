"""A client user interface for a player in gtr.
This is to be used by a networked client as the connection to the user.
The interface is expected to be entirely on the command line with 
output via stdout in a terminal window. However, the interface presented
is a set of action_* methods that are called when a particular GameAction
is needed. The Client object creates an ActionBuilder object (eg.
LaborerActionBuilder) that may contain internal states on the way to building
up a GameAction. 

For example, the LaborerActionBuilder needs to get 2 inputs from the player:
the card to take from the pool and the card to take from the players hand
if they have a Dock. The class has an internal state machine that stores
which of the choices have been made. Each user input causes a transition to
a new state. Specifically, the sequence is 
START->FROM_POOL->FROM_HAND->FINISHED
The transition to the FINISHED state sets the LaborerActionBuilder.done
flag and the action member to a GameAction representing the Laborer action.
The network interface sends this action to the server.

The ActionBuilder classes use lists of Choice objects to represent user
choices. These are simply containers for an item to be selected, a 
description of that item, and a flag to indicate whether it's selectable.
Unselectable choices exists so that a list can be displayed with certain
items "grayed out".

The RoleActionBuilder class is used for both the follow role action and
the lead role action because so much of the Palace and Petition code is
shared.
"""


import gtrutils
from card_manager import get_role_of_card as card2role
from card_manager import get_material_of_card as card2mat
import card_manager as cm
from gtrutils import get_detailed_card_summary as card2summary
import gtr
from building import Building
from gamestate import GameState
import message
from fsm import StateMachine
from card import Card

import collections
from collections import Counter
import logging
import pickle
import itertools
from itertools import izip_longest
from itertools import compress
import time
import glob
import copy

game_lg = logging.getLogger('gtr.game')
game_lg.propagate = False

class StartOverException(Exception):
    pass

class CancelDialogException(Exception):
    pass

class InvalidChoiceException(Exception):
    pass

class Choice(object):
    """Represents a choice in an ActionBuilder list.
    """
    def __init__(self, item, description, selectable=True):
        self.item = item
        self.description = description
        self.selectable = selectable

    def __repr__(self):
        return 'Choice({0!r}, {1!r}, {2!r})'.format(self.item, self.description, self.selectable)

    def __str__(self):
        return repr(self)

class ActionBuilder(object):
    """A base class for action builders that wraps the choices list
    and choice-making exceptions. Most action builders will use a 
    simple subclass of this or create a FSM to take multiple inputs
    while building a GameAction object.

    The member choices is a list of Choice objects, which can have a 
    description and a flag for whether that choice is selectable.
    """
    def __init__(self):
        self.choices = []
        self.done = False
        self.action = None
        self.prompt = None

    def make_selectable_choice(self, index):
        """Make a selection from the list of choices.
        This filters for selectable objects only.
        """
        selectable_items = [c.item for c in self.choices if c.selectable]
        try:
            item = selectable_items[index]
        except IndexError:
            raise InvalidChoiceException()
        else:
            return item

class SingleChoiceActionBuilder(ActionBuilder):
    """Gets a simple response from a list.
    """
    def __init__(self, action_type, choices):
        """The parameter choices is a list of Choice objects.

        For example:

            [Choice('Rubble', 'Build on a Rubble site', True),
             Choice('Concrete', 'Cannot build on Concrete', False).
             ...]

        """
        ActionBuilder.__init__(self)
        self.choices = choices
        self.action_type = action_type
        self.prompt = None

    def make_choice(self, index):
        item = self.make_selectable_choice(index)

        self.action = message.GameAction(self.action_type, item)
        self.done = True


class FSMActionBuilder(ActionBuilder):
    """An action builder subclass that uses a FSM to keep track of
    multiple sequential inputs building up a GameAction over many
    question.
    """

    def __init__(self):
        ActionBuilder.__init__(self)
        self.fsm = StateMachine()

    def make_choice(self, index):
        item = self.make_selectable_choice(index)

        self.fsm.pump(item)


class LaborerActionBuilder(FSMActionBuilder):
    """Puts together the information needed for a Laborer action.
    """

    def __init__(self, pool, hand, has_dock=False):
        FSMActionBuilder.__init__(self)

        self.hand = sorted(hand, cm.cmp_jacks_first)
        self.pool = sorted(pool, cm.cmp_jacks_first)

        self.has_dock = has_dock

        self.pool_card = None
        self.hand_card = None


        self.fsm.add_state('START', None, lambda _ : 'FROM_POOL')
        self.fsm.add_state('FROM_POOL',
            self.from_pool_arrival, self.from_pool_transition)
        self.fsm.add_state('FROM_HAND',
            self.from_hand_arrival, self.from_hand_transition)
        self.fsm.add_state('FINISHED', self.finished_arrival, None, True)

        self.fsm.set_start('START')

        # Move from Start state
        self.fsm.pump(None)


    def from_pool_arrival(self):
        self.choices = [Choice(c, card2summary(c), True) for c in self.pool]
        self.choices.append(Choice(None, 'Skip card from pool', True))
        self.prompt = 'Performing Laborer. Select card from pool'


    def from_pool_transition(self, choice):
        self.pool_card = choice

        return 'FROM_HAND' if self.has_dock else 'FINISHED'


    def from_hand_arrival(self):
        self.choices = [Choice(c, card2summary(c), c.name != 'Jack') for c in self.hand]
        self.choices.append(Choice(None, 'Skip card from hand', True))
        self.prompt = 'Performing Laborer. Select card from hand'


    def from_hand_transition(self, choice):
        self.hand_card = choice

        return 'FINISHED'


    def finished_arrival(self):
        self.done = True
        self.action = message.GameAction(message.LABORER, self.hand_card, self.pool_card)


class LegionaryActionBuilder(FSMActionBuilder):
    """Assemble the list of cards used to demand with the Legionary.
    """

    def __init__(self, hand, n_legionary_actions):
        FSMActionBuilder.__init__(self)

        self.hand = [Choice(c, card2summary(c)) for c in \
                     sorted(hand, cm.cmp_jacks_first) \
                     if c.name != 'Jack']

        self.cards = []
        self.n_max = n_legionary_actions

        self.fsm.add_state('START', None, lambda _ : 'GET_CARD')
        self.fsm.add_state('GET_CARD',
            self.get_card_arrival, self.get_card_transition)
        self.fsm.add_state('FINISHED', self.finished_arrival, None, True)

        self.fsm.set_start('START')

        # Move from Start state
        self.fsm.pump(None)


    def get_card_arrival(self):
        self.choices = copy.deepcopy(self.hand)

        for c in self.cards:
            for choice in self.choices:
                if choice.item == c and choice.selectable:
                    choice.selectable = False
                    break

        skip_msg = 'Skip further legionary actions' if self.n_max > 1 \
                else 'Skip this legionary action'

        self.choices.append(Choice('Skip', skip_msg, True))

        if len(self.cards) >= 1:
            self.choices.append(Choice('Undo', 'Undo', True))

        self.prompt = 'Select card{0} for Legionary ({1:d}/{2:d})'.format(
                's' if self.n_max > 1 else '',
                len(self.cards),
                self.n_max)


    def get_card_transition(self, choice):
        if choice == 'Skip':
            new_state = 'FINISHED'
        elif choice == 'Undo':
            self.cards.pop()
            new_state = 'GET_CARD'
        else:
            self.cards.append(choice)
            if len(self.cards) == self.n_max:
                new_state = 'FINISHED'
            elif len(self.cards) == len(self.hand):
                new_state = 'FINISHED'
            else:
                new_state = 'GET_CARD'

        return new_state


    def finished_arrival(self):
        self.done = True
        cards = self.cards if len(self.cards) else []
        self.action = message.GameAction(message.LEGIONARY, *cards)


class GiveCardsActionBuilder(FSMActionBuilder):
    """Assemble the set of cards to give to the Legionary player.

    In principle, the player can select which cards to give
    from the stockpile or clientele (for Bridge and Colisseum),
    but we determine these automatically since it's rarely useful.

    If the immune flag is True, then we just make an empty action.
    Otherwise, we ask for the cards from the player's hand.
    """

    # The member self.cards will accumulated cards as they are selected.
    # For every re-entry into the GET_CARD state, self.cards is compared
    # against legionary_mats to see which material demands are unsatisfied.

    def __init__(self, legionary_mats, hand, stockpile, clientele,
            has_bridge, has_coliseum, immune):

        FSMActionBuilder.__init__(self)
        self.hand = [Choice(c, card2summary(c)) for c in \
                     sorted(hand, cm.cmp_jacks_first) \
                     if c.name != 'Jack']
        self.stockpile = list(stockpile)
        self.clientele = list(clientele)

        self.stockpile_cards = []
        self.clientele_cards = []

        # self.cards will be returned with the GIVECARDS action
        self.cards = []
        self.mats = legionary_mats

        self.has_bridge = has_bridge
        self.has_coliseum = has_coliseum

        self.get_no_choice_cards()

        self.fsm.add_state('START', None, lambda _ : 'GET_CARD')
        self.fsm.add_state('GET_CARD',
            self.get_card_arrival, self.get_card_transition)
        self.fsm.add_state('GLORYTOROME', self.glory_to_rome_arrival,
                lambda _ : 'FINISHED')
        self.fsm.add_state('FINISHED', self.finished_arrival, None, True)

        self.fsm.set_start('START')

        # Move from Start state
        if immune:
            self.done = True
            self.action = message.GameAction(message.GIVECARDS, None)

        elif self.finished() and not self.stockpile_cards and not self.clientele_cards:
            self.fsm.set_start('GLORYTOROME')

        self.fsm.pump(None)


    def get_card_arrival(self):
        self.choices = copy.deepcopy(self.hand)
        mats = list(self.mats)

        # Mark as unselectable cards that have already been chosen
        for c in self.cards:
            for choice in self.choices:
                if choice.item == c and choice.selectable:
                    choice.selectable = False
                    break

        # Remove from the materials demanded the materials of the cards already chosen
        for c in self.cards:
            m = card2mat(c)
            if m in mats:
                mats.remove(m)

        for choice in self.choices:
            choice.selectable = choice.item.material in mats

        if len(self.cards) > 1:
            self.choices.append(Choice('Undo', 'Undo'))

        self.choices.append(Choice(None, 'None'))

        self.prompt = 'Rome demands: {0}! (currently giving: {1})'.format(
                ', '.join(mats),
                ', '.join(self.cards))



    def finished(self):
        leg_mats = Counter(self.mats)
        
        # Subtract selected cards to get the remaining required materials
        leg_mats.subtract([c.material for c in self.cards])

        # Compare required materials with hand. There should be no overlap
        materials = list(leg_mats.elements())

        # If there's no overlap with remaining cards in hand, this subtraction
        # shouldn't do anything to leg_mats
        leg_mats.subtract([c.item.material for c in self.hand if c.selectable])
        remaining_mats = list(leg_mats.elements())

        return len(materials) == len(remaining_mats)


    def get_card_transition(self, choice):
        if choice == 'Undo':
            self.cards.pop()
            new_state = 'GET_CARD'

        else:
            if choice is not None:
                self.cards.append(choice)

            if self.finished():            
                new_state = 'FINISHED'
            else:
                new_state = 'GET_CARD'

        return new_state

    def glory_to_rome_arrival(self):
        self.choices = [\
                Choice('Glory', 'Glory to Rome!'),
                Choice('Skip', 'Skip this action', selectable=False)
                ]

        self.prompt = 'Please make a selection'


    def finished_arrival(self):
        self.done = True

        cards = self.cards
        #cards = self.cards + self.stockpile_cards + self.clientele_cards

        self.action = message.GameAction(message.GIVECARDS, *cards)


    def get_no_choice_cards(self):
        self.stockpile_cards = []
        if self.has_bridge:
            for r in self.mats:
                for c in self.stockpile:
                    if card2mat(c) == r:
                        self.stockpile_cards.append(c)
                        self.stockpile.remove(c)
                        break
                        
        self.clientele_cards = []
        if self.has_coliseum:
            for r in self.mats:
                for c in self.clientele:
                    if card2mat(c) == r:
                        self.clientele_cards.append(c)
                        self.clientele.remove(c)
                        break


class MerchantActionBuilder(FSMActionBuilder):
    """Puts together the information needed for a Laborer action.
    """

    def __init__(self, stockpile, hand, has_atrium, has_basilica):
        FSMActionBuilder.__init__(self)

        self.hand = sorted(hand, cm.cmp_jacks_first)
        self.stockpile_cards = sorted(stockpile, cm.cmp_jacks_first)

        self.has_basilica = has_basilica
        self.has_atrium = has_atrium

        self.stockpile_card = None
        self.hand_card = None
        self.from_deck = False

        self.fsm.add_state('START', None, lambda _ : 'FROM_STOCKPILE')
        self.fsm.add_state('FROM_STOCKPILE',
            self.from_stockpile_arrival, self.from_stockpile_transition)
        self.fsm.add_state('FROM_HAND',
            self.from_hand_arrival, self.from_hand_transition)
        self.fsm.add_state('FROM_DECK',
            self.from_deck_arrival, self.from_deck_transition)
        self.fsm.add_state('FINISHED', self.finished_arrival, None, True)

        self.fsm.set_start('START')

        self.fsm.pump(None)


    def from_stockpile_arrival(self):
        self.choices = [Choice(c, card2summary(c)) for c in self.stockpile_cards]
        self.choices.append(Choice(None, 'Skip card from stockpile'))
        self.prompt = 'Select card from stockpile for Merchant'


    def from_stockpile_transition(self, choice):
        self.stockpile_card = choice

        if self.has_basilica:
            return 'FROM_BASILICA'

        elif self.has_atrium:
            return 'FROM_DECK'

        else:
            return 'FINISHED'


    def from_hand_arrival(self):
        self.choices = [Choice(c, card2summary(c), c.name != 'Jack') for c in self.hand]
        self.choices.append(Choice(None, 'Skip card from hand'))
        self.prompt = 'Select card from hand for Merchant action (Basilica)'


    def from_hand_transition(self, choice):
        self.hand_card = choice

        return 'FROM_DECK' if self.has_atrium else 'FINISHED'


    def from_deck_arrival(self):
        self.choices = [Choice(True, 'Take card from deck'),
                        Choice(False, 'Skip card from deck')]
        self.prompt = 'Take card from deck for Merchant action? (Atrium)'


    def from_deck_transition(self, choice):
        self.hand_card = choice

        return 'FINISHED'


    def finished_arrival(self):
        self.done = True
        self.action = message.GameAction(message.MERCHANT, self.stockpile_card,
                self.hand_card, self.from_deck)


class RoleActionBuilder(FSMActionBuilder):
    """Builds up a message.GameAction for LEADROLE or FOLLOWROLE.
    
    If role is not None, we generate a FOLLOWROLE action instead,
    otherwise, role is determined.
    """

    # The code for the petition and palace is shared between the
    # FOLLOWROLE and LEADROLE actions, so the other states have
    # some switches to deal with the two cases.
    # There are notes in individual functions.

    def __init__(self, hand, role=None, has_palace=False, petition_count=3):
        FSMActionBuilder.__init__(self)
        # A list of cards in the hand and whether they've been used.
        self.hand = [Choice(c, card2summary(c), True) for c in \
                           sorted(hand, Card.compare_jacks_first)]

        self.role = role
        self.following = role is not None

        self.action_units = [] # list of lists: [card1, card2, ... ]
        self.petition_cards = []

        self.has_palace = has_palace
        self.petition_count = petition_count

        self.fsm.add_state('START', None, lambda _: 'SELECT_CARD')
        self.fsm.add_state('SELECT_CARD',
            self.select_card_arrival, self.select_card_transition)
        self.fsm.add_state('PALACE_CARDS',
            self.palace_cards_arrival, self.palace_cards_transition)
        self.fsm.add_state('FIRST_PETITION',
            self.first_petition_arrival, self.first_petition_transition)
        self.fsm.add_state('MORE_PETITIONS',
            self.more_petitions_arrival, self.more_petitions_transition)
        self.fsm.add_state('JACK_ROLE',
            self.jack_role_arrival, self.jack_role_transition)
        self.fsm.add_state('PETITION_ROLE',
            self.petition_role_arrival, self.petition_role_transition)
        self.fsm.add_state('FINISHED', self.finished_arrival, None, True)
        # THINKER state is the end state for thinkering instead of following
        self.fsm.add_state('THINKER', self.thinker_arrival, None, True)

        self.fsm.set_start('START')

        # Move from Start state to SELECT_CARD
        self.fsm.pump(None)

    def get_hand_card(self, card):
        """Gets the Choice object corresponding to an unselected card name.

        If the selectable card does not exist, raises InvalidChoiceException.
        """
        for choice in self.hand:
            if isinstance(choice.item, Card) and choice.item.name == card and choice.selectable:
                return choice

        raise InvalidChoiceException()


    def select_card_action(self, card):
        """Finds the choice corresponding to card name in the list of cards in
        hand, and marks it as selected. Appends card object to action_unit
        list.

        Raises InvalidChoiceException if the card is not in hand or is
        not selectable.
        """
        choice = self.get_hand_card(card)

        choice.selectable = False
        self.action_units.append([choice.item])


    def finish_petition(self):
        """Takes the petition_cards list and adds it as an action unit to
        the action_units list. Marks the cards added as used in the hand
        list.
        """
        self.action_units.append(self.petition_cards)

        for card in self.petition_cards:
            choice = self.get_hand_card(card)
            choice.selectable = False

        self.petition_cards = []


    def finished_arrival(self):
        self.done = True
        if self.following:
            self.action = message.GameAction(
                message.FOLLOWROLE, False, len(self.action_units),
                *itertools.chain(*self.action_units))

        else:
            self.action = message.GameAction(
                message.LEADROLE, self.role, len(self.action_units),
                *itertools.chain(*self.action_units))


    def thinker_arrival(self):
        self.done = True
        self.action = message.GameAction(message.FOLLOWROLE, True, 0, None)


    def select_card_arrival(self):
        """This prepares the first card selection. For the case where we're
        following, we need the option to Thinker instead, and we also mark
        the cards that don't match the led role as unselectable.
        """
        self.choices = copy.deepcopy(self.hand)

        if self.following:
            for c in self.choices:
                if c.item != 'Jack' and card2role(c.item) != self.role:
                    c.selectable = False

            self.choices.append(Choice('Petition', 'Petition', True))
            self.choices.append(Choice('Think', 'Thinker instead of following', True))

            self.prompt = 'Select card to follow with'

        else:
            self.choices.append(Choice('Petition', 'Petition', True))
            self.prompt = 'Select card to lead with'


    def select_card_transition(self, card):
        """There are a couple checks if role is None,
        for the case where we're leading. If we're following,
        the role is always defined.
        """
        if self.following and card == 'Think':
            new_state = 'THINKER'

        elif card == 'Petition':
            new_state = 'FIRST_PETITION'

        else:
            if self.role is None and card.name == 'Jack':
                new_state = 'JACK_ROLE'

            else:
                if self.role is None and card.name != 'Jack':
                    self.role = card.role

                self.select_card_action(card.name)

                new_state = 'PALACE_CARDS' if self.has_palace else 'FINISHED'

        return new_state


    def jack_role_arrival(self):
        self.choices = [Choice(r, r, True) for r in cm.get_all_roles()]
        self.prompt = 'Select role for Jack'


    def jack_role_transition(self, choice):
        self.role = choice
        self.select_card_action('Jack')

        new_state = 'PALACE_CARDS' if self.has_palace else 'FINISHED'

        return new_state


    def petition_role_arrival(self):
        self.choices = [Choice(r, r, True) for r in cm.get_all_roles()]
        self.prompt = 'Select role for Petition'


    def petition_role_transition(self, choice):
        self.role = choice
        self.finish_petition()

        new_state = 'PALACE_CARDS' if self.has_palace else 'FINISHED'

        return new_state


    def first_petition_arrival(self):
        """Petitions are constructed one card at a time, adding
        cards to petition_cards. Once a complete petition is assembled,
        the cards are marked as used in hand and an action unit is
        added.

        The first card for a petition can be anything where we have
        3 (or 2 with a Circus) cards of the same role. 

        Subsequent cards are restricted to be the same role.
        """
        #TODO: Only make groups of 3 or 2 selectable.
        self.choices = self.get_petition_filtered_hand()
        self.choices.append(Choice(None, 'Cancel petition', True))

        self.prompt = 'Select cards for petition'


    def first_petition_transition(self, card):
        if card is None:
            # Cancel petition. Determine where we came from by whether
            # we've added any action units
            new_state = 'PALACE_CARDS' if self.action_units else 'SELECT_CARD'

        else:
            self.petition_cards.append(card)

            new_state = 'MORE_PETITIONS'

        return new_state


    def more_petitions_arrival(self):
        """The petition cards after the first are restricted to being
        the same role as the first petition card. Cancelling the petition
        is as simple as clearing the petition_cards list and returning to
        the PALACE_CARDS state or the SELECT_CARD state, depending on
        where we came from.
        """

        self.choices = self.get_petition_filtered_hand()
        self.choices.append(Choice(None, 'Cancel petition', True))

        self.prompt = "Select more cards for petition"


    def more_petitions_transition(self, choice):
        if choice is None:
            self.petition_cards = []

            # Cancel petition. Determine origin state by checking if an
            # action unit has been added.  # SELECT_CARD is the start
            # state, so no action units will exist yet.
            new_state = 'PALACE_CARDS' if self.action_units else 'SELECT_CARD'

        else:
            self.petition_cards.append(choice)

            if len(self.petition_cards) == self.petition_count:
                if self.role:
                    self.finish_petition()
                    new_state = 'PALACE_CARDS' if self.has_palace else 'FINISHED'

                else:
                    new_state = 'PETITION_ROLE'

            else:
                new_state = 'MORE_PETITIONS'

        return new_state


    def palace_cards_arrival(self):
        """Adding additional cards with the palace allow only roles that
        match the role of the first card (or the led role if following).
        """
        self.choices = copy.deepcopy(self.hand)
        for c in self.choices:
            # Mark as unselectable cards that don't match the role being led
            if c.item != 'Jack' and self.role != card2role(c.item):
                c.selectable = False

        self.choices.append(Choice('Petition', 'Petition', True))
        self.choices.append(Choice('Skip', 'Skip further Palace action', True))

        self.prompt = 'Select additional palace actions (currently {0:d} actions)'.format(
            len(self.action_units))


    def palace_cards_transition(self, choice):
        """Take an action with the palace. The role has already been
        determined. Petitioning and skipping more Palace actions are options.
        """
        if choice == 'Petition':
            new_state = 'FIRST_PETITION'

        elif choice == 'Skip':
            new_state = 'FINISHED'

        else:
            c = self.get_hand_card(choice)
            c.selectable = False

            self.action_units.append([choice])
            new_state = 'PALACE_CARDS'

        return new_state


    def get_petition_filtered_hand(self):
        """Gets a copy of the list of cards in the hand, but filters
        them so the cards that can't be added for the current petition
        are not selectable.

        This function does not change the list of cards in hand.

        TODO: update this so it's only groups of 3(2) that can be selected
        """
        petition_cpy = list(self.petition_cards)
        if self.petition_cards:
            petition_role = self.petition_cards[0].role
        else:
            petition_role = None

        choices = []

        for choice in self.hand:
            card = choice.item
            selectable = choice.selectable

            role_mismatch = petition_role is not None and card.name != 'Jack' and \
                petition_role != card.role

            if card.name == 'Jack':
                choices.append(Choice(card, 'Jack', False))

            elif role_mismatch or not selectable:
                choices.append(Choice(card, card2summary(card), False))

            elif card in petition_cpy and selectable:
                choices.append(Choice(card, card2summary(card), False))
                petition_cpy.remove(card)

            else:
                choices.append(Choice(card, card2summary(card), selectable))

        return choices


class ArchitectActionBuilder(FSMActionBuilder):
    """Assembles an architect action. There is a lot of info we need
    from the GameState.
    """

    def __init__(self, buildings, stockpile, hand, pool, in_town_sites,
            out_of_town_sites, has_archway, has_road, has_tower,
            has_scriptorium, oot_allowed):

        FSMActionBuilder.__init__(self)

        self.stockpile = sorted(stockpile)
        self.pool = sorted(pool)
        self.hand = sorted(hand, cm.cmp_jacks_first)
        self.sites_allowed = set(in_town_sites)
        if oot_allowed:
            self.sites_allowed.update(out_of_town_sites)

        self.complete_buildings = [b for b in buildings if b.complete]
        self.incomplete_buildings = [b for b in buildings if not b.complete]

        self.has_archway = has_archway
        self.has_road = has_road
        self.has_tower = has_tower
        self.has_scriptorium = has_scriptorium

        self.oot_allowed = oot_allowed

        self.building = None # An object of type Building
        self.material = None
        self.site = None

        self.from_pool = False


        self.fsm.add_state('START', None,
                lambda _: 'BUILDING' if len(self.incomplete_buildings) else 'FOUNDATION')
        self.fsm.add_state('BUILDING', 
                self.building_arrival, self.building_transition)
        self.fsm.add_state('MATERIAL', 
                self.material_arrival, self.material_transition)
        self.fsm.add_state('FOUNDATION', 
                self.foundation_arrival, self.foundation_transition)
        self.fsm.add_state('SITE', 
                self.site_arrival, self.site_transition)
        self.fsm.add_state('FINISHED', self.finished_arrival, None, True)

        self.fsm.set_start('START')

        self.fsm.pump(None)


    def building_arrival(self):
        stockpile_materials = [c.material for c in self.stockpile]
        pool_materials = [c.material for c in self.pool]

        available_materials = list(stockpile_materials)
        if self.has_archway:
            available_materials.extend(pool_materials)


        self.choices = []

        #game_lg.info(self.incomplete_buildings)
        
        for b in self.incomplete_buildings:
            material = b.foundation.material
            site_material = b.site

            stone = (self.has_road and 'Stone' in (material, site_material)
                            and len(available_materials))
            tower = self.has_tower and 'Rubble' in available_materials
            matches = (material in available_materials or
                                site_material in available_materials)
            scriptorium = self.has_scriptorium and 'Marble' in available_materials

            #game_lg.info(str([b.foundation.name, stone, tower, matches, scriptorium]))

            can_add = stone or tower or matches or scriptorium

            self.choices.append(Choice(b, str(b), can_add))

        self.choices.append(Choice('Start', 'Start a new building from hand'))
        self.choices.append(Choice('Skip', 'Skip Architect action'))

        self.prompt = 'Select a building to add a material to'


    def building_transition(self, choice):
        if isinstance(choice, Building):
            self.building = choice
            new_state = 'MATERIAL'
            
        elif choice is 'Start':
            new_state = 'FOUNDATION'

        else:
            new_state = 'FINISHED'


        return new_state


    def material_arrival(self):
        # Figure out which materials can potentially be added to a building
        okay_mats = set()

        if self.has_tower:
            okay_mats.add('Rubble')

        if self.has_scriptorium:
            okay_mats.add('Marble')

        materials = self.building.foundation.material, self.building.site
        okay_mats.update(materials)

        if self.has_road and 'Stone' in materials:
            okay_mats = set(cm.get_materials())

        # Choices list items are (bool, Card) where the boolean indicates if the 
        # Card is in the pool.
        self.choices = [Choice((False,c), card2summary(c), c.material in okay_mats)
                        for c in self.stockpile]

        if self.has_archway:
            self.choices.extend(
                    [Choice((True,c), '[POOL] '+ card2summary(c),
                        c.material in okay_mats) for c in self.pool])

            self.prompt = 'Select material from stockpile or pool to add to building ' + str(self.building)
        else:
            self.prompt = 'Select material from stockpile to add to building ' + str(self.building)

        self.choices.append(Choice('Cancel', 'Cancel'))


    def material_transition(self, choice):
        if choice == 'Cancel':
            self.building = None
            return 'BUILDING'

        else:
            self.from_pool = choice[0]
            choice = choice[1]

        self.material = choice

        return 'FINISHED'


    def foundation_arrival(self):

        def card_okay(c):
            return c.name != 'Jack' and c.material in self.sites_allowed and \
                c.name not in map(str, self.complete_buildings+self.incomplete_buildings) \
                or c.name == 'Statue'

        self.choices = [Choice(c, card2summary(c)) for c in self.hand if card_okay(c)]
        self.choices.append(Choice('Cancel', 'Cancel'))

        self.prompt = 'Select building to start from hand'


    def foundation_transition(self, choice):
        if choice == 'Cancel':
            new_state = 'BUILDING'

        else:
            self.building = Building(choice)

            if self.building.foundation == 'Statue':
                new_state = 'SITE'

            else:
                self.site = self.building.foundation.material
                new_state = 'FINISHED'

        return new_state


    def site_arrival(self):
        self.choices = [Choice(c, c+' Site', c in self.sites_allowed) for c in \
                        cm.get_materials()]

        self.prompt = 'Select a site to start the Statue on'


    def site_transition(self, choice):
        self.site = choice
        return 'FINISHED'


    def finished_arrival(self):
        self.done = True
        self.action = message.GameAction(
                message.ARCHITECT,
                self.building.foundation if self.building else None,
                self.material,
                self.site,
                self.from_pool)


class CraftsmanActionBuilder(FSMActionBuilder):
    """Assembles an architect action. There is a lot of info we need
    from the GameState.
    """

    def __init__(self, buildings, hand, in_town_sites,
            out_of_town_sites, has_road, has_tower,
            has_scriptorium, oot_allowed):

        FSMActionBuilder.__init__(self)


        self.hand = sorted(hand, cm.cmp_jacks_first)

        self.sites_allowed = set(in_town_sites)
        if oot_allowed:
            self.sites_allowed.update(out_of_town_sites)

        self.complete_buildings = [b for b in buildings if b.complete]
        self.incomplete_buildings = [b for b in buildings if not b.complete]

        self.has_road = has_road
        self.has_tower = has_tower
        self.has_scriptorium = has_scriptorium

        self.oot_allowed = oot_allowed

        self.building = None # An object of type Building
        self.material = None
        self.site = None

        self.fsm.add_state('START', None,
                lambda _: 'BUILDING' if len(self.incomplete_buildings) else 'FOUNDATION')
        self.fsm.add_state('BUILDING', 
                self.building_arrival, self.building_transition)
        self.fsm.add_state('MATERIAL', 
                self.material_arrival, self.material_transition)
        self.fsm.add_state('FOUNDATION', 
                self.foundation_arrival, self.foundation_transition)
        self.fsm.add_state('SITE', 
                self.site_arrival, self.site_transition)
        self.fsm.add_state('FINISHED', self.finished_arrival, None, True)

        self.fsm.set_start('START')

        self.fsm.pump(None)

    
    def building_arrival(self):
        materials = [c.material for c in self.hand if c.name != 'Jack']

        available_materials = list(materials)

        self.choices = []
        
        for b in self.incomplete_buildings:
            material = b.foundation.material
            site_material = b.site

            can_add = self.has_road and 'Stone' in (material, site_material) and len(available_materials) or \
                      self.has_tower and 'Rubble' in available_materials or \
                      material in available_materials or site_material in available_materials or \
                      self.has_scriptorium and 'Marble' in available_materials

            self.choices.append(Choice(b, str(b), can_add))

        self.choices.append(Choice('Start', 'Start a new building from hand'))
        self.choices.append(Choice('Skip', 'Skip Craftsman action'))

        self.prompt = 'Select a building to add a material to'


    def building_transition(self, choice):
        if isinstance(choice, Building):
            self.building = choice
            new_state = 'MATERIAL'
            
        elif choice is 'Start':
            new_state = 'FOUNDATION'

        else:
            new_state = 'FINISHED'

        return new_state


    def material_arrival(self):
        # Figure out which materials can potentially be added to a building
        okay_mats = set()

        if self.has_tower:
            okay_mats.add('Rubble')

        if self.has_scriptorium:
            okay_mats.add('Marble')

        materials = self.building.foundation.material, self.building.site
        okay_mats.update(materials)

        if self.has_road and 'Stone' in materials:
            okay_mats = set(cm.get_materials())

        self.choices = [Choice(c, card2summary(c), c.name != 'Jack' and c.material in okay_mats)
                        for c in self.hand]

        self.choices.append(Choice('Cancel', 'Cancel'))

        self.prompt = 'Select material from stockpile to add to building ' + str(self.building)


    def material_transition(self, choice):
        if choice == 'Cancel':
            self.building = None
            return 'BUILDING'

        self.material = choice

        return 'FINISHED'


    def foundation_arrival(self):

        def card_okay(c): 
            return c.name != 'Jack' and c.material in self.sites_allowed and \
                c.name not in map(str, self.complete_buildings+self.incomplete_buildings) \
                or c.name == 'Statue'

        self.choices = [Choice(c, card2summary(c)) for c in self.hand if card_okay(c)]
        self.choices.append(Choice('Cancel', 'Cancel'))

        self.prompt = 'Select building to start from hand'


    def foundation_transition(self, choice):
        if choice == 'Cancel':
            new_state = 'BUILDING'

        else:
            self.building = Building(choice)

            if self.building.foundation == 'Statue':
                new_state = 'SITE'

            else:
                self.site = self.building.foundation.material
                new_state = 'FINISHED'

        return new_state


    def site_arrival(self):
        self.choices = [Choice(c, c+' Site', c in self.sites_allowed) for c in \
                        cm.get_materials()]

        self.prompt = 'Select a site to start the Statue on'


    def site_transition(self, choice):
        self.site = choice
        return 'FINISHED'


    def finished_arrival(self):
        self.done = True
        self.action = message.GameAction(
                message.CRAFTSMAN,
                self.building.foundation if self.building else None,
                self.material,
                self.site)



class Client(object):
    """Rather than interact with the player via the command line and stdout,
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

    def __init__(self):
        self.game = gtr.Game()
        self.game.game_state = None
        self.player_id = None
        self.builder = None

    def get_player(self):
        return self.game.game_state.players[self.player_id]

    def update_game_state(self, gs):
        game_lg.debug('Updating game state')

        self.game.game_state = gs

        ap = self.game.game_state.active_player_index
        if self.player_id == ap:
            game_lg.debug('It\'s your turn')

            method_name = message.get_action_name(self.game.game_state.expected_action)
            method = getattr(self, 'action_' + method_name)

            game_lg.debug('Setting up ' + method_name + ' action builder')

            method()

        else:
            active_player = self.game.game_state.players[ap].name
            game_lg.info('Waiting on player ' + active_player)


    def make_choice(self, choice):
        """Makes a selection of a menu item.
        """
        game_lg.debug('Making selection for client: ' + str(choice))

        # The GUI uses lists indexed from 1, but we need 0-indexed
        if self.player_id != self.game.game_state.active_player_index:
            game_lg.info('It\'s not your turn')
            return

        try:
            self.builder.make_choice(choice-1)
        except InvalidChoiceException:
            game_lg.info('Invalid choice. Enter [1-{0:d}]'.format(
              len(self.builder.choices)))


    def check_action_builder(self):
        """Checks if the action builder is done. If so, return the action
        and clean up the action builder.

        Returns None if the action builder is not finished.
        Returns a GameAction object if it's done.
        """
        if self.builder and self.builder.done:
            action = self.builder.action
            game_lg.debug('Finished action builder, completed action: ' + str(action))
            self.builder = None
            return action
        else:
            game_lg.debug('Require more input to finish action builder.')
            return None


    def get_choices(self):
        if self.builder:
            return self.builder.choices
        else:
            return []


    def action_thinkerorlead(self):
        """Asks whether the player wants to think or lead at the start of their
        turn.
        """
        p = self.get_player()
        if len(p.hand) == 0:
            choices = [Choice(True, 'Thinker'), Choice(False, 'Lead a role', False)]
        else:
            choices = [Choice(True, 'Thinker'), Choice(False, 'Lead a role')]

        self.builder = SingleChoiceActionBuilder(message.THINKERORLEAD, choices)


    def action_usesenate(self):
        """Asks whether the player wants to think or lead at the start of their
        turn.
        """
        i = self.game.game_state.kip_index
        p_name = self.game.game_state.players[p].name

        self.builder = SingleChoiceActionBuilder(message.USESENATE,
            [Choice(True, 'Take {0:d}\'s Jack with Senate'.format(p_name)),
             Choice(False, 'Don\'t take Jack')])


    def action_thinkertype(self):
        """Asks for the type of thinker.
        """
        p = self.get_player()

        n_cards = max(self.game.max_hand_size(p) - len(p.hand), 1)
        cards_str = '{0:d} card{1}'.format(n_cards, 's' if n_cards==1 else '')

        self.builder = SingleChoiceActionBuilder(message.THINKERTYPE,
            [Choice(True, 'Thinker for Jack', bool(self.game.game_state.jacks)),
             Choice(False, 'Thinker for '+cards_str)])


    def action_uselatrine(self):
        """Asks which card, if any, the player wishes to use with the
        Latrine before thinking.
        """
        #game_lg.info('Choose a card to discard with the Latrine.')

        sorted_hand = sorted(self.get_player().hand)
        card_choices = [Choice(c, card2summary(c)) for c in sorted_hand]
        card_choices.insert(0, Choice(None, 'Skip discard'))

        self.builder = SingleChoiceActionBuilder(message.USELATRINE, card_choices)

        self.builder.prompt = 'Select a card to discard with the Latrine'


    def action_skipthinker(self):
        """Asks if the player wants to skip the thinker action.
        """
        choices = [Choice(True, 'Perform thinker'), Choice(False, 'Skip thinker')]

        self.builder = SingleChoiceActionBuilder(message.SKIPTHINKER, choices)

        self.builder.prompt = 'Skip thinker action?'


    def action_baroraqueduct(self):
        self.builder = SingleChoiceActionBuilder(message.BARORAQUEDUCT,
            [Choice(True, 'Bar then Aqueduct'), Choice(False, 'Aqueduct then Bar')])

        self.builder.prompt = 'Use the Bar or the Aqueduct first?'
        #TODO: We still have to answer this even if we want to skip both.


    def action_usevomitorium(self):
        """Asks if the player wants to discard their hand with the Vomitorium.

        Returns True if player uses the Vomitorium, False otherwise.
        """
        self.builder = SingleChoiceActionBuilder(message.USEVOMITORIUM,
            [Choice(True, 'Discard all'), Choice(False, 'Skip Vomitorium')])
        self.builder.prompt = 'Discard hand with Vomitorium?'


    def action_patronfrompool(self):
        p = self.get_player()
        limit = self.game.clientele_limit(p)
        clientele_full = len(p.clientele) >= limit
        self.builder = SingleChoiceActionBuilder(message.PATRONFROMPOOL,
            [ Choice(c, card2summary(c), not clientele_full) for c\
                    in sorted(self.game.game_state.pool) ] + \
            [ Choice(None, 'Skip Patron from pool') ])

        self.builder.prompt = \
            'Performing Patron, choose a client from pool (Clientele {}/{})'.format(
                str(p.n_clients()), str(self.game.clientele_limit(p)))


    def action_patronfromdeck(self):
        p = self.get_player()
        limit = self.game.clientele_limit(p)
        clientele_full = len(p.clientele) >= limit
        self.builder = SingleChoiceActionBuilder(message.PATRONFROMDECK,
            [ Choice(True, 'Patron from the deck', not clientele_full),
              Choice(False, 'Skip Patron from deck') ])

        self.builder.prompt = \
            'Performing Patron, take a card from the deck? (Clientele {}/{})'.format(
                str(p.n_clients()), str(self.game.clientele_limit(p)))


    def action_patronfromhand(self):
        p = self.get_player()
        limit = self.game.clientele_limit(p)
        clientele_full = len(p.clientele) >= limit
        cards = sorted([c for c in hand if c.name != 'Jack'])
        self.builder = SingleChoiceActionBuilder(message.PATRONFROMHAND,
            [ Choice(c, card2summary(c), not clientele_full) for c in cards ] +
            [ Choice(None, 'Skip Patron from hand') ])

        self.builder.prompt = \
            'Performing Patron, choose a client from pool (Clientele {}/{})'.format(
                str(p.n_clients()), str(self.game.clientele_limit(p)))


    def action_usefountain(self):
        self.builder = SingleChoiceActionBuilder(message.USEFOUNTAIN,
            [Choice(True, 'Use Fountain'), Choice(False, 'Don\'t use Fountain')])
        self.builder.prompt = 'Use Fountain to Craftsman from deck?'


    def action_fountain(self):
        """The Fountain allows you to draw a card from the deck, then
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
        #TODO: This is obsolete, but retained so the logic can be copied into a working version
        p = self.get_player()

        skip, building, material, site = (False, None, None, None)

        material_of_card = card2mat(p.fountain_card)

        card_choices = \
          [str(b) for b in p.incomplete_buildings
          if self.game.check_building_add_legal(p, str(b), p.fountain_card)]

        if not p.owns_building(p.fountain_card):
            card_choices.insert(0, 'Start {} buidling'.format(p.fountain_card))

        if len(card_choices) == 0:
            game_lg.warn('Can\'t use {} with a craftsman action'.format(p.fountain_card))
            return message.GameAction(message.FOUNTAIN, True, None, None, None)

        game_lg.info('Performing Craftsman with {}, choose a building option:'
                     .format(p.fountain_card))

        choices = ['Use {} to start or add to a building'.format(p.fountain_card),
                   'Don\'t play card, draw and skip action instead.']
        choice_index = self.choices_dialog(choices)

        if choice_index == 1:
            game_lg.info('Skipping Craftsman action and drawing card')
            return message.GameAction(message.FOUNTAIN, True, None, None, None)

        card_index = self.choices_dialog(card_choices, 'Select a building option')
        if card_index == 0: # Starting a new building
            building = p.fountain_card

            if building == 'Statue':
                sites = cm.get_materials()
                site_index = self.choices_dialog(sites)
                site = sites[site_index]
            else:
                site = card2mat(building)

        else: # Adding to a building from hand
            building = card_choices[card_index-1]
            material = p.fountain_card

        return message.GameAction(message.FOUNTAIN, False, building, material, site)


    def action_usesewer(self):
        """Asks whether the player wants to use their Sewer
        """
        self.builder = SingleChoiceActionBuilder(
                message.USESEWER,
                [Choice(True, 'Use Sewer'),
                 Choice(False, 'Place card in stockpile')])
        return


        #TODO: This is an obsolete implementation of using the Sewer separately for each card
        # This is not how it's handled above, but maybe it should be.
        
        p = self.get_player()
        done=False
        cards_to_move=[]
        choices=['All', 'None']
        choices.extend([card2summary(card)
                        for card in p.camp if card is not 'Jack'])
        while not done:
            game_lg.info('Do you wish to use your Sewer?')

            card_index = self.choices_dialog(choices, 'Select a card to take into your stockpile')
            if card_index == 0:
                cards_to_move.extend(choices[2:])
            elif card_index > 1:
                cards_to_move.append(choices.pop(card_index))
            else:
                done=True

        return message.GameAction(message.USESEWER, cards_to_move)


    def action_laborer(self):
        """Returns (card_from_pool, card_from_hand).
        """
        player = self.get_player()

        has_dock = self.game._player_has_active_building(player, 'Dock')
        pool = self.game.game_state.pool
        hand = player.hand

        self.builder = LaborerActionBuilder(pool, hand, has_dock)


    def action_merchant(self):
        """Returns (card_from_stockpile, card_from_hand, from_deck).
        """
        player = self.get_player()

        self.builder = MerchantActionBuilder(
                player.stockpile, player.hand,
                self.game._player_has_active_building(player, 'Atrium'),
                self.game._player_has_active_building(player, 'Basilica'))


    def action_stairway(self):
        """
        Asks the player if they wish to use the Stairway and returns

        (player, building, material, from_pool)

        player: the player that owns the building
        building: the name (string) of the building
        material: name of the material card to use
        from_pool: bool to use the Archway to take from the pool
        """
        #TODO: This is an obsolete implementation of a Stairway.
        #The logic needs to be converted into an action builder
        p = self.get_player()
        possible_buildings = [(pl, b) for pl in self.game.game_state.players
                              for b in pl.complete_buildings
                              if pl is not p
                              ]
        possible_buildings = sorted(possible_buildings, None, lambda x: x[0].name.lower() + str(x[1]).lower())
        game_lg.info('Use Stairway?')
        building_names = [pl.name + '\'s ' + str(b) for (pl,b) in possible_buildings]
        choices = sorted(building_names)
        choices.insert(0, 'Don\'t use Stairway')
        choice_index = self.choices_dialog(choices, 'Select option for Stairway')

        player_name, building_name, material, from_pool = None, None, None, False
        if choice_index != 0:
            player, building = possible_buildings[choice_index-1]
            player_name = player.name
            building_name = building.foundation

            has_archway = self.game._player_has_active_building(p, 'Archway')

            sorted_stockpile = sorted(p.stockpile)
            game_lg.info('Choose a material to add from your stockpile:')
            card_choices = [card2summary(card) for card in sorted_stockpile]

            if has_archway:
                sorted_pool = sorted(self.game.game_state.pool)
                pool_choices = ['[POOL]' + card2summary(card) for card in sorted_pool]
                card_choices.extend(pool_choices)

            card_index = self.choices_dialog(card_choices, 'Select a material to add')

            if card_index >= len(sorted_stockpile):
                from_pool = True
                material = sorted_pool[card_index - len(sorted_stockpile)]
            else:
                material = sorted_stockpile[card_index]

        return message.GameAction(message.STAIRWAY, player_name, building_name, material, from_pool)


    def action_legionary(self):
        p = self.get_player()

        self.builder = LegionaryActionBuilder(
                p.hand, self.game.game_state.legionary_count)

        
    def action_givecards(self):
        """A GameAction for GIVECARDS must be returned even if we're immune
        or don't have any cards demanded, or we don't have the cards in question.
        We can shortcut the player response, though. Glory to Rome.
        """
        p = self.get_player()
        leg_player = self.game.game_state.players[self.game.game_state.legionary_index]

        legionary_cards = leg_player.revealed

        has_bridge = self.game._player_has_active_building(leg_player, 'Bridge')
        has_coliseum = self.game._player_has_active_building(leg_player, 'Coliseum')

        has_palisade = self.game._player_has_active_building(p, 'Palisade')
        has_wall = self.game._player_has_active_building(p, 'Wall')

        immune = has_wall or (has_palisade and not has_bridge)

        self.builder = GiveCardsActionBuilder(
                map(lambda x: x.material, legionary_cards),
                p.hand,
                p.stockpile,
                p.clientele,
                has_bridge,
                has_coliseum,
                immune)

        
    def action_architect(self):
        """Returns (building, material, site, from_pool) to be built.

        If the action is to be skipped, returns None, None, None
        """
        player = self.get_player()

        self.builder = ArchitectActionBuilder(
                player.buildings,
                player.stockpile,
                player.hand,
                self.game.game_state.pool,
                self.game.game_state.in_town_sites,
                self.game.game_state.out_of_town_sites,
                self.game._player_has_active_building(player, 'Archway'),
                self.game._player_has_active_building(player, 'Road'),
                self.game._player_has_active_building(player, 'Tower'),
                self.game._player_has_active_building(player, 'Scriptorium'),
                self.game.game_state.oot_allowed)
                

    def action_craftsman(self):
        """Returns (building, material, site) to be built.

        If the action is to be skipped, returns None, None, None
        """
        player = self.get_player()

        game_lg.debug('Starting craftsman, out-of-town is ' + \
                        ('' if self.game.game_state.oot_allowed else 'not ') +\
                        'allowed.')

        self.builder = CraftsmanActionBuilder(
                player.buildings,
                player.hand,
                self.game.game_state.in_town_sites,
                self.game.game_state.out_of_town_sites,
                self.game._player_has_active_building(player, 'Road'),
                self.game._player_has_active_building(player, 'Tower'),
                self.game._player_has_active_building(player, 'Scriptorium'),
                self.game.game_state.oot_allowed)
                

    def action_leadrole(self):
        hand = self.get_player().hand
        has_palace = self.game._player_has_active_building(self.get_player(), 'Palace')
        petition_count = 2 if self.game._player_has_active_building(self.get_player(), 'Circus') else 3
        self.builder = RoleActionBuilder(hand, None, has_palace, petition_count)


    def action_followrole(self):
        hand = self.get_player().hand
        has_palace = self.game._player_has_active_building(self.get_player(), 'Palace')
        petition_count = 2 if self.game._player_has_active_building(self.get_player(), 'Circus') else 3
        role = self.game.game_state.role_led
        self.builder = RoleActionBuilder(hand, role, has_palace, petition_count)
