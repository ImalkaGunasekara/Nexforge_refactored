#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_store_by_domain
from app.operations.restore import run_restore
from app.storage.backup_store import read_json

# ─── CONFIG ──────────────────────────────────────────────
STORE = "nexforge-test-same-target-store.myshopify.com"
# ──────────────────────────────────────────────────────────


def prompt_handles(category: str) -> list[str] | None:
    """
    Prompt for handles of a given category.
    - Type 'all' to select all.
    - Press Enter to select none.
    - Otherwise, enter comma-separated handles.
    """
    print(f"\n📦 {category.upper()} selection")
    print("   Enter 'all' to restore all, press Enter to skip, or list handles separated by commas.")
    user_input = input(f"   {category} handles: ").strip()

    if not user_input:
        return None  # None means skip all (which will be interpreted as empty list later)
    if user_input.lower() == "all":
        return None  # None means "all" – we'll pass None to run_restore
    # Otherwise, split by comma and strip
    handles = [h.strip() for h in user_input.split(",") if h.strip()]
    return handles if handles else None  # If empty after stripping, treat as None (skip)


def prompt_locked_locations(backup_id: int) -> list[str] | None:
    print("\n🔒 Inventory location locking")
    print("   Enter location names to lock (comma-separated), or press Enter to skip.")

    # Display available locations from backup
    try:
        locations = read_json("locations", backup_id)
        if locations:
            print("\n   Available locations in this backup:")
            for loc in locations:
                name = loc.get("name", "Unnamed")
                print(f"     - {name}")
        else:
            print("   (No locations found in this backup)")
    except Exception:
        print("   (Could not read locations from backup)")

    user_input = input("\n   Locked locations: ").strip()
    if not user_input:
        return None
    locations_list = [loc.strip() for loc in user_input.split(",") if loc.strip()]
    return locations_list if locations_list else None


async def main():
    store = get_store_by_domain(STORE)
    if not store:
        print(f"❌ Store '{STORE}' not found in database. Run OAuth first.")
        return
    if not store.get("access_token"):
        print(f"❌ Store '{STORE}' has no access token. Reinstall the app.")
        return

    print("\n🔄 Interactive Restore")
    print(f"   Store: {STORE}")
    print("=" * 50)

    # 1. Backup ID
    backup_id_str = input("   Backup ID: ").strip()
    if not backup_id_str.isdigit():
        print("❌ Invalid backup ID. Must be a number.")
        return
    backup_id = int(backup_id_str)

    # 2. Products
    product_handles = prompt_handles("product")

    # 3. Collections
    collection_handles = prompt_handles("collection")

    # 4. Locked locations
    locked_locations = prompt_locked_locations(backup_id)

    # Confirm
    print("\n📋 Summary")
    print(f"   Backup ID: {backup_id}")
    print(f"   Products:  {'all' if product_handles is None else (product_handles or 'none')}")
    print(f"   Collections: {'all' if collection_handles is None else (collection_handles or 'none')}")
    print(f"   Locked locations: {locked_locations or 'none'}")

    confirm = input("\n   Proceed with restore? (y/N): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("   ❌ Restore cancelled.")
        return

    print("\n🔄 Starting restore...")
    result = await run_restore(
        store_id=store["id"],
        shop=STORE,
        backup_id=backup_id,
        selected_product_handles=product_handles,
        selected_collection_handles=collection_handles,
        locked_locations=locked_locations,
    )

    print("\n✅ Restore completed.")
    print(f"   Products restored: {len(result.get('restored_products', []))}")
    print(f"   Collections restored: {len(result.get('restored_collections', []))}")
    print(f"   Metaobject entries restored: {result.get('metaobject_entries_restored', 0)}")


if __name__ == "__main__":
    asyncio.run(main())