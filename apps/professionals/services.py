from apps.audit.services import log_action


def create_professional(user, serializer):
    serializer.save()
    log_action(user, "create", "professional", serializer.instance.id)


def delete_professional(user, instance):
    log_action(user, "delete", "professional", instance.id)
    instance.delete()
