from app.shopify.graphql import graphql_data
from app.shopify.queries.metaobjects import (
    CREATE_METAOBJECT,
    CREATE_METAOBJECT_DEFINITION,
    DELETE_METAOBJECT,
    GET_METAOBJECT_BY_ID,
    GET_METAOBJECT_DEFINITIONS,
    GET_METAOBJECTS_BY_TYPE,
    UPDATE_METAOBJECT,
)


async def get_metaobject_definitions(shop: str) -> list[dict]:
    definitions = []
    cursor = None

    while True:
        data = await graphql_data(
            shop=shop,
            query=GET_METAOBJECT_DEFINITIONS,
            variables={"cursor": cursor},
        )

        root = data.get("metaobjectDefinitions", {})
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


async def get_metaobject_definition_map(shop: str) -> dict[str, dict]:
    definitions = await get_metaobject_definitions(shop)
    result = {}

    for definition in definitions:
        type_name = (definition.get("type") or "").strip()
        if type_name and type_name not in result:
            result[type_name] = definition

    return result


async def get_metaobject(shop: str, metaobject_id: str) -> dict | None:
    data = await graphql_data(
        shop=shop,
        query=GET_METAOBJECT_BY_ID,
        variables={"id": metaobject_id},
    )
    return data.get("metaobject")


async def get_metaobjects_by_type(shop: str, type_name: str) -> list[dict]:
    metaobjects = []
    cursor = None

    while True:
        data = await graphql_data(
            shop=shop,
            query=GET_METAOBJECTS_BY_TYPE,
            variables={
                "type": type_name,
                "cursor": cursor,
            },
        )

        root = data.get("metaobjects", {})
        edges = root.get("edges", [])

        for edge in edges:
            node = edge.get("node") or {}
            if node.get("id"):
                metaobjects.append(node)

        page_info = root.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break

        cursor = page_info.get("endCursor")

    return metaobjects


async def get_metaobject_map_by_handle(shop: str, type_name: str) -> dict[str, dict]:
    metaobjects = await get_metaobjects_by_type(shop, type_name)
    result = {}

    for metaobject in metaobjects:
        handle = (metaobject.get("handle") or "").strip()
        if handle and handle not in result:
            result[handle] = metaobject

    return result


async def create_metaobject_definition(shop: str, definition_input: dict) -> dict:
    data = await graphql_data(
        shop=shop,
        query=CREATE_METAOBJECT_DEFINITION,
        variables={"definition": definition_input},
    )

    result = data.get("metaobjectDefinitionCreate") or {}
    return {
        "definition": result.get("metaobjectDefinition"),
        "errors": result.get("userErrors", []),
    }


async def ensure_metaobject_definition(shop: str, definition_input: dict) -> dict:
    type_name = (definition_input.get("type") or "").strip()
    if not type_name:
        return {"definition": None, "errors": [{"message": "Missing metaobject definition type"}]}

    definition_map = await get_metaobject_definition_map(shop)
    existing = definition_map.get(type_name)

    if existing:
        return {"definition": existing, "errors": []}

    return await create_metaobject_definition(shop, definition_input)


async def create_metaobject(shop: str, metaobject_input: dict) -> dict:
    data = await graphql_data(
        shop=shop,
        query=CREATE_METAOBJECT,
        variables={"metaobject": metaobject_input},
    )

    result = data.get("metaobjectCreate") or {}
    return {
        "metaobject": result.get("metaobject"),
        "errors": result.get("userErrors", []),
    }


async def update_metaobject(shop: str, metaobject_id: str, metaobject_input: dict) -> dict:
    data = await graphql_data(
        shop=shop,
        query=UPDATE_METAOBJECT,
        variables={
            "id": metaobject_id,
            "metaobject": metaobject_input,
        },
    )

    result = data.get("metaobjectUpdate") or {}
    return {
        "metaobject": result.get("metaobject"),
        "errors": result.get("userErrors", []),
    }


async def delete_metaobject(shop: str, metaobject_id: str) -> dict:
    data = await graphql_data(
        shop=shop,
        query=DELETE_METAOBJECT,
        variables={"id": metaobject_id},
    )

    result = data.get("metaobjectDelete") or {}
    return {
        "deleted_id": result.get("deletedId"),
        "errors": result.get("userErrors", []),
    }
