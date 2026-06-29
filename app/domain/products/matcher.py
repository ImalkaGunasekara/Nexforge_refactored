def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())


def normalize_sku(value: str | None) -> str:
    return normalize_text(value)


def normalize_barcode(value: str | None) -> str:
    return normalize_text(value)


def normalize_option_value(value: str | None) -> str:
    return normalize_text(value)


def build_variant_signature(variant: dict) -> tuple:
    selected_options = variant.get("selectedOptions") or []
    option_pairs = []

    for option in selected_options:
        name = normalize_text(option.get("name"))
        value = normalize_option_value(option.get("value"))
        option_pairs.append((name, value))

    option_pairs = tuple(sorted(option_pairs))

    return (
        normalize_sku(variant.get("sku")),
        normalize_barcode(variant.get("barcode")),
        option_pairs,
    )


def variants_match(source_variant: dict, target_variant: dict) -> bool:
    source_sku = normalize_sku(source_variant.get("sku"))
    target_sku = normalize_sku(target_variant.get("sku"))

    if source_sku and target_sku and source_sku == target_sku:
        return True

    source_barcode = normalize_barcode(source_variant.get("barcode"))
    target_barcode = normalize_barcode(target_variant.get("barcode"))

    if source_barcode and target_barcode and source_barcode == target_barcode:
        return True

    return build_variant_signature(source_variant) == build_variant_signature(target_variant)


def find_matching_variant(source_variant: dict, target_variants: list[dict]) -> dict | None:
    for target_variant in target_variants:
        if variants_match(source_variant, target_variant):
            return target_variant
    return None


def match_variants(source_variants: list[dict], target_variants: list[dict]) -> dict[str, str]:
    matched = {}

    for source_variant in source_variants:
        source_id = source_variant.get("id")
        if not source_id:
            continue

        target_variant = find_matching_variant(source_variant, target_variants)
        if target_variant and target_variant.get("id"):
            matched[str(source_id)] = str(target_variant["id"])

    return matched
