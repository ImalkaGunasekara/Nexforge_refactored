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
                collections.append(node)

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
    return data.get("collection")


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
