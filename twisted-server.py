#!/usr/bin/env python

from server import User, GameActionProtocol, GameActionFactory

from gtr import Game
from gamestate import GameState
from player import Player

import message
import argparse

from twisted.internet.protocol import ServerFactory, Protocol
from twisted.protocols.basic import NetstringReceiver

import pickle

import logging
import sys


lg = logging.getLogger('gtr')
formatter = logging.Formatter('%(message)s')
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
lg.addHandler(ch)
lg.setLevel(logging.DEBUG)
lg.propagate = False


def main():
    parser = argparse.ArgumentParser(description='Serve a GtR server.')
    parser.add_argument('--port', type=int, default=10000)
    parser.add_argument('--interface', type=str, default='localhost')
    parser.add_argument('--backup-file', type=str, 
            help='Sets file to save backups to. If the file exists, loads backups.')
    parser.add_argument('--load-backup-file', type=str, 
            help='Load backup from this file.')


    args = parser.parse_args()
    factory = GameActionFactory(args.backup_file, args.load_backup_file)

    from twisted.internet import reactor
    port = reactor.listenTCP(args.port, factory, interface=args.interface)

    print 'Serving on {0}'.format(port.getHost())

    reactor.run()


if __name__ == '__main__':
    main()
