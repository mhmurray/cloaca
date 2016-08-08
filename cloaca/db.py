import redis
import json
import time

import tornado
from tornado import gen
import tornadis
from tornadis.exceptions import TornadisException

from cloaca.error import GTRDBError
import cloaca.encode

from cloaca import lua_scripts

GAMEID = 'gameid'
GAMEPREFIX = 'game:'
GAMES = 'games'
GAMES_HOSTED_PREFIX = 'games_hosted:'
GAMES_JOINED_PREFIX = 'games_joined:'
GAME_HOSTS = 'game_hosts'

USERID = 'userid'
USERPREFIX='user:'
USERNAMES='usernames'

SESSIONS='sessions'
SESSION_AUTH_LENGTH_BYTES=16

db = None

def connect():
    global db
    if db is None:
        db = GTRDBTornadis()
    return db


class GTRDBTornadis(object):

    def __init__(self, host='localhost', port=6379, autoconnect=True):
        self.r = tornadis.Client()

        self.scripts_sha = {}


    @gen.coroutine
    def load_scripts(self):
        sha = yield self.r.call("SCRIPT", "LOAD", lua_scripts.REGISTER_USER)
        self.scripts_sha['register'] = sha

        sha = yield self.r.call("SCRIPT", "LOAD", lua_scripts.CREATE_GAME)
        self.scripts_sha['create_game'] = sha


    @gen.coroutine
    def create_game_with_host(self, host_user_id):
        """Create a new game hosted by user with ID host_user_id.
        Return the new game ID.
        
        First verifies that the host user exists.
        """
        game_id = yield self.r.call('EVALSHA', self.scripts_sha['create_game'],
                5,
                GAMEID,
                USERPREFIX+str(host_user_id),
                GAMES_HOSTED_PREFIX+str(host_user_id),
                GAMES,
                GAME_HOSTS,
                host_user_id)


        if not game_id:
            raise GTRDBError('Host user (ID {0:d}) does not exist.'.format(host_user_id))

        now = int(time.mktime(time.gmtime()))
        yield self.r.call('HMSET', GAMEPREFIX+str(game_id), 'date_created', now, 'game_json', '')

        raise gen.Return(game_id)


    @gen.coroutine
    def store_game(self, game_id, game_json):
        """Stores JSON-encoded Game object. Raise GTRDBError if an error occurs.
        """
        #game_json = encode.game_to_json(game)

        res = yield self.r.call('HSET', GAMEPREFIX+str(game_id), 'game_json', game_json)

        if isinstance(res, TornadisException):
            raise GTRDBError('Failed to store game {0!s}: "{1}"'
                    .format(game_id, res.message))


    @gen.coroutine
    def retrieve_game(self, game_id):
        """Retrieves a game, returning the JSON-encoding of the Game object.

        Raises GTRDBError if the game does not exist or if there is an error
        communicating with the database.
        """
        game_json = yield self.r.call('HGET', GAMEPREFIX+str(game_id), 'game_json')
        if isinstance(game_json, TornadisException):
            raise GTRDBError('Failed to retrieve game {0!s}: "{1}"'
                    .format(game_json.message))
        elif game_json is None:
            raise GTRDBError('Game {0!s} does not exist.'.format(game_id))

        #game_obj = encode.decode_game(json.loads(game_json))
        raise gen.Return(game_json)


    @gen.coroutine
    def retrieve_games(self, game_ids):
        """Retrieves a list of games as the JSON-encoding of the Game object.

        If a game doesn't exist, None will be returned in its place.
        """
        if len(game_ids) == 0:
            raise gen.Return([])
        else:
            pipeline = tornadis.Pipeline()

            for game_id in game_ids:
                pipeline.stack_call('HGET', GAMEPREFIX+str(game_id), 'game_json')

            pipeline = yield self.r.call(pipeline)

            raise gen.Return(pipeline)


    @gen.coroutine
    def retrieve_games_hosted_by_user(self, user_id):
        """Get list of game_ids hosted by user with ID user_id.
        """
        game_ids = yield self.r.call('LRANGE', GAMES_HOSTED_PREFIX+str(user_id), 0, -1)
        if isinstance(game_ids, TornadisException):
            raise GTRDBError('Failed to retrieve games hosted by user: {0}'
                    .format(user_id))
        else:
            raise gen.Return(game_ids)


    @gen.coroutine
    def retrieve_latest_games(self, n_games):
        """Get the n_games most recently-created games.
        """
        game_ids = yield self.r.call('LRANGE', GAMES, 0, n_games)
        raise gen.Return(game_ids)

    
    @gen.coroutine
    def add_user(self, username, auth_token):
        """Add a new user with auth_token. Sets the date_added timestamp.
        Auth token is stored in plaintext, so it should be hashed before
        providing it to this function.
        """
        # This check leaves open the possibility that the user is separately
        # registered between the check and the registration, but the register
        # function checks this atomically.
        exists = yield self.r.call('HEXISTS', USERNAMES, username)
        if isinstance(exists, TornadisException):
            raise GTRDBError('Error communicating with database: {0}'
                    .format(exists.message))
        elif exists:
            user_id = yield self.r.call('HGET', USERNAMES, username)
            if user_id is not None:
                raise GTRDBError('User {0} already exists with user ID {1}'
                        .format(username, user_id))
            else:
                raise GTRDBError('User {0} exists, but no user ID found.'
                        .format(username))

        user_id = yield self.register_user(username)
        unix_time_utc = int(time.mktime(time.gmtime()))

        result = yield self.r.call('HMSET', USERPREFIX+str(user_id),
                'date_added', unix_time_utc,
                'last_login', unix_time_utc,
                'auth', auth_token)

        if isinstance(result, TornadisException):
            raise GTRDBError(result.message)

        raise gen.Return(user_id)


    @gen.coroutine
    def register_user(self, username):
        result = yield self.r.call('EVALSHA', self.scripts_sha['register'],
                2, USERID, USERNAMES, username)

        if isinstance(result, TornadisException):
            if result.message.startswith('NOSCRIPT'):
                result = yield self.r.call('EVAL', lua_scripts.REGISTER_USER,
                        2, USERID, USERNAMES, username)
            else:
                raise GTRDBError('Failed to register new user {0}: {1}'
                        .format(username, result.message))

        if result is None:
            user_id = yield self.r.call('HGET', USERNAMES, username)
            if user_id is not None:
                raise GTRDBError('User {0} already exists with user ID {1}'
                        .format(username, user_id))

            raise GTRDBError('Failed to register new user {0}'
                    .format(username))
        else:
            raise gen.Return(result)


    @gen.coroutine
    def update_user_last_login(self, user_id, last_login_time):
        """Updates <last_login> field of user hash to last_login_time,
        represented as integer seconds since the UNIX epoch, UTC.

        Raise GTRDBError if user doesn't exist.
        """
        yield self.r.call('HSET', USERPREFIX+str(user_id), 'last_login', last_login_time)



    @gen.coroutine
    def retrieve_user_id_from_username(self, username):
        """Get user_id from username by examining the "users" table.
        Return None if the username is not found.
        """
        user_id = yield self.r.call('HGET', USERNAMES, username)
        if isinstance(user_id, TornadisException): 
            raise GTRDBError('Failed to get user ID for {0}: {1}'
                    .format(username, user_id.message))
        else:
            raise gen.Return(user_id)


    @gen.coroutine
    def retrieve_user_auth(self, user_id):
        user_auth = yield self.r.call('HGET', USERPREFIX+str(user_id), 'auth')
        if isinstance(user_auth, TornadisException):
            raise GTRDBError('Failed to get user auth for {0}: {1}'
                    .format(username, res.message))
        else:
            raise gen.Return(user_auth)


    @gen.coroutine
    def retrieve_user_session_auth(self, user_id):
        session_auth = yield self.r.call(
                'HGET', USERPREFIX+str(user_id), 'session_auth')
        if isinstance(session_auth, TornadisException):
            raise GTRDBError('Failed to get session token for {0}: {1}'
                    .format(username, session_auth.message))
        else:
            raise gen.Return(session_auth)


    @gen.coroutine
    def retrieve_userid_from_session_auth(self, session_auth):
        user_id = yield self.r.call('HGET', SESSIONS, session_auth)
        raise gen.Return(user_id)


    @gen.coroutine
    def retrieve_user(self, user_id):
        """Return the entire User dictionary.
        """
        res = yield self.r.call('HGETALL', USERPREFIX+str(user_id))
        if isinstance(res, TornadisException):
            raise GTRDBError('Failed to retrieve user {0!s}: {1}'
                    .format(user_id, res.message))
        else:
            # tornadis gives us hashes as lists, with alternating
            # key1, value1, key2, value2, etc.
            # This formats as a Python dict.
            user_dict = dict(zip(res[::2], res[1::2]))
            raise gen.Return(user_dict)


    @gen.coroutine
    def update_user_session(self, user_id, session_auth):
        """Replaces a session token for user.
        """
        old_session_auth = yield self.r.call(
                'HGET', USERPREFIX+str(user_id), 'session_auth')

        pipeline = tornadis.Pipeline()
        pipeline.stack_call('HSET', USERPREFIX+str(user_id),
                'session_auth', session_auth)

        if old_session_auth is not None:
            pipeline.stack_call('HDEL', SESSIONS, old_session_auth)

        pipeline.stack_call('HSET', SESSIONS, session_auth, user_id)
        res = yield self.r.call(pipeline)
