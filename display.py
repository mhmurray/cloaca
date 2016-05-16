"""Module with classes that display game objects such as
GameState, Player, Building.
"""

from collections import Counter

import card_manager as cm
from gtrutils import get_detailed_zone_summary, get_building_info, get_short_zone_summary, get_detailed_card_summary

class GameStateTextDisplay(object):
    """Display class for GameState objects.

    The description is returned as a list of strings, one per line.

    Args:
    game_state -- (GameState) object to display
    player_name -- (string) name of the player observing this game state. They
        will be listed first in the display. If unspecified, the leader will
        be the first in the player list.
    """

    def __init__(self, game_state, player=None):
        self.game_state = game_state
        self.player_name = player

    def public_text_string(self):
        """Return a list of strings that shows the current game state.
        """
        gs = self.game_state
        start_player = gs.players[0]
        for p in gs.players:
            if p.name == self.player_name:
                start_player = p

        s = []
        # print leader and priority
        s.append('--> Turn {0} | leader: {1} | priority: {2}'.format(
          gs.turn_index,
          gs.players[gs.leader_index].name,
          gs.players[gs.priority_index].name,
        ))

        # print pool.
        pool_string = 'Pool: '
        pool_mats = Counter([c.material for c in gs.pool])
        pool_string += '  '.join([mat[:3] + ' x' + str(cnt) for mat, cnt in pool_mats.items()]) + '\n'

        

        s.append(pool_string)

        s.append('({0:d}/{1:d}) Library/Jacks'
                .format(len(gs.library), len(gs.jacks)))

        sites_string = ' '.join(
                [mat[:3]+'[{0:d}/{1:d}]'.format(gs.in_town_sites.count(mat),
                                                gs.out_of_town_sites.count(mat)) 
                for mat in cm.get_materials()]
                ) + '   Sites [in/out]'

        s.append(sites_string)

        s.append('')
        for player in gs.players_in_turn_order(start_player):
            disp = PlayerTextDisplay(player)
            s.extend(disp.text())
            s.append('')
        
        return s

class PlayerTextDisplay(object):
    """A class to display information about one player in text.

    Methods are provided that return a string describing each of the
    player's zones, eg. clientele(), and one method to get all of it
    at once, all(), which returns a list of strings, one per line.
    """
    
    def __init__(self, player):
        self.player = player

    def text(self):
        player = self.player
        s = []
        # name
        s.append('--> Player {0} :'.format(player.name))

        # hand
        s.append(self.hand_private())

        # Vault
        if len(player.vault) > 0:
            s.append(self.vault_public())

        # influence
        if player.influence:
            s.append(self.influence())

        # clientele
        if len(player.clientele) > 0:
            s.append(self.clientele())

        # Stockpile
        if len(player.stockpile) > 0:
            s.append(self.stockpile())

        # Buildings
        if len(player.buildings) > 0:
            # be sure there is at least one non-empty site
            for building in player.buildings:
                if building:
                    s.append(self.buildings())
                    break


        # Camp
        if len(player.camp) > 0:
            s.append(self.camp())

        # Revealed cards
        if len(player.revealed) > 0:
            s.append(self.revealed())


        # TODO Fountain revealed card

        return s

    def hand_public(self):
        """Return a string describing the player's public-facing hand.

        Revealed information is the number of cards and the number of jacks.
        """
        n_jacks = self.player.hand.count('Jack')
        hand_string = 'Hand : {0:d} cards (inc. {1:d} jacks)'
        return hand_string.format(len(self.player.hand), n_jacks)

    def hand_private(self):
        """Return a string describing all of the player's hand."""
        cards_string = '{0}: \n'.format(self.hand_public())
        cards_string += get_detailed_zone_summary(self.player.hand)

        return cards_string

    def vault_public(self):
        """Return a string describing the player's public-facing vault."""
        return 'Vault : {0:d} cards'.format(len(self.player.vault))

    def clientele(self):
        """Return a string describing a player's clientele."""
        roles = []
        for card in self.player.clientele:
            roles.append(card.role)
        cards_string = 'Clientele : ' + get_short_zone_summary(roles)
        return cards_string

    def stockpile(self):
        """Return a string describing a player's stockpile."""
        materials = []
        for card in self.player.stockpile:
            materials.append(card.material)
        cards_string = 'Stockpile : ' + get_short_zone_summary(materials)
        return cards_string

    def buildings(self):
        """Return a string describing the player's buildings."""
        cards_string = 'Buildings: \n'
        buildings_info = []
        for building in self.player.buildings:
            if building:
                buildings_info.append(get_building_info(building))
        cards_string += '\n'.join(buildings_info)
        return cards_string

    def influence(self):
        """Return a string describing the player's influence."""
        influence_string = 'Influence : {0}'.format(self.player.influence_points)
        return influence_string

    def camp(self):
        """Return a string describing the player's camp."""
        cards_string = 'Camp : \n' + get_detailed_zone_summary(self.player.camp)
        return cards_string

    def revealed(self):
        """Return a string describing the player's cards revealed
        with Legionary.
        """
        cards_string = 'Revealed : \n' + get_detailed_zone_summary(self.player.revealed)
        return cards_string
