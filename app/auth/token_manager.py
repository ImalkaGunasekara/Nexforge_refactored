import httpx

from app.config import SHOPIFY_CLIENT_ID, SHOPIFY_CLIENT_SECRET


async def exchange_code_for_token(shop: str, code: str):
    url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": SHOPIFY_CLIENT_ID,
        "client_secret": SHOPIFY_CLIENT_SECRET,
        "code": code,
        "expiring": 1,   # <-- REQUIRED for expiring offline tokens
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)

    if response.status_code != 200:
        print(f"❌ Token exchange failed for {shop}: {response.status_code} {response.text}")
        return None, None, None

    data = response.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    scopes = data.get("scope") or data.get("scopes")

    return access_token, refresh_token, scopes


async def refresh_access_token(shop: str, refresh_token: str):
    url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": SHOPIFY_CLIENT_ID,
        "client_secret": SHOPIFY_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)

    if response.status_code != 200:
        print(f"❌ Token refresh failed for {shop}: {response.status_code} {response.text}")
        return None, None, None

    data = response.json()
    new_access_token = data.get("access_token")
    new_refresh_token = data.get("refresh_token", refresh_token)
    scopes = data.get("scope") or data.get("scopes")

    return new_access_token, new_refresh_token, scopes