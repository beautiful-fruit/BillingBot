from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

from datetime import datetime, timedelta
from typing import Any, Union
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc

START_TS = datetime(
    year=2025,
    month=1,
    day=1,
    tzinfo=UTC
)

TS_LEN = 42
INST_LEN = 10
SEQ_LEN = 12

MAX_TS = (1 << TS_LEN) - 1
MAX_INST = (1 << INST_LEN) - 1
MAX_SEQ = (1 << SEQ_LEN) - 1


class SnowflakeID():
    value: int

    def __init__(self, value: Union[int, str]):
        if isinstance(value, str):
            value = int(value)
        self.value = value

    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, obj: Any) -> bool:
        if isinstance(obj, self.__class__):
            return self.value == obj.value
        return False

    def __hash__(self) -> int:
        return self.value

    @property
    def timestamp(self) -> datetime:
        delta_seconds = (self.value >> (INST_LEN + SEQ_LEN)) / 1000
        return START_TS + timedelta(seconds=delta_seconds)

    @property
    def instance_id(self) -> int:
        return (self.value >> SEQ_LEN) & MAX_INST

    @property
    def sequence(self) -> int:
        return self.value & MAX_SEQ

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema["type"] = "string"
        json_schema["examples"] = ["6209533852516352"]
        json_schema["title"] = "SnowflakeID"
        return json_schema

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        serializer = core_schema.plain_serializer_function_ser_schema(str)
        inner_schema = core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.is_instance_schema(
                cls=cls,
            ),
            serialization=serializer
        )

        def uid_validator(value: Any) -> SnowflakeID:
            if isinstance(value, SnowflakeID):
                return value
            return SnowflakeID(value=value)

        return core_schema.no_info_before_validator_function(uid_validator, inner_schema)


class SnowflakeGenerator():
    _last_timestamp: int
    _sequence: int
    _instance: int

    def __init__(self, instance_id: int = 0):
        self._last_timestamp = 0
        self._sequence = 0
        self._instance = instance_id

    def __next__(self) -> SnowflakeID:
        delta = (datetime.now(UTC) - START_TS)
        current = int(delta.total_seconds() * 1000)

        if current == self._last_timestamp:
            while current != self._last_timestamp:
                delta = (datetime.now(UTC) - START_TS)
                current = int(delta.total_seconds() * 1000)
            self._sequence += 1
        else:
            self._sequence = 0

        self._last_timestamp = current

        value = (current << (INST_LEN + SEQ_LEN))
        value |= self._instance << (SEQ_LEN)
        value |= self._sequence

        return SnowflakeID(value=value)

    def next_id(self) -> SnowflakeID:
        return self.__next__()
