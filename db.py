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
GAMELIST = 'games'

USERID = 'userid'
USERPREFIX='user:'
USERS='usernames'

SESSIONPREFIX='session:'
SESSIONEXPIRE=36000 # 10 hours
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

    @gen.coroutine
    def retrieve_game_id(self):
        """Get a new unique game id. Each call returns a different id.
        """
        game_id = yield self.r.call('INCR', GAMEID)

        if isinstance(game_id, TornadisException):
            raise GTRDBError('Failed to get new game id.')
        else:
            raise gen.Return(game_id)


    @gen.coroutine
    def store_game(self, game_id, game):
        """Stores a Game object. Raise GTRDBError if an error occurs.
        """
        game_json = encode.game_to_json(game)

        pipeline = tornadis.Pipeline()
        pipeline.stack_call('SADD', GAMELIST, game_id)
        pipeline.stack_call('SET', GAMEPREFIX+str(game_id), game_json)

        res = yield self.r.call(pipeline)

        if isinstance(res, TornadisException):
            raise GTRDBError('Failed to store game {0!s}: "{1}"'
                    .format(game_id, res.message))


    @gen.coroutine
    def retrieve_game(self, game_id):
        """Retrieves a Game object.

        Raises GTRDBError if the game does not exist or if there is an error
        communicating with the database.
        """
        game_json = yield self.r.call('GET', GAMEPREFIX+str(game_id))
        if isinstance(game_json, TornadisException):
            raise GTRDBError('Failed to retrieve game {0!s}: "{1}"'
                    .format(game_json.message))
        elif game_json is None:
            raise GTRDBError('Game {0!s} does not exist.'.format(game_id))

        raise gen.Return(encode.decode_game(json.loads(game_json)))


    @gen.coroutine
    def retrieve_games(self, game_ids):
        """Get list of Game objects from a list of game IDs.
        """
        pipeline = tornadis.Pipeline()
        for id in game_ids:
            pipeline.stack_call('GET', GAMEPREFIX+str(id))

        res = yield self.r.call(pipeline)

        if isinstance(res, TornadisException):
            raise GTRDBError('Failed to retrieve {0:d} games: {1}'
                    .format(len(game_ids), res.message))
        else:
            raise gen.Return([encode.json_to_game(r) for r in res])


    @gen.coroutine
    def retrieve_all_games(self):
        """Get all games, return as list of game_ids (strings)
        """
        res = yield self.r.call('SMEMBERS', GAMELIST)
        if isinstance(res, TornadisException):
            raise GTRDBError('Failed to retrieve all game ids: {0}'
                    .format(res.message))
        else:
            raise gen.Return(res)

    
    @gen.coroutine
    def delete_game(self, game_id):
        """Remove game from database.
        """
        pipeline = tornadis.Pipeline()
        pipeline.stack_call('DELETE', GAMEPREFIX+str(game_id))
        pipeline.stack_call('SREM', GAMELIST, game_id)
        res = yield self.r.call(pipeline)
        if isinstance(res, TornadisException):
            raise GTRDBError('Failed to delete game {0!s}: {1}'
                    .format(game_id, res.message))
        else:
            raise gen.Return(res)


    @gen.coroutine
    def add_user(self, username, auth_token):
        """Add a new user with auth_token. Sets the date_added timestamp.
        Auth token is stored in plaintext, so it should be hashed before
        providing it to this function.
        """
        # This check leaves open the possibility that the user is separately
        # registered between the check and the registration, but the register
        # function checks this atomically.
        exists = yield self.r.call('HEXISTS', USERS, username)
        if isinstance(exists, TornadisException):
            raise GTRDBError('Error communicating with database: {0}'
                    .format(exists.message))
        elif exists:
            user_id = yield self.r.call('HGET', USERS, username)
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
                2, USERID, USERS, username)

        if isinstance(result, TornadisException):
            if result.message.startswith('NOSCRIPT'):
                result = yield self.r.call('EVAL', lua_scripts.REGISTER_USER,
                        2, USERID, USERS, username)
            else:
                raise GTRDBError('Failed to register new user {0}: {1}'
                        .format(username, result.message))

        if result is None:
            user_id = yield self.r.call('HGET', USERS, username)
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
        user_id = yield self.r.call('HGET', USERS, username)
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
            raise gen.Return(res)


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
