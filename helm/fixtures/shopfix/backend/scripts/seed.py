"""Idempotent seed: 3 sellers, 18 listings."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Base, SessionLocal, engine
from app.models.listing import Listing
from app.models.user import User
from app.services.auth import hash_password

SELLERS = [
    ("weaver@shopfix.test", "Loom & Thread"),
    ("clay@shopfix.test", "Clay Studio"),
    ("ink@shopfix.test", "Ink & Paper"),
]

LISTINGS = [
    ("Handwoven scarf", 4500, "fashion"),
    ("Ceramic mug set", 3200, "home"),
    ("Letterpress cards", 1800, "paper"),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for email, name in SELLERS:
        if not db.query(User).filter_by(email=email).first():
            db.add(User(email=email, hashed_password=hash_password("demo1234"), display_name=name))
    db.commit()
    sellers = db.query(User).filter(User.email.like("%@shopfix.test")).all()
    for seller in sellers:
        for title, price, tag in LISTINGS:
            full_title = f"{title} — {seller.display_name}"
            if db.query(Listing).filter_by(seller_id=seller.id, title=full_title).first():
                continue
            db.add(
                Listing(
                    seller_id=seller.id,
                    title=full_title,
                    description=f"Sold by {seller.display_name}",
                    price_cents=price,
                    tags=tag,
                )
            )
    db.commit()
    db.close()
    print("Seeded ShopFix")


if __name__ == "__main__":
    main()
