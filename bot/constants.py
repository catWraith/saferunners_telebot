# Conversation state integers
ASK_LOCATION, ASK_TIME, ASK_CUSTOM_TIME = range(3)

# Keys for user_data / bot_data
UD_TZ = "tz"                          # per-user timezone name
UD_ACTIVE = "active_session"          # per-user session dict
UD_JOB = "deadline_job"               # per-user Job reference
BD_CONTACTS = "contacts_by_user"      # bot_data: owner_id (str) -> List[chat_id]
BD_BLACKLIST = "blacklist_by_user"    # bot_data: owner_id (str) -> Set[blocked_chat_id]