import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth.token_manager import exchange_code_for_token
from app.config import APP_URL, SHOPIFY_CLIENT_ID
from app.database import add_store, get_store_by_domain, log_token_event, update_store_tokens

router = APIRouter(prefix="/auth", tags=["auth"])

SCOPES = (
    "read_products,write_products,"
    "read_customers,write_customers,"
    "read_orders,write_orders,"
    "read_inventory,write_inventory,"
    "read_locations,write_locations,"
    "read_fulfillments,"
    "read_metaobjects,write_metaobjects,"
    "read_metaobject_definitions,write_metaobject_definitions,"
    "read_publications,write_publications"
)

state_store = {}


@router.get("/login")
async def login(request: Request):
    shop = request.query_params.get("shop")
    embedded = request.query_params.get("embedded") == "1"

    if not shop:
        raise HTTPException(status_code=400, detail="Missing shop parameter")

    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"

    state = secrets.token_urlsafe(16)
    state_store[state] = shop

    redirect_uri = f"{APP_URL}/auth/callback"
    params = {
        "client_id": SHOPIFY_CLIENT_ID,
        "scope": SCOPES,
        "redirect_uri": redirect_uri,
        "state": state,
        "access_mode": "offline",
    }
    auth_url = f"[{shop}](https://{shop}/admin/oauth/authorize)" + urlencode(params)

    if embedded:
        return HTMLResponse(
            f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Authorization Required - Nexforge</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    text-align: center;
                    padding: 60px 20px;
                    background: #f6f6f7;
                    margin: 0;
                }}
                .card {{
                    background: white;
                    max-width: 480px;
                    margin: 0 auto;
                    padding: 40px 32px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                }}
                h2 {{ color: #202223; margin: 0 0 12px 0; font-size: 20px; }}
                p {{ color: #5c5f62; line-height: 1.5; margin: 0 0 28px 0; font-size: 15px; }}
                .btn {{
                    display: inline-block;
                    padding: 14px 28px;
                    background: #008060;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 15px;
                }}
                .btn:hover {{ background: #006e52; }}
                .note {{
                    margin-top: 24px;
                    font-size: 13px;
                    color: #8c9196;
                }}
                .note a {{ color: #5c5f62; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Authorize Nexforge</h2>
                <p>Click below to grant this app access to your store.</p>
                <a href="{auth_url}" target="_top" class="btn">Authorize with Shopify</a>
                <p class="note">
                    If the button doesn't work, <a href="{auth_url}" target="_blank">open in a new tab</a>.
                </p>
            </div>
        </body>
        </html>
        """
        )

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    shop = request.query_params.get("shop")

    if not code or not state or not shop:
        raise HTTPException(status_code=400, detail="Missing parameters")

    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"

    expected_shop = state_store.pop(state, None)
    if expected_shop != shop:
        raise HTTPException(status_code=400, detail="Invalid state")

    access_token, refresh_token, granted_scopes = await exchange_code_for_token(shop, code)
    if not access_token:
        raise HTTPException(status_code=500, detail="Failed to get access token")

    if not granted_scopes:
        granted_scopes = SCOPES

    existing = get_store_by_domain(shop)

    if existing:
        old_access = existing.get("access_token")
        old_refresh = existing.get("refresh_token")
        old_scopes = existing.get("scopes") or ""

        old_set = {s.strip() for s in old_scopes.split(",") if s.strip()}
        new_set = {s.strip() for s in granted_scopes.split(",") if s.strip()}
        scope_changed = old_set != new_set

        if scope_changed:
            added = new_set - old_set
            removed = old_set - new_set
            print(f"🔔 Scope change detected for {shop}:")
            if added:
                print(f"   ➕ Added: {', '.join(sorted(added))}")
            if removed:
                print(f"   ➖ Removed: {', '.join(sorted(removed))}")

        update_store_tokens(shop, access_token, refresh_token, scopes=granted_scopes)

        event_type = "scope_update" if scope_changed else "oauth_reconnect"
        log_token_event(
            shop,
            event_type,
            old_access=old_access,
            new_access=access_token,
            old_refresh=old_refresh,
            new_refresh=refresh_token,
            old_scopes=old_scopes,
            new_scopes=granted_scopes,
        )

        action_text = "reconnected" if not scope_changed else "reconnected with updated scopes"
        scopes_html = f"<p><strong>Scopes:</strong> {granted_scopes}</p>" if scope_changed else ""

        return HTMLResponse(
            f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Nexforge - {action_text.title()}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    text-align: center;
                    padding: 60px 20px;
                    background: #f6f6f7;
                    margin: 0;
                }}
                .card {{
                    background: white;
                    max-width: 560px;
                    margin: 0 auto;
                    padding: 48px 32px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                }}
                h2 {{ color: #202223; margin: 0 0 12px 0; font-size: 20px; }}
                p {{ color: #5c5f62; line-height: 1.5; margin: 0 0 24px 0; font-size: 15px; }}
                .status {{ color: #008060; font-weight: 600; }}
                .btn {{
                    display: inline-block;
                    padding: 14px 28px;
                    background: #008060;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 15px;
                }}
                .btn:hover {{ background: #006e52; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>✅ Nexforge Catalog Guardian</h2>
                <p class="status">Successfully {action_text}!</p>
                <p>Store: <strong>{shop}</strong></p>
                {scopes_html}
                <a href="{APP_URL}/" class="btn">Back to App</a>
            </div>
        </body>
        </html>
        """
        )

    add_store(
        domain=shop,
        access_token=access_token,
        refresh_token=refresh_token,
        scopes=granted_scopes,
        webhook_secret=None,
        default_location_id=None,
    )
    log_token_event(
        shop,
        "oauth_exchange",
        new_access=access_token,
        new_refresh=refresh_token,
        new_scopes=granted_scopes,
    )

    return HTMLResponse(
        f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Nexforge - Installed</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                text-align: center;
                padding: 60px 20px;
                background: #f6f6f7;
                margin: 0;
            }}
            .card {{
                background: white;
                max-width: 560px;
                margin: 0 auto;
                padding: 48px 32px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }}
            h2 {{ color: #202223; margin: 0 0 12px 0; font-size: 20px; }}
            p {{ color: #5c5f62; line-height: 1.5; margin: 0 0 24px 0; font-size: 15px; }}
            .status {{ color: #008060; font-weight: 600; }}
            .btn {{
                display: inline-block;
                padding: 14px 28px;
                background: #008060;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-weight: 600;
                font-size: 15px;
            }}
            .btn:hover {{ background: #006e52; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>✅ Nexforge Catalog Guardian</h2>
            <p class="status">Successfully installed!</p>
            <p>Store: <strong>{shop}</strong></p>
            <a href="{APP_URL}/" class="btn">Open App</a>
        </div>
    </body>
    </html>
    """
    )
