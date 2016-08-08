# Atomically checks if username is available, increments user id,
# and registers username with the new user_id.
#
# KEYS[1] is "userid"
# KEYS[2] is the "users" list of user_ids by username
# ARGV[1] is the requested username
#
# Returns the new user_id if username is available, false otherwise.
#
# Note, because this dynamically generates the user_id, it technically
# doesn't comply with the rule that all keys be passed in via the KEYS
# table. This should only be a problem if running in Redis Cluster in
# the future.
REGISTER_USER="""
if redis.call("HEXISTS", KEYS[2], ARGV[1]) == 1 then
    return false
else
    local user_id = redis.call("INCR", KEYS[1])
    redis.call("HSET", "user:"..user_id, "username", ARGV[1])
    redis.call("HSET", KEYS[2], ARGV[1], user_id)
    return user_id
end
"""

# Creates a new game with given host user ID. Sets the 'host' field,
# but not the 'date_created' or 'game_json' fields.
#
# KEYS[1] is 'gameid'
# KEYS[2] is 'user:<host_user_id>'
# KEYS[3] is 'games_hosted:<host_user_id>'
# KEYS[4] is 'games'
# KEYS[5] is 'game_hosts'
# ARGV[1] is host_user_id
CREATE_GAME="""
if redis.call("EXISTS", KEYS[2]) == 0 then
    return false
else
    local game_id = redis.call("INCR", KEYS[1])
    redis.call("HMSET", "game:"..game_id, "host", ARGV[1])
    redis.call("LPUSH", KEYS[3], game_id)
    redis.call("LPUSH", KEYS[4], game_id)
    redis.call("LPUSH", KEYS[5], ARGV[1])
    return game_id
end
"""
