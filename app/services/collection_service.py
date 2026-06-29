from app.services.publication_service import apply_publications
from app.shopify.graphql import graphql_data
from app.shopify.queries.collections import (
    CREATE_COLLECTION,
    DELETE_COLLECTION,
    GET_COLLECTION_BY_ID,
    GET_COLLECTIONS_PAGE,
    UPDATE_COLLECTION,
    UPDATE_COLLECTION_IMAGE,
)


def _flatten_collection_node(node: dict) -> dict:
    """Convert raw GraphQL collection node into a flat dict with lists."""
    # Flatten metafields
    metafields = []
    mf_root = node.get("metafields", {})
    for edge in mf_root.get("edges", []):
        mf_node = edge.get("node", {})
        if mf_node.get("id"):
            metafields.append(mf_node)

    flat = dict(node)
    flat["metafields"] = metafields
    return flat


async def get_collections(shop: str) -> list[dict]:
    collections = []
    cursor = None

    while True:
        data = await graphql_data(
            shop=shop,
            query=GET_COLLECTIONS_PAGE,
            variables={"cursor": cursor},
        )

        root = data.get("collections", {})
        edges = root.get("edges", [])

        for edge in edges:
            node = edge.get("node") or {}
            if node.get("id"):
                collections.append(_flatten_collection_node(node))

        page_info = root.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break

        cursor = page_info.get("endCursor")

    return collections


async def get_collection(shop: str, collection_id: str) -> dict | None:
    data = await graphql_data(
        shop=shop,
        query=GET_COLLECTION_BY_ID,
        variables={"id": collection_id},
    )
    node = data.get("collection")
    if node:
        return _flatten_collection_node(node)
    return None


async def create_collection(shop: str, collection_input: dict) -> dict:
    data = await graphql_data(
        shop=shop,
        query=CREATE_COLLECTION,
        variables={"input": collection_input},
    )

    result = data.get("collectionCreate") or {}
    return {
        "collection": result.get("collection"),
        "errors": result.get("userErrors", []),
    }


async def update_collection(shop: str, collection_input: dict) -> dict:
    data = await graphql_data(
        shop=shop,
        query=UPDATE_COLLECTION,
        variables={"input": collection_input},
    )

    result = data.get("collectionUpdate") or {}
    return {
        "collection": result.get("collection"),
        "errors": result.get("userErrors", []),
    }


async def delete_collection(shop: str, collection_id: str) -> dict:
    data = await graphql_data(
        shop=shop,
        query=DELETE_COLLECTION,
        variables={"input": {"id": collection_id}},
    )

    result = data.get("collectionDelete") or {}
    return {
        "deleted_collection_id": result.get("deletedCollectionId"),
        "errors": result.get("userErrors", []),
    }


async def set_collection_image(shop: str, collection_id: str, image_src: str | None, alt_text: str | None = None) -> dict:
    collection_input = {"id": collection_id}

    if image_src:
        collection_input["image"] = {
            "src": image_src,
            "altText": alt_text,
        }
    else:
        collection_input["image"] = None

    data = await graphql_data(
        shop=shop,
        query=UPDATE_COLLECTION_IMAGE,
        variables={"input": collection_input},
    )

    result = data.get("collectionUpdate") or {}
    return {
        "collection": result.get("collection"),
        "errors": result.get("userErrors", []),
    }


async def update_collection_publications(shop: str, collection_id: str, publication_ids: list[str]) -> dict:
    return await apply_publications(
        shop=shop,
        owner_id=collection_id,
        target_publication_ids=publication_ids,
    )