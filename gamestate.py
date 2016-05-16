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


lg = logging.getLogger(__name__)
lg.addHandler(logging.NullHandler())

class GameState(object):
    """Data object containing the state of a game.
    """
