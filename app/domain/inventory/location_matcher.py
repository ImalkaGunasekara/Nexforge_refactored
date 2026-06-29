def normalize_location_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(name.strip().lower().split())


def build_location_index(locations: list[dict]) -> dict[str, dict]:
    index = {}

    for location in locations:
        name = normalize_location_name(location.get("name"))
        if name and name not in index:
            index[name] = location

    return index


def match_location(source_location: dict, target_locations: list[dict]) -> dict | None:
    source_name = normalize_location_name(source_location.get("name"))
    if not source_name:
        return None

    target_index = build_location_index(target_locations)
    return target_index.get(source_name)


def match_locations(source_locations: list[dict], target_locations: list[dict]) -> dict[str, str]:
    matched = {}
    target_index = build_location_index(target_locations)

    for source in source_locations:
        source_id = source.get("id")
        source_name = normalize_location_name(source.get("name"))

        if not source_id or not source_name:
            continue

        target = target_index.get(source_name)
        if target and target.get("id"):
            matched[str(source_id)] = str(target["id"])

    return matched
