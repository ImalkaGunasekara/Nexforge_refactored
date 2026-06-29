def normalize_metafield_type(type_name: str | None) -> str:
    if not type_name:
        return ""

    type_name = type_name.strip()

    aliases = {
        "string": "single_line_text_field",
        "integer": "number_integer",
        "json_string": "json",
        "rich_text": "rich_text_field",
    }

    return aliases.get(type_name, type_name)


def metafield_types_match(source_type: str | None, target_type: str | None) -> bool:
    return normalize_metafield_type(source_type) == normalize_metafield_type(target_type)
