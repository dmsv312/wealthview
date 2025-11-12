import os
from uuid import uuid4

import transliterate
from django.utils.text import slugify


def slugify_with_translit(title):
    transliterated = transliterate.translit(title, 'ru', reversed=True)
    return slugify(transliterated, allow_unicode=True)


def unique_slug_generator(model_instance, title):
    slug = slugify_with_translit(title)
    model_class = model_instance.__class__

    object_pk = 0
    while model_class._default_manager.filter(slug=slug).exists():
        object_pk += 1
        slug = f'{slug}-{object_pk}'

    return slug


def path_and_rename(instance, filename):
    upload_to = "media/img/articles/users"
    ext = filename.split('.')[-1]
    # get filename
    if instance.pk:
        filename = '{}.{}'.format(instance.pk, ext)
    else:
        # set filename as random string
        filename = '{}.{}'.format(uuid4().hex, ext)
    # return the whole path to the file
    return os.path.join(upload_to, filename)
