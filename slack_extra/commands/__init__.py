import codecs
import logging
import re
import shlex
from typing import Any

from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncApp
from slack_bolt.async_app import AsyncRespond
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.commands.info import info_handler
from slack_extra.commands.manager import manager_handler
from slack_extra.config import config


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
        "name": "manager",
        "description": "Manage your managers",
        "function": manager_handler,
        "parameters": [
            {
                "name": "action",
                "type": "choice",
                "choices": ["add", "remove"],
                "description": "Action to perform",
                "required": True,
            },
            {
                "name": "manager",
                "type": "user",
                "description": "Manager to add or remove",
                "required": True,
            },
        ],
    },
]


def register_commands(app: AsyncApp):
    COMMAND_PREFIX = "/se" if config.environment == "production" else "/dev-se"
    admin_help = ""
    help = "Available commands:\n"

    # Validate command definitions (particularly `choice` parameter definitions).
    # A 'choice' parameter MUST include a non-empty list/tuple under the 'choices' key.
    for cmd in COMMANDS:
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

        params = " ".join([_param_display(param) for param in parameters])
        if cmd.get("admin"):
            admin_help += f"- `{COMMAND_PREFIX} {cmd['name']}{f' {params}' if params else ''}`: {cmd['description']}\n"
        else:
            help += f"- `{COMMAND_PREFIX} {cmd['name']}{f' {params}' if params else ''}`: {cmd['description']}\n"

    @app.command(COMMAND_PREFIX)
    async def inn_command(
        ack: AsyncAck, client: AsyncWebClient, respond: AsyncRespond, command: dict
    ):
        await ack()
        user_id = command.get("user_id")
        raw_text = command.get("text", "")

        try:
            tokens = shlex.split(raw_text, posix=True) if raw_text else []
        except ValueError as e:
            await respond(f"Could not parse command text: {e}")
            return

        command_name = tokens[0] if tokens else ""
        for cmd in COMMANDS:
            if cmd["name"] != command_name:
                continue

            if cmd.get("admin") and user_id != "U054VC2KM9P":
                await respond("You do not have permission to use this command.")
                return

            parsed = tokens[1:]
            params = cmd.get("parameters", []) or []
            args_tokens = parsed
            logging.debug(
                f"Command '{command_name}' invoked by user '{user_id}' with raw text: {raw_text}"
            )
            logging.debug(f"Parsed tokens: {tokens}")

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
                logging.debug(
                    f"Adjusted args tokens for trailing string parameter: {args_tokens}"
                )

            import inspect

            kwargs_for_params: dict[str, Any] = {}
            errors: list[str] = []

            if "current_user" in [p.get("type") for p in params]:
                pname = next(
                    p.get("name") for p in params if p.get("type") == "current_user"
                )
                kwargs_for_params[pname] = user_id
                params = [p for p in params if p.get("type") != "current_user"]

            # Keep special-case shimming if present (omitted here for clarity, retained behavior above if needed)

            for idx, param in enumerate(params):
                pname = param.get("name")
                ptype = param.get("type", "string")
                default = param.get("default", None)

                logging.debug(
                    f"Processing parameter '{pname}' of type '{ptype}' at position {idx}"
                )

                if idx < len(args_tokens):
                    raw_val = args_tokens[idx]
                else:
                    raw_val = default

                logging.debug(f"Raw value for parameter '{pname}': {raw_val}")

                # Normalize missing values
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
                        # First, try to extract explicit Slack mention or plain ID.
                        value = None
                        email_candidate: str | None = None

                        if isinstance(raw_val, str):
                            raw_val_str = raw_val.strip()

                            # explicit mention or plain id
                            uid = _normalize_user_token(raw_val_str)
                            if uid:
                                value = uid
                                logging.debug(
                                    f"User token normalized from mention/id: {uid}"
                                )
                            else:
                                # mailto form: <mailto:...|...>
                                mailto = _extract_mailto(raw_val_str)
                                if mailto:
                                    email_candidate = mailto
                                # bare-looking email address
                                elif "@" in raw_val_str and _EMAIL_SIMPLE_RE.match(
                                    raw_val_str
                                ):
                                    email_candidate = raw_val_str
                                else:
                                    # not an id/mention or email-looking token; leave value None and record param error below
                                    email_candidate = None
                        else:
                            email_candidate = None

                        # If we have an email candidate, attempt lookup. On any failure, *do not* return an error:
                        # set the resolved user id to None and pass the email through to the handler via kwargs.
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
                                    logging.debug(
                                        f"Lookup by email '{email}' returned: {uid} (raw response: {data})"
                                    )
                                    if uid and re.match(r"^[UW][A-Z0-9]+$", uid):
                                        value = uid
                                        kwargs_for_params["email"] = email
                                    else:
                                        # Lookup didn't return an ID -> treat as unresolved but still pass email
                                        value = None
                                        kwargs_for_params["email"] = email
                                else:
                                    # Unexpected response type -> treat as unresolved but pass email
                                    logging.debug(
                                        f"Unexpected response type for users_lookupByEmail: {resp}"
                                    )
                                    value = None
                                    kwargs_for_params["email"] = email
                            except SlackApiError as e:
                                # On API error (not found, missing scopes, etc.), do not propagate error to caller.
                                # Instead set user to None and pass the email through.
                                logging.debug(
                                    f"Slack API error looking up email '{email}': {getattr(e, 'response', str(e))}"
                                )
                                value = None
                                kwargs_for_params["email"] = email
                            except Exception:
                                logging.exception("Error looking up user by email")
                                value = None
                                kwargs_for_params["email"] = email
                        # If neither uid nor email_candidate produced a value, and we still don't have a value,
                        # treat it as an unresolved token and allow the handler to receive None.
                        # (This preserves backwards compatibility where handlers can accept a `user` of None.)
                        # No error is appended for email lookup failures per the requested behavior.

                    elif ptype == "channel":
                        if not isinstance(raw_val, str):
                            errors.append(
                                f"Parameter '{pname}' must be a channel mention or ID (e.g. <#C123ABC|name>)."
                            )
                            continue
                        chan = _normalize_channel_token(raw_val)
                        if chan:
                            value = chan
                        else:
                            errors.append(
                                f"Parameter '{pname}' must be a channel mention or ID (e.g. <#C123ABC|name>)."
                            )
                            continue

                    elif ptype == "choice":
                        choices = param.get("choices")
                        if not choices or not isinstance(choices, (list, tuple)):
                            errors.append(
                                f"Parameter '{pname}' is a choice type but no choices were defined."
                            )
                            continue
                        if not isinstance(raw_val, str):
                            errors.append(
                                f"Parameter '{pname}' must be one of: {', '.join(map(str, choices))}."
                            )
                            continue
                        try:
                            lower_map = {str(c).lower(): c for c in choices}
                        except Exception:
                            errors.append(
                                f"Parameter '{pname}' must be one of: {', '.join(map(str, choices))}."
                            )
                            continue
                        match = lower_map.get(raw_val.lower())
                        if match is None:
                            errors.append(
                                f"Parameter '{pname}' must be one of: {', '.join(map(str, choices))}."
                            )
                            continue
                        value = match

                    else:
                        # string or unknown types => treat as string and decode escape sequences
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
                await respond("; ".join(errors))
                return

            # Prepare handler kwargs
            handler = cmd["function"]

            if not handler:
                await respond(f"The `{command_name}` command is not yet implemented.")
                return

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

            await handler(**handler_kwargs)
            return

        is_admin = user_id == "U054VC2KM9P"
        final_help = help
        if is_admin:
            final_help += "\n*Admin Commands:*\n" + admin_help
        await respond(final_help)
