GET_LOCATIONS = """
query GetLocations($cursor: String) {
  locations(first: 100, after: $cursor) {
    edges {
      cursor
      node {
        id
        name
        isActive
        fulfillsOnlineOrders
        address {
          address1
          address2
          city
          province
          zip
          country
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


GET_INVENTORY_LEVELS = """
query GetInventoryLevels($inventoryItemId: ID!) {
  inventoryItem(id: $inventoryItemId) {
    id
    tracked
    requiresShipping
    inventoryLevels(first: 100) {
      edges {
        node {
          id
          quantities(names: ["available"]) {
            name
            quantity
          }
          location {
            id
            name
          }
        }
      }
    }
  }
}
"""


SET_INVENTORY_QUANTITIES = """
mutation SetInventoryQuantities($input: InventorySetQuantitiesInput!) {
  inventorySetQuantities(input: $input) {
    inventoryAdjustmentGroup {
      createdAt
      reason
      referenceDocumentUri
      changes {
        name
        delta
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""


ACTIVATE_INVENTORY_AT_LOCATION = """
mutation ActivateInventoryAtLocation($inventoryItemId: ID!, $locationId: ID!, $available: Int) {
  inventoryActivate(inventoryItemId: $inventoryItemId, locationId: $locationId, available: $available) {
    inventoryLevel {
      id
    }
    userErrors {
      field
      message
    }
  }
}
"""


SET_TRACKED_AND_SHIPPING = """
mutation UpdateInventoryItem($input: InventoryItemInput!) {
  inventoryItemUpdate(input: $input) {
    inventoryItem {
      id
      tracked
      requiresShipping
    }
    userErrors {
      field
      message
    }
  }
}
"""
