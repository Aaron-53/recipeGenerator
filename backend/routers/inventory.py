from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from typing import List
from schemas.inventory import (
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
)
from utils.auth_utils import get_current_user_from_token
from configs.database import get_collection
from bson import ObjectId

router = APIRouter(prefix="/inventory", tags=["inventory"])


def validate_object_id(item_id: str) -> ObjectId:
    """Validate and convert string to ObjectId"""
    try:
        return ObjectId(item_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid item ID format"
        )


@router.post(
    "/items", status_code=status.HTTP_201_CREATED, response_model=InventoryItemResponse
)
async def create_inventory_item(
    item: InventoryItemCreate, current_user: dict = Depends(get_current_user_from_token)
):
    """Create a new inventory item for the current user"""

    inventory_collection = await get_collection("inventory")

    item_dict = {
        "name": item.name,
        "quantity": item.quantity,
        "unit": item.unit,
        "category": item.category,
        "notes": item.notes,
        "user_id": current_user["user_id"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = await inventory_collection.insert_one(item_dict)

    return InventoryItemResponse(
        item_id=str(result.inserted_id),
        user_id=current_user["user_id"],
        name=item.name,
        quantity=item.quantity,
        unit=item.unit,
        category=item.category,
        notes=item.notes,
        created_at=item_dict["created_at"],
        updated_at=item_dict["updated_at"],
    )


@router.get("/items", response_model=List[InventoryItemResponse])
async def get_all_inventory_items(
    current_user: dict = Depends(get_current_user_from_token),
    category: str = None,
):
    """Get all inventory items for the current user"""

    inventory_collection = await get_collection("inventory")

    # Build query filter
    query = {"user_id": current_user["user_id"]}
    if category:
        query["category"] = category

    # Get items
    cursor = inventory_collection.find(query)
    items = await cursor.to_list(length=None)

    return [
        InventoryItemResponse(
            item_id=str(item["_id"]),
            user_id=item["user_id"],
            name=item["name"],
            quantity=item["quantity"],
            unit=item["unit"],
            category=item.get("category"),
            notes=item.get("notes"),
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )
        for item in items
    ]


@router.get("/items/{item_id}", response_model=InventoryItemResponse)
async def get_inventory_item(
    item_id: str, current_user: dict = Depends(get_current_user_from_token)
):
    """Get a specific inventory item by ID"""

    object_id = validate_object_id(item_id)
    inventory_collection = await get_collection("inventory")

    item = await inventory_collection.find_one(
        {"_id": object_id, "user_id": current_user["user_id"]}
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )

    return InventoryItemResponse(
        item_id=str(item["_id"]),
        user_id=item["user_id"],
        name=item["name"],
        quantity=item["quantity"],
        unit=item["unit"],
        category=item.get("category"),
        notes=item.get("notes"),
        created_at=item["created_at"],
        updated_at=item["updated_at"],
    )


@router.put("/items/{item_id}", response_model=InventoryItemResponse)
async def update_inventory_item(
    item_id: str,
    item_update: InventoryItemUpdate,
    current_user: dict = Depends(get_current_user_from_token),
):
    """Update an inventory item"""

    object_id = validate_object_id(item_id)
    inventory_collection = await get_collection("inventory")

    # Check if item exists and belongs to user
    existing_item = await inventory_collection.find_one(
        {"_id": object_id, "user_id": current_user["user_id"]}
    )

    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )

    # Build update data (only include fields that were provided)
    update_data = {}
    if item_update.name is not None:
        update_data["name"] = item_update.name
    if item_update.quantity is not None:
        update_data["quantity"] = item_update.quantity
    if item_update.unit is not None:
        update_data["unit"] = item_update.unit
    if item_update.category is not None:
        update_data["category"] = item_update.category
    if item_update.notes is not None:
        update_data["notes"] = item_update.notes

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update provided",
        )

    update_data["updated_at"] = datetime.utcnow()

    # Update the item
    await inventory_collection.update_one({"_id": object_id}, {"$set": update_data})

    # Get updated item
    updated_item = await inventory_collection.find_one({"_id": object_id})

    return InventoryItemResponse(
        item_id=str(updated_item["_id"]),
        user_id=updated_item["user_id"],
        name=updated_item["name"],
        quantity=updated_item["quantity"],
        unit=updated_item["unit"],
        category=updated_item.get("category"),
        notes=updated_item.get("notes"),
        created_at=updated_item["created_at"],
        updated_at=updated_item["updated_at"],
    )


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_id: str, current_user: dict = Depends(get_current_user_from_token)
):
    """Delete an inventory item"""

    object_id = validate_object_id(item_id)
    inventory_collection = await get_collection("inventory")

    # Check if item exists and belongs to user
    existing_item = await inventory_collection.find_one(
        {"_id": object_id, "user_id": current_user["user_id"]}
    )

    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )

    # Delete the item
    await inventory_collection.delete_one({"_id": object_id})

    return None


@router.get("/stats")
async def get_inventory_stats(
    current_user: dict = Depends(get_current_user_from_token),
):
    """Get inventory statistics for the current user"""

    inventory_collection = await get_collection("inventory")

    # Get all items for user
    cursor = inventory_collection.find({"user_id": current_user["user_id"]})
    items = await cursor.to_list(length=None)

    # Calculate statistics
    total_items = len(items)
    categories = {}

    for item in items:
        category = item.get("category", "uncategorized")
        if category not in categories:
            categories[category] = 0
        categories[category] += 1

    return {
        "total_items": total_items,
        "categories": categories,
        "items_by_category": categories,
    }
