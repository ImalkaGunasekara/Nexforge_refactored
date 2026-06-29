from app.domain.products.builder import (
    build_product_input_from_backup,
    build_variant_rest_input,
)
from app.domain.products.matcher import find_matching_variant
from app.shopify.graphql import graphql_data
from app.shopify.queries.products import (
    GET_PRODUCT_BY_ID,
    GET_PRODUCTS_PAGE,
)
from app.shopify.rest import rest_delete, rest_get, rest_post, rest_put


def _flatten_product_node(node: dict) -> dict:
    variants = []
    variants_root = node.get("variants", {})
    for edge in variants_root.get("edges", []):
        variant_node = edge.get("node", {})
        if variant_node.get("id"):
            variants.append(variant_node)

    images = []
    images_root = node.get("images", {})
    for edge in images_root.get("edges", []):
        img_node = edge.get("node", {})
        if img_node.get("id"):
            images.append(img_node)

    metafields = []
    mf_root = node.get("metafields", {})
    for edge in mf_root.get("edges", []):
        mf_node = edge.get("node", {})
        if mf_node.get("id"):
            metafields.append(mf_node)

    flat = dict(node)
    flat["variants"] = variants
    flat["images"] = images
    flat["metafields"] = metafields
    return flat


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
                products.append(_flatten_product_node(node))

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
    node = data.get("product")
    if node:
        return _flatten_product_node(node)
    return None


async def get_product_map_by_handle(shop: str) -> dict[str, dict]:
    products = await get_products(shop)
    result = {}

    for product in products:
        handle = (product.get("handle") or "").strip()
        if handle and handle not in result:
            result[handle] = product

    return result


async def create_product(shop: str, product_input: dict) -> dict:
    result = await rest_post(shop, "products.json", json_data={"product": product_input})
    return {"product": result.get("product"), "errors": []}


async def update_product(shop: str, product_input: dict) -> dict:
    product_id = product_input.get("id")
    if not product_id:
        return {"product": None, "errors": [{"message": "Product ID required for update"}]}

    # Only keep fields that are accepted by the REST API on update
    allowed_fields = {
        "title", "body_html", "vendor", "product_type", "tags",
        "status", "published", "published_scope", "template_suffix"
    }
    update_data = {k: v for k, v in product_input.items() if k in allowed_fields}

    result = await rest_put(shop, f"products/{product_id}.json", json_data={"product": update_data})
    return {"product": result.get("product"), "errors": []}


async def delete_product(shop: str, product_id: str) -> dict:
    await rest_delete(shop, f"products/{product_id}.json")
    return {"deleted_product_id": product_id, "errors": []}


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
    return product.get("variants", [])


def build_variant_bulk_inputs(source_variants: list[dict], target_product: dict | None = None) -> list[dict]:
    target_variants = extract_variants(target_product)
    payload = []

    for source_variant in source_variants:
        variant_input = build_variant_rest_input(source_variant)
        matched_target = find_matching_variant(source_variant, target_variants)
        if matched_target and matched_target.get("id"):
            variant_input["id"] = matched_target["id"]
        payload.append(variant_input)

    return payload


async def bulk_upsert_variants(shop: str, product_id: str, source_variants: list[dict], target_product: dict | None = None) -> dict:
    variants_input = build_variant_bulk_inputs(source_variants, target_product)
    if not variants_input:
        return {"product": None, "errors": []}

    result = await rest_post(
        shop,
        f"products/{product_id}/variants/bulk_update.json",
        json_data={"variants": variants_input},
    )
    return {"product": result.get("product"), "errors": result.get("errors", [])}