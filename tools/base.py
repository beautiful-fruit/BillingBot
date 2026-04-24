from discord import Bot, Member, Message, User, TextChannel
from openai.types.chat import ChatCompletionToolUnionParam, ChatCompletionMessageToolCall
from orjson import dumps, loads

from inspect import isawaitable, signature
from typing import (
    Annotated,
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Generic,
    get_args,
    get_origin,
    Literal,
    Optional,
    TypeAlias,
    TypeVar,
    Union,
)
from types import NoneType, UnionType

T = TypeVar("T", bound="Callable")
U = TypeVar("U")

SystemEventCallback: TypeAlias = Callable[[str, TextChannel], Awaitable[None]]


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
    enable_in_system_event: bool

    def __init__(
        self,
        class_name: str,
        func: Callable[..., U],
        description: str = "",
        enable_in_system_event: bool = True
    ) -> None:
        self._class_name = class_name
        self._func = func
        self._description = description
        self._depends = {}
        self.enable_in_system_event = enable_in_system_event

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
            elif type_set.issuperset({Message, NoneType}):
                self._depends[name] = "message"
            elif type_set.issuperset({Message}):
                self._depends[name] = "message"
                self.enable_in_system_event = False
            elif type_set.issuperset({TextChannel}):
                self._depends[name] = "text_channel"
            elif type_set.issuperset({User, Member, NoneType}):
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
        channel: TextChannel,
        message: Optional[Message] = None
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
                if isinstance(channel, TextChannel):
                    function_args[param_name] = channel
                else:
                    raise ValueError("Current channel is not a text channel")
            elif dep == "user_or_member":
                function_args[param_name] = message.author if message else None

        return self._func(**function_args)

    def _map_python_type_to_json_schema(self, ann) -> str:
        origin = get_origin(ann)
        if origin is Annotated:
            ann = ann.__origin__

        if ann is str:
            return "string"
        if ann is int:
            return "integer"
        if ann is float:
            return "number"
        if ann is bool:
            return "boolean"
        if ann in [list, tuple]:
            return "array"
        if ann is dict:
            return "object"

        raise ValueError(f"Unsupported parameter type: {ann}")

    @property
    def tool_param(self) -> ChatCompletionToolUnionParam:
        return self._tool_param


class ToolBase():
    class_name: ClassVar[str]
    description: ClassVar[str]
    _registered_tools: ClassVar[dict[str, ToolData]]
    _bot: ClassVar[Optional[Bot]]
    _system_event_callback: ClassVar[Optional[SystemEventCallback]]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.class_name is None:
            cls.class_name = cls.__name__

        cls.description = getattr(cls, "description", "")
        cls._registered_tools = {}
        cls._bot = None
        cls._system_event_callback = None

    @classmethod
    async def setup(
        cls,
        bot: Bot,
        system_event_callback: SystemEventCallback
    ) -> None:
        cls._bot = bot
        cls._system_event_callback = system_event_callback

    @classmethod
    def register(
        cls,
        description: str,
        *,
        enable_in_system_event: bool = True
    ) -> Callable[[T], T]:
        def decorator(func: T) -> T:
            tool = ToolData(
                class_name=cls.class_name or cls.__name__,
                func=func,
                description=description,
                enable_in_system_event=enable_in_system_event
            )
            cls._registered_tools[tool.function_name] = tool
            return func

        return decorator

    @classmethod
    def get_registered_tools(
        cls,
        in_system_event: bool = False
    ) -> list[ChatCompletionToolUnionParam]:
        if in_system_event:
            return [
                tool.tool_param
                for tool in cls._registered_tools.values()
                if tool.enable_in_system_event
            ]
        return [
            tool.tool_param
            for tool in cls._registered_tools.values()
        ]

    @classmethod
    async def call_tool(
        cls,
        tool_call: ChatCompletionMessageToolCall,
        channel: TextChannel,
        message: Optional[Message] = None,
    ) -> Optional[str]:
        function_name = tool_call.function.name
        tool = cls._registered_tools.get(function_name)
        if not tool or cls._bot is None:
            return None

        result = tool.call(
            tool_call,
            bot=cls._bot,
            channel=channel,
            message=message
        )
        if isawaitable(result):
            result = await result

        try:
            return dumps(result).decode("utf-8")
        except Exception as e:
            raise ValueError(
                f"Tool function return value is not JSON serializable: {str(e)}") from e
