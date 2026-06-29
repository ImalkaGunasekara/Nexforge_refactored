from app.shopify.graphql import graphql_data
from app.shopify.queries.publications import (
    GET_PUBLICATIONS,
    GET_RESOURCE_PUBLICATIONS,
    PUBLISH_RESOURCE,
    UNPUBLISH_RESOURCE,
)


async def get_publications(shop: str) -> list[dict]:
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
                publications.append(
                    {
                        "id": node.get("id"),
                        "name": node.get("name"),
                    }
                )

        page_info = root.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break

        cursor = page_info.get("endCursor")

    return publications


async def get_publication_map(shop: str) -> dict[str, str]:
    publications = await get_publications(shop)
    result = {}

    for publication in publications:
        name = (publication.get("name") or "").strip()
        pub_id = publication.get("id")

        if name and pub_id:
            result[name] = pub_id

    return result


async def get_resource_publications(shop: str, owner_id: str) -> list[dict]:
    data = await graphql_data(
        shop=shop,
        query=GET_RESOURCE_PUBLICATIONS,
        variables={"id": owner_id},
    )

    node = data.get("node") or {}
    root = node.get("resourcePublications", {})
    edges = root.get("edges", [])

    results = []
    for edge in edges:
        pub_node = edge.get("node") or {}
        publication = pub_node.get("publication") or {}

        publication_id = publication.get("id")
        publication_name = publication.get("name")

        if publication_id:
            results.append(
                {
                    "publication_id": publication_id,
                    "publication_name": publication_name,
                    "is_published": pub_node.get("isPublished"),
                    "publish_date": pub_node.get("publishDate"),
                }
            )

    return results


async def get_current_publication_ids(shop: str, owner_id: str) -> list[str]:
    publications = await get_resource_publications(shop, owner_id)
    return [
        item["publication_id"]
        for item in publications
        if item.get("publication_id") and item.get("is_published")
    ]


async def publish_resource(shop: str, owner_id: str, publication_ids: list[str]) -> dict:
    if not publication_ids:
        return {"published": [], "errors": []}

    data = await graphql_data(
        shop=shop,
        query=PUBLISH_RESOURCE,
        variables={
            "id": owner_id,
            "input": [{"publicationId": pub_id} for pub_id in publication_ids],
        },
    )

    result = data.get("publishablePublish") or {}
    return {
        "published": publication_ids,
        "errors": result.get("userErrors", []),
    }


async def unpublish_resource(shop: str, owner_id: str, publication_ids: list[str]) -> dict:
    if not publication_ids:
        return {"unpublished": [], "errors": []}

    data = await graphql_data(
        shop=shop,
        query=UNPUBLISH_RESOURCE,
        variables={
            "id": owner_id,
            "input": [{"publicationId": pub_id} for pub_id in publication_ids],
        },
    )

    result = data.get("publishableUnpublish") or {}
    return {
        "unpublished": publication_ids,
        "errors": result.get("userErrors", []),
    }


async def apply_publications(shop: str, owner_id: str, target_publication_ids: list[str]) -> dict:
    current_ids = set(await get_current_publication_ids(shop, owner_id))
    target_ids = set(target_publication_ids)

    to_publish = sorted(target_ids - current_ids)
    to_unpublish = sorted(current_ids - target_ids)

    publish_result = await publish_resource(shop, owner_id, to_publish)
    unpublish_result = await unpublish_resource(shop, owner_id, to_unpublish)

    return {
        "published": publish_result.get("published", []),
        "unpublished": unpublish_result.get("unpublished", []),
        "publish_errors": publish_result.get("errors", []),
        "unpublish_errors": unpublish_result.get("errors", []),
    }
