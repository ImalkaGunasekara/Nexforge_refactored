def clean_dict(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}


def build_product_input_from_backup(product: dict) -> dict:
    return clean_dict(
        {
            "title": product.get("title"),
            "handle": product.get("handle"),
            "descriptionHtml": product.get("descriptionHtml"),
            "vendor": product.get("vendor"),
            "productType": product.get("productType"),
            "tags": product.get("tags", []),
            "status": product.get("status"),
            "options": build_product_options_input(product),
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
            "compareAtPrice": variant.get("compareAtPrice"),
            "taxable": variant.get("taxable"),
            "position": variant.get("position"),
            "inventoryItem": build_inventory_item_input(variant),
            "selectedOptions": [
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
            "requiresShipping": inventory_item.get("requiresShipping"),
        }
    )

    return payload or None
