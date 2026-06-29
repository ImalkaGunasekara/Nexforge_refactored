GET_PUBLICATIONS = """
query GetPublications($cursor: String) {
  publications(first: 100, after: $cursor) {
    edges {
      cursor
      node {
        id
        name
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


GET_RESOURCE_PUBLICATIONS = """
query GetResourcePublications($id: ID!) {
  node(id: $id) {
    ... on Publishable {
      resourcePublicationsCount {
        count
      }
      resourcePublications(first: 100) {
        edges {
          node {
            publication {
              id
              name
            }
            isPublished
            publishDate
          }
        }
      }
    }
  }
}
"""


PUBLISH_RESOURCE = """
mutation PublishResource($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    publishable {
      availablePublicationsCount {
        count
      }
      resourcePublicationsCount {
        count
      }
    }
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


UNPUBLISH_RESOURCE = """
mutation UnpublishResource($id: ID!, $input: [PublicationInput!]!) {
  publishableUnpublish(id: $id, input: $input) {
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
