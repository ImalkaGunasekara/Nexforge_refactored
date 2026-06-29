def clean_dict(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


def _tags_to_string(tags) -> str:
    if not tags:
        return ""
    if isinstance(tags, list):
        return ", ".join(str(t) for t in tags)
    return str(tags)


def build_product_input_from_backup(product: dict) -> dict:
    status = product.get("status")
    if status:
        status = status.lower()

    return clean_dict(
        {
            "title": product.get("title"),
            "handle": product.get("handle"),
            "body_html": product.get("descriptionHtml"),
            "vendor": product.get("vendor"),
            "product_type": product.get("productType"),
            "tags": _tags_to_string(product.get("tags")),
            "status": status,
            "options": build_product_options_input(product),  # only for create
        }
    )


def build_product_options_input(product: dict) -> list[dict]:
    options = product.get("options") or []
    result = []
    for option in options:
        result.append(
            clean_dict(
                {
                    "name": option.get("name"),
                    "values": option.get("values", []),
                }
            )
        )
    return result


def build_variant_input_from_backup(variant: dict) -> dict:
    selected_options = variant.get("selectedOptions") or []
    return clean_dict(
        {
            "title": variant.get("title"),
            "sku": variant.get("sku"),
            "barcode": variant.get("barcode"),
            "price": variant.get("price"),
            "compare_at_price": variant.get("compareAtPrice"),
            "taxable": variant.get("taxable"),
            "position": variant.get("position"),
            "inventory_item": build_inventory_item_input(variant),
            "selected_options": [
                clean_dict(
                    {
                        "name": option.get("name"),
                        "value": option.get("value"),
                    }
                )
                for option in selected_options
            ],
        }
    )


def build_inventory_item_input(variant: dict) -> dict | None:
    inventory_item = variant.get("inventoryItem") or {}
    if not inventory_item:
        return None
    payload = clean_dict(
        {
            "tracked": inventory_item.get("tracked"),
            "requires_shipping": inventory_item.get("requiresShipping"),
        }
    )
    return payload or None


def build_variant_rest_input(variant: dict) -> dict:
    selected_options = variant.get("selectedOptions") or []
    option_values = ["", "", ""]
    for i, opt in enumerate(selected_options[:3]):
        option_values[i] = opt.get("value", "")

    payload = clean_dict(
        {
            "sku": variant.get("sku"),
            "barcode": variant.get("barcode"),
            "price": variant.get("price"),
            "compare_at_price": variant.get("compareAtPrice"),
            "taxable": variant.get("taxable"),
            "position": variant.get("position"),
            "option1": option_values[0] or None,
            "option2": option_values[1] or None,
            "option3": option_values[2] or None,
            "weight": variant.get("weight"),
            "weight_unit": variant.get("weight_unit"),
            "requires_shipping": variant.get("requires_shipping"),
        }
    )

    inv_item = variant.get("inventoryItem") or {}
    if inv_item.get("tracked"):
        payload["inventory_management"] = "shopify"
    else:
        payload["inventory_management"] = None

    return payload