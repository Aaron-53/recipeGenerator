from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from typing import List
import json
from schemas.inventory import (
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    InventoryQuickParseRequest,
    ParsedInventoryDelta,
)
from utils.auth_utils import get_current_user_from_token
from configs.database import get_collection
from bson import ObjectId
from services.inventory_parser import parse_inventory_input_with_llm, _normalize_unit, CONVERSION_MAP

router = APIRouter(prefix="/inventory", tags=["inventory"])


def validate_object_id(item_id: str) -> ObjectId:
    """Validate and convert string to ObjectId"""
    try:
        return ObjectId(item_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid item ID format"
        )


def _convert_count_to_unit(count: float, from_unit: str | None, to_unit: str | None) -> float:
    """Convert quantity from one unit to another when possible.

    Uses parser CONVERSION_MAP normalization and adds common metric bridges.
    Returns original count if conversion is not known.
    """
    if count is None:
        return 0.0

    from_u = _normalize_unit(from_unit)
    to_u = _normalize_unit(to_unit)

    if not from_u or not to_u or from_u == to_u:
        return float(count)

    # Common metric bridges used heavily in inventory updates.
    bridge_factors: dict[tuple[str, str], float] = {
        ("kg", "g"): 1000.0,
        ("g", "kg"): 0.001,
        ("l", "ml"): 1000.0,
        ("ml", "l"): 0.001,
    }
    factor = bridge_factors.get((from_u, to_u))
    if factor is not None:
        return float(count) * factor

    # Convert through map target units if available.
    from_meta = CONVERSION_MAP.get(from_u)
    to_meta = CONVERSION_MAP.get(to_u)
    if from_meta and to_meta:
        from_target, from_factor = from_meta
        to_target, to_factor = to_meta
        if from_target == to_target and to_factor:
            # source -> shared target -> requested unit
            in_target = float(count) * float(from_factor)
            return in_target / float(to_factor)

    return float(count)


@router.post("/parse-input", response_model=List[ParsedInventoryDelta])
async def parse_inventory_quick_input(
    body: InventoryQuickParseRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    """Parse freeform inventory text and apply changes to inventory."""

    user_id = current_user["user_id"]

    try:
        inventory_collection = await get_collection("inventory")
        # Fetch current inventory for context
        cursor = inventory_collection.find({"user_id": user_id})
        current_inventory = await cursor.to_list(length=None)

        # Convert to format expected by parser
        inventory_for_llm = [
            {
                "name": item.get("name"),
                "quantity": item.get("quantity"),
                "unit": item.get("unit"),
            }
            for item in current_inventory
        ]

        parsed = parse_inventory_input_with_llm(body.text.strip(), inventory_for_llm)
    except Exception as exc:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[inventory.parse-input] ERROR: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to parse inventory: {str(exc)}",
        ) from exc

    print(
        "[inventory.parse-input] user="
        f"{user_id} parsed_deltas="
        f"{json.dumps(parsed, ensure_ascii=True)}"
    )

    # Apply changes to inventory
    for delta in parsed:
        item_name = delta.get("item", "").strip().lower()
        count = float(delta.get("count", 0))
        unit = delta.get("unit")
        op = delta.get("op", "+")

        # Normalize unit
        if unit:
            unit = _normalize_unit(unit)

        # Find matching item in current inventory (case-insensitive)
        matching_item = None
        for inv_item in current_inventory:
            if inv_item.get("name", "").lower() == item_name:
                matching_item = inv_item
                break

        if op == "+":
            # Add operation
            if matching_item:
                existing_unit = matching_item.get("unit")
                adjusted_count = _convert_count_to_unit(count, unit, existing_unit)
                # Update existing item: add to quantity
                new_quantity = float(matching_item.get("quantity", 0)) + adjusted_count
                await inventory_collection.update_one(
                    {"_id": matching_item["_id"]},
                    {
                        "$set": {
                            "quantity": new_quantity,
                            "updated_at": datetime.utcnow(),
                        }
                    },
                )
                matching_item["quantity"] = new_quantity
            else:
                # Create new item
                new_item = {
                    "name": delta.get("item"),
                    "quantity": count,
                    "unit": unit or "",
                    "category": None,
                    "notes": None,
                    "user_id": user_id,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
                await inventory_collection.insert_one(new_item)
                current_inventory.append(new_item)

        elif op == "-":
            # Remove operation (decrease quantity)
            if matching_item:
                existing_unit = matching_item.get("unit")
                adjusted_count = _convert_count_to_unit(count, unit, existing_unit)
                current_qty = float(matching_item.get("quantity", 0))
                new_quantity = max(0, current_qty - adjusted_count)

                if new_quantity <= 0:
                    # Delete if quantity becomes 0 or less
                    await inventory_collection.delete_one({"_id": matching_item["_id"]})
                    current_inventory = [
                        x for x in current_inventory if x.get("_id") != matching_item.get("_id")
                    ]
                else:
                    # Update quantity
                    await inventory_collection.update_one(
                        {"_id": matching_item["_id"]},
                        {
                            "$set": {
                                "quantity": new_quantity,
                                "updated_at": datetime.utcnow(),
                            }
                        },
                    )
                    matching_item["quantity"] = new_quantity

    return parsed


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
