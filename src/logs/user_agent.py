import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

from django.conf import settings
from django.db import models


class DeviceCategory(models.TextChoices):
    AUTO = "auto"
    COMPUTER = "computer"
    MOBILE = "mobile"
    SMART_SPEAKER = "smart_speaker"
    SMART_TV = "smart_tv"
    WATCH = "watch"


class UserAgentType(models.TextChoices):
    APP = "app", "App"
    BOT = "bot", "Bot"
    BROWSER = "browser", "Browser"
    LIBRARY = "library", "Library"


@dataclass
class UserAgentData:
    user_agent: str
    type: UserAgentType
    name: str
    is_bot: bool
    device_name: str = ""
    device_category: DeviceCategory | None = None

    @classmethod
    # pylint: disable=redefined-builtin
    def from_dicts(
        cls,
        user_agent: str,
        type: UserAgentType,
        ua_dict: "UserAgentDict",
        device: "DeviceDict | None",
    ):
        return cls(
            user_agent=user_agent,
            type=type,
            name=ua_dict["name"],
            is_bot=type == "bot" or ua_dict.get("category") == "bot",
            device_name=device["name"] if device else "",
            device_category=DeviceCategory(device["category"]) if device else None,
        )


class BaseUserAgentDict(TypedDict):
    name: str
    pattern: str
    comments: str | None
    description: str | None
    examples: list[str] | None
    svg: str | None
    urls: list[str] | None


class UserAgentDict(BaseUserAgentDict):
    category: Literal["bot"] | None


class DeviceDict(BaseUserAgentDict):
    category: Literal["auto", "computer", "mobile", "smart_speaker", "smart_tv", "watch"]


class ReferrerDict(BaseUserAgentDict):
    category: Literal["app", "host"]


user_agent_dict_cache: dict[str, list] = {}


def get_referrer_dict(referrer: str) -> ReferrerDict | None:
    return get_dict_from_file("referrers", referrer)


def get_useragent_data(user_agent: str) -> UserAgentData | None:
    basenames: list[tuple[UserAgentType, str]] = [
        (UserAgentType.BOT, "bots"),
        (UserAgentType.APP, "apps"),
        (UserAgentType.LIBRARY, "libraries"),
        (UserAgentType.BROWSER, "browsers"),
    ]

    for key, basename in basenames:
        ua_dict: UserAgentDict | None = get_dict_from_file(basename, user_agent)

        if ua_dict:
            device_dict: DeviceDict | None = get_dict_from_file("devices", user_agent) if key != "bot" else None

            return UserAgentData.from_dicts(
                user_agent=user_agent,
                type=key,
                ua_dict=ua_dict,
                device=device_dict,
            )

    return None


def get_dict_from_file(basename: str, value: str):
    for ua_dict in get_dicts_from_file(basename):
        if re.search(ua_dict["pattern"], value):
            return ua_dict
    return None


def get_dicts_from_file(basename: str):
    from logs import user_agent

    cached = user_agent.user_agent_dict_cache.get(basename, None)
    if cached is not None:
        return cached

    dicts = []
    json_path = Path(settings.BASE_DIR).resolve() / f"user-agents-v2/src/{basename}.json"

    if json_path.is_file():
        with json_path.open("rt") as f:
            dicts = json.loads(f.read()).get("entries", [])

    user_agent.user_agent_dict_cache[basename] = dicts

    return dicts
