GET_COLLECTIONS_PAGE = """
query GetCollectionsPage($cursor: String) {
  collections(first: 50, after: $cursor) {
    edges {
      cursor
      node {
        id
        handle
        title
        descriptionHtml
        updatedAt
        image {
          id
          url
          altText
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


GET_COLLECTION_BY_ID = """
query GetCollectionById($id: ID!) {
  collection(id: $id) {
    id
    handle
    title
    descriptionHtml
    updatedAt
    image {
      id
      url
      altText
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


CREATE_COLLECTION = """
mutation CreateCollection($input: CollectionInput!) {
  collectionCreate(input: $input) {
    collection {
      id
      handle
      title
    }
    userErrors {
      field
      message
    }
  }
}
"""


UPDATE_COLLECTION = """
mutation UpdateCollection($input: CollectionInput!) {
  collectionUpdate(input: $input) {
    collection {
      id
      handle
      title
    }
    userErrors {
      field
      message
    }
  }
}
"""


DELETE_COLLECTION = """
mutation DeleteCollection($input: CollectionDeleteInput!) {
  collectionDelete(input: $input) {
    deletedCollectionId
    shop {
      id
    }
    userErrors {
      field
      message
    }
  }
}
"""


UPDATE_COLLECTION_IMAGE = """
mutation UpdateCollectionImage($input: CollectionInput!) {
  collectionUpdate(input: $input) {
    collection {
      id
      image {
        id
        url
        altText
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""
