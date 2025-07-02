import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

from django.db import models
from django.utils.translation import gettext_lazy as _


submodule_dir = Path(__file__).parent.parent / "submodules"


class DeviceCategory(models.TextChoices):
    AUTO = "auto", _("Auto")
    COMPUTER = "computer", _("Computer")
    MOBILE = "mobile", _("Mobile")
    SMART_SPEAKER = "smart_speaker", _("Smart speaker")
    SMART_TV = "smart_tv", _("Smart TV")
    WATCH = "watch", _("Watch")


class UserAgentType(models.TextChoices):
    APP = "app", _("App")
    BOT = "bot", _("Bot")
    BROWSER = "browser", _("Browser")
    LIBRARY = "library", _("Library")


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

    if user_agent.startswith("azsdk-python-storage-blob"):
        return UserAgentData(
            user_agent=user_agent,
            type=UserAgentType.LIBRARY,
            is_bot=True,
            name="Azure SDK",
        )

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


def get_dict_from_file(basename: str, value: str) -> dict | None:
    for ua_dict in get_dicts_from_file(basename):
        if re.search(ua_dict["pattern"], value):
            return ua_dict
    return None


def get_dicts_from_file(basename: str) -> list[dict]:
    from spodcat.logs import user_agent

    cached = user_agent.user_agent_dict_cache.get(basename, None)
    if cached is not None:
        return cached

    dicts = []
    json_path = submodule_dir / f"user-agents-v2/src/{basename}.json"

    if json_path.is_file():
        with json_path.open("rt") as f:
            dicts = json.loads(f.read()).get("entries", [])

    user_agent.user_agent_dict_cache[basename] = dicts

    return dicts
