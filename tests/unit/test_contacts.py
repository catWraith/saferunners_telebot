from bot.utils.contacts import add_contact, list_contacts, remove_contact_everywhere
from bot.constants import BD_CONTACTS


def test_add_and_list_contacts():
    bot_data = {}
    add_contact(bot_data, 111, 200)
    add_contact(bot_data, 111, 201)
    add_contact(bot_data, 111, 200)  # dedupe
    ids = list_contacts(bot_data, 111)
    assert sorted(ids) == [200, 201]
    assert BD_CONTACTS in bot_data


def test_remove_contact_everywhere():
    bot_data = {BD_CONTACTS: {"111": [1, 2], "222": [2, 3]}}
    removed = remove_contact_everywhere(bot_data, 2)
    assert removed == 2
    assert list_contacts(bot_data, 111) == [1]
    assert list_contacts(bot_data, 222) == [3]
