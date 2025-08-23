from typing import Dict, Any, List
from bot.constants import BD_CONTACTS


def _ensure(bot_data: Dict[str, Any], owner_id: int) -> List[int]:
    mapping = bot_data.setdefault(BD_CONTACTS, {})
    return mapping.setdefault(str(owner_id), [])


def add_contact(bot_data: Dict[str, Any], owner_id: int, contact_chat_id: int) -> None:
    lst = _ensure(bot_data, owner_id)
    if contact_chat_id not in lst:
        lst.append(contact_chat_id)


def list_contacts(bot_data: Dict[str, Any], owner_id: int) -> List[int]:
    return list(_ensure(bot_data, owner_id))


def remove_contact_everywhere(bot_data: Dict[str, Any], chat_id: int) -> int:
    mapping = bot_data.setdefault(BD_CONTACTS, {})
    removed = 0
    for _, lst in mapping.items():
        if chat_id in lst:
            lst.remove(chat_id)
            removed += 1
    return removed
