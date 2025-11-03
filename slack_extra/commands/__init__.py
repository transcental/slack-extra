import logging
import re
import shlex

from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncApp
from slack_bolt.async_app import AsyncRespond
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.commands.info import info_handler
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
                "type": "string",
                "description": "Channel mention or id",
                "default": None,
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
            # Exclude current_user from help display
            cmd["parameters"] = [
                p for p in parameters if p.get("type") != "current_user"
            ]

        def _param_display(param):
            name = param.get("name")
            if param.get("type") == "choice":
                choices = param.get("choices") or []
                # show choices in help text like: action=add|remove|list
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

        # Parse the incoming text with shlex so quoted arguments are preserved and escape sequences are allowed.
        try:
            tokens = shlex.split(raw_text, posix=True) if raw_text else []
        except ValueError as e:
            await respond(f"Could not parse command text: {e}")
            return

        command_name = tokens[0] if tokens else ""  # type: ignore (text is always... text)
        for cmd in COMMANDS:
            if cmd["name"] == command_name:
                if cmd.get("admin") and not user_id == "U054VC2KM9P":
                    await respond("You do not have permission to use this command.")
                    return
                if cmd["function"]:
                    parsed = tokens[1:]
                    params = cmd.get("parameters", [])
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
                            " ".join(remaining)
                            if remaining
                            else params[-1].get("default", "")
                        )
                        # Decode escape sequences like \n, \t inside the joined string
                        try:
                            import codecs

                            last_string = codecs.decode(last_string, "unicode_escape")
                        except Exception:
                            # If decode fails, fall back to the raw joined string
                            pass
                        args_tokens = first_parts + [last_string]
                        logging.debug(
                            f"Adjusted args tokens for trailing string parameter: {args_tokens}"
                        )

                    # Build kwargs mapping parameter names to typed/validated values
                    import inspect
                    import re
                    import codecs

                    kwargs_for_params = {}
                    errors = []

                    if "current_user" in [p.get("type") for p in params]:
                        pname = next(
                            p.get("name")
                            for p in params
                            if p.get("type") == "current_user"
                        )
                        kwargs_for_params[pname] = user_id
                        params.remove(
                            next(p for p in params if p.get("type") == "current_user")
                        )

                    # Special handling for commands with required user, optional int, optional string
                    if (
                        len(params) >= 3
                        and params[0].get("required", False)
                        and not params[1].get("required", False)
                        and params[1].get("type") == "integer"
                        and not params[2].get("required", False)
                        and params[2].get("type") == "string"
                    ):
                        if len(parsed) > 0:
                            user_str = parsed[0]
                            if len(parsed) > 1:
                                try:
                                    int(parsed[1])
                                    amount_str = parsed[1]
                                    reason_str = " ".join(parsed[2:])
                                except ValueError:
                                    amount_str = ""
                                    reason_str = " ".join(parsed[1:])
                            else:
                                amount_str = ""
                                reason_str = ""
                            args_tokens = [user_str, amount_str, reason_str]
                        else:
                            args_tokens = []
                    # Special handling for commands with optional user, optional int
                    elif (
                        len(params) >= 2
                        and not params[0].get("required", False)
                        and params[0].get("type") == "user"
                        and not params[1].get("required", False)
                        and params[1].get("type") == "integer"
                    ):
                        if len(parsed) > 0:
                            try:
                                int(parsed[0])
                                # First arg is int, assign to amount, second to user if present
                                amount_str = parsed[0]
                                user_str = parsed[1] if len(parsed) > 1 else ""
                            except ValueError:
                                # First arg not int, assign to user, second to amount if int
                                user_str = parsed[0]
                                if len(parsed) > 1:
                                    try:
                                        int(parsed[1])
                                        amount_str = parsed[1]
                                    except ValueError:
                                        amount_str = ""
                                else:
                                    amount_str = ""
                        else:
                            user_str = ""
                            amount_str = ""
                        args_tokens = [user_str, amount_str]

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
                            # Type validation & coercion
                            if ptype == "integer":
                                try:
                                    value = int(raw_val)
                                except Exception:
                                    errors.append(
                                        f"Parameter '{pname}' must be an integer."
                                    )
                                    continue
                            elif ptype == "user":
                                # Accept Slack mention/ID or email. Prefer resolving emails first so
                                # addresses like 'user@domain' don't get mistaken for a raw user ID.
                                if not isinstance(raw_val, str):
                                    errors.append(
                                        f"Parameter '{pname}' must be a user mention, ID, or email (e.g. <@U123ABC|name> or user@example.com)."
                                    )
                                    continue
                                raw_val_str = raw_val.strip()
                                # If it looks like an email address, try to resolve via Slack API first.
                                if "@" in raw_val_str and re.match(
                                    r"^[^@\s]+@[^@\s]+\.[^@\s]+$", raw_val_str
                                ):
                                    email = raw_val_str
                                    try:
                                        resp = await client.users_lookupByEmail(
                                            email=email
                                        )
                                        # resp may be a SlackResponse-like object or a dict; normalize to a dict-like variable.
                                        data = (
                                            getattr(resp, "data", resp)
                                            if resp is not None
                                            else {}
                                        )
                                        if isinstance(data, dict):
                                            # Prefer explicit user field when present.
                                            user_obj = data.get("user") or {}
                                            uid = user_obj.get("id")
                                            logging.debug(
                                                f"Lookup by email '{email}' returned: {uid} (raw response: {data})"
                                            )
                                            if uid and re.match(
                                                r"^[UW][A-Z0-9]+$", uid
                                            ):
                                                value = uid
                                                # Store the original email so handlers that declare `email` can receive it.
                                                kwargs_for_params["email"] = email
                                            else:
                                                # No user id in response: try to fall back to token normalization
                                                norm = _normalize_user_token(
                                                    raw_val_str
                                                )
                                                if norm and re.match(
                                                    r"^[UW][A-Z0-9]+$", norm
                                                ):
                                                    value = norm
                                                else:
                                                    api_err = None
                                                    if data.get("ok") is False:
                                                        api_err = data.get("error")
                                                    if api_err:
                                                        errors.append(
                                                            f"Could not find Slack user for email '{email}': {api_err}"
                                                        )
                                                    else:
                                                        errors.append(
                                                            f"Could not find a Slack user for email '{email}'."
                                                        )
                                                    continue
                                        else:
                                            # Unexpected response type; log and fail with a clear message.
                                            logging.debug(
                                                f"Unexpected response type for users_lookupByEmail: {resp}"
                                            )
                                            norm = _normalize_user_token(raw_val_str)
                                            if norm and re.match(
                                                r"^[UW][A-Z0-9]+$", norm
                                            ):
                                                value = norm
                                            else:
                                                errors.append(
                                                    f"Could not find a Slack user for email '{email}'."
                                                )
                                                continue
                                    except SlackApiError as e:
                                        # SlackApiError often contains a response dict with an 'error' key.
                                        api_err = None
                                        try:
                                            if hasattr(e, "response") and isinstance(
                                                e.response, dict
                                            ):
                                                api_err = e.response.get("error")
                                        except Exception:
                                            api_err = None
                                        if api_err:
                                            errors.append(
                                                f"Slack API error looking up email '{email}': {api_err}"
                                            )
                                        else:
                                            errors.append(
                                                f"Slack API error looking up email '{email}': {e}"
                                            )
                                        continue
                                    except Exception as e:
                                        logging.exception(
                                            "Error looking up user by email"
                                        )
                                        # Last-resort: try normalizing as a Slack token before failing entirely.
                                        norm = _normalize_user_token(raw_val_str)
                                        if norm and re.match(r"^[UW][A-Z0-9]+$", norm):
                                            value = norm
                                        else:
                                            errors.append(
                                                f"Error looking up Slack user for email '{raw_val_str}': {e}"
                                            )
                                        continue
                                else:
                                    # Not an email-looking token: try normalizing Slack mention/ID
                                    norm = _normalize_user_token(raw_val_str)
                                    logging.debug(
                                        f"Normalized user token '{raw_val}' to '{norm}'"
                                    )
                                    if norm and re.match(r"^[UW][A-Z0-9]+$", norm):
                                        value = norm
                                    else:
                                        errors.append(
                                            f"Parameter '{pname}' must be a user mention, ID, or email (e.g. <@U123ABC|name> or user@example.com)."
                                        )
                                        continue
                            elif ptype == "channel":
                                # Normalize Slack channel mention formats like <#C123ABC|name> to the channel id and validate.
                                if not isinstance(raw_val, str):
                                    errors.append(
                                        f"Parameter '{pname}' must be a channel mention or ID (e.g. <#C123ABC|name>)."
                                    )
                                    continue
                                # Match <#C123ABC|name> or <#C123ABC>
                                m = re.match(
                                    r"^<#([CG][A-Z0-9]+)(?:\|[^>]+)?>$", raw_val
                                )
                                if m:
                                    value = m.group(1)
                                elif re.match(r"^[CG][A-Z0-9]+$", raw_val):
                                    value = raw_val
                                else:
                                    errors.append(
                                        f"Parameter '{pname}' must be a channel mention or ID (e.g. <#C123ABC|name>)."
                                    )
                                    continue
                            elif ptype == "choice":
                                # Validate against an explicit list of allowed choices supplied on the parameter.
                                # Comparison is case-insensitive; the canonical value (as defined in choices)
                                # will be used when returning the parsed value.
                                choices = param.get("choices")
                                if not choices or not isinstance(
                                    choices, (list, tuple)
                                ):
                                    errors.append(
                                        f"Parameter '{pname}' is a choice type but no choices were defined."
                                    )
                                    continue
                                if not isinstance(raw_val, str):
                                    errors.append(
                                        f"Parameter '{pname}' must be one of: {', '.join(map(str, choices))}."
                                    )
                                    continue
                                # Build a mapping of lowercase->canonical to allow case-insensitive matching
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
                                # Use canonical form from choices
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

                    # Prepare the invocation kwargs for the handler.
                    handler = cmd["function"]
                    sig = inspect.signature(handler)
                    handler_kwargs = {
                        "ack": ack,
                        "client": client,
                        "respond": respond,
                        "performer": user_id,
                    }

                    # Backwards compatibility:
                    # If the handler accepts a parameter named 'text', pass the original raw_text.
                    # Otherwise, pass only the named parameters that the handler declares.
                    if "text" in sig.parameters:
                        handler_kwargs["text"] = raw_text
                    else:
                        for pname, pvalue in kwargs_for_params.items():
                            if pname in sig.parameters:
                                handler_kwargs[pname] = pvalue

                    await handler(**handler_kwargs)
                else:
                    await respond(
                        f"The `{command_name}` command is not yet implemented."
                    )
                return
        is_admin = user_id == "U054VC2KM9P"
        final_help = help
        if is_admin:
            final_help += "\n*Admin Commands:*\n" + admin_help
        await respond(final_help)
