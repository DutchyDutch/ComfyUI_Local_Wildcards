import fnmatch
import json
import random
import re
import secrets
from pathlib import Path


NODE_DIR = Path(__file__).resolve().parent
WILDCARD_DIR = NODE_DIR / "wildcards"

INSERT_PLACEHOLDER = "Select wildcard to insert"
NO_WILDCARDS = "No wildcards found"

ROOT_GROUP_NAME = "Root"
HEADER_PREFIX = "• "

MAX_SEED = 9007199254740991
MAX_DROPDOWN_ITEMS = 50000

SUPPORTED_FILE_EXTENSIONS = [".txt", ".json", ".yaml", ".yml"]

TOKEN_RE = re.compile(r"__([^\r\n]+?)__")
CHOICE_RE = re.compile(r"\{([^{}\r\n]*\|[^{}\r\n]*)\}")

_CACHE_SIGNATURE = None
_CACHE_WILDCARDS = None
_CACHE_DROPDOWN = None


def ensure_wildcard_dir():
    try:
        WILDCARD_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as error:
        print(f"[ComfyUI Local Wildcards] Could not create wildcards folder: {error}")


def normalize_wildcard_name(name):
    name = str(name or "").strip()
    name = name.replace("\\", "/")

    while "//" in name:
        name = name.replace("//", "/")

    if name.startswith("__") and name.endswith("__") and len(name) >= 4:
        name = name[2:-2]

    name = name.strip("/")
    name = name.strip()

    lower_name = name.lower()

    for extension in SUPPORTED_FILE_EXTENSIONS:
        if lower_name.endswith(extension):
            name = name[: -len(extension)]
            break

    return name.strip()


def clean_text_line(line):
    line = str(line).strip()

    if not line:
        return None

    if line.startswith("#"):
        return None

    if line.startswith("//"):
        return None

    return line


def normalize_relative_name(path):
    try:
        relative = path.relative_to(WILDCARD_DIR)
        no_suffix = relative.with_suffix("")
        return no_suffix.as_posix()
    except Exception:
        return path.stem


def get_dropdown_directory(path):
    try:
        relative_parent = path.parent.relative_to(WILDCARD_DIR)
    except Exception:
        return ROOT_GROUP_NAME

    if str(relative_parent) in ["", "."]:
        return ROOT_GROUP_NAME

    return relative_parent.as_posix()


def unique_keep_order(items):
    seen = set()
    output = []

    for item in items:
        item = normalize_wildcard_name(item)

        if not item:
            continue

        if item not in seen:
            seen.add(item)
            output.append(item)

    return output


def leaf_name(name):
    name = normalize_wildcard_name(name)

    if "/" in name:
        name = name.split("/")[-1]

    if "." in name:
        name = name.split(".")[-1]

    return name.strip()


def token_contains_glob(token):
    token = str(token)

    return "*" in token or "?" in token or "[" in token


def to_unicode_bold(text):
    normal_upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    bold_upper = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙"

    normal_lower = "abcdefghijklmnopqrstuvwxyz"
    bold_lower = "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"

    normal_digits = "0123456789"
    bold_digits = "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"

    translation = {}

    for normal, bold in zip(normal_upper, bold_upper):
        translation[ord(normal)] = bold

    for normal, bold in zip(normal_lower, bold_lower):
        translation[ord(normal)] = bold

    for normal, bold in zip(normal_digits, bold_digits):
        translation[ord(normal)] = bold

    return str(text).translate(translation)


def add_dropdown_name(display_groups, directory_name, wildcard_name):
    directory_name = str(directory_name or ROOT_GROUP_NAME).strip()

    if not directory_name:
        directory_name = ROOT_GROUP_NAME

    wildcard_name = normalize_wildcard_name(wildcard_name)

    if not wildcard_name:
        return

    if directory_name not in display_groups:
        display_groups[directory_name] = set()

    display_groups[directory_name].add(wildcard_name)


def add_name_to_database(
    wildcards,
    display_groups,
    name,
    choices,
    show_in_dropdown=False,
    dropdown_directory=ROOT_GROUP_NAME,
):
    name = normalize_wildcard_name(name)

    if not name:
        return

    cleaned_choices = []

    for choice in choices:
        if choice is None:
            continue

        choice = str(choice).strip()

        if choice:
            cleaned_choices.append(choice)

    if not cleaned_choices:
        return

    names_to_add = unique_keep_order(
        [
            name,
            name.lower(),
        ]
    )

    for database_name in names_to_add:
        if database_name not in wildcards:
            wildcards[database_name] = []

        wildcards[database_name].extend(cleaned_choices)

    if show_in_dropdown:
        add_dropdown_name(display_groups, dropdown_directory, name)


def add_choices_with_names(
    wildcards,
    display_groups,
    database_names,
    display_names_to_show,
    choices,
    dropdown_directory=ROOT_GROUP_NAME,
):
    for name in database_names:
        add_name_to_database(
            wildcards,
            display_groups,
            name,
            choices,
            show_in_dropdown=False,
            dropdown_directory=dropdown_directory,
        )

    for name in display_names_to_show:
        add_name_to_database(
            wildcards,
            display_groups,
            name,
            choices,
            show_in_dropdown=True,
            dropdown_directory=dropdown_directory,
        )


def value_to_choices(value):
    choices = []

    if value is None:
        return choices

    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                cleaned = item.strip()

                if cleaned:
                    choices.append(cleaned)

            elif isinstance(item, (int, float, bool)):
                choices.append(str(item))

            elif isinstance(item, dict):
                if "text" in item:
                    choices.append(str(item["text"]))
                elif "value" in item:
                    choices.append(str(item["value"]))
                elif "prompt" in item:
                    choices.append(str(item["prompt"]))
                elif "name" in item:
                    choices.append(str(item["name"]))
                else:
                    choices.append(json.dumps(item, ensure_ascii=False))

            else:
                choices.append(str(item))

    elif isinstance(value, str):
        cleaned = value.strip()

        if cleaned:
            choices.append(cleaned)

    elif isinstance(value, (int, float, bool)):
        choices.append(str(value))

    return choices


def load_txt_file(path, wildcards, display_groups):
    try:
        choices = []

        with open(path, "r", encoding="utf-8") as file:
            for line in file.readlines():
                cleaned = clean_text_line(line)

                if cleaned is not None:
                    choices.append(cleaned)

        if not choices:
            return

        relative_name = normalize_relative_name(path)
        simple_name = path.stem
        dropdown_directory = get_dropdown_directory(path)

        database_names = unique_keep_order(
            [
                relative_name,
                simple_name,
                leaf_name(relative_name),
            ]
        )

        display_names_to_show = unique_keep_order(
            [
                relative_name,
            ]
        )

        add_choices_with_names(
            wildcards,
            display_groups,
            database_names,
            display_names_to_show,
            choices,
            dropdown_directory=dropdown_directory,
        )

    except Exception as error:
        print(f"[ComfyUI Local Wildcards] Could not read TXT file {path}: {error}")


def data_path_to_dot_name(parts):
    clean_parts = []

    for part in parts:
        part = str(part).strip()

        if part:
            clean_parts.append(part)

    return ".".join(clean_parts)


def data_path_to_slash_name(parts):
    clean_parts = []

    for part in parts:
        part = str(part).strip()

        if part:
            clean_parts.append(part)

    return "/".join(clean_parts)


def walk_data(
    value,
    wildcards,
    display_groups,
    file_relative_name,
    file_simple_name,
    data_parts,
    dropdown_directory,
):
    try:
        current_dot_name = data_path_to_dot_name(data_parts)
        current_slash_name = data_path_to_slash_name(data_parts)

        direct_choice_keys = [
            "choices",
            "options",
            "values",
            "items",
            "wildcards",
            "prompts",
            "list",
            "data",
        ]

        if isinstance(value, dict):
            for direct_key in direct_choice_keys:
                if direct_key in value and isinstance(value[direct_key], list):
                    choices = value_to_choices(value[direct_key])

                    if choices:
                        if current_dot_name:
                            current_leaf = leaf_name(current_dot_name)
                            full_dot_name = f"{file_relative_name}.{current_dot_name}"
                            full_slash_name = f"{file_relative_name}/{current_slash_name}"

                            database_names = unique_keep_order(
                                [
                                    current_dot_name,
                                    current_slash_name,
                                    current_leaf,
                                    full_dot_name,
                                    full_slash_name,
                                    f"{file_simple_name}.{current_dot_name}",
                                    f"{file_simple_name}/{current_slash_name}",
                                ]
                            )

                            display_names_to_show = unique_keep_order(
                                [
                                    full_slash_name,
                                ]
                            )
                        else:
                            database_names = unique_keep_order(
                                [
                                    file_relative_name,
                                    file_simple_name,
                                    leaf_name(file_relative_name),
                                ]
                            )

                            display_names_to_show = unique_keep_order(
                                [
                                    file_relative_name,
                                ]
                            )

                        add_choices_with_names(
                            wildcards,
                            display_groups,
                            database_names,
                            display_names_to_show,
                            choices,
                            dropdown_directory=dropdown_directory,
                        )

                    return

            for key, child_value in value.items():
                key = str(key).strip()

                if not key:
                    continue

                if key == "__yaml_list__":
                    continue

                child_parts = data_parts + [key]

                if isinstance(child_value, dict):
                    walk_data(
                        child_value,
                        wildcards,
                        display_groups,
                        file_relative_name,
                        file_simple_name,
                        child_parts,
                        dropdown_directory,
                    )

                else:
                    child_dot_name = data_path_to_dot_name(child_parts)
                    child_slash_name = data_path_to_slash_name(child_parts)
                    child_leaf = leaf_name(child_dot_name)

                    full_dot_name = f"{file_relative_name}.{child_dot_name}"
                    full_slash_name = f"{file_relative_name}/{child_slash_name}"

                    choices = value_to_choices(child_value)

                    if choices:
                        database_names = unique_keep_order(
                            [
                                child_dot_name,
                                child_slash_name,
                                child_leaf,
                                key,
                                full_dot_name,
                                full_slash_name,
                                f"{file_simple_name}.{child_dot_name}",
                                f"{file_simple_name}/{child_slash_name}",
                            ]
                        )

                        display_names_to_show = unique_keep_order(
                            [
                                full_slash_name,
                            ]
                        )

                        add_choices_with_names(
                            wildcards,
                            display_groups,
                            database_names,
                            display_names_to_show,
                            choices,
                            dropdown_directory=dropdown_directory,
                        )

        else:
            choices = value_to_choices(value)

            if choices:
                database_names = unique_keep_order(
                    [
                        file_relative_name,
                        file_simple_name,
                        leaf_name(file_relative_name),
                    ]
                )

                display_names_to_show = unique_keep_order(
                    [
                        file_relative_name,
                    ]
                )

                add_choices_with_names(
                    wildcards,
                    display_groups,
                    database_names,
                    display_names_to_show,
                    choices,
                    dropdown_directory=dropdown_directory,
                )

    except Exception as error:
        print(f"[ComfyUI Local Wildcards] Could not walk data in {file_relative_name}: {error}")


def load_json_file(path, wildcards, display_groups):
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        relative_name = normalize_relative_name(path)
        simple_name = path.stem
        dropdown_directory = get_dropdown_directory(path)

        walk_data(
            data,
            wildcards,
            display_groups,
            relative_name,
            simple_name,
            [],
            dropdown_directory,
        )

    except Exception as error:
        print(f"[ComfyUI Local Wildcards] Could not read JSON file {path}: {error}")


def count_leading_spaces(text):
    count = 0

    for character in text:
        if character == " ":
            count += 1
        else:
            break

    return count


def collect_yaml_block_scalar(lines, start_index, parent_indent, folded=True):
    collected_raw_lines = []
    index = start_index

    while index < len(lines):
        raw_line = lines[index].rstrip("\r\n")
        stripped = raw_line.strip()

        if not stripped:
            collected_raw_lines.append("")
            index += 1
            continue

        indent = count_leading_spaces(raw_line)

        if indent <= parent_indent:
            break

        collected_raw_lines.append(raw_line)
        index += 1

    non_empty_indents = []

    for raw_line in collected_raw_lines:
        if raw_line.strip():
            non_empty_indents.append(count_leading_spaces(raw_line))

    if non_empty_indents:
        base_indent = min(non_empty_indents)
    else:
        base_indent = parent_indent + 1

    cleaned_lines = []

    for raw_line in collected_raw_lines:
        if raw_line.strip():
            cleaned_lines.append(raw_line[base_indent:].rstrip())
        else:
            cleaned_lines.append("")

    if folded:
        paragraphs = []
        current_words = []

        for line in cleaned_lines:
            stripped_line = line.strip()

            if not stripped_line:
                if current_words:
                    paragraphs.append(" ".join(current_words))
                    current_words = []
                continue

            current_words.append(stripped_line)

        if current_words:
            paragraphs.append(" ".join(current_words))

        return "\n".join(paragraphs).strip(), index

    return "\n".join(cleaned_lines).strip(), index


def parse_simple_yaml_lines(lines):
    root = {}
    stack = [(-1, root)]
    index = 0

    block_markers = [">", "|", ">-", "|-", ">+", "|+"]

    while index < len(lines):
        line_without_newline = lines[index].rstrip("\r\n")
        stripped = line_without_newline.strip()

        if not stripped:
            index += 1
            continue

        if stripped.startswith("#"):
            index += 1
            continue

        indent = count_leading_spaces(line_without_newline)

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]

        if stripped == "-" or stripped.startswith("- "):
            if "__yaml_list__" not in parent:
                parent["__yaml_list__"] = []

            if stripped == "-":
                item = ""
            else:
                item = stripped[2:].strip()

            if item in block_markers:
                folded = item.startswith(">")
                block_text, next_index = collect_yaml_block_scalar(
                    lines,
                    index + 1,
                    indent,
                    folded=folded,
                )

                if block_text:
                    parent["__yaml_list__"].append(block_text)

                index = next_index
                continue

            parent["__yaml_list__"].append(item.strip('"').strip("'"))
            index += 1
            continue

        if ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()

            if not key:
                index += 1
                continue

            if value in block_markers:
                folded = value.startswith(">")
                block_text, next_index = collect_yaml_block_scalar(
                    lines,
                    index + 1,
                    indent,
                    folded=folded,
                )

                parent[key] = block_text
                index = next_index
                continue

            if value == "":
                new_dict = {}
                parent[key] = new_dict
                stack.append((indent, new_dict))
                index += 1
                continue

            if value.startswith("[") and value.endswith("]"):
                inside = value[1:-1].strip()
                items = []

                if inside:
                    for part in inside.split(","):
                        cleaned = part.strip().strip('"').strip("'")

                        if cleaned:
                            items.append(cleaned)

                parent[key] = items
                index += 1
                continue

            parent[key] = value.strip('"').strip("'")
            index += 1
            continue

        index += 1

    return root


def fix_simple_yaml_lists(value):
    if isinstance(value, dict):
        if "__yaml_list__" in value and len(value) == 1:
            return value["__yaml_list__"]

        fixed = {}

        for key, child_value in value.items():
            if key == "__yaml_list__":
                fixed[key] = child_value
            else:
                fixed[key] = fix_simple_yaml_lists(child_value)

        return fixed

    if isinstance(value, list):
        return [fix_simple_yaml_lists(item) for item in value]

    return value


def load_yaml_file(path, wildcards, display_groups):
    try:
        with open(path, "r", encoding="utf-8") as file:
            text = file.read()

        data = None

        try:
            import yaml

            data = yaml.safe_load(text)
        except Exception:
            data = None

        if data is None:
            lines = text.splitlines()
            data = parse_simple_yaml_lines(lines)
            data = fix_simple_yaml_lists(data)

        if not data:
            return

        relative_name = normalize_relative_name(path)
        simple_name = path.stem
        dropdown_directory = get_dropdown_directory(path)

        walk_data(
            data,
            wildcards,
            display_groups,
            relative_name,
            simple_name,
            [],
            dropdown_directory,
        )

    except Exception as error:
        print(f"[ComfyUI Local Wildcards] Could not read YAML file {path}: {error}")


def get_wildcard_file_paths():
    ensure_wildcard_dir()

    paths = []

    try:
        for path in WILDCARD_DIR.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_FILE_EXTENSIONS:
                paths.append(path)

    except Exception as error:
        print(f"[ComfyUI Local Wildcards] Could not scan wildcards folder: {error}")

    paths = sorted(paths, key=lambda p: p.as_posix().lower())

    return paths


def get_scan_signature():
    paths = get_wildcard_file_paths()

    signature = []

    for path in paths:
        try:
            stat = path.stat()
            relative = path.relative_to(WILDCARD_DIR).as_posix()
            signature.append((relative, stat.st_mtime_ns, stat.st_size))

        except Exception:
            pass

    return tuple(signature)


def build_wildcard_database():
    wildcards = {}
    display_groups = {}

    try:
        paths = get_wildcard_file_paths()

        for path in paths:
            suffix = path.suffix.lower()

            if suffix == ".txt":
                load_txt_file(path, wildcards, display_groups)

            elif suffix == ".json":
                load_json_file(path, wildcards, display_groups)

            elif suffix in [".yaml", ".yml"]:
                load_yaml_file(path, wildcards, display_groups)

    except Exception as error:
        print(f"[ComfyUI Local Wildcards] Could not build wildcard database: {error}")

    return wildcards, display_groups


def build_grouped_dropdown(display_groups):
    dropdown = [INSERT_PLACEHOLDER]

    try:
        if not display_groups:
            dropdown.append(NO_WILDCARDS)
            return dropdown

        total_count = 0

        directories = sorted(
            display_groups.keys(),
            key=lambda x: (x != ROOT_GROUP_NAME, x.lower()),
        )

        for directory in directories:
            wildcard_names = sorted(display_groups[directory], key=lambda x: x.lower())

            if not wildcard_names:
                continue

            bold_directory = to_unicode_bold(directory)
            dropdown.append(f"{HEADER_PREFIX}{bold_directory}")

            for name in wildcard_names:
                dropdown.append(f"    __{name}__")
                total_count += 1

                if total_count >= MAX_DROPDOWN_ITEMS:
                    dropdown.append(
                        f"Too many wildcards - showing first {MAX_DROPDOWN_ITEMS}"
                    )
                    return dropdown

    except Exception as error:
        print(f"[ComfyUI Local Wildcards] Could not build dropdown: {error}")
        return [INSERT_PLACEHOLDER, NO_WILDCARDS]

    return dropdown


def get_wildcard_database():
    global _CACHE_SIGNATURE
    global _CACHE_WILDCARDS
    global _CACHE_DROPDOWN

    try:
        signature = get_scan_signature()

        if (
            _CACHE_SIGNATURE == signature
            and _CACHE_WILDCARDS is not None
            and _CACHE_DROPDOWN is not None
        ):
            return _CACHE_WILDCARDS, _CACHE_DROPDOWN

        wildcards, display_groups = build_wildcard_database()
        dropdown = build_grouped_dropdown(display_groups)

        _CACHE_SIGNATURE = signature
        _CACHE_WILDCARDS = wildcards
        _CACHE_DROPDOWN = dropdown

        total_dropdown_names = 0

        for names in display_groups.values():
            total_dropdown_names += len(names)

        print(
            f"[ComfyUI Local Wildcards] Scanned {len(get_wildcard_file_paths())} files, found {total_dropdown_names} dropdown wildcard names in {len(display_groups)} directories."
        )

        return wildcards, dropdown

    except Exception as error:
        print(f"[ComfyUI Local Wildcards] Database error: {error}")
        return {}, [INSERT_PLACEHOLDER, NO_WILDCARDS]


def get_dropdown_wildcards():
    try:
        _wildcards, dropdown = get_wildcard_database()
        return dropdown

    except Exception as error:
        print(f"[ComfyUI Local Wildcards] Dropdown scan failed: {error}")
        return [INSERT_PLACEHOLDER, NO_WILDCARDS]


def get_glob_matching_keys(wildcards, pattern):
    pattern = normalize_wildcard_name(pattern)
    pattern_lower = pattern.lower()

    matches = []
    seen = set()

    for key in wildcards.keys():
        key_text = normalize_wildcard_name(key)

        if not key_text:
            continue

        key_lower = key_text.lower()
        key_leaf_lower = leaf_name(key_text).lower()

        direct_match = fnmatch.fnmatchcase(key_lower, pattern_lower)
        leaf_match = fnmatch.fnmatchcase(key_leaf_lower, pattern_lower)

        if not direct_match and not leaf_match:
            continue

        if key_lower in seen:
            continue

        seen.add(key_lower)
        matches.append(key)

    return sorted(matches, key=lambda x: str(x).lower())


def get_choices_for_token(wildcards, token, rng=None):
    token = normalize_wildcard_name(token)

    if not token:
        return None

    direct_candidates = unique_keep_order(
        [
            token,
            token.lower(),
        ]
    )

    for candidate in direct_candidates:
        if candidate in wildcards:
            return wildcards[candidate]

    token_leaf = leaf_name(token)

    leaf_candidates = unique_keep_order(
        [
            token_leaf,
            token_leaf.lower(),
        ]
    )

    for candidate in leaf_candidates:
        if candidate in wildcards:
            return wildcards[candidate]

    token_lower = token.lower()

    for key, choices in wildcards.items():
        key_normalized = normalize_wildcard_name(key)

        if key_normalized.lower() == token_lower:
            return choices

    if token_contains_glob(token):
        matching_keys = get_glob_matching_keys(wildcards, token)

        if matching_keys:
            if rng is None:
                selected_key = matching_keys[0]
            else:
                selected_key = rng.choice(matching_keys)

            return wildcards[selected_key]

    return None


def expand_random_choices(text, rng):
    current_text = str(text)
    changed = False

    def replace_choice(match):
        nonlocal changed

        content = match.group(1)
        options = []

        for option in content.split("|"):
            options.append(option.strip())

        if not options:
            return match.group(0)

        changed = True
        return rng.choice(options)

    new_text = CHOICE_RE.sub(replace_choice, current_text)

    return new_text, changed


def expand_wildcards(text, wildcards, rng, max_depth=30):
    current_text = str(text)

    for _ in range(max_depth):
        changed_anything = False

        current_text, changed_choices = expand_random_choices(current_text, rng)

        if changed_choices:
            changed_anything = True

        def replace_token(match):
            nonlocal changed_anything

            token = match.group(1).strip()
            choices = get_choices_for_token(wildcards, token, rng)

            if not choices:
                return match.group(0)

            changed_anything = True
            return rng.choice(choices)

        new_text = TOKEN_RE.sub(replace_token, current_text)

        if new_text != current_text:
            changed_anything = True

        current_text = new_text

        if not changed_anything:
            return current_text

    return current_text


class LocalWildcardText:
    CATEGORY = "Local Wildcards"
    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("text", "used_seed")
    FUNCTION = "process"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "A photo of __color__",
                    },
                ),
                "insert_wildcard": (
                    get_dropdown_wildcards(),
                ),
                "seed_mode": (
                    ["fixed", "random"],
                    {
                        "default": "fixed",
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": MAX_SEED,
                        "step": 1,
                        "display": "number",
                    },
                ),
            }
        }

    @classmethod
    def IS_CHANGED(cls, text, insert_wildcard, seed_mode, seed):
        if seed_mode == "random":
            return float("nan")

        signature = get_scan_signature()

        return str((text, seed_mode, seed, signature))

    def process(self, text, insert_wildcard, seed_mode, seed):
        if seed_mode == "random":
            used_seed = secrets.randbelow(MAX_SEED)
        else:
            used_seed = int(seed)

        rng = random.Random(used_seed)

        wildcards, _dropdown = get_wildcard_database()
        output_text = expand_wildcards(text, wildcards, rng)

        return {
            "ui": {
                "used_seed": [str(used_seed)],
                "expanded_text": [output_text],
            },
            "result": (
                output_text,
                used_seed,
            ),
        }


NODE_CLASS_MAPPINGS = {
    "LocalWildcardText": LocalWildcardText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LocalWildcardText": "Local Wildcard Text",
}