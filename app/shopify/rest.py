import json
from app.shopify.client import (
    build_admin_rest_url,
    build_rest_headers,
    force_refresh_access_token,
    shopify_request_with_retry,
)


async def shopify_rest_request(
    shop: str,
    method: str,
    path: str,
    json_data: dict | None = None,
    params: dict | None = None,
    timeout: float = 60.0,
    _retry: bool = True,
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

    if response.status_code == 401 and _retry:
        print(f"🔄 REST token expired for {shop}, refreshing...")
        new_token = await force_refresh_access_token(shop)
        headers["X-Shopify-Access-Token"] = new_token
        return await shopify_rest_request(
            shop=shop,
            method=method,
            path=path,
            json_data=json_data,
            params=params,
            timeout=timeout,
            _retry=False,
        )

    if response.status_code >= 400:
        error_body = response.text
        try:
            error_json = response.json()
            error_body = error_json.get("errors", error_body)
        except:
            pass
        # Debug: print payload for 406
        if response.status_code == 406 and json_data:
            print(f"🔍 406 Error - Payload sent:\n{json.dumps(json_data, indent=2)}")
        raise Exception(f"Shopify REST error {response.status_code}: {error_body}")

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