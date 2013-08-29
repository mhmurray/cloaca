#!/usr/bin/env python

""" Provides hooks to the possible game actions.
This is meant to be included as an interface for a command intepreter.
See for instance cmd_loop.py. The command interpreter handles
talking to the user and receiving input, which it translates to
calls to this interface.
"""



class CloacaClientHook(object):
  def __init__(self, server_hook, player_name):
    self.server_hook = server_hook
    self.player_name = player_name

  def ThinkerForAJack(self):
    self.server_hook.
