#!/usr/bin/env python

import pprint

pp = pprint.PrettyPrinter(indent=2)

class Player:
  def __init__(self, hand = None):
    self.hand = hand or []

  def __repr__(self):
    rep='Player(hand={hand!r})'.format(hand=self.hand)
    return rep

class Game:
  def __init__(self, players = []):
    self.players = []
    for player in players:
      self.players.append(player)

  def __repr__(self):
    rep='Game(players={players!r})'.format(players=self.players)
    return rep


the_players = []
#for i in range(0,2):
#  the_players.append(Player())
player1 = Player()
player2 = Player()
the_players.append(player1)
the_players.append(player2)

game = Game(the_players)

print 'Initializing game with players...'
pp.pprint(vars(game))

print 'Setting hands...'
game.players[0].hand.append('name1')
game.players[1].hand.append('name2')
pp.pprint(vars(game))
