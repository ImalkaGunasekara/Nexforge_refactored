from app.shopify.client import (
    build_admin_rest_url,
    build_rest_headers,
    shopify_request_with_retry,
)


async def shopify_rest_request(
    shop: str,
    method: str,
    path: str,
    json_data: dict | None = None,
    params: dict | None = None,
    timeout: float = 60.0,
):
    url = build_admin_rest_url(shop, path)
    headers = await build_rest_headers(shop)

    response = await shopify_request_with_retry(
        method=method,
        url=url,
        headers=headers,
        json_data=json_data,
        params=params,
        timeout=timeout,
    )

    if response.status_code >= 400:
        raise Exception(f"Shopify REST error {response.status_code}: {response.text}")

    if not response.text:
        return {}

    return response.json()


async def rest_get(shop: str, path: str, params: dict | None = None, timeout: float = 60.0):
    return await shopify_rest_request(
        shop=shop,
        method="GET",
        path=path,
        params=params,
        timeout=timeout,
    )


async def rest_post(shop: str, path: str, json_data: dict | None = None, timeout: float = 60.0):
    return await shopify_rest_request(
        shop=shop,
        method="POST",
        path=path,
        json_data=json_data,
        timeout=timeout,
    )


async def rest_put(shop: str, path: str, json_data: dict | None = None, timeout: float = 60.0):
    return await shopify_rest_request(
        shop=shop,
        method="PUT",
        path=path,
        json_data=json_data,
        timeout=timeout,
    )


async def rest_delete(shop: str, path: str, timeout: float = 60.0):
    return await shopify_rest_request(
        shop=shop,
        method="DELETE",
        path=path,
        timeout=timeout,
    )
