import asyncio
from typing import Optional

from app.database import create_restore_job, update_restore_status
from app.services.collection_service import (
    create_collection,
    get_collections,
    update_collection,
    update_collection_publications,
)
from app.services.image_service import (
    reconcile_collection_image,
    reconcile_product_images,
)
from app.services.inventory_service import (
    activate_inventory_at_location,
    get_locations,
    set_inventory_quantities,
)
from app.services.metafield_service import (
    ensure_metafield_definition,
    set_metafields,
)
from app.services.metaobject_service import (
    ensure_metaobject_definition,
)
from app.services.product_service import (
    bulk_upsert_variants,
    create_product_from_backup,
    get_product,
    get_product_map_by_handle,
    update_product_from_backup,
)
from app.services.publication_service import get_publication_map
from app.storage.backup_store import read_json
from app.storage.report_store import write_json_report
from app.domain.metafields.ref_rewriter import extract_metaobject_gids
from app.domain.products.matcher import match_variants


async def run_restore(
    store_id: int,
    shop: str,
    backup_id: int,
    selected_product_handles: Optional[list[str]] = None,
    selected_collection_handles: Optional[list[str]] = None,
    locked_locations: Optional[list[str]] = None,
) -> dict:
    """
    Single restore engine – granular by design.
    - If selected_product_handles is None → all products in backup are restored.
    - If selected_collection_handles is None → all collections in backup are restored.
    - Products/collections are matched by handle: update if exists, create otherwise.
    - Locked locations: inventory is activated (connected) but quantities are NOT overwritten.
    """
    restore_id = create_restore_job(store_id, backup_id)
    try:
        update_restore_status(restore_id, "running")

        # 1. Load backup artifacts
        products_backup = read_json("products", backup_id)          # list of dicts
        collections_backup = read_json("collections", backup_id)    # list of dicts
        locations_backup = read_json("locations", backup_id)        # list of dicts
        metaobject_defs_backup = read_json("metaobject_definitions", backup_id) or []
        inventory_levels_backup = read_json("inventory_levels", backup_id) if read_json("inventory_levels", backup_id) else {}
        publication_map = await get_publication_map(shop)

        # 2. Determine scope
        if selected_product_handles is None:
            selected_product_handles = [p["handle"] for p in products_backup if p.get("handle")]
        if selected_collection_handles is None:
            selected_collection_handles = [c["handle"] for c in collections_backup if c.get("handle")]

        selected_product_handles = set(selected_product_handles)
        selected_collection_handles = set(selected_collection_handles)

        # Filter backups
        products_to_restore = [p for p in products_backup if p.get("handle") in selected_product_handles]
        collections_to_restore = [c for c in collections_backup if c.get("handle") in selected_collection_handles]

        if not products_to_restore and not collections_to_restore:
            update_restore_status(restore_id, "completed")
            return {"restore_id": restore_id, "message": "No items selected"}

        # 3. Discover metaobject references in selected entities
        metaobject_refs = set()
        for product in products_to_restore:
            for mf in product.get("metafields", []):
                metaobject_refs.update(extract_metaobject_gids(mf.get("value"), mf.get("type")))
            for variant in product.get("variants", []):
                for mf in variant.get("metafields", []):
                    metaobject_refs.update(extract_metaobject_gids(mf.get("value"), mf.get("type")))
        for collection in collections_to_restore:
            for mf in collection.get("metafields", []):
                metaobject_refs.update(extract_metaobject_gids(mf.get("value"), mf.get("type")))

        # 4. Ensure metaobject definitions & entries (simplified: ensure all definitions from backup exist)
        # In a production version, we would also create/update entries and build an entry_id_map.
        # For now, we only ensure definitions to avoid errors on metafield creation.
        for defn in metaobject_defs_backup:
            await ensure_metaobject_definition(shop, defn)

        # 5. Ensure metafield definitions for all metafields in scope
        definitions_to_ensure = set()
        for product in products_to_restore:
            for mf in product.get("metafields", []):
                definitions_to_ensure.add(("PRODUCT", mf.get("namespace"), mf.get("key"), mf.get("type")))
            for variant in product.get("variants", []):
                for mf in variant.get("metafields", []):
                    definitions_to_ensure.add(("PRODUCTVARIANT", mf.get("namespace"), mf.get("key"), mf.get("type")))
        for collection in collections_to_restore:
            for mf in collection.get("metafields", []):
                definitions_to_ensure.add(("COLLECTION", mf.get("namespace"), mf.get("key"), mf.get("type")))

        for owner_type, ns, key, mf_type in definitions_to_ensure:
            await ensure_metafield_definition(
                shop,
                owner_type,
                {
                    "namespace": ns,
                    "key": key,
                    "type": mf_type,
                    "name": f"{ns}.{key}",
                }
            )

        # 6. Get target state (existing products/collections)
        target_product_map = await get_product_map_by_handle(shop)  # handle -> product dict
        target_collections = await get_collections(shop)
        target_collection_map = {c["handle"]: c for c in target_collections if c.get("handle")}
        target_locations = await get_locations(shop)

        # 7. Restore products
        restored_products = []
        for backup_product in products_to_restore:
            handle = backup_product.get("handle")
            existing = target_product_map.get(handle)

            if existing:
                product_id = existing["id"]
                # Update shell
                await update_product_from_backup(shop, product_id, backup_product)
                # Variants (bulk upsert)
                source_variants = backup_product.get("variants", [])
                await bulk_upsert_variants(shop, product_id, source_variants, existing)
                # Metafields (no entry_id_map yet)
                await set_metafields(
                    shop,
                    f"gid://shopify/Product/{product_id}",
                    backup_product.get("metafields", []),
                    entry_id_map={}  # Placeholder – will be filled when metaobject entries are restored
                )
                # Images
                await reconcile_product_images(shop, product_id, backup_product, existing)
                restored_products.append({"handle": handle, "action": "updated", "id": product_id})
            else:
                # Create
                result = await create_product_from_backup(shop, backup_product)
                new_product = result.get("product")
                if new_product:
                    product_id = new_product["id"]
                    # Metafields
                    await set_metafields(
                        shop,
                        f"gid://shopify/Product/{product_id}",
                        backup_product.get("metafields", []),
                        entry_id_map={}
                    )
                    # Images
                    await reconcile_product_images(shop, product_id, backup_product, None)
                    restored_products.append({"handle": handle, "action": "created", "id": product_id})

        # 8. Restore collections
        restored_collections = []
        for backup_collection in collections_to_restore:
            handle = backup_collection.get("handle")
            existing = target_collection_map.get(handle)

            collection_input = {
                "title": backup_collection.get("title"),
                "handle": handle,
                "descriptionHtml": backup_collection.get("descriptionHtml"),
            }
            # Add rules for smart collections
            if backup_collection.get("rules"):
                collection_input["rules"] = backup_collection.get("rules")
                collection_input["disjunctive"] = backup_collection.get("disjunctive", False)

            if existing:
                collection_id = existing["id"]
                collection_input["id"] = collection_id
                await update_collection(shop, collection_input)
                # Image
                await reconcile_collection_image(shop, collection_id, backup_collection.get("image"), existing.get("image"))
                # Publications
                pub_names = backup_collection.get("publication_names", [])
                pub_ids = [publication_map.get(name) for name in pub_names if name in publication_map]
                await update_collection_publications(shop, collection_id, pub_ids)
                # Metafields
                await set_metafields(
                    shop,
                    f"gid://shopify/Collection/{collection_id}",
                    backup_collection.get("metafields", []),
                    entry_id_map={}
                )
                restored_collections.append({"handle": handle, "action": "updated", "id": collection_id})
            else:
                result = await create_collection(shop, collection_input)
                new_collection = result.get("collection")
                if new_collection:
                    collection_id = new_collection["id"]
                    # Image
                    await reconcile_collection_image(shop, collection_id, backup_collection.get("image"), None)
                    # Publications
                    pub_names = backup_collection.get("publication_names", [])
                    pub_ids = [publication_map.get(name) for name in pub_names if name in publication_map]
                    await update_collection_publications(shop, collection_id, pub_ids)
                    # Metafields
                    await set_metafields(
                        shop,
                        f"gid://shopify/Collection/{collection_id}",
                        backup_collection.get("metafields", []),
                        entry_id_map={}
                    )
                    restored_collections.append({"handle": handle, "action": "created", "id": collection_id})

        # 9. Inventory sync (for restored products)
        locked_locations = locked_locations or []
        # Build mapping of handle -> source variants
        source_variants_by_handle = {}
        for bp in products_to_restore:
            handle = bp.get("handle")
            if handle in [p["handle"] for p in restored_products]:
                source_variants_by_handle[handle] = bp.get("variants", [])

        # Refresh target product map to get updated variants with inventory_item_id
        target_product_map = await get_product_map_by_handle(shop)

        for handle, source_variants in source_variants_by_handle.items():
            target_product = target_product_map.get(handle)
            if not target_product:
                continue
            target_variants = target_product.get("variants", [])
            # Match variants (source -> target)
            variant_match = match_variants(source_variants, target_variants)
            # Reverse map: target_id -> source variant
            target_to_source = {target_id: source_id for source_id, target_id in variant_match.items()}

            for target_var in target_variants:
                target_var_id = target_var["id"]
                source_var = target_to_source.get(str(target_var_id))
                if not source_var:
                    continue
                source_inv_item = source_var.get("inventoryItem", {})
                source_inv_id = source_inv_item.get("id")
                if not source_inv_id:
                    continue
                target_inv_id = target_var.get("inventoryItem", {}).get("id")
                if not target_inv_id:
                    continue

                # Get levels from backup
                source_levels = inventory_levels_backup.get(source_inv_id, [])
                for level in source_levels:
                    source_loc_id = level.get("location_id")
                    source_available = level.get("available", 0)
                    # Find source location name
                    source_loc_name = None
                    for loc in locations_backup:
                        if str(loc.get("id")) == str(source_loc_id):
                            source_loc_name = loc.get("name")
                            break
                    if not source_loc_name:
                        continue

                    # Find target location by name
                    target_loc = None
                    for loc in target_locations:
                        if loc.get("name") == source_loc_name:
                            target_loc = loc
                            break
                    if not target_loc:
                        continue
                    target_loc_id = target_loc["id"]

                    # Check locking
                    if source_loc_name in locked_locations:
                        # Activate but do NOT set quantity (preserve existing)
                        await activate_inventory_at_location(
                            shop,
                            target_inv_id,
                            target_loc_id,
                            available=None
                        )
                    else:
                        # Set quantity
                        await set_inventory_quantities(
                            shop,
                            name="available",
                            reason="Restore from backup",
                            quantities=[{
                                "inventoryItemId": target_inv_id,
                                "locationId": target_loc_id,
                                "quantity": source_available,
                            }],
                            ignore_compare_quantity=True,
                        )

        # 10. Report
        report = {
            "restore_id": restore_id,
            "backup_id": backup_id,
            "store_id": store_id,
            "restored_products": restored_products,
            "restored_collections": restored_collections,
            "locked_locations_applied": locked_locations,
        }
        write_json_report("restore", restore_id, report)

        update_restore_status(restore_id, "completed")
        return report

    except Exception as e:
        update_restore_status(restore_id, "failed", error_message=str(e))
        raise