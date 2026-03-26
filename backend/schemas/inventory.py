from pydantic import BaseModel, Field
from typing import Optional
from typing import Literal
from datetime import datetime


class InventoryItemBase(BaseModel):
    """Base inventory item schema"""

    name: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=20)  # e.g., "kg", "lbs", "pieces"
    category: Optional[str] = Field(
        None, max_length=50
    )  # e.g., "vegetables", "meat", "dairy"
    notes: Optional[str] = Field(None, max_length=500)


class InventoryItemCreate(InventoryItemBase):
    """Schema for creating an inventory item"""

    pass


class InventoryItemUpdate(BaseModel):
    """Schema for updating an inventory item"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    category: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)


class InventoryItemResponse(InventoryItemBase):
    """Schema for inventory item response"""

    item_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryQuickParseRequest(BaseModel):
    """Freeform inventory command text from quick input."""

    text: str = Field(..., min_length=1, max_length=1000)


class ParsedInventoryDelta(BaseModel):
    """Minimal parsed item delta: + for add, - for remove."""

    item: str = Field(..., min_length=1, max_length=100)
    count: float = Field(..., ge=0)
    unit: str = Field(..., min_length=1, max_length=30)
    op: Literal["+", "-"]
