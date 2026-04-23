from os import getenv, listdir
from os.path import isdir
from re import match

AVAILABLE_MODES: list[str] = [
    re_match.group(1)
    for re_match in [
        match(r"^system.(.+).md$", f)
        for f in listdir("prompts")
    ] if re_match is not None
] if isdir("prompts") else []


class OpenAIConfig():
    api_key: str
    base_url: str
    model: str
    max_history_messages: int = 1000
    max_tokens: int = 10_000
    max_tool_iterations: int = 5
    response_mode: str

    def __init__(self):
        api_key = getenv("OPENAI_API_KEY")
        base_url = getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
        model = getenv("OPENAI_MODEL", "gpt-4-0613")

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY must be set in environment variables.")

        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_history_messages = int(getenv(
            "OPENAI_MAX_HISTORY_MESSAGES",
            self.max_history_messages
        ))
        self.max_tokens = int(getenv(
            "OPENAI_MAX_TOKENS",
            self.max_tokens
        ))
        self.max_tool_iterations = int(getenv(
            "OPENAI_MAX_TOOL_ITERATIONS",
            self.max_tool_iterations
        ))

        self.response_mode = "default" if "default" in AVAILABLE_MODES else AVAILABLE_MODES[0]
