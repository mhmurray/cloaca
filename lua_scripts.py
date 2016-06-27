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
