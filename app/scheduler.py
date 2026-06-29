import asyncio
from apscheduler.schedulers.background import BackgroundScheduler

from app.auth.token_manager import refresh_access_token
from app.database import get_stores, update_store_tokens, clear_store_tokens, log_token_event


async def _refresh_all_tokens():
    stores = get_stores()
    for store in stores:
        domain = store["shopify_domain"]
        refresh_token = store.get("refresh_token")
        if not refresh_token:
            continue

        new_access, new_refresh, new_scopes = await refresh_access_token(domain, refresh_token)
        if new_access and new_refresh:
            update_store_tokens(domain, new_access, new_refresh, scopes=new_scopes)
            print(f"✅ Refreshed tokens for {domain}")
        else:
            # Refresh failed – clear tokens so user re-authenticates
            clear_store_tokens(domain)
            log_token_event(
                domain,
                "tokens_cleared_scheduler",
                error_body="Proactive refresh failed, tokens wiped"
            )
            print(f"🚫 Cleared dead tokens for {domain}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: asyncio.run(_refresh_all_tokens()),
        'interval',
        days=1,
        id='token_refresh'
    )
    scheduler.start()
    print("🕒 Token refresh scheduler started (runs daily)")