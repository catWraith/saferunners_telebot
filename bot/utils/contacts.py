from typing import Dict, Any, List
from bot.constants import BD_CONTACTS, BD_BLACKLIST


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

def remove_contact(bot_data: Dict[str, Any], owner_id: int, contact_chat_id: int) -> bool:
    lst = _ensure(bot_data, owner_id)
    if contact_chat_id in lst:
        lst.remove(contact_chat_id)
        return True
    return False

# -------- Blacklist (contacts control who can alert them) --------
def _bl_map(bot_data: Dict[str, Any]) -> Dict[str, List[int]]:
    return bot_data.setdefault(BD_BLACKLIST, {})

def blacklist_add(bot_data: Dict[str, Any], contact_id: int, runner_id: int) -> None:
    bl = _bl_map(bot_data).setdefault(str(contact_id), [])
    if runner_id not in bl:
        bl.append(runner_id)

def blacklist_remove(bot_data: Dict[str, Any], contact_id: int, runner_id: int) -> bool:
    bl = _bl_map(bot_data).setdefault(str(contact_id), [])
    if runner_id in bl:
        bl.remove(runner_id)
        return True
    return False

def blacklist_list(bot_data: Dict[str, Any], contact_id: int) -> List[int]:
    return list(_bl_map(bot_data).get(str(contact_id), []))