from app.shopify.client import (
    build_admin_graphql_url,
    build_graphql_headers,
    shopify_request_with_retry,
)


async def shopify_graphql_request(
    shop: str,
    query: str,
    variables: dict | None = None,
    timeout: float = 60.0,
):
    url = build_admin_graphql_url(shop)
    headers = await build_graphql_headers(shop)

    payload = {
        "query": query,
        "variables": variables or {},
    }

    response = await shopify_request_with_retry(
        method="POST",
        url=url,
        headers=headers,
        json_data=payload,
        timeout=timeout,
    )

    if response.status_code >= 400:
        raise Exception(f"Shopify GraphQL error {response.status_code}: {response.text}")

    data = response.json()

    if "errors" in data and data["errors"]:
        raise Exception(f"Shopify GraphQL top-level errors: {data['errors']}")

    return data


async def graphql_data(
    shop: str,
    query: str,
    variables: dict | None = None,
    timeout: float = 60.0,
):
    data = await shopify_graphql_request(
        shop=shop,
        query=query,
        variables=variables,
        timeout=timeout,
    )
    return data.get("data", {})


async def graphql_edges(
    shop: str,
    query: str,
    root_key: str,
    variables: dict | None = None,
    timeout: float = 60.0,
):
    data = await graphql_data(
        shop=shop,
        query=query,
        variables=variables,
        timeout=timeout,
    )
    root = data.get(root_key, {})
    return root.get("edges", [])


async def graphql_node(
    shop: str,
    query: str,
    root_key: str,
    variables: dict | None = None,
    timeout: float = 60.0,
):
    data = await graphql_data(
        shop=shop,
        query=query,
        variables=variables,
        timeout=timeout,
    )
    return data.get(root_key)
