from django.db import models

# Create your models here.
"""
...................................................
.................... Country  .....................
...................................................
"""


class Country(models.Model):
    class Meta:
        verbose_name = "Страна"
        verbose_name_plural = "Страны"

    code = models.CharField(max_length=3, primary_key=True, unique=True, verbose_name="Код в базе данных")
    name = models.CharField(max_length=64, unique=True, null=True, verbose_name="Название страны")

    def save(self):
        self.code = self.code.upper()
        super(Country, self).save()

    def __str__(self):
        return self.name
