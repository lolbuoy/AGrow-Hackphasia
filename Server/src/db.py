import redis
from config import CONFIG


class RedisDB:
    def __init__(self):
        self.client = redis.Redis(
            host=CONFIG.REDIS_HOST,
            port=CONFIG.REDIS_PORT,
            db=CONFIG.REDIS_DB,
            username=CONFIG.REDIS_USERNAME,
            password=CONFIG.REDIS_PASSWORD,
        )

    def set_key(self, key, value):
        self.client.set(key, value)

    def get_key(self, key):
        return self.client.get(key)


db = RedisDB()
