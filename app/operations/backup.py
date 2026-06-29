from app.database import create_backup_record, update_backup_status
from app.services.collection_service import get_collections
from app.services.inventory_service import get_locations, get_inventory_levels, flatten_inventory_levels
from app.services.metaobject_service import get_metaobject_definitions, get_metaobject
from app.services.product_service import get_products
from app.storage.backup_store import write_json
from app.shopify.graphql import graphql_data
from app.shopify.queries.metafields import GET_METAFIELD_DEFINITIONS
from app.shopify.queries.publications import GET_PUBLICATIONS
from app.domain.metafields.ref_rewriter import extract_metaobject_gids


async def _get_metafield_definitions_for_owner(shop: str, owner_type: str) -> list[dict]:
    definitions = []
    cursor = None

    while True:
        data = await graphql_data(
            shop=shop,
            query=GET_METAFIELD_DEFINITIONS,
            variables={
                "ownerType": owner_type,
                "cursor": cursor,
            },
        )

        root = data.get("metafieldDefinitions", {})
        edges = root.get("edges", [])

        for edge in edges:
            node = edge.get("node") or {}
            if node.get("id"):
                definitions.append(node)

        page_info = root.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break

        cursor = page_info.get("endCursor")

    return definitions


async def _get_all_metafield_definitions(shop: str) -> dict[str, list[dict]]:
    owner_types = [
        "PRODUCT",
        "PRODUCTVARIANT",
        "COLLECTION",
    ]

    result = {}
    for owner_type in owner_types:
        result[owner_type] = await _get_metafield_definitions_for_owner(shop, owner_type)

    return result


async def _get_publications(shop: str) -> list[dict]:
    publications = []
    cursor = None

    while True:
        data = await graphql_data(
            shop=shop,
            query=GET_PUBLICATIONS,
            variables={"cursor": cursor},
        )

        root = data.get("publications", {})
        edges = root.get("edges", [])

        for edge in edges:
            node = edge.get("node") or {}
            if node.get("id"):
                publications.append(node)

        page_info = root.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break

        cursor = page_info.get("endCursor")

    return publications


async def _fetch_inventory_levels(shop: str, products: list[dict]) -> dict:
    """
    Fetch inventory levels for all variants in the product list.
    Returns a dict: inventory_item_id -> list of {location_id, available}
    """
    levels_by_inv_item = {}
    for product in products:
        for variant in product.get("variants", []):
            inv_item = variant.get("inventoryItem", {})
            inv_id = inv_item.get("id")
            if not inv_id:
                continue
            # Fetch via service
            item_data = await get_inventory_levels(shop, inv_id)
            if item_data:
                levels = flatten_inventory_levels(item_data)
                levels_by_inv_item[inv_id] = [
                    {"location_id": l["location_id"], "available": l["available"]}
                    for l in levels
                ]
    return levels_by_inv_item


def _extract_metaobject_gids_from_metafields(metafields: list[dict]) -> set[str]:
    """Extract metaobject GIDs from a list of metafields."""
    gids = set()
    for mf in metafields:
        mf_type = mf.get("type")
        value = mf.get("value")
        if value and mf_type in ("metaobject_reference", "list.metaobject_reference"):
            gids.update(extract_metaobject_gids(value, mf_type))
    return gids


async def _fetch_metaobject_entries(shop: str, products: list[dict], collections: list[dict]) -> dict:
    """
    Scan products and collections for metaobject references,
    fetch the referenced entries, and return a dict of entries keyed by GID.
    """
    # 1. Collect all referenced GIDs
    refs = set()
    for product in products:
        # Product metafields
        refs.update(_extract_metaobject_gids_from_metafields(product.get("metafields", [])))
        # Variant metafields
        for variant in product.get("variants", []):
            refs.update(_extract_metaobject_gids_from_metafields(variant.get("metafields", [])))
    for collection in collections:
        refs.update(_extract_metaobject_gids_from_metafields(collection.get("metafields", [])))

    if not refs:
        return {}

    # 2. Fetch each metaobject entry
    entries = {}
    for gid in refs:
        try:
            entry = await get_metaobject(shop, gid)
            if entry:
                entries[gid] = entry
        except Exception as e:
            print(f"⚠️ Could not fetch metaobject {gid}: {e}")

    return entries


async def run_backup(store_id: int, shop: str, backup_type: str = "full") -> int:
    backup_id = create_backup_record(store_id=store_id, backup_type=backup_type)

    try:
        update_backup_status(backup_id, "running")

        products = await get_products(shop)
        collections = await get_collections(shop)
        locations = await get_locations(shop)
        metafield_definitions = await _get_all_metafield_definitions(shop)
        metaobject_definitions = await get_metaobject_definitions(shop)
        publications = await _get_publications(shop)
        inventory_levels = await _fetch_inventory_levels(shop, products)
        metaobject_entries = await _fetch_metaobject_entries(shop, products, collections)

        write_json("products", backup_id, products)
        write_json("collections", backup_id, collections)
        write_json("locations", backup_id, locations)
        write_json("metafield_definitions", backup_id, metafield_definitions)
        write_json("metaobject_definitions", backup_id, metaobject_definitions)
        write_json("publications", backup_id, publications)
        write_json("inventory_levels", backup_id, inventory_levels)
        write_json("metaobject_entries", backup_id, metaobject_entries)

        manifest = {
            "backup_id": backup_id,
            "store_id": store_id,
            "shop": shop,
            "backup_type": backup_type,
            "files": [
                f"products_{backup_id}.json",
                f"collections_{backup_id}.json",
                f"locations_{backup_id}.json",
                f"metafield_definitions_{backup_id}.json",
                f"metaobject_definitions_{backup_id}.json",
                f"publications_{backup_id}.json",
                f"inventory_levels_{backup_id}.json",
                f"metaobject_entries_{backup_id}.json",
            ],
        }
        write_json("manifest", backup_id, manifest)

        update_backup_status(backup_id, "completed")
        return backup_id

    except Exception as exc:
        update_backup_status(backup_id, "failed", error_message=str(exc))
        raise