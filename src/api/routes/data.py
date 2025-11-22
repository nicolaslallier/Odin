"""Data CRUD routes for API service.

This module provides generic CRUD endpoints for data management.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.models.schemas import DataItem, DataListResponse

router = APIRouter(prefix="/data", tags=["data"])

# In-memory storage for demonstration (replace with database in production)
_data_store: dict[int, DataItem] = {}
_next_id = 1


@router.post("/", response_model=DataItem)
async def create_data_item(item: DataItem) -> DataItem:
    """Create a new data item.

    Args:
        item: Data item to create

    Returns:
        Created data item with assigned ID
    """
    global _next_id
    item.id = _next_id
    _data_store[_next_id] = item
    _next_id += 1
    return item


@router.get("/{item_id}", response_model=DataItem)
async def read_data_item(item_id: int) -> DataItem:
    """Read a data item by ID.

    Args:
        item_id: ID of the item to read

    Returns:
        Data item

    Raises:
        HTTPException: If item not found
    """
    if item_id not in _data_store:
        raise HTTPException(status_code=404, detail="Item not found")
    return _data_store[item_id]


@router.put("/{item_id}", response_model=DataItem)
async def update_data_item(item_id: int, item: DataItem) -> DataItem:
    """Update a data item.

    Args:
        item_id: ID of the item to update
        item: Updated item data

    Returns:
        Updated data item

    Raises:
        HTTPException: If item not found
    """
    if item_id not in _data_store:
        raise HTTPException(status_code=404, detail="Item not found")
    item.id = item_id
    _data_store[item_id] = item
    return item


@router.delete("/{item_id}")
async def delete_data_item(item_id: int) -> dict[str, str]:
    """Delete a data item.

    Args:
        item_id: ID of the item to delete

    Returns:
        Confirmation message

    Raises:
        HTTPException: If item not found
    """
    if item_id not in _data_store:
        raise HTTPException(status_code=404, detail="Item not found")
    del _data_store[item_id]
    return {"message": f"Item {item_id} deleted"}


@router.get("/", response_model=DataListResponse)
async def list_data_items() -> DataListResponse:
    """List all data items.

    Returns:
        List of all data items
    """
    items = list(_data_store.values())
    return DataListResponse(items=items, total=len(items))

