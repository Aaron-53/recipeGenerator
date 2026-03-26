from typing import List

from configs.database import get_collection


async def get_user_inventory_names(user_id: str) -> List[str]:
    coll = await get_collection("inventory")
    cursor = coll.find({"user_id": user_id})
    items = await cursor.to_list(length=None)
    names: List[str] = []
    for item in items:
        name = item.get("name")
        if name and str(name).strip():
            names.append(str(name).strip())
    return names
