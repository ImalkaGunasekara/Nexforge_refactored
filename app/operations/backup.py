from app.database import create_backup_record, update_backup_status
from app.services.collection_service import get_collections
from app.services.inventory_service import get_locations
from app.services.metaobject_service import get_metaobject_definitions
from app.services.product_service import get_products
from app.storage.backup_store import write_json
from app.shopify.graphql import graphql_data
from app.shopify.queries.metafields import GET_METAFIELD_DEFINITIONS
from app.shopify.queries.publications import GET_PUBLICATIONS


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

        write_json("products", backup_id, products)
        write_json("collections", backup_id, collections)
        write_json("locations", backup_id, locations)
        write_json("metafield_definitions", backup_id, metafield_definitions)
        write_json("metaobject_definitions", backup_id, metaobject_definitions)
        write_json("publications", backup_id, publications)

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
            ],
        }
        write_json("manifest", backup_id, manifest)

        update_backup_status(backup_id, "completed")
        return backup_id

    except Exception as exc:
        update_backup_status(backup_id, "failed", error_message=str(exc))
        raise
