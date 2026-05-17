"""Billing and invoicing."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InvoiceLine:
    description: str
    amount_cents: int


@dataclass
class Invoice:
    customer_id: str
    lines: list[InvoiceLine] = field(default_factory=list)
