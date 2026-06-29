import json
import re


METAOBJECT_GID_PATTERN = re.compile(r"gid://shopify/Metaobject/\d+")


def extract_metaobject_gids(value: str | None, metafield_type: str | None) -> list[str]:
    if not value:
        return []

    metafield_type = (metafield_type or "").strip()

    if metafield_type in {
        "metaobject_reference",
        "list.metaobject_reference",
    }:
        return METAOBJECT_GID_PATTERN.findall(value)

    return []


def rewrite_metaobject_refs(
    value: str | None,
    metafield_type: str | None,
    entry_id_map: dict[str, str] | None,
) -> str | None:
    if value is None:
        return value

    if not entry_id_map:
        return value

    metafield_type = (metafield_type or "").strip()

    if metafield_type == "metaobject_reference":
        return entry_id_map.get(value, value)

    if metafield_type == "list.metaobject_reference":
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                rewritten = [entry_id_map.get(item, item) for item in parsed]
                return json.dumps(rewritten)
        except Exception:
            return value

    return value
