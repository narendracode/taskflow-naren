import math
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int
    page: int
    limit: int
    pages: int

    @classmethod
    def build(cls, data: list[T], total: int, page: int, limit: int) -> "PaginatedResponse[T]":
        pages = math.ceil(total / limit) if limit > 0 else 0
        return cls(data=data, total=total, page=page, limit=limit, pages=pages)


class AssigneeStats(BaseModel):
    name: str
    count: int


class StatsResponse(BaseModel):
    by_status: dict[str, int]
    by_assignee: dict[str, AssigneeStats | int]
