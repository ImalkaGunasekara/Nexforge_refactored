GET_PRODUCTS_PAGE = """
query GetProductsPage($cursor: String) {
  products(first: 50, after: $cursor) {
    edges {
      cursor
      node {
        id
        title
        handle
        status
        vendor
        productType
        tags
        descriptionHtml
        options {
          id
          name
          values
        }
        featuredImage {
          id
          url
          altText
        }
        images(first: 50) {
          edges {
            node {
              id
              url
              altText
            }
          }
        }
        variants(first: 100) {
          edges {
            node {
              id
              title
              sku
              barcode
              price
              compareAtPrice
              inventoryQuantity
              taxable
              position
              selectedOptions {
                name
                value
              }
              inventoryItem {
                id
                tracked
                requiresShipping
              }
              image {
                id
                url
                altText
              }
            }
          }
        }
        metafields(first: 100) {
          edges {
            node {
              id
              namespace
              key
              type
              value
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


GET_PRODUCT_BY_ID = """
query GetProductById($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    status
    vendor
    productType
    tags
    descriptionHtml
    options {
      id
      name
      values
    }
    featuredImage {
      id
      url
      altText
    }
    images(first: 50) {
      edges {
        node {
          id
          url
          altText
        }
      }
    }
    variants(first: 100) {
      edges {
        node {
          id
          title
          sku
          barcode
          price
          compareAtPrice
          inventoryQuantity
          taxable
          position
          selectedOptions {
            name
            value
          }
          inventoryItem {
            id
            tracked
            requiresShipping
          }
          image {
            id
            url
            altText
          }
        }
      }
    }
    metafields(first: 100) {
      edges {
        node {
          id
          namespace
          key
          type
          value
        }
      }
    }
  }
}
"""


CREATE_PRODUCT = """
mutation CreateProduct($input: ProductInput!) {
  productCreate(input: $input) {
    product {
      id
      title
      handle
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""


UPDATE_PRODUCT = """
mutation UpdateProduct($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      title
      handle
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""


DELETE_PRODUCT = """
mutation DeleteProduct($input: ProductDeleteInput!) {
  productDelete(input: $input) {
    deletedProductId
    userErrors {
      field
      message
    }
  }
}
"""


SET_PRODUCT_VARIANTS_BULK = """
mutation ProductVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    product {
      id
    }
    userErrors {
      field
      message
    }
  }
}
"""
