import httpx

from app.auth.token_manager import refresh_access_token
from app.config import SHOPIFY_API_VERSION
from app.database import get_store_by_domain, log_token_event, update_store_tokens


def build_admin_rest_url(shop: str, path: str) -> str:
    clean_path = path.lstrip("/")
    return f"[{shop}](https://{shop}/admin/api/{SHOPIFY_API_VERSION}/{clean_path})"


def build_admin_graphql_url(shop: str) -> str:
    return f"[{shop}](https://{shop}/admin/api/{SHOPIFY_API_VERSION}/graphql.json)"


async def get_valid_access_token(shop: str) -> str:
    store = get_store_by_domain(shop)
    if not store:
        raise Exception(f"Store not found: {shop}")

    access_token = store.get("access_token")
    refresh_token = store.get("refresh_token")
    scopes = store.get("scopes") or ""

    if access_token:
        return access_token

    if not refresh_token:
        raise Exception(f"No access token or refresh token available for {shop}")

    new_access_token, new_refresh_token, new_scopes = await refresh_access_token(shop, refresh_token)
    if not new_access_token:
        raise Exception(f"Failed to refresh access token for {shop}")

    update_store_tokens(
        shop,
        new_access_token,
        new_refresh_token,
        scopes=new_scopes or scopes,
    )

    log_token_event(
        shop,
        "token_refresh",
        old_access=access_token,
        new_access=new_access_token,
        old_refresh=refresh_token,
        new_refresh=new_refresh_token,
        old_scopes=scopes,
        new_scopes=new_scopes or scopes,
    )

    return new_access_token


async def build_shopify_headers(shop: str) -> dict:
    access_token = await get_valid_access_token(shop)
    return {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def build_graphql_headers(shop: str) -> dict:
    return await build_shopify_headers(shop)


async def build_rest_headers(shop: str) -> dict:
    return await build_shopify_headers(shop)


async def shopify_request_with_retry(
    method: str,
    url: str,
    headers: dict,
    json_data: dict | None = None,
    params: dict | None = None,
    timeout: float = 60.0,
):
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            params=params,
        )

    return response
