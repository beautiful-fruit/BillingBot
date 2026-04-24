from os import listdir
from os.path import isdir

PROMPTS_DIR = "prompts"


class PromptStore:
    __builtin_prompts__ = ["system", "summary"]
    system: dict[str, str]
    summary: str
    event: str
    _others: dict[str, str]

    def __init__(self) -> None:
        self.system = {}
        self.summary = ""
        self._others = {}

        if not isdir(PROMPTS_DIR):
            return

        for prompt_file in filter(
            lambda f: f.endswith(".md"),
            listdir(PROMPTS_DIR)
        ):
            with open(f"{PROMPTS_DIR}/{prompt_file}", "r", encoding="utf-8") as f:
                content = f.read()

            prompt_name = prompt_file[:-3]
            if prompt_name.startswith("system"):
                response_mode = prompt_name.split(".", 1)[1] \
                    if "." in prompt_name else "default"
                self.system[response_mode] = content
            elif prompt_name == "summary":
                self.summary = content
            elif prompt_name == "event":
                self.event = content
            else:
                self._others[prompt_name] = content

    def get_system_prompt(self, mode: str) -> str:
        return self.system.get(mode, self.system.get("default", ""))

    def __getattr__(self, name: str) -> str:
        if name in self.__builtin_prompts__:
            return super().__getattribute__(name)
        if name in self._others:
            return self._others[name]
        return ""

    def __getitem__(self, name: str) -> str:
        return self.__getattr__(name)

    def get_all_prompts(self) -> dict[str, str]:
        return {
            **self._others,
            **{
                name: getattr(self, name)
                for name in self.__builtin_prompts__
            },
        }
