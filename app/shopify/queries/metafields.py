GET_METAFIELD_DEFINITIONS = """
query GetMetafieldDefinitions($ownerType: MetafieldOwnerType!, $cursor: String) {
  metafieldDefinitions(first: 100, ownerType: $ownerType, after: $cursor) {
    edges {
      cursor
      node {
        id
        name
        namespace
        key
        description
        type {
          name
        }
        ownerType
        validations {
          name
          value
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


GET_OWNER_METAFIELDS = """
query GetOwnerMetafields($ownerId: ID!) {
  node(id: $ownerId) {
    ... on HasMetafields {
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
}
"""


SET_METAFIELDS = """
mutation SetMetafields($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields {
      id
      namespace
      key
      type
      value
    }
    userErrors {
      field
      message
    }
  }
}
"""


CREATE_METAFIELD_DEFINITION = """
mutation CreateMetafieldDefinition($definition: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $definition) {
    createdDefinition {
      id
      name
      namespace
      key
      ownerType
      type {
        name
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""


UPDATE_METAFIELD_DEFINITION = """
mutation UpdateMetafieldDefinition($definition: MetafieldDefinitionUpdateInput!) {
  metafieldDefinitionUpdate(definition: $definition) {
    updatedDefinition {
      id
      name
      namespace
      key
      ownerType
      type {
        name
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""


DELETE_METAFIELD = """
mutation DeleteMetafield($input: MetafieldDeleteInput!) {
  metafieldDelete(input: $input) {
    deletedId
    userErrors {
      field
      message
    }
  }
}
"""
