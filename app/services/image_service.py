from app.services.collection_service import set_collection_image


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
