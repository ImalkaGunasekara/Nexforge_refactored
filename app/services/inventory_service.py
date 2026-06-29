from app.domain.inventory.location_matcher import match_locations
from app.shopify.graphql import graphql_data
from app.shopify.queries.inventory import (
    ACTIVATE_INVENTORY_AT_LOCATION,
    GET_INVENTORY_LEVELS,
    GET_LOCATIONS,
    SET_INVENTORY_QUANTITIES,
    SET_TRACKED_AND_SHIPPING,
)


async def get_locations(shop: str) -> list[dict]:
    locations = []
    cursor = None

    while True:
        data = await graphql_data(
            shop=shop,
            query=GET_LOCATIONS,
            variables={"cursor": cursor},
        )

        root = data.get("locations", {})
        edges = root.get("edges", [])

        for edge in edges:
            node = edge.get("node") or {}
            if node.get("id"):
                locations.append(node)

        page_info = root.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break

        cursor = page_info.get("endCursor")

    return locations


async def get_inventory_levels(shop: str, inventory_item_id: str) -> dict | None:
    data = await graphql_data(
        shop=shop,
        query=GET_INVENTORY_LEVELS,
        variables={"inventoryItemId": inventory_item_id},
    )
    return data.get("inventoryItem")


async def get_location_map(source_locations: list[dict], target_locations: list[dict]) -> dict[str, str]:
    return match_locations(source_locations, target_locations)


async def activate_inventory_at_location(
    shop: str,
    inventory_item_id: str,
    location_id: str,
    available: int | None = None,
) -> dict:
    data = await graphql_data(
        shop=shop,
        query=ACTIVATE_INVENTORY_AT_LOCATION,
        variables={
            "inventoryItemId": inventory_item_id,
            "locationId": location_id,
            "available": available,
        },
    )

    result = data.get("inventoryActivate") or {}
    return {
        "inventory_level": result.get("inventoryLevel"),
        "errors": result.get("userErrors", []),
    }


async def set_inventory_quantities(
    shop: str,
    name: str,
    reason: str,
    quantities: list[dict],
    reference_document_uri: str | None = None,
    ignore_compare_quantity: bool = True,
) -> dict:
    input_payload = {
        "name": name,
        "reason": reason,
        "quantities": quantities,
        "ignoreCompareQuantity": ignore_compare_quantity,
    }

    if reference_document_uri:
        input_payload["referenceDocumentUri"] = reference_document_uri

    data = await graphql_data(
        shop=shop,
        query=SET_INVENTORY_QUANTITIES,
        variables={"input": input_payload},
    )

    result = data.get("inventorySetQuantities") or {}
    return {
        "adjustment_group": result.get("inventoryAdjustmentGroup"),
        "errors": result.get("userErrors", []),
    }


async def update_inventory_item_flags(
    shop: str,
    inventory_item_id: str,
    tracked: bool | None = None,
    requires_shipping: bool | None = None,
) -> dict:
    input_payload = {"id": inventory_item_id}

    if tracked is not None:
        input_payload["tracked"] = tracked

    if requires_shipping is not None:
        input_payload["requiresShipping"] = requires_shipping

    data = await graphql_data(
        shop=shop,
        query=SET_TRACKED_AND_SHIPPING,
        variables={"input": input_payload},
    )

    result = data.get("inventoryItemUpdate") or {}
    return {
        "inventory_item": result.get("inventoryItem"),
        "errors": result.get("userErrors", []),
    }


def extract_available_quantity(level_node: dict) -> int:
    quantities = level_node.get("quantities") or []
    for quantity in quantities:
        if quantity.get("name") == "available":
            return int(quantity.get("quantity") or 0)
    return 0


def flatten_inventory_levels(inventory_item: dict | None) -> list[dict]:
    if not inventory_item:
        return []

    root = inventory_item.get("inventoryLevels", {})
    edges = root.get("edges", [])

    results = []
    for edge in edges:
        node = edge.get("node") or {}
        location = node.get("location") or {}

        results.append(
            {
                "inventory_level_id": node.get("id"),
                "location_id": location.get("id"),
                "location_name": location.get("name"),
                "available": extract_available_quantity(node),
            }
        )

    return results
