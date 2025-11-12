from django.db import models
from django.db.models.signals import pre_save
from tinymce.models import HTMLField

from WealthView.utils import unique_slug_generator, path_and_rename

# Create your models here.

"""
...................................................
.................... Category model ...............
...................................................
"""


class Category(models.Model):

    title = models.CharField(max_length=64, null=True, help_text="Название категории")
    parent = models.ForeignKey('self', blank=True, null=True, related_name='children', on_delete=models.CASCADE,
                               help_text="Родительская категория (если имеется)")
    slug = models.SlugField(max_length=128, unique=True, blank=True,
                            help_text="Генерируется автоматически по заголовку")

    class Meta:
        ordering = ("title",)
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        full_path = [self.title]
        k = self.parent
        while k is not None:
            full_path.append(k.title)
            k = k.parent
        return '\\'.join(full_path[::-1])


"""
...................................................
.................... Article model ................
...................................................
"""


class Article(models.Model):
    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'

    # TODO: published?
    title = models.CharField(max_length=128, help_text="Заголовок статьи")
    description = models.TextField(help_text="Описание статьи", blank=True)
    slug = models.SlugField(max_length=128, unique=True, blank=True,
                            help_text="Генерируется автоматически по заголовку")
    category = models.ForeignKey(Category, on_delete=models.PROTECT,
                                 help_text="Подкатегория для статьи")
    thumbnail = models.ImageField(upload_to=path_and_rename, blank=True,
                                  default="media/img/articles/default_thumb.png",
                                  help_text="Превью-изображение для статьи.")
    # content = models.TextField(help_text="Содержание статьи")
    content = HTMLField(help_text="Содержание статьи")
    date = models.DateTimeField()
    seo_title = models.CharField(max_length=128, help_text="Заголовок статьи для SEO", blank=True)

    def __str__(self):
        return "#{id} ({title})...".format(id=self.id, title=self.title[:16])


def slug_save(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = unique_slug_generator(instance, instance.title)


def slug_category_save(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = unique_slug_generator(instance, instance.title)


pre_save.connect(slug_save, sender=Article)
pre_save.connect(slug_category_save, sender=Category)