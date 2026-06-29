from app.database import add_clone, get_store_by_domain
from app.operations.backup import run_backup
from app.operations.restore import run_restore


async def run_clone(
    source_domain: str,
    target_domain: str,
    locked_locations: list[str] | None = None,
) -> dict:
    """
    Clone a store:
    - Take a full backup of the source store.
    - Restore all products and collections into the target store.
    - Respect inventory location locking.
    """
    # Get source store details
    source_store = get_store_by_domain(source_domain)
    if not source_store:
        raise ValueError(f"Source store not found: {source_domain}")
    if not source_store.get("access_token"):
        raise ValueError(f"Source store has no valid token: {source_domain}")

    # Get target store details (needed for restore)
    target_store = get_store_by_domain(target_domain)
    if not target_store:
        raise ValueError(f"Target store not found: {target_domain}")
    if not target_store.get("access_token"):
        raise ValueError(f"Target store has no valid token: {target_domain}")

    # 1. Backup source
    backup_id = await run_backup(
        store_id=source_store["id"],
        shop=source_domain,
        backup_type="clone_source",
    )

    # 2. Restore into target (all products and collections)
    restore_result = await run_restore(
        store_id=target_store["id"],
        shop=target_domain,
        backup_id=backup_id,
        selected_product_handles=None,      # all products
        selected_collection_handles=None,   # all collections
        locked_locations=locked_locations,
    )

    # 3. Record clone job
    add_clone(
        source_store_id=source_store["id"],
        target_domain=target_domain,
        target_token=target_store.get("access_token"),
    )

    return {
        "source_domain": source_domain,
        "target_domain": target_domain,
        "backup_id": backup_id,
        "restore_result": restore_result,
        "status": "completed",
    }