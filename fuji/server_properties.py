import json
import sys
from typing import Any, Literal, Mapping, TypedDict, Union, cast

if sys.version_info >= (3, 9):
    from builtins import list as List
else:
    from typing import List

LevelType = Literal[
    "default",
    "normal",
    "flat",
    "large_biomes",
    "amplified",
    "single_biome_surface",
    "buffet",  # <=1.15
    "default_1_1",  # <=1.15
    "customized",  # <=1.15
]

JSON_Any = Union[str, int, float, bool, None, Mapping[str, Any], List[Any]]
JSON_Object = Mapping[str, JSON_Any]

ServerProperties = TypedDict(
    "ServerProperties",
    {
        "enable-jmx-monitoring": bool,
        "rcon.port": int,
        "level-seed": int,
        "gamemode": str,
        "enable-command-block": bool,
        "enable-query": bool,
        "generator-settings": JSON_Object,
        "enforce-secure-profile": bool,
        "level-name": str,
        "motd": str,
        "query.port": int,
        "pvp": bool,
        "generate-structures": bool,
        "max-chained-neighbor-updates": int,
        "difficulty": Literal["peaceful", "easy", "normal", "hard"],
        "network-compression-threshold": int,
        "max-tick-time": int,
        "require-resource-pack": bool,
        "use-native-transport": bool,
        "max-players": int,
        "online-mode": bool,
        "enable-status": bool,
        "allow-flight": bool,
        "initial-disabled-packs": str,
        "broadcast-rcon-to-ops": bool,
        "view-distance": int,
        "server-ip": str,
        "resource-pack-prompt": str,
        "allow-nether": bool,
        "server-port": int,
        "enable-rcon": bool,
        "sync-chunk-writes": bool,
        "op-permission-level": int,
        "prevent-proxy-connections": bool,
        "hide-online-players": bool,
        "resource-pack": str,
        "entity-broadcast-range-percentage": int,
        "simulation-distance": int,
        "rcon.password": str,
        "player-idle-timeout": int,
        "debug": bool,
        "force-gamemode": bool,
        "rate-limit": int,
        "hardcore": bool,
        "white-list": bool,
        "broadcast-console-to-ops": bool,
        "spawn-npcs": bool,
        "spawn-animals": bool,
        "log-ips": bool,
        "function-permission-level": Literal[1, 2, 3, 4],
        "initial-enabled-packs": str,
        "level-type": LevelType,
        "text-filtering-config": None,  # Unfinished feature (by Mojang)
        "spawn-monsters": bool,
        "enforce-whitelist": bool,
        "spawn-protection": int,
        "resource-pack-sha1": str,
        "max-world-size": int,
    },
)


def deserialize_server_properties(properties: str, /) -> ServerProperties:
    """Convert the items in a server.properties file into a dictionary.

    Parameters
    ----------
    server_properties : :class:`str`
        The contents of a server.properties file.

    Returns
    -------
    :class:`dict`
        A mapping of server.properties keys to their converted values.
    """
    result = {}

    for line in properties.splitlines():
        if line.startswith("#"):
            continue  # Skip comments

        key, value = line.split("=", 1)
        new_value: JSON_Any

        if value in ("true", "false"):
            new_value = value == "true"
        elif value.isnumeric():
            new_value = int(value)
        elif value == "":
            new_value = None
        elif value.startswith("{"):
            new_value = json.loads(value)
        else:
            new_value = value  # Leave as string

        result[key] = new_value

    return cast(ServerProperties, result)


def serialize_server_properties(properties: ServerProperties) -> str:
    """Convert a dictionary of server.properties keys and values into a string.

    Parameters
    ----------
    properties : :class:`dict`
        A mapping of server.properties keys to their values.

    Returns
    -------
    :class:`str`
        The contents of a server.properties file.
    """
    lines = []

    for key, value in properties.items():
        if value is None:
            value = ""
        elif isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, int):
            value = str(value)
        elif isinstance(value, dict):
            value = json.dumps(value)
        else:
            value = str(value)

        lines.append(f"{key}={value}")

    return "\n".join(lines)
