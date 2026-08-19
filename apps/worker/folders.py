"""Resolve Telegram chat folders (dialog filters)."""

from __future__ import annotations

from dataclasses import dataclass

from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.tl.types import Channel, DialogFilter, InputPeerChannel


@dataclass
class FolderChannel:
    telegram_id: str
    title: str
    username: str | None
    is_private: bool
    access_hash: int
    channel_id: int


def _filter_title(f: DialogFilter) -> str:
    title = f.title
    if hasattr(title, "text"):
        return title.text
    return str(title)


async def list_folder_names(client: TelegramClient) -> list[str]:
    result = await client(GetDialogFiltersRequest())
    names: list[str] = []
    for f in result.filters:
        if isinstance(f, DialogFilter):
            names.append(_filter_title(f))
    return names


async def get_folder_channels(client: TelegramClient, folder_name: str) -> list[FolderChannel]:
    result = await client(GetDialogFiltersRequest())
    target: DialogFilter | None = None
    for f in result.filters:
        if isinstance(f, DialogFilter) and _filter_title(f) == folder_name:
            target = f
            break
    if target is None:
        available = await list_folder_names(client)
        raise ValueError(f"Folder '{folder_name}' not found. Available: {available}")

    peers = list(target.pinned_peers or []) + list(target.include_peers or [])
    seen: set[int] = set()
    channels: list[FolderChannel] = []
    for peer in peers:
        if not isinstance(peer, InputPeerChannel):
            continue
        if peer.channel_id in seen:
            continue
        seen.add(peer.channel_id)
        try:
            entity = await client.get_entity(peer)
        except Exception:
            continue
        if not isinstance(entity, Channel):
            continue
        username = getattr(entity, "username", None)
        channels.append(
            FolderChannel(
                telegram_id=str(entity.id),
                title=entity.title or username or str(entity.id),
                username=username,
                is_private=username is None,
                access_hash=peer.access_hash,
                channel_id=peer.channel_id,
            )
        )
    return channels
