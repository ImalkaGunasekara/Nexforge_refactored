from app.services.collection_service import set_collection_image
from app.shopify.rest import rest_get, rest_post, rest_put, rest_delete


def normalize_image_url(url: str | None) -> str:
    if not url:
        return ""
    return url.strip()


def images_match(source_url: str | None, target_url: str | None) -> bool:
    return normalize_image_url(source_url) == normalize_image_url(target_url)


def build_collection_image_payload(image: dict | None) -> tuple[str | None, str | None]:
    if not image:
        return None, None
    return image.get("url"), image.get("altText")


async def reconcile_collection_image(shop: str, collection_id: str, source_image: dict | None, target_image: dict | None) -> dict:
    source_url, source_alt = build_collection_image_payload(source_image)
    target_url, _ = build_collection_image_payload(target_image)

    if images_match(source_url, target_url):
        return {
            "changed": False,
            "collection": None,
            "errors": [],
        }

    result = await set_collection_image(
        shop=shop,
        collection_id=collection_id,
        image_src=source_url,
        alt_text=source_alt,
    )

    return {
        "changed": True,
        "collection": result.get("collection"),
        "errors": result.get("errors", []),
    }


async def reconcile_product_images(shop: str, product_id: str, backup_product: dict, target_product: dict | None) -> dict:
    """
    Reconcile product images:
    - Add missing images (by src)
    - Delete extra images (not in backup)
    - Set featured image (from backup.featuredImage)
    """
    backup_images = backup_product.get("images", [])
    target_images = target_product.get("images", []) if target_product else []

    # Build maps by src
    backup_src_map = {img["src"]: img for img in backup_images if img.get("src")}
    target_src_map = {img["src"]: img for img in target_images if img.get("src")}

    # Add missing images
    for src, img in backup_src_map.items():
        if src not in target_src_map:
            await rest_post(shop, f"products/{product_id}/images.json", {
                "image": {"src": src, "alt": img.get("altText", "")}
            })

    # Delete extra images
    for src, img in target_src_map.items():
        if src not in backup_src_map:
            await rest_delete(shop, f"products/{product_id}/images/{img['id']}.json")

    # Now set featured image: fetch updated product to get image IDs
    updated_product = await rest_get(shop, f"products/{product_id}.json")
    updated_images = updated_product.get("product", {}).get("images", [])

    featured_backup = backup_product.get("featuredImage")
    if featured_backup and featured_backup.get("src"):
        featured_src = featured_backup["src"]
        # Find the image ID with that src
        target_img_id = None
        for img in updated_images:
            if img.get("src") == featured_src:
                target_img_id = img["id"]
                break
        if target_img_id:
            # Set as featured using PUT on product
            await rest_put(shop, f"products/{product_id}.json", {
                "product": {"id": product_id, "image": {"id": target_img_id}}
            })
        else:
            # If not found (shouldn't happen if we added it), clear featured
            await rest_put(shop, f"products/{product_id}.json", {
                "product": {"id": product_id, "image": None}
            })
    else:
        # Clear featured image
        await rest_put(shop, f"products/{product_id}.json", {
            "product": {"id": product_id, "image": None}
        })

    return {"success": True}