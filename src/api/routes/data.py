"""Data CRUD routes for API service.

This module provides generic CRUD endpoints for data management using
the repository pattern for data persistence.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.domain.entities import DataItem as DataItemEntity
from src.api.exceptions import DatabaseError, ResourceNotFoundError
from src.api.models.schemas import DataItem, DataListResponse
from src.api.repositories.data_repository import DataRepository
from src.api.services.container import ServiceContainer

router = APIRouter(prefix="/data", tags=["data"])


def get_container(request: Request) -> ServiceContainer:
    """Dependency to get service container from app state.

    Args:
        request: FastAPI request object

    Returns:
        Service container instance
    """
    return request.app.state.container


async def get_repository(container: ServiceContainer = Depends(get_container)) -> DataRepository:
    """Dependency to get data repository.

    Args:
        container: Service container

    Yields:
        Data repository instance with active session
    """
    async with container.database.get_session() as session:
        yield DataRepository(session)


@router.post("/", response_model=DataItem)
async def create_data_item(
    item: DataItem, repository: DataRepository = Depends(get_repository)
) -> DataItem:
    """Create a new data item.

    Args:
        item: Data item to create
        repository: Data repository instance

    Returns:
        Created data item with assigned ID

    Raises:
        HTTPException: If creation fails
    """
    try:
        entity = DataItemEntity(name=item.name, description=item.description, data=item.data)
        created_entity = await repository.create(entity)
        return DataItem(
            id=created_entity.id,
            name=created_entity.name,
            description=created_entity.description,
            data=created_entity.data,
        )
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/{item_id}", response_model=DataItem)
async def read_data_item(
    item_id: int, repository: DataRepository = Depends(get_repository)
) -> DataItem:
    """Read a data item by ID.

    Args:
        item_id: ID of the item to read
        repository: Data repository instance

    Returns:
        Data item

    Raises:
        HTTPException: If item not found
    """
    try:
        entity = await repository.get_by_id(item_id)
        return DataItem(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            data=entity.data,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.put("/{item_id}", response_model=DataItem)
async def update_data_item(
    item_id: int, item: DataItem, repository: DataRepository = Depends(get_repository)
) -> DataItem:
    """Update a data item.

    Args:
        item_id: ID of the item to update
        item: Updated item data
        repository: Data repository instance

    Returns:
        Updated data item

    Raises:
        HTTPException: If item not found or update fails
    """
    try:
        entity = await repository.get_by_id(item_id)
        entity.update(name=item.name, description=item.description, data=item.data)
        updated_entity = await repository.update(entity)
        return DataItem(
            id=updated_entity.id,
            name=updated_entity.name,
            description=updated_entity.description,
            data=updated_entity.data,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.delete("/{item_id}")
async def delete_data_item(
    item_id: int, repository: DataRepository = Depends(get_repository)
) -> dict[str, str]:
    """Delete a data item.

    Args:
        item_id: ID of the item to delete
        repository: Data repository instance

    Returns:
        Confirmation message

    Raises:
        HTTPException: If item not found or deletion fails
    """
    try:
        await repository.delete(item_id)
        return {"message": f"Item {item_id} deleted"}
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/", response_model=DataListResponse)
async def list_data_items(repository: DataRepository = Depends(get_repository)) -> DataListResponse:
    """List all data items.

    Args:
        repository: Data repository instance

    Returns:
        List of all data items

    Raises:
        HTTPException: If listing fails
    """
    try:
        entities = await repository.get_all()
        items = [
            DataItem(id=entity.id, name=entity.name, description=entity.description, data=entity.data)
            for entity in entities
        ]
        total = await repository.count()
        return DataListResponse(items=items, total=total)
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=e.message)

