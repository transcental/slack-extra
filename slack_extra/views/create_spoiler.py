from collections import defaultdict
from copy import deepcopy

from slack_bolt.async_app import AsyncAck
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.config import config
from slack_extra.tables import Spoiler


def _split_spoilers_in_inline_elements(inline_elements):
    """
    inline_elements: list of dicts (inline items like {'type':'text','text':'...'}, {'type':'emoji',...}, ...)
    Returns: tuple (bold_inline_elements, redacted_inline_elements).

    - bold_inline_elements: same structure but any spoilered runs are forced bold by adding a
      neutral 'style': {'bold': True} on the resulting text elements (no 'spoiler' property).
    - redacted_inline_elements: same structure but spoilered runs are replaced with an inline code
      block containing the literal string [spoiler hidden] (we encode that as text with a code style
      using {'style': {'code': True}}). Emojis and other non-text inline elements that fall within
      spoiler ranges will be considered part of the spoiler and thus replaced by the redaction.

    Each returned element may include an internal transient '_src_idx' integer indicating the index of the
    original input element it originated from. This is used by higher-level callers to remap combined
    inline lists back into sectioned structures. Callers should strip these before returning results to
    external consumers.
    """
    # Build flattened char/element list for all inline elements. For text elements we create one
    # entry per character; for non-text inline elements (emoji, user tokens, etc.) we create a
    # single placeholder entry so they can be included in spoiler segments.
    char_list = []  # entries: {'type': 'char'|'elem', 'char'?, 'src_idx', 'is_marker', 'in_spoiler', 'el'?}
    for i, el in enumerate(inline_elements):
        text = el.get("text") if isinstance(el, dict) else None
        if isinstance(text, str):
            for j, ch in enumerate(text):
                char_list.append(
                    {
                        "type": "char",
                        "char": ch,
                        "src_idx": i,
                        "offset": j,
                        "is_marker": False,
                        "in_spoiler": False,
                    }
                )
        elif isinstance(el, dict):
            # Non-text inline element (emoji, user mention, etc.). Represent as a single entry so
            # it can be included in spoiler runs and thus hidden in the redacted variant.
            char_list.append(
                {
                    "type": "elem",
                    "char": None,
                    "src_idx": i,
                    "is_nontext": True,
                    "el": deepcopy(el),
                    "is_marker": False,
                    "in_spoiler": False,
                }
            )

    if not char_list:
        # Nothing to do; return shallow copies of original inline elements for both variants
        b = [deepcopy(el) for el in inline_elements]
        r = [deepcopy(el) for el in inline_elements]
        return b, r

    # Mark '||' markers and compute in_spoiler state. Markers can only be characters equal to '|'.
    in_spoiler = False
    i = 0
    n = len(char_list)
    while i < n:
        entry = char_list[i]
        if (
            entry["type"] == "char"
            and entry["char"] == "|"
            and i + 1 < n
            and char_list[i + 1]["type"] == "char"
            and char_list[i + 1]["char"] == "|"
        ):
            # mark both pipe chars as markers and toggle
            char_list[i]["is_marker"] = True
            char_list[i + 1]["is_marker"] = True
            in_spoiler = not in_spoiler
            i += 2
        else:
            # For both 'char' and 'elem' entries, propagate current in_spoiler state
            char_list[i]["in_spoiler"] = in_spoiler
            i += 1

    # Build segments of contiguous visible chars (and non-text items) with same in_spoiler.
    # Assign each segment an id so that multi-element spoilers can be collapsed to a single
    # redaction element in the redacted variant.
    segments = []  # each: {'in_spoiler': bool, 'chars':[char_entry,...], 'id': int}
    seg = None
    seg_id = 0
    for ch in char_list:
        if ch.get("is_marker"):
            continue
        if seg is None:
            seg = {"in_spoiler": ch["in_spoiler"], "chars": [ch], "id": seg_id}
        elif seg["in_spoiler"] == ch["in_spoiler"]:
            seg["chars"].append(ch)
        else:
            segments.append(seg)
            seg_id += 1
            seg = {"in_spoiler": ch["in_spoiler"], "chars": [ch], "id": seg_id}
    if seg:
        segments.append(seg)

    # Group the segment chars (and non-text items) by their source inline element index to create
    # slices per original inline element. Non-text items produce slices with 'nontext': True and carry
    # the original element so they can be handled (and redacted) correctly.
    slices_by_src = defaultdict(list)  # src_idx -> list of slice dicts
    for s in segments:
        cur_src = None
        cur_chars = []
        for c in s["chars"]:
            src = c["src_idx"]
            if c.get("is_nontext"):
                # Flush any pending text for previous source
                if cur_src is not None and cur_chars:
                    slices_by_src[cur_src].append(
                        {
                            "in_spoiler": s["in_spoiler"],
                            "text": "".join(cur_chars),
                            "seg_id": s["id"],
                        }
                    )
                    cur_src = None
                    cur_chars = []
                # Add a non-text slice for this source
                slices_by_src[src].append(
                    {
                        "in_spoiler": s["in_spoiler"],
                        "nontext": True,
                        "el": deepcopy(c["el"]),
                        "seg_id": s["id"],
                    }
                )
                continue
            if cur_src is None:
                cur_src = src
                cur_chars = [c["char"]]
            elif src != cur_src:
                slices_by_src[cur_src].append(
                    {
                        "in_spoiler": s["in_spoiler"],
                        "text": "".join(cur_chars),
                        "seg_id": s["id"],
                    }
                )
                cur_src = src
                cur_chars = [c["char"]]
            else:
                cur_chars.append(c["char"])
        if cur_src is not None and cur_chars:
            slices_by_src[cur_src].append(
                {
                    "in_spoiler": s["in_spoiler"],
                    "text": "".join(cur_chars),
                    "seg_id": s["id"],
                }
            )

    # Rebuild inline elements list: for each original inline element, replace text elements with their slices.
    # Non-text slices are emitted for bold variant but collapsed into the redaction element in the redacted
    # variant when they are inside a spoiler segment.
    bold_out = []
    redacted_out = []
    emitted_seg_ids = set()
    for idx, el in enumerate(inline_elements):
        slices = slices_by_src.get(idx, [])
        if slices:
            for sl in slices:
                if sl.get("nontext"):
                    # Bold variant: preserve the original non-text element (remove any spoiler flags).
                    new_b = deepcopy(sl["el"])
                    new_b.pop("spoiler", None)
                    # record source index for tracing
                    new_b["_src_idx"] = idx
                    bold_out.append(new_b)
                    # Redacted variant: collapse spoilered non-text into the segment's single code element.
                    if sl["in_spoiler"]:
                        segid = sl["seg_id"]
                        if segid not in emitted_seg_ids:
                            # Use style.code for inline code and include a source index
                            code_el = {
                                "type": "text",
                                "text": "[spoiler hidden]",
                                "style": {"code": True},
                                "_src_idx": idx,
                            }
                            redacted_out.append(code_el)
                            emitted_seg_ids.add(segid)
                    else:
                        # Preserve non-spoiler non-text and record source
                        preserved = deepcopy(sl["el"])
                        preserved["_src_idx"] = idx
                        redacted_out.append(preserved)
                    continue
                # Text slice handling
                new_b = deepcopy(el)
                new_b["text"] = sl["text"]
                new_b.pop("spoiler", None)
                if sl["in_spoiler"]:
                    new_b["style"] = new_b.get("style", {})
                    new_b["style"]["bold"] = True
                else:
                    # ensure no bold carried
                    if "style" in new_b:
                        new_b["style"] = {
                            k: v
                            for k, v in new_b.get("style", {}).items()
                            if k != "bold"
                        }
                # record source index for tracing
                new_b["_src_idx"] = idx
                bold_out.append(new_b)

                # Redacted handling for text slices: emit one code element per spoiler segment id
                if sl["in_spoiler"]:
                    segid = sl["seg_id"]
                    if segid not in emitted_seg_ids:
                        # Use style.code for inline code and include a source index
                        code_el = {
                            "type": "text",
                            "text": "[spoiler hidden]",
                            "style": {"code": True},
                            "_src_idx": idx,
                        }
                        redacted_out.append(code_el)
                        emitted_seg_ids.add(segid)
                else:
                    new_r = deepcopy(el)
                    new_r["text"] = sl["text"]
                    new_r.pop("spoiler", None)
                    if "style" in new_r:
                        new_r["style"] = {
                            k: v
                            for k, v in new_r.get("style", {}).items()
                            if k != "bold"
                        }
                    new_r["_src_idx"] = idx
                    redacted_out.append(new_r)
        else:
            # No visible slices for this element (all markers) - skip
            continue
    return bold_out, redacted_out


def _is_inline_elements_list(lst):
    """
    Heuristic: treat a list as inline-elements if at least one element is a dict with a string 'text' key.
    This avoids accidentally processing lists of blocks that are not inline elements.
    """
    if not isinstance(lst, list) or not lst:
        return False
    for item in lst:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            return True
    return False


def _process_object_variants(obj):
    """
    Recursively walk dict/list structure and apply splitter to inline element lists.
    Returns a tuple: (bold_variant, redacted_variant), where each is a deep-copied structure
    of the original but with inline elements transformed as required.
    """
    if isinstance(obj, list):
        # If this list looks like inline elements, process it as inline elements
        if _is_inline_elements_list(obj):
            return _split_spoilers_in_inline_elements(obj)
        else:
            # Merge consecutive rich_text_section items so spoilers can span newlines.
            bold_list = []
            redacted_list = []
            i = 0
            while i < len(obj):
                item = obj[i]
                # detect runs of rich_text_section or rich_text_preformatted dicts so spoilers may span across them
                if isinstance(item, dict) and item.get("type") in (
                    "rich_text_section",
                    "rich_text_preformatted",
                ):
                    run = []
                    j = i
                    while (
                        j < len(obj)
                        and isinstance(obj[j], dict)
                        and obj[j].get("type")
                        in ("rich_text_section", "rich_text_preformatted")
                    ):
                        run.append(obj[j])
                        j += 1
                    if len(run) == 1:
                        # Single block - recurse normally (preserves type)
                        b_item, r_item = _process_object_variants(run[0])
                        bold_list.append(b_item)
                        redacted_list.append(r_item)
                    else:
                        # Merge their inline 'elements' with newline markers between sections so spoilers can span newlines
                        merged_inline = []
                        combined_to_run_index = []
                        for run_idx, sec in enumerate(run):
                            elems = sec.get("elements", [])
                            if run_idx > 0:
                                # represent section break as a newline text element so spoilers may span sections
                                merged_inline.append({"type": "text", "text": "\n"})
                                combined_to_run_index.append(
                                    run_idx - 1
                                )  # newline maps to previous run (will be redistributed)
                            for el in deepcopy(elems):
                                merged_inline.append(el)
                                combined_to_run_index.append(run_idx)
                        # process merged inline elements as a single inline list
                        b_merged, r_merged = _split_spoilers_in_inline_elements(
                            merged_inline
                        )
                        # Distribute merged results back into the original run blocks, preserving each block's type and metadata
                        per_run_b = [[] for _ in run]
                        per_run_r = [[] for _ in run]

                        # Group outputs by their _src_idx so we can replay outputs in merged-input order.
                        def distribute_grouped(output_list, target_per_run):
                            grouped = defaultdict(list)
                            orphans = []
                            for out_el in output_list:
                                if isinstance(out_el, dict) and "_src_idx" in out_el:
                                    src = out_el.pop("_src_idx")
                                    grouped[src].append(out_el)
                                else:
                                    orphans.append(out_el)
                            # Iterate merged positions in order and append grouped outputs for each position
                            for pos, run_idx in enumerate(combined_to_run_index):
                                if pos in grouped:
                                    target_per_run[run_idx].extend(grouped[pos])
                            # Place orphans at the end of the first run as fallback
                            if orphans:
                                target_per_run[0].extend(orphans)

                        distribute_grouped(b_merged, per_run_b)
                        distribute_grouped(r_merged, per_run_r)

                        # If any run corresponds to a preformatted block and contains a redaction code element,
                        # collapse the entire run's redacted elements into a single preformatted redaction so code
                        # blocks inside spoilers are represented as block-level redactions.
                        for run_idx, sec in enumerate(run):
                            if sec.get("type") == "rich_text_preformatted":
                                # detect any code-style redaction in per_run_r[run_idx]
                                has_code = any(
                                    isinstance(x, dict)
                                    and isinstance(x.get("style"), dict)
                                    and x["style"].get("code")
                                    for x in per_run_r[run_idx]
                                )
                                if has_code:
                                    per_run_r[run_idx] = [
                                        {
                                            "type": "text",
                                            "text": "[spoiler hidden]",
                                            "style": {"code": True},
                                        }
                                    ]
                        # Now rewrap per-run outputs into blocks matching the original types and metadata
                        for run_idx, sec in enumerate(run):
                            sec_copy_b = deepcopy(sec)
                            sec_copy_b["elements"] = per_run_b[run_idx]
                            bold_list.append(sec_copy_b)
                            sec_copy_r = deepcopy(sec)
                            sec_copy_r["elements"] = per_run_r[run_idx]
                            redacted_list.append(sec_copy_r)
                    i = j
                else:
                    b_item, r_item = _process_object_variants(item)
                    bold_list.append(b_item)
                    redacted_list.append(r_item)
                    i += 1
            return bold_list, redacted_list
    elif isinstance(obj, dict):
        bold = {}
        redacted = {}
        for k, v in obj.items():
            # If the value is a list of inline elements, replace it with processed lists.
            if isinstance(v, list) and _is_inline_elements_list(v):
                b_v, r_v = _split_spoilers_in_inline_elements(v)
                bold[k] = b_v
                redacted[k] = r_v
            else:
                b_v, r_v = _process_object_variants(v)
                bold[k] = b_v
                redacted[k] = r_v
        return bold, redacted
    else:
        return deepcopy(obj), deepcopy(obj)


def split_spoilers_in_rich_text_blocks(blocks):
    """
    Accepts:
      - a single block dict, or
      - a list of blocks

    Returns a tuple (bold_blocks, redacted_blocks) where each is the input structure with
    inline spoilers handled as:
      - bold_blocks: spoilered runs forced bold (no 'spoiler' key)
      - redacted_blocks: spoilered runs replaced with an inline code block '[spoiler hidden]' with
        style {'code': True}

    NOTE: internal transient '_src_idx' annotations are stripped from the returned structures.
    """
    b, r = _process_object_variants(blocks)

    def _strip_src(obj):
        # Recursively remove any '_src_idx' keys from dicts in the structure.
        if isinstance(obj, list):
            return [_strip_src(x) for x in obj]
        if isinstance(obj, dict):
            new = {}
            for k, v in obj.items():
                if k == "_src_idx":
                    continue
                new[k] = _strip_src(v)
            return new
        return deepcopy(obj)

    return _strip_src(b), _strip_src(r)


async def create_spoiler_handler(ack: AsyncAck, body: dict, client: AsyncWebClient):
    from slack_extra.env import env

    await ack()
    view = body["view"]
    state = view["state"]["values"]
    channel = view.get("private_metadata", "")

    rich_text = state["spoiler_input"]["spoiler_input"]["rich_text_value"]
    files = state["spoiler_files"]["spoiler_files"]["files"]
    files_to_upload = []
    for f in files:
        async with env.http.get(
            f["url_private_download"],
            headers={"Authorization": f"Bearer {config.slack.bot_token}"},
        ) as resp:
            if resp.status != 200:
                await client.chat_postEphemeral(
                    channel=channel,
                    user=body["user"]["id"],
                    text=f"i couldn't download the file {f['name']} :(\nplease try uploading it again!",
                )
                return
            data = await resp.read()
            files_to_upload.append(
                {
                    "file": data,
                    "filename": f["name"],
                    "title": f["name"],
                }
            )

    bold_blocks, redacted_blocks = split_spoilers_in_rich_text_blocks(rich_text)

    blocks_to_post = []
    if isinstance(bold_blocks, dict):
        blocks_to_post.append(bold_blocks)
    else:
        blocks_to_post.extend(bold_blocks)
    # add a visual separator
    blocks_to_post.append({"type": "divider"})
    if isinstance(redacted_blocks, dict):
        blocks_to_post.append(redacted_blocks)
    else:
        blocks_to_post.extend(redacted_blocks)

    message_blocks = [
        redacted_blocks,
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View spoiler",
                        "emoji": True,
                    },
                    "action_id": "view_spoiler",
                    "value": "db",
                }
            ],
        },
    ]

    user_id = body["user"]["id"]
    slack_user = await client.users_info(user=user_id)
    display_name = (
        slack_user.get("user", {}).get("profile", {}).get("display_name")
        or slack_user.get("user", {}).get("real_name")
        or "Unknown User"
    )
    pfp = slack_user.get("user", {}).get("profile", {}).get("image_512") or None

    msg = await client.chat_postMessage(
        channel=channel,
        blocks=message_blocks,
        text="spoiler :hehe:",
        username=display_name,
        icon_url=pfp,
        unfurl_media=True,
        unfurl_links=True,
    )

    db_entry = Spoiler(
        channel=channel, message_ts=msg["ts"], message=bold_blocks, user=user_id
    )
    await Spoiler.insert(db_entry)
    await client.files_upload_v2(
        channel=channel,
        file_uploads=files_to_upload,
    )
