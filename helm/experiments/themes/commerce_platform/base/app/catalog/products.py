"""Product catalog — search and listing agents may conflict."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Product:
    sku: str
    title: str
    price_cents: int


_CATALOG: list[Product] = []


def list_products() -> list[Product]:
    return list(_CATALOG)
