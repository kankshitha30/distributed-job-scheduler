import math
from typing import Generic, TypeVar, List, Sequence
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    page: int
    page_size: int
    total: int
    total_pages: int

    @classmethod
    def create(cls, items: Sequence[T], total: int, page: int, page_size: int) -> "PaginatedResponse[T]":
        total_pages = math.ceil(total / page_size) if page_size > 0 else 1
        return cls(
            items=list(items),
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )
