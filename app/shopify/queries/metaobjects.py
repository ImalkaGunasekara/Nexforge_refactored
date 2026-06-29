GET_METAOBJECT_DEFINITIONS = """
query GetMetaobjectDefinitions($cursor: String) {
  metaobjectDefinitions(first: 100, after: $cursor) {
    edges {
      cursor
      node {
        id
        name
        type
        fieldDefinitions {
          key
          name
          required
          type {
            name
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


GET_METAOBJECT_BY_ID = """
query GetMetaobjectById($id: ID!) {
  metaobject(id: $id) {
    id
    handle
    type
    fields {
      key
      value
    }
  }
}
"""


GET_METAOBJECTS_BY_TYPE = """
query GetMetaobjectsByType($type: String!, $cursor: String) {
  metaobjects(type: $type, first: 100, after: $cursor) {
    edges {
      cursor
      node {
        id
        handle
        type
        fields {
          key
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


CREATE_METAOBJECT_DEFINITION = """
mutation CreateMetaobjectDefinition($definition: MetaobjectDefinitionCreateInput!) {
  metaobjectDefinitionCreate(definition: $definition) {
    metaobjectDefinition {
      id
      name
      type
    }
    userErrors {
      field
      message
    }
  }
}
"""


CREATE_METAOBJECT = """
mutation CreateMetaobject($metaobject: MetaobjectCreateInput!) {
  metaobjectCreate(metaobject: $metaobject) {
    metaobject {
      id
      handle
      type
    }
    userErrors {
      field
      message
    }
  }
}
"""


UPDATE_METAOBJECT = """
mutation UpdateMetaobject($id: ID!, $metaobject: MetaobjectUpdateInput!) {
  metaobjectUpdate(id: $id, metaobject: $metaobject) {
    metaobject {
      id
      handle
      type
    }
    userErrors {
      field
      message
    }
  }
}
"""


DELETE_METAOBJECT = """
mutation DeleteMetaobject($id: ID!) {
  metaobjectDelete(id: $id) {
    deletedId
    userErrors {
      field
      message
    }
  }
}
"""
