from galaxy.jobs.mapper import JobMappingException

DEFAULT_JOB_DESTINATION_ID = "local"

def has_license(user):
    user_group_assocs = user.groups or []
    user_has_license = 'have_license' in [user_group_assoc.group.name for user_group_assoc in user_group_assocs]
    if not user_has_license:
        raise JobMappingException("No license, no tool!")
    else:
        return DEFAULT_JOB_DESTINATION_ID

