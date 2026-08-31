"""Sync Telegram folder channels → supplier offers → storefront products."""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from telethon.tl.types import InputPeerChannel

from apps.api.db import SessionLocal
from apps.api.models.catalog import (
    Category,
    ChannelStatus,
    Product,
    ProductOffer,
    SupplierChannel,
)
from apps.api.services.admin_alerts import is_price_jump, notify_admin_ops
from apps.api.services.customer_notify import customer_telegrams_for, deliver_customer_telegrams
from apps.api.services.favorite_alerts import notify_favorite_watchers, watches_for_update
from apps.api.services.pricing import (
    SupplierBid,
    quote_storefront,
    receipt_payload,
    resolve_markup,
    with_price_receipt,
)
from apps.worker.config import get_worker_settings
from apps.worker.folders import get_folder_channels
from apps.worker.offer_identity import OfferKind, classify_offer, min_price_for_kind
from apps.worker.parser import normalize_title, parse_price_text
from apps.worker.reject_stats import note_reject, sync_stats_for_store
from apps.worker.tg import make_telegram_client
from apps.worker.attachments import message_price_texts

logger = logging.getLogger(__name__)


def make_slug(identity_key: str, display_title: str) -> str:
    normalized = normalize_title(display_title)
    ascii_part = unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_part).strip("-")[:60] or "item"
    digest = identity_key[:8]
    return f"{base}-{digest}"


def external_key(raw_title: str, message_id: int | None = None) -> str:
    seed = f"{normalize_title(raw_title)}|{message_id or ''}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()


async def ensure_schema(session: AsyncSession) -> None:
    await session.execute(
        text("ALTER TABLE supplier_channels ADD COLUMN IF NOT EXISTS folder_label VARCHAR(128)")
    )
    await session.execute(
        text(
            "ALTER TABLE store_settings "
            "ADD COLUMN IF NOT EXISTS markup_rules JSONB NOT NULL DEFAULT '[]'::jsonb"
        )
    )
    await session.execute(
        text(
            "ALTER TABLE store_settings "
            "ADD COLUMN IF NOT EXISTS last_sync_stats JSONB NOT NULL DEFAULT '{}'::jsonb"
        )
    )
    await session.execute(
        text(
            "ALTER TABLE supplier_channels "
            "ADD COLUMN IF NOT EXISTS counts_toward_price BOOLEAN NOT NULL DEFAULT true"
        )
    )
    await session.commit()


async def upsert_channel(
    session: AsyncSession,
    *,
    telegram_id: str,
    title: str,
    username: str | None,
    is_private: bool,
    folder_label: str,
) -> SupplierChannel:
    result = await session.execute(
        select(SupplierChannel).where(SupplierChannel.telegram_id == telegram_id)
    )
    channel = result.scalar_one_or_none()
    if channel is None:
        channel = SupplierChannel(
            telegram_id=telegram_id,
            title=title,
            username=username,
            is_private=is_private,
            folder_label=folder_label,
            status=ChannelStatus.active,
        )
        session.add(channel)
        await session.flush()
    else:
        channel.title = title
        channel.username = username
        channel.is_private = is_private
        channel.folder_label = folder_label
        channel.status = ChannelStatus.active
    return channel


async def sync_folder(
    folder_name: str = "Apple",
    *,
    messages_per_channel: int = 100,
    category_slug: str = "apple",
    channel_title: str | None = None,
    telegram_id: str | None = None,
) -> dict[str, int]:
    worker_settings = get_worker_settings()
    markup = worker_settings.default_markup_percent
    markup_rules: list = []
    round_to = worker_settings.price_round_to
    min_price = Decimal(worker_settings.min_offer_price_rub)

    stats = {
        "channels": 0,
        "messages": 0,
        "lines": 0,
        "offers": 0,
        "products": 0,
        "rejected": 0,
        "errors": 0,
        "attachments": 0,
        "photos": 0,
        "favorite_notices": 0,
        "quarantined": 0,
        "reject_reasons": {},
        "reject_samples": {},
    }
    parse_errors: list[tuple[str, str]] = []
    price_jumps: list[tuple[str, Decimal, Decimal]] = []

    async def _flush_alerts() -> None:
        try:
            await notify_admin_ops(folder_name, parse_errors, price_jumps)
        except Exception:  # noqa: BLE001
            logger.exception("Admin ops alert failed")

    client = make_telegram_client()
    async with client:
        folder_channels = await get_folder_channels(client, folder_name)
        if telegram_id:
            folder_channels = [fc for fc in folder_channels if str(fc.telegram_id) == str(telegram_id)]
        elif channel_title:
            needle = channel_title.casefold()
            folder_channels = [fc for fc in folder_channels if needle in fc.title.casefold()]
        logger.info(
            "Folder '%s': %s channels (filter title=%r id=%r)",
            folder_name,
            len(folder_channels),
            channel_title,
            telegram_id,
        )

        async with SessionLocal() as session:
            await ensure_schema(session)
            try:
                from apps.api.services.admin_catalog import get_or_create_store_settings

                store = await get_or_create_store_settings(session)
                markup = float(store.default_markup_percent)
                markup_rules = list(store.markup_rules or [])
                round_to = int(store.price_round_to)
                await session.commit()
            except Exception:  # noqa: BLE001
                logger.warning("StoreSettings unavailable — using env markup defaults")
                await session.rollback()
                await ensure_schema(session)
            result = await session.execute(select(Category).where(Category.slug == category_slug))
            category = result.scalar_one_or_none()
            if category is None:
                category = Category(
                    slug=category_slug,
                    name=folder_name,
                    sort_order=20,
                    is_active=True,
                )
                session.add(category)
                await session.flush()

            display_meta: dict[str, dict] = {}
            synced_channel_ids: list = []
            favorite_events: list = []
            channel_counts_price: dict[uuid.UUID, bool] = {}
            channel_title_by_id: dict[uuid.UUID, str] = {}

            for fc in folder_channels:
                channel: SupplierChannel | None = None
                try:
                    channel = await upsert_channel(
                        session,
                        telegram_id=fc.telegram_id,
                        title=fc.title,
                        username=fc.username,
                        is_private=fc.is_private,
                        folder_label=folder_name,
                    )
                    synced_channel_ids.append(channel.id)
                    channel_counts_price[channel.id] = bool(getattr(channel, "counts_toward_price", True))
                    channel_title_by_id[channel.id] = channel.title or fc.title or "?"
                    stats["channels"] += 1

                    entity = await client.get_entity(
                        InputPeerChannel(fc.channel_id, fc.access_hash)
                    )
                    messages = await client.get_messages(entity, limit=messages_per_channel)
                    active_keys: set[str] = set()

                    for msg in messages:
                        doc = msg.document
                        blobs = await message_price_texts(
                            caption=msg.message,
                            document=doc,
                            size=getattr(doc, "size", None) if doc is not None else None,
                            mime=getattr(doc, "mime_type", None) if doc is not None else None,
                            download=lambda m=msg: client.download_media(m, file=bytes),
                        )
                        if not blobs:
                            continue
                        stats["messages"] += 1
                        if doc is not None:
                            stats["attachments"] += 1
                        for text in blobs:
                            for line in parse_price_text(text):
                                stats["lines"] += 1
                                if line.price < min_price:
                                    note_reject(
                                        stats,
                                        "below_min_price",
                                        title=line.title,
                                    )
                                    continue
                                identity = classify_offer(line.title, section=line.section)
                                # title already has careful section glue from parser
                                if not identity.publish or not identity.identity_key:
                                    note_reject(
                                        stats,
                                        identity.reject_reason or "unpublished_identity",
                                        title=line.title,
                                    )
                                    continue
                                floor = max(min_price, Decimal(min_price_for_kind(identity.kind)))
                                if line.price < floor:
                                    note_reject(
                                        stats,
                                        f"below_kind_floor:{identity.kind.value}",
                                        title=line.title,
                                    )
                                    continue

                                ext = external_key(line.title, msg.id)
                                active_keys.add(ext)
                                meta = display_meta.setdefault(
                                    identity.identity_key,
                                    {
                                        "title": identity.display_title,
                                        "brand": identity.brand,
                                        "device_category": identity.device_category,
                                        "device_name": identity.device_name,
                                        "config": identity.config,
                                        "model": identity.model,
                                        "storage": identity.storage,
                                        "color": identity.color,
                                        "sim": identity.sim,
                                        "ram": identity.ram,
                                        "regions": set(),
                                        "kind": identity.kind.value,
                                        "band": identity.band,
                                        "model_code": identity.model_code,
                                    },
                                )
                                if identity.region:
                                    meta["regions"].add(identity.region)

                                existing = await session.execute(
                                    select(ProductOffer).where(
                                        ProductOffer.channel_id == channel.id,
                                        ProductOffer.external_key == ext,
                                    )
                                )
                                offer = existing.scalar_one_or_none()
                                payload = {
                                    "message_id": msg.id,
                                    "date": msg.date.isoformat() if msg.date else None,
                                    "raw": line.raw,
                                    "section": line.section,
                                    "identity_key": identity.identity_key,
                                    "sim": identity.sim,
                                    "region": identity.region,
                                    "model": identity.model,
                                }
                                if offer is None:
                                    session.add(
                                        ProductOffer(
                                            channel_id=channel.id,
                                            external_key=ext,
                                            raw_title=line.title,
                                            raw_price=line.price,
                                            currency="RUB",
                                            source_message_id=str(msg.id),
                                            raw_payload=payload,
                                            is_active=True,
                                        )
                                    )
                                else:
                                    offer.raw_title = line.title
                                    offer.raw_price = line.price
                                    offer.source_message_id = str(msg.id)
                                    offer.raw_payload = payload
                                    offer.is_active = True
                                    offer.parsed_at = datetime.now(timezone.utc)
                                stats["offers"] += 1

                    if active_keys:
                        all_offers = await session.execute(
                            select(ProductOffer).where(
                                ProductOffer.channel_id == channel.id,
                                ProductOffer.is_active.is_(True),
                            )
                        )
                        for offer in all_offers.scalars().all():
                            if offer.external_key not in active_keys:
                                offer.is_active = False

                    channel.last_parsed_at = datetime.now(timezone.utc)
                    channel.last_error = None
                    await session.commit()
                except Exception as exc:  # noqa: BLE001
                    stats["errors"] += 1
                    logger.exception("Channel sync failed: %s", fc.title)
                    await session.rollback()
                    if channel is not None:
                        try:
                            channel = await session.merge(channel)
                            channel.last_error = str(exc)[:1000]
                            channel.status = ChannelStatus.error
                            await session.commit()
                        except Exception:  # noqa: BLE001
                            await session.rollback()
                    parse_errors.append((fc.title, str(exc)[:1000]))

            channel_ids = (
                synced_channel_ids
                if (telegram_id or channel_title) and synced_channel_ids
                else (
                    await session.execute(
                        select(SupplierChannel.id).where(SupplierChannel.folder_label == folder_name)
                    )
                ).scalars().all()
            )

            if not channel_ids:
                logger.warning("No channels stored for folder %s", folder_name)
                await _flush_alerts()
                return stats

            offers = list(
                (
                    await session.execute(
                        select(ProductOffer).where(
                            ProductOffer.channel_id.in_(channel_ids),
                            ProductOffer.is_active.is_(True),
                        )
                    )
                )
                .scalars()
                .all()
            )
            by_key: dict[str, list[ProductOffer]] = defaultdict(list)
            for offer in offers:
                section = (offer.raw_payload or {}).get("section")
                identity = classify_offer(
                    offer.raw_title,
                    section=section if isinstance(section, str) else None,
                )
                if not identity.publish or not identity.identity_key:
                    continue
                key = identity.identity_key
                meta = display_meta.setdefault(
                    key,
                    {
                        "title": identity.display_title,
                        "brand": identity.brand,
                        "device_category": identity.device_category,
                        "device_name": identity.device_name,
                        "config": identity.config,
                        "model": identity.model,
                        "storage": identity.storage,
                        "color": identity.color,
                        "sim": identity.sim,
                        "ram": identity.ram,
                        "band": identity.band,
                        "model_code": identity.model_code,
                        "regions": set(),
                        "kind": identity.kind.value,
                    },
                )
                if identity.region:
                    meta["regions"].add(identity.region)
                meta.update(
                    {
                        "title": identity.display_title,
                        "brand": identity.brand,
                        "device_category": identity.device_category,
                        "device_name": identity.device_name,
                        "config": identity.config,
                        "model": identity.model,
                        "storage": identity.storage,
                        "color": identity.color,
                        "sim": identity.sim,
                        "ram": identity.ram,
                        "band": identity.band,
                        "model_code": identity.model_code,
                        "kind": identity.kind.value,
                    }
                )
                by_key[key].append(offer)

            publish_kinds = {
                OfferKind.iphone.value,
                OfferKind.apple_other.value,
                OfferKind.samsung.value,
                OfferKind.sony.value,
                OfferKind.insta360.value,
                OfferKind.android.value,
                OfferKind.gaming.value,
                OfferKind.dyson.value,
                OfferKind.yandex.value,
                OfferKind.meta.value,
                OfferKind.audio.value,
                OfferKind.camera.value,
            }
            seen_product_ids: set[uuid.UUID] = set()
            skip_group_reasons: dict[str, int] = stats.setdefault("skip_group_reasons", {})
            for key, offer_list in by_key.items():
                if not key:
                    continue
                meta = display_meta.get(key) or {}
                title = meta.get("title")
                kind = meta.get("kind")
                brand = meta.get("brand") or None
                if not title or kind not in publish_kinds or not brand:
                    reason = (
                        "missing_title"
                        if not title
                        else "kind_not_published"
                        if kind not in publish_kinds
                        else "missing_brand"
                    )
                    skip_group_reasons[reason] = int(skip_group_reasons.get(reason, 0)) + 1
                    continue
                try:
                    kind_enum = OfferKind(kind)
                except ValueError:
                    skip_group_reasons["bad_kind"] = int(skip_group_reasons.get("bad_kind", 0)) + 1
                    continue
                floor = Decimal(max(int(min_price), min_price_for_kind(kind_enum)))
                prices = [
                    SupplierBid(
                        Decimal(o.raw_price),
                        channel_title_by_id.get(o.channel_id)
                        or (o.channel.title if getattr(o, "channel", None) else None)
                        or "?",
                    )
                    for o in offer_list
                    if Decimal(o.raw_price) >= floor
                    and channel_counts_price.get(o.channel_id, True)
                ]
                if not prices:
                    skip_group_reasons["no_priced_offers"] = int(
                        skip_group_reasons.get("no_priced_offers", 0)
                    ) + 1
                    continue
                markup_pct = resolve_markup(
                    markup,
                    markup_rules,
                    brand=brand,
                    category=str(meta.get("device_category") or "") or None,
                    kind=kind,
                )
                quote = quote_storefront(prices, markup_percent=markup_pct, round_to=round_to)
                cost, price = quote.cost_median, quote.price
                if cost is None or price is None or cost < floor:
                    skip_group_reasons["quote_failed"] = int(
                        skip_group_reasons.get("quote_failed", 0)
                    ) + 1
                    continue
                stats["quarantined"] += len(quote.quarantined)
                receipt = receipt_payload(quote, markup_pct, round_to)
                slug = make_slug(key, title)
                regions = sorted(meta.get("regions") or [])
                attrs = {
                    "norm_key": key,
                    "folder": folder_name,
                    "kind": kind,
                    "device_category": meta.get("device_category") or "",
                    "device_name": meta.get("device_name") or title,
                    "config": meta.get("config") or "",
                    "model": meta.get("model"),
                    "storage": meta.get("storage"),
                    "color": meta.get("color"),
                    "sim": meta.get("sim"),
                    "ram": meta.get("ram"),
                    "band": meta.get("band") or "",
                    "model_code": meta.get("model_code") or "",
                    "condition": (
                        "asis+"
                        if str(meta.get("device_category") or "").endswith("ASIS+")
                        else "asis"
                        if str(meta.get("device_category") or "").endswith("ASIS")
                        else ""
                    ),
                    "region_samples": regions,
                }
                attrs = with_price_receipt(attrs, receipt)

                existing = await session.execute(select(Product).where(Product.slug == slug))
                product = existing.scalar_one_or_none()
                if product is None:
                    linked = next((o.product_id for o in offer_list if o.product_id), None)
                    if linked:
                        product = await session.get(Product, linked)

                if product is None:
                    product = Product(
                        slug=slug,
                        title=title,
                        brand=brand,
                        category_id=category.id,
                        attributes=attrs,
                        cost_median=cost,
                        price=price,
                        markup_percent=Decimal(str(markup_pct)),
                        is_manual=False,
                        is_hot=False,
                        is_published=True,
                    )
                    session.add(product)
                    await session.flush()
                    stats["products"] += 1
                else:
                    old_price = product.price
                    was_published = bool(product.is_published)
                    product.title = title
                    product.brand = brand or product.brand
                    product.category_id = category.id
                    product.cost_median = cost
                    product.price = price
                    product.markup_percent = Decimal(str(markup_pct))
                    product.is_published = True
                    product.attributes = attrs
                    flag_modified(product, "attributes")
                    stats["products"] += 1
                    if is_price_jump(
                        Decimal(str(old_price)) if old_price is not None else None,
                        price,
                    ):
                        price_jumps.append((title, Decimal(str(old_price)), price))
                    favorite_events.extend(
                        watches_for_update(
                            product_id=product.id,
                            title=title,
                            was_published=was_published,
                            old_price=Decimal(str(old_price)) if old_price is not None else None,
                            new_price=price,
                        )
                    )

                seen_product_ids.add(product.id)
                for offer in offer_list:
                    offer.product_id = product.id

            stale = await session.execute(
                select(Product).where(
                    Product.is_manual.is_(False),
                    Product.attributes.contains({"folder": folder_name}),
                )
            )
            # Filtered single-channel sync must not unpublish the rest of the folder.
            if not (telegram_id or channel_title):
                for product in stale.scalars().all():
                    if product.id not in seen_product_ids:
                        product.is_published = False

            try:
                notices = await notify_favorite_watchers(session, favorite_events)
                stats["favorite_notices"] = len(notices)
                jobs = await customer_telegrams_for(session, notices)
            except Exception:  # noqa: BLE001
                logger.exception("Favorite watch notices failed")
                jobs = []
            try:
                from apps.api.services.admin_catalog import get_or_create_store_settings

                store = await get_or_create_store_settings(session)
                store.last_sync_stats = {
                    "folder": folder_name,
                    "finished_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    **sync_stats_for_store(stats),
                }
                flag_modified(store, "last_sync_stats")
            except Exception:  # noqa: BLE001
                logger.warning("Could not persist last_sync_stats")
            await session.commit()
            if jobs:
                try:
                    await deliver_customer_telegrams(jobs)
                except Exception:  # noqa: BLE001
                    logger.exception("Customer telegram favorite notices failed")

    await _flush_alerts()
    logger.info("Sync done: %s", stats)
    return stats


async def run_parse_cycle(folder_name: str | None = None) -> dict[str, int]:
    worker_settings = get_worker_settings()
    if not worker_settings.telegram_api_id or not worker_settings.telegram_api_hash:
        logger.warning("Telegram credentials missing — parse cycle skipped")
        return {"channels": 0, "lines": 0, "skipped": 1}

    folder = folder_name or "Apple"
    try:
        return await sync_folder(folder)
    except Exception as exc:
        logger.exception("Parse cycle failed")
        try:
            await notify_admin_ops(folder, [("цикл парсинга", str(exc)[:300])], [])
        except Exception:  # noqa: BLE001
            logger.exception("Admin ops alert failed")
        return {"channels": 0, "lines": 0, "skipped": 0, "errors": 1}
