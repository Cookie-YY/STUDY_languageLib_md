import typing
import json
from redis import ConnectionError
from json.decoder import JSONDecodeError

from bytedredis import Client

from modelserver.config import settings


class ByteRedis:
    TTL = 86400
    RETRY_NUM = 3

    def __init__(self) -> None:
        """Initialize redis client from url
        """
        # self.client = redis.Redis.from_url(settings.redis.url)
        self.client = Client.from_url(settings.redis.url)

    def keys(self, pattern: str = '*') -> typing.List[str]:
        """Get keys that matches pattern.

        Args:
            pattern: String pattern.

        Returns:
            Keys that matches pattern.
        """
        return self.client.keys(pattern)

    def set(self, key: str, value: typing.Union[int, str, float, dict, list], ex: typing.Optional[int] = None) -> None:
        """Set value to redis.

        Args:
            key: Key.
            value: Value.
            ex: Expire time in seconds.
        """
        # redis does not support list value
        if isinstance(value, list):
            value = json.dumps(value)
        if type(key) != str:
            raise TypeError('only str is accepted as redis key')
        if type(value) not in {int, str, float, dict, list}:
            raise TypeError('only int, str, float and dict are accepted as redis value')
        if type(value) == dict:
            value = json.dumps(value)

        for i in range(self.RETRY_NUM):
            try:
                self.client.set(key, value, ex)
                break
            except ConnectionError as e:
                if i == self.RETRY_NUM - 1:
                    raise e
                continue

    def get(self, key: str) -> typing.Union[int, str, float, dict, list]:
        """Get value from redis.

        Args:
            key: Key.

        Returns:
            Value.
        """
        value = None
        for i in range(self.RETRY_NUM):
            try:
                value = self.client.get(key)
                break
            except ConnectionError as e:
                if self.RETRY_NUM - 1 == i:
                    raise e
                continue
        try:
            value = json.loads(value)
        except JSONDecodeError:
            pass
        except TypeError:
            pass

        return value

    def delete(self, key: str) -> bool:
        """Delete from redis.

        Args:
            key: Key.

        Returns:
            Whether the delete command was executed successful.
        """
        if not self.client.exists(key):
            return False
        self.client.delete(key)
        return True


Redis = ByteRedis
redis_client = Redis()
