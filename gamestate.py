import gtrutils
from error import GTRError
from player import Player
from building import Building
import random
import logging
import card_manager
from collections import Counter
from zone import Zone
from card import Card

import stack

lg = logging.getLogger(__name__)
lg.addHandler(logging.NullHandler())

class GameState(object):
    """Data object containing the state of a game.
    """

    def __init__(self):
        self.players = []
        self.leader_index = None
        self.turn_number = 0
        self.is_role_led = False
        self.role_led = None
        self.active_player = None
        self.turn_index = 0
        self.jacks = Zone()
        self.library = Zone()
        self.pool = Zone()
        self.in_town_sites = []
        self.out_of_town_sites = []
        self.oot_allowed = False
        self.used_oot = False
        self.stack = stack.Stack()
        self.legionary_count = 0
        self.legionary_index = 0
        self.legionary_resp_indices = []
        self.kip_index = 0
        self.senate_resp_indices = []
        self.expected_action = None
        self.game_id = 0
        self.host = None

        self.game_log = []

