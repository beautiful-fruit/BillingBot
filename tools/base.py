from discord import Bot, Member, Message, User, TextChannel
from openai.types.chat import ChatCompletionToolUnionParam, ChatCompletionMessageToolCall
from orjson import dumps, loads

from inspect import isawaitable, signature
from typing import (
    Annotated,
    Any,
    Callable,
    ClassVar,
    Generic,
    get_args,
    get_origin,
    Literal,
    Optional,
    TypeVar,
    Union,
)
from types import UnionType

T = TypeVar("T", bound="Callable")
U = TypeVar("U")


class ToolData(Generic[U]):
    _class_name: str
    _func: Callable[..., U]
    _description: str
    _depends: dict[str, Literal[
        "bot",
        "message",
        "text_channel",
        "user_or_member"
    ]]
    _tool_param: ChatCompletionToolUnionParam

    def __init__(
        self,
        class_name: str,
        func: Callable[..., U],
        description: str = "",
    ) -> None:
        self._class_name = class_name
        self._func = func
        self._description = description
        self._depends = {}

        parameters = signature(self._func).parameters
        properties = {}
        required = []

        for name, param in parameters.items():
            annotation = param.annotation
            is_annotated = get_origin(annotation) is Annotated

            param_type = annotation.__origin__ if is_annotated else annotation
            param_description = annotation.__metadata__[0] \
                if is_annotated and annotation.__metadata__ else ""

            type_origin = get_origin(param_type)
            if type_origin is Union or type_origin is UnionType:
                type_set = set(get_args(param_type))
            else:
                type_set = {param_type}
            if type_set.issuperset({Bot}):
                self._depends[name] = "bot"
            elif type_set.issuperset({Message}):
                self._depends[name] = "message"
            elif type_set.issuperset({TextChannel}):
                self._depends[name] = "text_channel"
            elif type_set.issuperset({User, Member}):
                self._depends[name] = "user_or_member"

            if name in self._depends:
                continue

            properties[name] = {
                "type": self._map_python_type_to_json_schema(param_type),
                "description": param_description
            }

            if param.default is param.empty:
                required.append(name)

        self._tool_param = {
            "type": "function",
            "function": {
                "name": self.function_name,
                "description": self._description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    @property
    def function_name(self) -> str:
        return f"{self._class_name}-{self._func.__name__}"

    def call(
        self,
        tool_call: ChatCompletionMessageToolCall,
        bot: Bot,
        message: Message
    ) -> U:
        function_args: dict[str, Any] = loads(tool_call.function.arguments)
        if not isinstance(function_args, dict):
            raise ValueError("Tool function arguments must be a JSON object")

        for param_name, dep in self._depends.items():
            if dep == "bot":
                function_args[param_name] = bot
            elif dep == "message":
                function_args[param_name] = message
            elif dep == "text_channel":
                if isinstance(message.channel, TextChannel):
                    function_args[param_name] = message.channel
                else:
                    raise ValueError("Current channel is not a text channel")
            elif dep == "user_or_member":
                function_args[param_name] = message.author

        return self._func(**function_args)

    def _map_python_type_to_json_schema(self, ann) -> str:
        origin = get_origin(ann)
        if origin is Annotated:
            ann = ann.__origin__

        if ann is str:
            return "string"
        elif ann is int:
            return "integer"
        elif ann is float:
            return "number"
        elif ann is bool:
            return "boolean"
        elif ann in [list, tuple]:
            return "array"
        elif ann is dict:
            return "object"

        raise ValueError(f"Unsupported parameter type: {ann}")

    @property
    def tool_param(self) -> ChatCompletionToolUnionParam:
        return self._tool_param


class ToolBase():
    class_name: ClassVar[Optional[str]] = None
    _registered_tools: ClassVar[dict[str, ToolData]] = {}

    @classmethod
    def register(cls, description: str) -> Callable[[T], T]:
        def decorator(func: T) -> T:
            tool = ToolData(
                class_name=cls.class_name or cls.__name__,
                func=func,
                description=description
            )
            cls._registered_tools[tool.function_name] = tool
            return func

        return decorator

    @classmethod
    def get_registered_tools(cls) -> list[ChatCompletionToolUnionParam]:
        return [
            tool.tool_param
            for tool in cls._registered_tools.values()
        ]

    @classmethod
    async def call_tool(
        cls,
        tool_call: ChatCompletionMessageToolCall,
        bot: Bot,
        message: Message
    ) -> Optional[str]:
        function_name = tool_call.function.name
        tool = cls._registered_tools.get(function_name)
        if not tool:
            return None

        result = tool.call(tool_call, bot, message)
        if isawaitable(result):
            result = await result

        try:
            return dumps(result).decode("utf-8")
        except Exception as e:
            raise ValueError(
                f"Tool function return value is not JSON serializable: {str(e)}")
