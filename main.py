from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse

from app.auth.oauth import router as auth_router
from app.database import init_db, get_store_by_domain, create_backup_record, create_restore_job
from app.operations.backup import run_backup
from app.operations.restore import run_restore
from app.operations.clone import run_clone
from app.scheduler import start_scheduler
from app.config import APP_URL


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    start_scheduler()
    yield
    # Shutdown (if needed, e.g., scheduler.shutdown())


app = FastAPI(
    title="Nexforge Catalog Guardian",
    lifespan=lifespan,
)

# ─── Auth routes ────────────────────────────────────────
app.include_router(auth_router)

# ─── Root / health ──────────────────────────────────────
@app.get("/")
async def root(request: Request):
    shop = request.query_params.get("shop")
    if shop:
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"
        store = get_store_by_domain(shop)
        if store and store.get("access_token"):
            return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Nexforge Catalog Guardian</title>
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
                    <p class="status">Connected to <strong>{shop}</strong></p>
                    <a href="{APP_URL}/auth/login?shop={shop}" target="_top" class="btn">Reconnect</a>
                </div>
            </body>
            </html>
            """)
        return RedirectResponse(url=f"{APP_URL}/auth/login?shop={shop}")
    return {"status": "ok", "message": "Nexforge Catalog Guardian API"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# ─── API endpoints ──────────────────────────────────────
@app.post("/api/backup")
async def start_backup(request: Request, background_tasks: BackgroundTasks):
    shop = request.headers.get("X-Shopify-Shop-Domain")
    if not shop:
        raise HTTPException(400, detail="Missing X-Shopify-Shop-Domain header")

    store = get_store_by_domain(shop)
    if not store:
        raise HTTPException(401, detail="Store not registered")
    if not store.get("access_token"):
        raise HTTPException(401, detail="Store token expired. Re-authenticate at /auth/login")

    backup_id = create_backup_record(store["id"], "full")
    background_tasks.add_task(run_backup, store["id"], shop, "full")
    return {"backup_id": backup_id, "message": "Backup started"}


@app.post("/api/restore")
async def start_restore(
    request: Request,
    background_tasks: BackgroundTasks,
    backup_id: int,
    selected_product_handles: list[str] | None = None,
    selected_collection_handles: list[str] | None = None,
    locked_locations: list[str] | None = None,
):
    shop = request.headers.get("X-Shopify-Shop-Domain")
    if not shop:
        raise HTTPException(400, detail="Missing X-Shopify-Shop-Domain header")

    store = get_store_by_domain(shop)
    if not store:
        raise HTTPException(401, detail="Store not registered")
    if not store.get("access_token"):
        raise HTTPException(401, detail="Store token expired. Re-authenticate at /auth/login")

    restore_id = create_restore_job(store["id"], backup_id)
    background_tasks.add_task(
        run_restore,
        store["id"],
        shop,
        backup_id,
        selected_product_handles,
        selected_collection_handles,
        locked_locations,
    )
    return {"restore_id": restore_id, "message": "Restore started"}


@app.post("/api/clone")
async def start_clone(
    request: Request,
    background_tasks: BackgroundTasks,
    target_domain: str,
    locked_locations: list[str] | None = None,
):
    shop = request.headers.get("X-Shopify-Shop-Domain")
    if not shop:
        raise HTTPException(400, detail="Missing X-Shopify-Shop-Domain header")

    store = get_store_by_domain(shop)
    if not store:
        raise HTTPException(401, detail="Source store not registered")
    if not store.get("access_token"):
        raise HTTPException(401, detail="Source store token expired. Re-authenticate at /auth/login")

    # Check target store exists
    target_store = get_store_by_domain(target_domain)
    if not target_store:
        raise HTTPException(400, detail=f"Target store {target_domain} not registered")
    if not target_store.get("access_token"):
        raise HTTPException(400, detail=f"Target store {target_domain} has no valid token")

    background_tasks.add_task(
        run_clone,
        shop,                # source
        target_domain,       # target
        locked_locations,
    )
    return {"message": f"Clone from {shop} to {target_domain} started"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)