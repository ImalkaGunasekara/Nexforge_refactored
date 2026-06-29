from app.domain.metafields.ref_rewriter import rewrite_metaobject_refs
from app.domain.metafields.type_mapper import metafield_types_match
from app.shopify.graphql import graphql_data
from app.shopify.queries.metafields import (
    CREATE_METAFIELD_DEFINITION,
    DELETE_METAFIELD,
    GET_METAFIELD_DEFINITIONS,
    GET_OWNER_METAFIELDS,
    SET_METAFIELDS,
    UPDATE_METAFIELD_DEFINITION,
)


async def get_metafield_definitions(shop: str, owner_type: str) -> list[dict]:
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


async def get_metafield_definition_map(shop: str, owner_type: str) -> dict[tuple[str, str], dict]:
    definitions = await get_metafield_definitions(shop, owner_type)
    result = {}

    for definition in definitions:
        namespace = (definition.get("namespace") or "").strip()
        key = (definition.get("key") or "").strip()

        if namespace and key:
            result[(namespace, key)] = definition

    return result


async def get_owner_metafields(shop: str, owner_id: str) -> list[dict]:
    data = await graphql_data(
        shop=shop,
        query=GET_OWNER_METAFIELDS,
        variables={"ownerId": owner_id},
    )

    node = data.get("node") or {}
    metafields_root = node.get("metafields", {})
    edges = metafields_root.get("edges", [])

    results = []
    for edge in edges:
        metafield = edge.get("node") or {}
        if metafield.get("id"):
            results.append(metafield)

    return results


async def get_owner_metafield_map(shop: str, owner_id: str) -> dict[tuple[str, str], dict]:
    metafields = await get_owner_metafields(shop, owner_id)
    result = {}

    for metafield in metafields:
        namespace = (metafield.get("namespace") or "").strip()
        key = (metafield.get("key") or "").strip()

        if namespace and key:
            result[(namespace, key)] = metafield

    return result


async def create_metafield_definition(shop: str, definition_input: dict) -> dict:
    data = await graphql_data(
        shop=shop,
        query=CREATE_METAFIELD_DEFINITION,
        variables={"definition": definition_input},
    )

    result = data.get("metafieldDefinitionCreate") or {}
    return {
        "definition": result.get("createdDefinition"),
        "errors": result.get("userErrors", []),
    }


async def update_metafield_definition(shop: str, definition_input: dict) -> dict:
    data = await graphql_data(
        shop=shop,
        query=UPDATE_METAFIELD_DEFINITION,
        variables={"definition": definition_input},
    )

    result = data.get("metafieldDefinitionUpdate") or {}
    return {
        "definition": result.get("updatedDefinition"),
        "errors": result.get("userErrors", []),
    }


async def ensure_metafield_definition(shop: str, owner_type: str, definition_input: dict) -> dict:
    namespace = (definition_input.get("namespace") or "").strip()
    key = (definition_input.get("key") or "").strip()

    if not namespace or not key:
        return {"definition": None, "errors": [{"message": "Missing metafield definition namespace/key"}]}

    definition_map = await get_metafield_definition_map(shop, owner_type)
    existing = definition_map.get((namespace, key))

    if not existing:
        return await create_metafield_definition(shop, definition_input)

    existing_type = ((existing.get("type") or {}).get("name") or "").strip()
    incoming_type = (definition_input.get("type") or "").strip()

    if metafield_types_match(existing_type, incoming_type):
        return {"definition": existing, "errors": []}

    update_input = {
        "id": existing.get("id"),
        "name": definition_input.get("name"),
        "description": definition_input.get("description"),
        "namespace": namespace,
        "key": key,
        "type": incoming_type,
    }

    return await update_metafield_definition(shop, update_input)


def build_metafields_set_input(
    owner_id: str,
    metafields: list[dict],
    entry_id_map: dict[str, str] | None = None,
) -> list[dict]:
    payload = []

    for metafield in metafields:
        namespace = metafield.get("namespace")
        key = metafield.get("key")
        mf_type = metafield.get("type")
        value = metafield.get("value")

        if not namespace or not key or value is None:
            continue

        rewritten_value = rewrite_metaobject_refs(value, mf_type, entry_id_map)

        payload.append(
            {
                "ownerId": owner_id,
                "namespace": namespace,
                "key": key,
                "type": mf_type,
                "value": rewritten_value,
            }
        )

    return payload


async def set_metafields(
    shop: str,
    owner_id: str,
    metafields: list[dict],
    entry_id_map: dict[str, str] | None = None,
) -> dict:
    metafields_input = build_metafields_set_input(
        owner_id=owner_id,
        metafields=metafields,
        entry_id_map=entry_id_map,
    )

    if not metafields_input:
        return {"metafields": [], "errors": []}

    data = await graphql_data(
        shop=shop,
        query=SET_METAFIELDS,
        variables={"metafields": metafields_input},
    )

    result = data.get("metafieldsSet") or {}
    return {
        "metafields": result.get("metafields", []),
        "errors": result.get("userErrors", []),
    }


async def delete_metafield(shop: str, metafield_id: str) -> dict:
    data = await graphql_data(
        shop=shop,
        query=DELETE_METAFIELD,
        variables={"input": {"id": metafield_id}},
    )

    result = data.get("metafieldDelete") or {}
    return {
        "deleted_id": result.get("deletedId"),
        "errors": result.get("userErrors", []),
    }
