import redis

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Test write
r.set("name", "anwer")

# Test read
value = r.get("name")
print("Value from Redis:", value)
