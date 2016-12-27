#!/usr/bin/env python

import tornado.ioloop
from tornado.web import StaticFileHandler
from tornado.websocket import WebSocketHandler
from tornado import gen, escape
import tornado.httpserver

import os
import os.path
import logging
import logging.config
import json
import re
import argparse
import sys

from cloaca.server import GTRServer
import cloaca.db
import cloaca.handlers
from cloaca.handlers import (
        BaseHandler, CreateGameHandler, JoinGameHandler,
        StartGameHandler, GameHandler, GameListHandler,
        LoginPageHandler, RegisterHandler, AuthenticateHandler,
        LogoutHandler, GameWSHandler,
        )

lg = logging.getLogger('cloacaapp')

_DEFAULT_LOG_CONFIG_PATH = os.path.join(cloaca.handlers.APPDIR, 'logging_default.json')

class _LoggingSetupError(Exception):
    """Exception used only in the following logging setup code."""
    pass

def _setup_logging_imp(path):
    """Logging setup. See `setup_logging()`.

    Raise _LoggingSetupError if anything goes wrong.
    """
    try:
        with open(path, 'rt') as f:
            try:
                config = json.load(f)
            except ValueError as e:
                raise _LoggingSetupError('Error parsing JSON in file {0}: {1}'
                        .format(path, e.message))
    except IOError as e:
        raise _LoggingSetupError(str(e))

    try:
        logging.config.dictConfig(config)
    except ValueError as e:
        raise _LoggingSetupError('Failed to load logging config from file {0}. {1}'
                .format(path, e.message))


def setup_logging(path):
    """Get log config from file. If parsing the JSON fails or the file cannot
    be read, an error is printed, and the default configuration is loaded.
    
    If this fails, `logging.config.basicConfig()` is used instead
    """
    try:
        _setup_logging_imp(path)
        return
    except _LoggingSetupError as e:
        sys.stderr.write(e.message+'\n')

        if path != _DEFAULT_LOG_CONFIG_PATH:
            try:
                _setup_logging_imp(_DEFAULT_LOG_CONFIG_PATH)
                sys.stderr.write('Using default logging config instead.\n')
                return
            except _LoggingSetupError as e:
                sys.stderr.write(e.message+'\n')

    sys.stderr.write('Using logging.config.basicConfig() instead.\n')
    logging.basicConfig(level=logging.WARNING)


def make_app(database):
    app_path = cloaca.handlers.APPDIR
    site_path = os.path.join(app_path, 'site')
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
    # WEBSOCKET_URI = '/ws/'
    WEBSOCKET_URI = '/ws'
    JS_MIN = 'cloaca.min.js'
    CSS_MIN = 'style.min.css'

    # Check if minified files have been built and use them in GameHandler.
    js_main_path = '/js/main'
    if os.path.exists(os.path.join(site_path, JS_MIN)):
        js_main_path = os.path.join('/', JS_MIN.rstrip('.js'))

    css_path = '/style.css'
    if os.path.exists(os.path.join(site_path, CSS_MIN)):
        css_path = os.path.join('/', CSS_MIN)

    return tornado.web.Application([
        (r'/(favicon.ico)', tornado.web.StaticFileHandler, {'path':site_path}),
        (r'/newgame', CreateGameHandler, {'database':database, 'server':server}),
        (r'/joingame/([0-9]+)', JoinGameHandler, {'database':database, 'server':server}),
        (r'/startgame/([0-9]+)', StartGameHandler, {'database':database, 'server':server}),
        (r'/game/([0-9]+)', GameHandler, {'database':database, 'server':server,
            'websocket_uri':WEBSOCKET_URI,
            'js_main_path': js_main_path,
            'stylesheet_path': css_path,
            }),
        (r'/(style.css)', tornado.web.StaticFileHandler, {'path':site_path}),
        (r'/(style.min.css)', tornado.web.StaticFileHandler, {'path':site_path}),
        (r'/js/(.*)', tornado.web.StaticFileHandler, {'path':js_path}),
        (r'/(cloaca.min.js)', tornado.web.StaticFileHandler, {'path':site_path}),
        (r'/', GameListHandler, {'database':database}),
        (WEBSOCKET_URI, GameWSHandler, {'database':database, 'server':server}),
        #(r'/register', RegisterHandler, {'database': database}),
        (r'/login', LoginPageHandler, {'database': database}),
        (r'/auth', AuthenticateHandler, {'database': database}),
        (r'/logout', LogoutHandler, {'database': database}),
        ],
        **settings)

if __name__ == '__main__':

    parser = argparse.ArgumentParser('Run Cloaca server')
    parser.add_argument('--port', default=8080, type=int,
            help=('Default port for the Cloaca server'))
    parser.add_argument('--redis-port', default=6379, type=int,
            help=('Redis port'))
    parser.add_argument('--redis-host', default='localhost',
            help=('Redis host'))
    parser.add_argument('--redis-db', default=0, type=int,
            help=('Redis database'))
    parser.add_argument('--no-ssl', default=False, action='store_true',
            help=('Run server without SSL'))
    parser.add_argument('--ssl-cert', default=None,
            help=('SSL Certificate path'))
    parser.add_argument('--ssl-key', default=None,
            help=('SSL Key path'))
    # This doesn't work with tornadis.
    #parser.add_argument('--redis-prefix', default='',
    #        help=('Custom prefix to redis keys'))
    parser.add_argument('--log-config',
            help=('Path to logging config file. See --log-create-config.'))
    parser.add_argument('--log-level',
            help=('Globally set the log level for all modules. Valid settings '
                  'are the same as the Python logging module (eg. DEBUG). '
                  'Overrides configuration in --log-config.'))
    parser.add_argument('--log-create-config', nargs='?',
            help=('Generate a logging config file in the current directory '
                  'and exit. A file name can be specified or '
                  'or "log_config.json" is used by default.'))

    args = parser.parse_args()

    # Logging configuration
    if args.log_create_config is not None:
        filename = args.log_create_config
        if filename is None:
            filename = 'log_config.json'

        if os.path.exists(filename):
            sys.stderr.write('Could not create log config file {0} because '
                    'that file already exists. Please move it out of the way.\n'
                    .format(filename))
            exit(1)
        else:
            import shutil
            logging_config_default = os.path.join(cloaca.handlers.APPDIR, 'logging_default.json')
            shutil.copy(logging_config_default, filename)
            sys.stderr.write('Created {0}\n'.format(filename))
            exit(0)


    if args.log_config is not None:
        if os.path.isabs(args.log_config):
            log_config = args.log_config
        else:
            log_config = os.path.abspath(os.path.join(os.getcwd(), args.log_config))
    else:
        log_config = os.path.join(cloaca.handlers.APPDIR, 'logging_default.json')

    setup_logging(log_config)


    if args.log_level is not None:
        try:
            # In case of numeric level
            level = int(args.log_level)
        except ValueError:
            # Assume string like DEBUG. setLevel() will catch further errors.
            level = args.log_level

        try:
            logging.getLogger('tornado').setLevel(level)
            logging.getLogger('cloaca').setLevel(level)
            logging.getLogger('cloacaapp').setLevel(level)
            logging.getLogger('handlers').setLevel(level)
            logging.getLogger('tornadis').setLevel(level)
        except ValueError as e:
            sys.stderr.write(e.message + '\n')


    # Check for SSL cert or --no-ssl
    if not args.no_ssl and (args.ssl_cert is None or args.ssl_key is None):
        sys.stderr.write(
                '--no-ssl argument was not specified but no SSL cert or key '
                'provided (--ssl-cert / --ssl-key\n')
        sys.exit(1)


    # Connect to database
    lg.info('Connecting to Redis database at {0}:{1!s}'.format(args.redis_host, args.redis_port))
    database = cloaca.db.connect(
            host=args.redis_host,
            port=args.redis_port,
            prefix='') # prefix doesn't work with Lua scripts yet.

    ioloop = tornado.ioloop.IOLoop.current()
    ioloop.run_sync(lambda: database.select(args.redis_db))


    # Start server
    lg.info('Starting Cloaca server on port {0}'.format(args.port))
    app = make_app(database)

    settings = {}
    if not args.no_ssl:
        settings['ssl_options'] = {
                    "certfile": os.path.abspath(args.ssl_cert),
                    "keyfile": os.path.abspath(args.ssl_key),
                }

    httpserver = tornado.httpserver.HTTPServer(app, **settings)

    httpserver.listen(args.port)
    tornado.ioloop.IOLoop.current().start()
