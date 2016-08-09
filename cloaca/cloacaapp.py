#!/usr/bin/env python

import tornado.ioloop
from tornado.web import StaticFileHandler
from tornado.websocket import WebSocketHandler
from tornado import gen, escape

import os
import os.path
import logging
import logging.config
import json
import re
import argparse

from cloaca.server import GTRServer
import cloaca.db
from cloaca.handlers import (
        BaseHandler, CreateGameHandler, JoinGameHandler,
        StartGameHandler, GameHandler, GameListHandler,
        LoginPageHandler, RegisterHandler, AuthenticateHandler,
        LogoutHandler, GameWSHandler,
        )

lg = logging.getLogger('cloacaapp')

# Set up logging. See logging.json for config
def setup_logging(
        default_path='logging.json',
        default_level=logging.INFO,
        env_key='GTR_LOG_CFG'):
    """Setup logging configuration
    """
    path = default_path
    value = os.getenv(env_key, None)
    if value is not None:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

setup_logging()


def make_app(database):
    path = os.path.dirname(__file__)
    site_path = os.path.join(path, 'site')
    js_path = os.path.join(site_path, 'js')
    ioloop = tornado.ioloop.IOLoop.current()
    ioloop.run_sync(database.load_scripts)

    server = GTRServer(database)

    def send_command(user_id, command):
        try:
            cxn = GameWSHandler.client_cxn_by_user_id[user_id]
        except KeyError:
            lg.debug('User ID {0!s} is not connected.'.format(user_id))
            return

        cxn.send_command(command)

    server.send_command = send_command

    settings = dict(
            cookie_secret='__TODO:_GENERATE_COOKIE_SECRET__',
            login_url='/login',
            xsrf_cookies=True,
            )
    return tornado.web.Application([
        (r'/(favicon.ico)', tornado.web.StaticFileHandler, {'path':site_path}),
        (r'/newgame', CreateGameHandler, {'database':database, 'server':server}),
        (r'/joingame/([0-9]+)', JoinGameHandler, {'database':database, 'server':server}),
        (r'/startgame/([0-9]+)', StartGameHandler, {'database':database, 'server':server}),
        (r'/game/([0-9]+)', GameHandler, {'database':database, 'server':server}),
        (r'/(style.css)', tornado.web.StaticFileHandler, {'path':site_path}),
        (r'/js/(.*)', tornado.web.StaticFileHandler, {'path':js_path}),
        (r'/', GameListHandler, {'database':database}),
        (r'/ws', GameWSHandler, {'database':database, 'server':server}),
        (r'/register', RegisterHandler, {'database': database}),
        (r'/login', LoginPageHandler, {'database': database}),
        (r'/auth', AuthenticateHandler, {'database': database}),
        (r'/logout', LogoutHandler, {'database': database}),
        ],
        **settings)

if __name__ == '__main__':

    parser = argparse.ArgumentParser('Run Cloaca server')
    parser.add_argument('--server-port', default=8080, type=int,
            help=('Default port for the Cloaca server'))
    parser.add_argument('--redis-port', default=6379, type=int,
            help=('Redis port'))
    parser.add_argument('--redis-host', default='localhost',
            help=('Redis host'))
    parser.add_argument('--redis-db', default=0, type=int,
            help=('redis database'))
    # This doesn't work with tornadis.
    #parser.add_argument('--redis-prefix', default='',
    #        help=('Custom prefix to redis keys'))

    args = parser.parse_args()

    lg.info('Starting Cloaca server on port {0}'.format(args.server_port))
    lg.info('Connecting to Redis database at {0}:{1!s}'.format(args.redis_host, args.redis_port))
    database = cloaca.db.connect(
            host=args.redis_host,
            port=args.redis_port,
            prefix='') # prefix doesn't work with Lua scripts yet.

    ioloop = tornado.ioloop.IOLoop.current()
    ioloop.run_sync(lambda: database.select(args.redis_db))

    app = make_app(database)

    app.listen(args.server_port)
    tornado.ioloop.IOLoop.current().start()
