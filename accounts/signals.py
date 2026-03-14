from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from accounts.models import Profile
from apply.models import Application
from pulses.models import Pulse


def _delete_field_file(file_field):
    if not file_field:
        return
    file_name = getattr(file_field, "name", "")
    if not file_name:
        return
    storage = file_field.storage
    if storage.exists(file_name):
        storage.delete(file_name)


def _delete_previous_file_on_change(model_cls, instance, field_name):
    if not instance.pk:
        return
    try:
        previous = model_cls.objects.get(pk=instance.pk)
    except model_cls.DoesNotExist:
        return
    previous_file = getattr(previous, field_name)
    current_file = getattr(instance, field_name)
    previous_name = getattr(previous_file, "name", "")
    current_name = getattr(current_file, "name", "")
    if previous_name and previous_name != current_name:
        _delete_field_file(previous_file)


@receiver(pre_save, sender=Profile)
def cleanup_replaced_profile_picture(sender, instance, **kwargs):
    _delete_previous_file_on_change(Profile, instance, "profile_picture")


@receiver(pre_save, sender=Profile)
def cleanup_replaced_profile_resume(sender, instance, **kwargs):
    _delete_previous_file_on_change(Profile, instance, "resume_file")


@receiver(post_delete, sender=Profile)
def cleanup_deleted_profile_picture(sender, instance, **kwargs):
    _delete_field_file(instance.profile_picture)


@receiver(post_delete, sender=Profile)
def cleanup_deleted_profile_resume(sender, instance, **kwargs):
    _delete_field_file(instance.resume_file)


@receiver(pre_save, sender=Application)
def cleanup_replaced_resume(sender, instance, **kwargs):
    _delete_previous_file_on_change(Application, instance, "resume_file")


@receiver(post_delete, sender=Application)
def cleanup_deleted_resume(sender, instance, **kwargs):
    _delete_field_file(instance.resume_file)


@receiver(pre_save, sender=Pulse)
def cleanup_replaced_pulse_video(sender, instance, **kwargs):
    _delete_previous_file_on_change(Pulse, instance, "video")


@receiver(post_delete, sender=Pulse)
def cleanup_deleted_pulse_video(sender, instance, **kwargs):
    _delete_field_file(instance.video)
