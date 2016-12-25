import json

from cloaca.card import Card
from cloaca import message
from message import GameAction
from encode_binary import GTREncodingError

_CONVERT_STRINGS = {
        'Patron' : 0,
        'Laborer' : 1,
        'Craftsman' : 2,
        'Architect' : 3,
        'Legionary' : 4,
        'Merchant' : 5,
        'Marble' : 0,
        'Rubble' : 1,
        'Wood' : 2,
        'Concrete' : 3,
        'Brick' : 4,
        'Stone' : 5,
        }

def game_action_to_str(action):
    """Serialize a GameAction as a string."""
    def convert(o):
        if o is None:
            return None
        elif isinstance(o, bool):
            return int(o)
        elif isinstance(o, Card):
            return o.ident
        elif isinstance(o, basestring):
            try:
                s = _CONVERT_STRINGS[o]
            except KeyError:
                pass
            else:
                return s
        else:
            return o

    action_list = [action.action] + map(convert, action.args)

    return json.dumps(action_list, separators=(',',':'))
