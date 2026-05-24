import codecs
import logging
import re
from typing import Any

from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncApp
from slack_bolt.async_app import AsyncRespond
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.commands.channel.anchor import anchor_handler
from slack_extra.commands.channel.manager import manager_handler
from slack_extra.commands.channel.move import move_handler
from slack_extra.commands.group import group_handler
from slack_extra.commands.info import info_handler
from slack_extra.commands.love import love_handler
from slack_extra.commands.spoiler import spoiler_handler
from slack_extra.config import config
from slack_extra.utils.logging import send_heartbeat

COMMANDS = [
    {
        "name": "info",
        "description": "Get info about users or channels",
        "function": info_handler,
        "parameters": [
            {
                "name": "user",
                "type": "user",
                "description": "Can be a user mention, ID or email",
                "default": None,
            },
            {
                "name": "channel",
                "type": "channel",
                "description": "Channel mention or id",
                "default": None,
            },
        ],
    },
    {
        "name": "spoiler",
        "description": "Send a message hidden behind a spoiler button",
        "function": spoiler_handler,
        "parameters": [
            {
                "name": "spoiler",
                "type": "string",
                "description": "Text to hide!",
                "required": False,
            }
        ],
    },
    {
        "name": "group",
        "description": "Join or leave a user group!",
        "function": group_handler,
        "parameters": [
            {
                "name": "action",
                "type": "choice",
                "choices": ["join", "leave"],
                "description": "Join or leave a user group",
                "required": True,
            },
            {
                "name": "group",
                "type": "subteam",
                "required": True,
                "description": "The user group to join or leave",
            },
        ],
    },
    {
        "name": "channel",
        "description": "Channel management commands",
        "subcommands": [
            {
                "name": "move",
                "description": "Automatically move users from one channel to another",
                "function": move_handler,
                "parameters": [
                    {
                        "name": "start",
                        "type": "channel",
                        "description": "Origin channel with all the users in",
                        "required": False,
                    },
                    {
                        "name": "end",
                        "type": "channel",
                        "description": "End channel that users will be moved to",
                        "required": False,
                    },
                    {
                        "name": "exclude",
                        "type": "string",
                        "description": "Comma-separated list of user IDs to exclude from moving",
                        "required": False,
                    },
                ],
            },
            {
                "name": "anchor",
                "description": "Anchor a message in the current channel",
                "function": anchor_handler,
                "parameters": [
                    {
                        "name": "action",
                        "type": "choice",
                        "choices": ["enable", "disable"],
                        "required": False,
                    }
                ],
            },
            {
                "name": "manager",
                "description": "Manage your channel managers",
                "function": manager_handler,
                "parameters": [
                    {
                        "name": "action",
                        "type": "choice",
                        "choices": ["get", "add", "remove"],
                        "description": "Action to perform",
                        "required": True,
                    },
                    {
                        "name": "user",
                        "type": "user",
                        "description": "Channel manager to add or remove",
                        "required": False,
                    },
                ],
            },
        ],
    },
    {
        "name": "anchor",
        "alias_of": "channel anchor",
        "hidden": True,
        "description": "Alias for channel anchor",
    },
    {
        "name": "move",
        "alias_of": "channel move",
        "hidden": True,
        "description": "Alias for channel move",
    },
    {
        "name": "manager",
        "alias_of": "channel manager",
        "hidden": True,
        "description": "Alias for channel manager",
    },
    {"name": "<3", "description": "<3", "function": love_handler, "hidden": True},
]


def _normalize_user_token(token: str) -> str | None:
    """Extract a Slack user id from common mention forms or accept raw ids.

    Supported forms:
    - <@U123ABC|username>
    - <@U123ABC>
    - U123ABC

    Returns the extracted user id (e.g. 'U123ABC') or None if not recognized.
    """
    if not isinstance(token, str):
        return None

    # Match <@U123ABC|name> or <@U123ABC>
    m = re.match(r"^<@([UW][A-Z0-9]+)(?:\|[^>]+)?>$", token)
    if m:
        return m.group(1)

    # Plain id like U123ABC or W123ABC
    if re.match(r"^[UW][A-Z0-9]+$", token):
        return token

    return None


def _normalize_channel_token(token: str) -> str | None:
    """Extract channel id from common Slack channel forms.

    Supported forms:
    - <#C123ABC|name>
    - <#C123ABC>
    - C123ABC or G123ABC
    """
    if not isinstance(token, str):
        return None

    m = re.match(r"^<#([CG][A-Z0-9]+)(?:\|[^>]+)?>$", token)
    if m:
        return m.group(1)

    if re.match(r"^[CG][A-Z0-9]+$", token):
        return token

    return None


def _normalize_subteam_token(token: str) -> str | None:
    """Extract a Slack subteam (user group) id from common mention forms or accept raw ids.

    Supported forms:
    - <!subteam^S123ABC|@groupname>
    - S123ABC

    Returns the extracted subteam id (e.g. 'S123ABC') or None if not recognized.
    """
    if not isinstance(token, str):
        return None

    # Match <!subteam^S123ABC|name> or <!subteam^S123ABC>
    m = re.match(r"^<!subteam\^([S][A-Z0-9]+)(?:\|[^>]+)?>$", token)
    if m:
        return m.group(1)

    # Plain id like S123ABC
    if re.match(r"^[S][A-Z0-9]+$", token):
        return token

    return None


def _extract_mailto(token: str) -> str | None:
    """
    Extract an email from Slack's mailto token form:
      <mailto:amber@hackclub.com|amber@hackclub.com>
    or
      <mailto:amber@hackclub.com>
    Returns the extracted email string or None.
    """
    if not isinstance(token, str):
        return None

    m = re.match(r"^<mailto:([^|>]+)(?:\|[^>]+)?>$", token, re.I)
    if m:
        return m.group(1).strip()

    return None


# Simple email detection regex (not full validation)
_EMAIL_SIMPLE_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _assign_tokens_to_params(
    parsed_tokens: list[str], params: list[dict]
) -> list[str | None]:
    """
    Assign incoming tokens to params by type when possible.

    Rules (greedy, in token order):
      - If token looks like a channel -> assign to first unassigned param of type 'channel'
      - Else if token looks like a user mention/ID or an email/mailto -> assign to first unassigned param of type 'user'
      - Else if token looks like a subteam -> assign to first unassigned param of type 'subteam'
      - Else if token matches a 'choice' param's choices -> assign to that 'choice' param
      - Else -> assign to the next unassigned param (fallback)
    Returns a list aligned to params where each slot is the token assigned to that param or None.
    """
    if not parsed_tokens or not params:
        return [None] * len(params)

    logging.debug(
        "_assign_tokens_to_params: tokens=%s params_types=%s",
        parsed_tokens,
        [p.get("type") for p in params],
    )

    free_indices = [i for i in range(len(params))]
    assigned: list[str | None] = [None] * len(params)

    for tok in parsed_tokens:
        tok_str = tok if isinstance(tok, str) else str(tok)
        chosen_idx = None

        # Try channel (accept bare channel names starting with '#')
        if (
            isinstance(tok_str, str) and tok_str.startswith("#")
        ) or _normalize_channel_token(tok_str):
            logging.debug("Token '%s' detected as channel-like", tok_str)
            for i in free_indices:
                if params[i].get("type") == "channel":
                    chosen_idx = i
                    logging.debug(
                        " -> will assign token '%s' to channel param index %s (name=%s)",
                        tok_str,
                        i,
                        params[i].get("name"),
                    )
                    break

        # Try user / email forms
        if chosen_idx is None:
            if _normalize_user_token(tok_str):
                logging.debug("Token '%s' detected as user-id-like", tok_str)
            if _extract_mailto(tok_str) or (
                "@" in tok_str and _EMAIL_SIMPLE_RE.match(tok_str)
            ):
                logging.debug("Token '%s' detected as email-like", tok_str)
            if (
                _normalize_user_token(tok_str)
                or _extract_mailto(tok_str)
                or ("@" in tok_str and _EMAIL_SIMPLE_RE.match(tok_str))
            ):
                for i in free_indices:
                    if params[i].get("type") == "user":
                        chosen_idx = i
                        logging.debug(
                            " -> will assign token '%s' to user param index %s (name=%s)",
                            tok_str,
                            i,
                            params[i].get("name"),
                        )
                        break

        # Try subteam
        if chosen_idx is None and _normalize_subteam_token(tok_str):
            logging.debug("Token '%s' detected as subteam-like", tok_str)
            for i in free_indices:
                if params[i].get("type") == "subteam":
                    chosen_idx = i
                    logging.debug(
                        " -> will assign token '%s' to subteam param index %s (name=%s)",
                        tok_str,
                        i,
                        params[i].get("name"),
                    )
                    break

        # Try matching a choice param
        if chosen_idx is None:
            for i in free_indices:
                if params[i].get("type") == "choice":
                    choices = params[i].get("choices") or []
                    try:
                        lower_map = {str(c).lower(): c for c in choices}
                    except Exception:
                        lower_map = {}
                    if lower_map.get(tok_str.lower()) is not None:
                        chosen_idx = i
                        logging.debug(
                            "Token '%s' matched choice param index %s (name=%s)",
                            tok_str,
                            i,
                            params[i].get("name"),
                        )
                        break

        # Fallback to first free param
        if chosen_idx is None and free_indices:
            chosen_idx = free_indices[0]
            logging.debug(
                "Token '%s' falling back to first free param index %s (name=%s)",
                tok_str,
                chosen_idx,
                params[chosen_idx].get("name"),
            )

        if chosen_idx is not None:
            assigned[chosen_idx] = tok_str
            free_indices.remove(chosen_idx)
            logging.debug(
                "Assigned token '%s' -> index %s (param=%s). Remaining free indices: %s",
                tok_str,
                chosen_idx,
                params[chosen_idx].get("name"),
                free_indices,
            )

        if not free_indices:
            break

    logging.debug("Final token->param assignment: %s", assigned)
    return assigned


async def _find_channel_id_by_name(client: AsyncWebClient, name: str) -> str | None:
    """
    Look up a channel id by a bare channel name (like '#foo' or 'foo').
    Returns the channel id (e.g. 'C123ABC') or None if not found.

    This paginates conversations_list and matches on 'name' or 'name_normalized'.
    """
    if not isinstance(name, str) or name.strip() == "":
        return None
    lookup_name = name.strip().lstrip("#")
    try:
        cursor = None
        while True:
            # Request both public and private channels where the bot is a member
            resp = await client.conversations_list(
                limit=200, cursor=cursor, types="public_channel,private_channel"
            )
            data = getattr(resp, "data", resp) if resp is not None else {}
            channels = []
            if isinstance(data, dict):
                channels = data.get("channels") or []
            # Match by name (exact) or name_normalized
            for ch in channels:
                cname = ch.get("name")
                cname_norm = ch.get("name_normalized")
                if cname == lookup_name or cname_norm == lookup_name:
                    return ch.get("id")
            # Pagination
            if isinstance(data, dict):
                cursor = (data.get("response_metadata") or {}).get("next_cursor")
            else:
                cursor = None
            if not cursor:
                break
    except SlackApiError as e:
        logging.debug(
            f"Slack API error looking up channel name '{name}': {getattr(e, 'response', str(e))}"
        )
    except Exception:
        logging.exception("Error looking up channel by name")
    return None


def register_commands(app: AsyncApp):
    COMMAND_PREFIX = "/se" if config.environment == "production" else "/dev-se"

    def _param_display(param: dict[str, Any]) -> str:
        name = param.get("name")
        if param.get("type") == "choice":
            choices = param.get("choices") or []
            try:
                choices_str = "|".join(str(c) for c in choices)
            except Exception:
                choices_str = ""
            display = f"{name}={choices_str}" if choices_str else name
        else:
            display = name
        if param.get("required", False):
            return f"<{display}>"
        else:
            return f"[{display}]"

    def validate_commands(commands):
        for cmd in commands:
            if "alias_of" in cmd:
                if "subcommands" in cmd:
                    validate_commands(cmd["subcommands"])
                continue

            for p in cmd.get("parameters", []) or []:
                if p.get("type") == "choice":
                    choices = p.get("choices")
                    if (
                        not choices
                        or not isinstance(choices, (list, tuple))
                        or len(choices) == 0
                    ):
                        raise ValueError(
                            f"Command '{cmd.get('name')}' parameter '{p.get('name')}' is type 'choice' but 'choices' is missing or invalid."
                        )

            parameters = cmd.get("parameters", [])
            if "current_user" in [p.get("type") for p in parameters]:
                cmd["parameters"] = [
                    p for p in parameters if p.get("type") != "current_user"
                ]

            if "subcommands" in cmd:
                validate_commands(cmd["subcommands"])

    validate_commands(COMMANDS)

    def get_help(commands, prefix, is_admin=False):
        h = ""
        for cmd in commands:
            if cmd.get("hidden"):
                continue

            if bool(cmd.get("admin")) != is_admin:
                if not (
                    "subcommands" in cmd
                    and get_help(
                        cmd["subcommands"], f"{prefix} {cmd['name']}", is_admin
                    )
                ):
                    continue

            parameters = cmd.get("parameters", [])
            params = " ".join([_param_display(param) for param in parameters])

            full_command = f"{prefix} {cmd['name']}"

            if "subcommands" in cmd:
                sub_help = get_help(cmd["subcommands"], full_command, is_admin)
                if sub_help:
                    h += sub_help
                if cmd.get("function") and bool(cmd.get("admin")) == is_admin:
                    h += f"- `{full_command}{f' {params}' if params else ''}`: {cmd['description']}\n"
            else:
                h += f"- `{full_command}{f' {params}' if params else ''}`: {cmd['description']}\n"
        return h

    help_msg = "Available commands:\n" + get_help(COMMANDS, COMMAND_PREFIX, False)
    admin_help_msg = get_help(COMMANDS, COMMAND_PREFIX, True)

    @app.command(COMMAND_PREFIX)
    async def inn_command(
        ack: AsyncAck, client: AsyncWebClient, respond: AsyncRespond, command: dict
    ):
        await ack()
        user_id = command.get("user_id")
        raw_text = command.get("text", "")

        await send_heartbeat(
            f"<@{user_id}> ({user_id}) ran {raw_text}", [f"```{command}```"]
        )

        ran = f"\n_You ran `{COMMAND_PREFIX} {raw_text}`_" if raw_text else ""

        try:
            # Tokenizer that preserves Slack angle-bracket tokens (e.g. <#C123|name>, <@U123>, <mailto:...>),
            # preserves quoted strings as single tokens, and otherwise splits on whitespace.
            token_re = re.compile(r'(<[^>\s]+>)|("([^"\\]|\\.)*")|(\S+)')
            if raw_text:
                matches = list(token_re.finditer(raw_text))
                tokens = [m.group(0) for m in matches]

                def _unwrap(tok: str) -> str:
                    if tok and len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"':
                        inner = tok[1:-1]
                        try:
                            return codecs.decode(inner, "unicode_escape")
                        except Exception:
                            return inner
                    return tok

                tokens = [_unwrap(t) for t in tokens]
            else:
                tokens = []
        except Exception as e:
            await respond(f"Could not parse command text: {e}{ran}")
            return

        # Navigate through subcommands
        cmd = None
        tokens_consumed = 0

        # Guard against infinite alias loops
        max_resolutions = 10
        resolutions = 0

        while resolutions < max_resolutions:
            current_commands = COMMANDS
            tokens_consumed = 0
            cmd = None

            for i, token in enumerate(tokens):
                normalized_token = (
                    token.replace("&lt;", "<")
                    .replace("&gt;", ">")
                    .replace("&amp;", "&")
                )
                found = next(
                    (
                        c
                        for c in current_commands
                        if c["name"] == normalized_token
                        or normalized_token in c.get("aliases", [])
                    ),
                    None,
                )

                if found:
                    cmd = found
                    tokens_consumed = i + 1
                    if "alias_of" in found:
                        break
                    if "subcommands" in found:
                        current_commands = found["subcommands"]
                    else:
                        break
                else:
                    break

            if cmd and "alias_of" in cmd:
                resolutions += 1
                alias_tokens = cmd["alias_of"].split()
                tokens = alias_tokens + tokens[tokens_consumed:]
                continue

            break

        if resolutions == max_resolutions:
            await respond(f"Too many command aliases resolved (infinite loop?).{ran}")
            return

        if cmd and cmd.get("function"):
            if cmd.get("admin") and user_id != "U054VC2KM9P":
                await respond(f"You do not have permission to use this command.{ran}")
                return

            args_tokens = tokens[tokens_consumed:]
            params = cmd.get("parameters", []) or []

            # If the last declared parameter is a 'string', join the remainder into one argument.
            if params and params[-1].get("type") == "string":
                num_non_string = max(0, len(params) - 1)
                first_parts = args_tokens[:num_non_string]
                remaining = args_tokens[num_non_string:]
                last_string = (
                    " ".join(remaining) if remaining else params[-1].get("default", "")
                )
                try:
                    last_string = codecs.decode(last_string, "unicode_escape")
                except Exception:
                    pass
                args_tokens = first_parts + [last_string]

            # Attempt to assign tokens to params by type
            if args_tokens and params:
                mapped = _assign_tokens_to_params(args_tokens, params)
                args_tokens = [
                    mapped[i] if i < len(mapped) else None for i in range(len(params))
                ]
            else:
                args_tokens = [None] * len(params)

            import inspect

            kwargs_for_params: dict[str, Any] = {}
            errors: list[str] = []

            if "current_user" in [p.get("type") for p in params]:
                pname = next(
                    p.get("name") for p in params if p.get("type") == "current_user"
                )
                kwargs_for_params[pname] = user_id
                params = [p for p in params if p.get("type") != "current_user"]

            for idx, param in enumerate(params):
                pname = param.get("name")
                ptype = param.get("type", "string")
                default = param.get("default", None)
                raw_val = args_tokens[idx] if idx < len(args_tokens) else default

                if raw_val is None or raw_val == "":
                    value = None
                else:
                    if ptype == "integer":
                        try:
                            value = int(raw_val)
                        except Exception:
                            errors.append(f"Parameter '{pname}' must be an integer.")
                            continue
                    elif ptype == "user":
                        value = None
                        email_candidate = None
                        if isinstance(raw_val, str):
                            raw_val_str = raw_val.strip()
                            uid = _normalize_user_token(raw_val_str)
                            if uid:
                                value = uid
                            else:
                                mailto = _extract_mailto(raw_val_str)
                                if mailto:
                                    email_candidate = mailto
                                elif "@" in raw_val_str and _EMAIL_SIMPLE_RE.match(
                                    raw_val_str
                                ):
                                    email_candidate = raw_val_str

                        if email_candidate:
                            email = email_candidate
                            try:
                                resp = await client.users_lookupByEmail(email=email)
                                data = (
                                    getattr(resp, "data", resp)
                                    if resp is not None
                                    else {}
                                )
                                if isinstance(data, dict):
                                    user_obj = data.get("user") or {}
                                    uid = user_obj.get("id")
                                    if uid and re.match(r"^[UW][A-Z0-9]+$", uid):
                                        value = uid
                                        kwargs_for_params["email"] = email
                                    else:
                                        kwargs_for_params["email"] = email
                            except Exception:
                                kwargs_for_params["email"] = email

                    elif ptype == "channel":
                        if not isinstance(raw_val, str):
                            errors.append(
                                f"Parameter '{pname}' must be a channel mention or ID."
                            )
                            continue
                        chan = _normalize_channel_token(raw_val)
                        if chan:
                            value = chan
                        else:
                            try:
                                resolved = await _find_channel_id_by_name(
                                    client, raw_val.strip()
                                )
                                if resolved:
                                    value = resolved
                                else:
                                    errors.append(
                                        f"Parameter '{pname}' must be a channel mention, ID or name."
                                    )
                                    continue
                            except Exception:
                                errors.append(
                                    f"Parameter '{pname}' must be a channel mention or ID."
                                )
                                continue

                    elif ptype == "choice":
                        choices = param.get("choices")
                        if not choices:
                            errors.append(
                                f"Parameter '{pname}' is a choice type but no choices defined."
                            )
                            continue
                        match = next(
                            (
                                c
                                for c in choices
                                if str(c).lower() == str(raw_val).lower()
                            ),
                            None,
                        )
                        if match is None:
                            errors.append(
                                f"Parameter '{pname}' must be one of: {', '.join(map(str, choices))}."
                            )
                            continue
                        value = match

                    elif ptype == "subteam":
                        if not isinstance(raw_val, str):
                            errors.append(
                                f"Parameter '{pname}' must be a usergroup mention or ID."
                            )
                            continue
                        s_id = _normalize_subteam_token(raw_val.strip())
                        if s_id:
                            value = s_id
                        else:
                            errors.append(
                                f"Parameter '{pname}' must be a usergroup mention or ID."
                            )
                            continue
                    else:
                        if isinstance(raw_val, str):
                            try:
                                value = codecs.decode(raw_val, "unicode_escape")
                            except Exception:
                                value = raw_val
                        else:
                            value = str(raw_val)

                if value is None:
                    value = param.get("default")
                kwargs_for_params[pname] = value

            if errors:
                await respond("; ".join(errors) + ran)
                return

            handler = cmd["function"]
            sig = inspect.signature(handler)
            handler_kwargs: dict[str, Any] = {
                "ack": ack,
                "client": client,
                "respond": respond,
                "performer": user_id,
            }

            if "text" in sig.parameters:
                handler_kwargs["text"] = raw_text
            else:
                for pname, pvalue in kwargs_for_params.items():
                    if pname in sig.parameters:
                        handler_kwargs[pname] = pvalue
            if "command" in sig.parameters:
                handler_kwargs["command"] = command
            if "raw_command" in sig.parameters:
                handler_kwargs["raw_command"] = f"{COMMAND_PREFIX} {raw_text}"
            if "location" in sig.parameters:
                handler_kwargs["location"] = command.get("channel_id")

            await handler(**handler_kwargs)
            return

        is_admin = user_id == "U054VC2KM9P"
        final_help = help_msg
        if is_admin and admin_help_msg:
            final_help += "\n*Admin Commands:*\n" + admin_help_msg

        await respond(final_help + ran)
