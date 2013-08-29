#!/usr/bin/env python

import readline
import cmd

""" Accepts control commands for a client in a cloaca game.
All available actions should be accessible through this interface,
but attempting an illegal action will result in an error message
and re-prompting.
"""

class CloacaCmd(cmd.Cmd):
  def CloacaCmd():
    self.prompt = '---->'

  def do_exit(self, line):
    """ Exits the interpreter """
    # The return value here is the 'stop' flag in Cmd.postcmd()
    return True

  def do_EOF(self, line):
    """ Exits the interpreter """
    return True

  def do_quit(self, line):
    """ Exits the interpreter """
    return True

  def postcmd(self, stop, line):
    if stop:
      print('Goodbye!')
      exit()
  

def main():
  interpreter = CloacaCmd()
  interpreter.cmdloop('Welcome to the test-stand for the Cloaca command interpreter')

if __name__ == '__main__':
  main()
