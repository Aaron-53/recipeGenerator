# Inventory API Documentation

## Overview

The Inventory API allows authenticated users to manage their kitchen inventory items. All routes are protected and require authentication.

## Authentication

All inventory endpoints require a valid JWT token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### Create Inventory Item

**POST** `/inventory/items`

Create a new inventory item for the authenticated user.

**Request Body:**

```json
{
  "name": "Tomatoes",
  "quantity": 5.0,
  "unit": "kg",
  "category": "vegetables",
  "notes": "Fresh organic tomatoes"
}
```

**Response:** `201 Created`

```json
{
  "item_id": "64abc123...",
  "user_id": "64xyz789...",
  "name": "Tomatoes",
  "quantity": 5.0,
  "unit": "kg",
  "category": "vegetables",
  "notes": "Fresh organic tomatoes",
  "created_at": "2026-03-11T10:30:00",
  "updated_at": "2026-03-11T10:30:00"
}
```

---

### Get All Inventory Items

**GET** `/inventory/items`

Get all inventory items for the authenticated user.

**Query Parameters:**

- `category` (optional): Filter by category

**Response:** `200 OK`

```json
[
  {
    "item_id": "64abc123...",
    "user_id": "64xyz789...",
    "name": "Tomatoes",
    "quantity": 5.0,
    "unit": "kg",
    "category": "vegetables",
    "notes": "Fresh organic tomatoes",
    "created_at": "2026-03-11T10:30:00",
    "updated_at": "2026-03-11T10:30:00"
  }
]
```

---

### Get Single Inventory Item

**GET** `/inventory/items/{item_id}`

Get a specific inventory item by ID.

**Response:** `200 OK`

```json
{
  "item_id": "64abc123...",
  "user_id": "64xyz789...",
  "name": "Tomatoes",
  "quantity": 5.0,
  "unit": "kg",
  "category": "vegetables",
  "notes": "Fresh organic tomatoes",
  "created_at": "2026-03-11T10:30:00",
  "updated_at": "2026-03-11T10:30:00"
}
```

---

### Update Inventory Item

**PUT** `/inventory/items/{item_id}`

Update an existing inventory item. Only provided fields will be updated.

**Request Body:**

```json
{
  "quantity": 3.5,
  "notes": "Running low"
}
```

**Response:** `200 OK`

```json
{
  "item_id": "64abc123...",
  "user_id": "64xyz789...",
  "name": "Tomatoes",
  "quantity": 3.5,
  "unit": "kg",
  "category": "vegetables",
  "notes": "Running low",
  "created_at": "2026-03-11T10:30:00",
  "updated_at": "2026-03-11T11:15:00"
}
```

---

### Delete Inventory Item

**DELETE** `/inventory/items/{item_id}`

Delete an inventory item.

**Response:** `204 No Content`

---

### Get Inventory Statistics

**GET** `/inventory/stats`

Get statistics about the user's inventory.

**Response:** `200 OK`

```json
{
  "total_items": 15,
  "categories": {
    "vegetables": 5,
    "fruits": 3,
    "dairy": 4,
    "meat": 2,
    "grains": 1
  },
  "items_by_category": {
    "vegetables": 5,
    "fruits": 3,
    "dairy": 4,
    "meat": 2,
    "grains": 1
  }
}
```

## Field Descriptions

- **name** (required): Name of the inventory item (1-100 characters)
- **quantity** (required): Quantity of the item (must be > 0)
- **unit** (required): Unit of measurement (e.g., "kg", "lbs", "pieces", 1-20 characters)
- **category** (optional): Category of the item (max 50 characters)
- **notes** (optional): Additional notes (max 500 characters)

## Common Categories

Suggested categories for organizing items:

- `vegetables`
- `fruits`
- `dairy`
- `meat`
- `poultry`
- `seafood`
- `grains`
- `spices`
- `condiments`
- `beverages`
- `snacks`

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Could not validate credentials"
}
```

### 404 Not Found

```json
{
  "detail": "Inventory item not found"
}
```

### 400 Bad Request

```json
{
  "detail": "Invalid item ID format"
}
```

## Usage Examples

### Using cURL

```bash
# Get all items
curl -X GET "http://localhost:8000/inventory/items" \
  -H "Authorization: Bearer your-jwt-token"

# Create item
curl -X POST "http://localhost:8000/inventory/items" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Milk",
    "quantity": 2.0,
    "unit": "liters",
    "category": "dairy"
  }'

# Update item
curl -X PUT "http://localhost:8000/inventory/items/64abc123..." \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 1.5
  }'

# Delete item
curl -X DELETE "http://localhost:8000/inventory/items/64abc123..." \
  -H "Authorization: Bearer your-jwt-token"
```

### Using JavaScript/Fetch

```javascript
const API_URL = "http://localhost:8000";
const token = localStorage.getItem("token");

// Get all items
const response = await fetch(`${API_URL}/inventory/items`, {
  headers: {
    Authorization: `Bearer ${token}`,
  },
});
const items = await response.json();

// Create item
const newItem = await fetch(`${API_URL}/inventory/items`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    name: "Eggs",
    quantity: 12,
    unit: "pieces",
    category: "dairy",
  }),
});
```

## Testing

Run inventory tests:

```bash
python test_inventory.py
```

## Notes

- All items are automatically associated with the authenticated user
- Users can only access their own inventory items
- Item IDs are MongoDB ObjectIds
- Timestamps are in UTC
- The `updated_at` field is automatically updated on each modification
