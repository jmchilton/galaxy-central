
LICENSED_TOOLS = ["cat1"]


def has_license(context, tool):
    if tool.id not in LICENSED_TOOLS:
        return True
    user = context.trans.user
    user_group_assocs = user.groups or []
    user_has_license = 'have_license' in [user_group_assoc.group.name for user_group_assoc in user_group_assocs]
    return user_has_license
