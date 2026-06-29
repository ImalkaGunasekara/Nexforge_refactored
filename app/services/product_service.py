from app.domain.products.builder import (
    build_product_input_from_backup,
    build_variant_input_from_backup,
)
from app.domain.products.matcher import find_matching_variant
from app.shopify.graphql import graphql_data
from app.shopify.queries.products import (
    CREATE_PRODUCT,
    DELETE_PRODUCT,
    GET_PRODUCT_BY_ID,
    GET_PRODUCTS_PAGE,
    SET_PRODUCT_VARIANTS_BULK,
    UPDATE_PRODUCT,
)


async def get_products(shop: str) -> list[dict]:
    products = []
    cursor = None

    while True:
        data = await graphql_data(
            shop=shop,
            query=GET_PRODUCTS_PAGE,
            variables={"cursor": cursor},
        )

        root = data.get("products", {})
        edges = root.get("edges", [])

        for edge in edges:
            node = edge.get("node") or {}
            if node.get("id"):
                products.append(node)

        page_info = root.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break

        cursor = page_info.get("endCursor")

    return products


async def get_product(shop: str, product_id: str) -> dict | None:
    data = await graphql_data(
        shop=shop,
        query=GET_PRODUCT_BY_ID,
        variables={"id": product_id},
    )
    return data.get("product")


async def get_product_map_by_handle(shop: str) -> dict[str, dict]:
    products = await get_products(shop)
    result = {}

    for product in products:
        handle = (product.get("handle") or "").strip()
        if handle and handle not in result:
            result[handle] = product

    return result


async def create_product(shop: str, product_input: dict) -> dict:
    data = await graphql_data(
        shop=shop,
        query=CREATE_PRODUCT,
        variables={"input": product_input},
    )

    result = data.get("productCreate") or {}
    return {
        "product": result.get("product"),
        "errors": result.get("userErrors", []),
    }


async def update_product(shop: str, product_input: dict) -> dict:
    data = await graphql_data(
        shop=shop,
        query=UPDATE_PRODUCT,
        variables={"input": product_input},
    )

    result = data.get("productUpdate") or {}
    return {
        "product": result.get("product"),
        "errors": result.get("userErrors", []),
    }


async def delete_product(shop: str, product_id: str) -> dict:
    data = await graphql_data(
        shop=shop,
        query=DELETE_PRODUCT,
        variables={"input": {"id": product_id}},
    )

    result = data.get("productDelete") or {}
    return {
        "deleted_product_id": result.get("deletedProductId"),
        "errors": result.get("userErrors", []),
    }


async def create_product_from_backup(shop: str, backup_product: dict) -> dict:
    product_input = build_product_input_from_backup(backup_product)
    return await create_product(shop, product_input)


async def update_product_from_backup(shop: str, product_id: str, backup_product: dict) -> dict:
    product_input = build_product_input_from_backup(backup_product)
    product_input["id"] = product_id
    return await update_product(shop, product_input)


def extract_variants(product: dict | None) -> list[dict]:
    if not product:
        return []

    variants_root = product.get("variants", {})
    edges = variants_root.get("edges", [])

    results = []
    for edge in edges:
        node = edge.get("node") or {}
        if node.get("id"):
            results.append(node)

    return results


def build_variant_bulk_inputs(source_variants: list[dict], target_product: dict | None = None) -> list[dict]:
    target_variants = extract_variants(target_product)
    payload = []

    for source_variant in source_variants:
        variant_input = build_variant_input_from_backup(source_variant)
        matched_target = find_matching_variant(source_variant, target_variants)

        if matched_target and matched_target.get("id"):
            variant_input["id"] = matched_target["id"]

        payload.append(variant_input)

    return payload


async def bulk_upsert_variants(shop: str, product_id: str, source_variants: list[dict], target_product: dict | None = None) -> dict:
    variants_input = build_variant_bulk_inputs(
        source_variants=source_variants,
        target_product=target_product,
    )

    if not variants_input:
        return {"product": None, "errors": []}

    data = await graphql_data(
        shop=shop,
        query=SET_PRODUCT_VARIANTS_BULK,
        variables={
            "productId": product_id,
            "variants": variants_input,
        },
    )

    result = data.get("productVariantsBulkUpdate") or {}
    return {
        "product": result.get("product"),
        "errors": result.get("userErrors", []),
    }
