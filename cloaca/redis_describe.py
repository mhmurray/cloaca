#!/usr/bin/env python

GAMEID = 'gameid'
GAMEPREFIX = 'game:'
GAMES = 'games'
GAMES_HOSTED_PREFIX = 'games_hosted:'
GAME_HOSTS = 'game_hosts'
GAME_DATA_KEY = 'game_data'

USERID = 'userid'
USERPREFIX='user:'
USERNAMES='usernames'

SESSIONS='sessions'
SESSION_AUTH_LENGTH_BYTES=16

import redis

import binascii
import sys
import time
import os

def main():
    try:
        action = sys.argv[1]
    except IndexError:
        action = None

    if action == 'describe':
        describe()
    elif action == 'clear':
        clear_database()
    elif action == 'cleargames':
        clear_games()
    elif action == 'addusers':
        for username in sys.argv[2:]:
            add_user(username)
    elif action == 'addusersscript':
        for username in sys.argv[2:]:
            add_user_script(username)
    elif action == 'clearscripts':
        clear_scripts()
    elif action == 'addsession':
        for user_id in sys.argv[2:]:
            add_session(user_id)
    elif action == 'addgames':
        for user_id in sys.argv[2:]:
            add_game(user_id)
    else:
        print 'Need action argument'
        exit()


def describe():
    r = redis.Redis()

    user_id_index = int(r.get(USERID))
    n_users = r.hlen(USERNAMES)

    username_id_dict = r.hgetall(USERNAMES)

    print 'Last used user ID is {0}.'.format(user_id_index)
    print 'There are', n_users, 'users.'
    for username, user_id in username_id_dict.items():
        print user_id, ':', username
        userinfo = r.hgetall(USERPREFIX+user_id)
        info_str = ('    username: {0:>8}  auth: {1:10}  date_added: {2:12}\n'
                '        last_login:{3:12}  session_auth: {4:32}'
                .format(userinfo.get('username', '<MISSING>'),
                        userinfo.get('auth', '<MISSING>'),
                        userinfo.get('date_added', '<MISSING>'),
                        userinfo.get('last_login', '<MISSING>'),
                        userinfo.get('session_auth', '<MISSING>'),
                        ))
        print info_str
        games_hosted = r.lrange(GAMES_HOSTED_PREFIX+str(user_id), 0, -1)
        print '  Hosting {0:d} games : {1}'.format(
                len(games_hosted), ','.join(games_hosted))

    print

    n_sessions = r.hlen(SESSIONS)
    print 'There are {0:d} sessions'.format(n_sessions)
    sessions_map = r.hgetall(SESSIONS)
    print '{0:>32}    {1:>10}'.format('Session', 'User ID')
    for session_auth, user_id in sessions_map.items():
        print '{0:>20}    {1:>10}'.format(session_auth, user_id)

    print

    if r.exists(GAMES):
        n_games = r.llen(GAMES)
        games_list = r.lrange(GAMES, 0, -1)

        print 'There are {0:d} games.'.format(n_games)
        print '{0:>8}    {1:>8}    {2:>15}    {3:>10}'.format(
                'Game ID', 'Host ID', 'Date created', 'JSON')
        for game_id in games_list:
            game_dict = r.hgetall(GAMEPREFIX+str(game_id))
            info_str='{0:>8}    {1:>8}    {2:>15}    {3:>10}'.format(
                    game_id,
                    game_dict.get('host', '<MISSING>'),
                    game_dict.get('date_created', '<MISSING>'),
                    game_dict.get('game_data', '<MISSING>'),
                    )
                    
            print info_str

    print


def clear_users():
    """DELETES ALL USERS FROM THE DATABASE."""
    r = redis.Redis()

    username_id_dict = r.hgetall(USERNAMES)
    for username, user_id in username_id_dict.items():
        r.hdel(USERNAMES, username)
        r.delete(USERPREFIX+user_id)

    r.set(USERID, 0)


def clear_database():
    clear_sessions()
    clear_games()
    clear_users()


def clear_sessions():
    """DELETES ALL SESSION AUTH TOKENS."""
    r = redis.Redis()

    r.delete(SESSIONS)


def clear_scripts():
    """Clears all loaded scripts."""
    r = redis.Redis()
    r.script_flush()


def clear_games():
    """DELETES ALL GAMES."""
    r = redis.Redis()

    game_hosts = r.lrange(GAME_HOSTS, 0, -1)
    for user_id in game_hosts:
        r.delete(GAMES_HOSTED_PREFIX+str(user_id))

    r.delete(GAME_HOSTS)

    games_list = r.lrange(GAMES, 0, -1)
    for game_id in games_list:
        r.delete(GAMEPREFIX+str(game_id))
    
    r.delete(GAMES)
    r.set(GAMEID, 0)


def add_game(user_id):
    """Adds a game with user_id as host.
    """
    r = redis.Redis()

    game_id = r.incr(GAMEID)
    now = int(time.mktime(time.gmtime()))
    r.hmset(GAMEPREFIX+str(game_id), {'host':user_id, 'date_created' : now, 'game_data' : ''})
    r.lpush(GAMES_HOSTED_PREFIX+str(user_id), game_id)
    r.lpush(GAME_HOSTS, user_id)
    r.lpush(GAMES, game_id)


def add_session(user_id):
    # Doing this atomically isn't important because only the session_auth
    # field in the user hash is authoratative. The old session in SESSIONS
    # exists until the new session is completely set up.
    r = redis.Redis()

    if not r.exists(USERPREFIX+str(user_id)):
        print 'User ID {0} doesn\'t exist'.format(user_id)
        return

    old_session_auth = r.hget(USERPREFIX+str(user_id), 'session_auth')

    new_session_auth = binascii.hexlify(os.urandom(SESSION_AUTH_LENGTH_BYTES))

    r.hset(USERPREFIX+str(user_id), 'session_auth', new_session_auth)
    r.hset(SESSIONS, new_session_auth, user_id)
    if old_session_auth is not None:
        r.hdel(SESSIONS, old_session_auth)


def add_user(username):
    r = redis.Redis()

    if r.hexists(USERNAMES, username):
        print 'User already exists:', username, 'with user ID', r.hget(USERNAMES, username)
        return None

    unix_time_utc = int(time.mktime(time.gmtime())) # integer seconds since epoch in UTC
    user_id = r.incr(USERID)
    r.hset(USERNAMES, username, user_id)
    r.hset(USERPREFIX+str(user_id), 'username', username)
    r.hset(USERPREFIX+str(user_id), 'date_added', unix_time_utc)
    return user_id

def add_user_script(username):
    r = redis.Redis()

    script_file = './cloaca/register_user.lua'
    with open(script_file) as f:
        script = f.read()

    register = r.register_script(script)
    
    # The script does it's own check if the user exists, returning False.
    user_id = register(args=[username], keys=[USERID, USERNAMES])

    if user_id:
        unix_time_utc = int(time.mktime(time.gmtime())) # integer seconds since epoch in UTC
        r.hset(USERPREFIX+str(user_id), 'date_added', unix_time_utc)
        return user_id
    else:
        print 'User already exists:', username, 'with user ID', r.hget(USERNAMES, username)
        return None


if __name__ == '__main__':
    main()
