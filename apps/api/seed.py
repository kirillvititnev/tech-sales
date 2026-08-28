"""Seed demo categories and HOT product for local development."""

import asyncio
import secrets
from decimal import Decimal

from sqlalchemy import select

from apps.api.db import SessionLocal
from apps.api.models.catalog import Category, Product
from apps.api.models.user import User, UserRole


CATEGORIES = [
    ("smartphones", "Смартфоны", 10),
    ("apple", "Apple", 20),
    ("samsung", "Samsung", 30),
    ("dyson", "Dyson", 40),
    ("playstation", "PlayStation", 50),
    ("rayban", "Ray-Ban", 60),
    ("oculus", "Oculus", 70),
    ("hot", "HOT", 1),
]


async def seed() -> None:
    async with SessionLocal() as db:
        for slug, name, sort in CATEGORIES:
            exists = await db.execute(select(Category).where(Category.slug == slug))
            if not exists.scalar_one_or_none():
                db.add(Category(slug=slug, name=name, sort_order=sort))

        admin = await db.execute(select(User).where(User.email == "admin@whiteshop.local"))
        if not admin.scalar_one_or_none():
            from apps.api.config import get_settings

            settings = get_settings()
            password_hash = None
            if settings.admin_password:
                from passlib.context import CryptContext

                password_hash = CryptContext(schemes=["bcrypt"], deprecated="auto").hash(
                    settings.admin_password
                )
            db.add(
                User(
                    email="admin@whiteshop.local",
                    name="Admin",
                    role=UserRole.admin,
                    referral_code=f"ADM{secrets.token_hex(3).upper()}",
                    bonus_balance=0,
                    password_hash=password_hash,
                )
            )

        demo = await db.execute(select(Product).where(Product.slug == "iphone-16-pro-256"))
        if not demo.scalar_one_or_none():
            apple = await db.execute(select(Category).where(Category.slug == "apple"))
            apple_cat = apple.scalar_one()
            db.add(
                Product(
                    slug="iphone-16-pro-256",
                    title="iPhone 16 Pro 256GB",
                    brand="Apple",
                    category_id=apple_cat.id,
                    description="Демо-товар для локальной витрины White Shop.",
                    attributes={"storage": "256GB"},
                    cost_median=Decimal("98000"),
                    price=Decimal("108900"),
                    markup_percent=Decimal("10"),
                    is_manual=True,
                    is_hot=True,
                    is_published=True,
                )
            )

        await db.commit()
        print("Seed OK")


if __name__ == "__main__":
    asyncio.run(seed())
