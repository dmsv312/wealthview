from django.contrib.auth.models import User
from django.db import models


# Create your models here.
# TODO: Own User
# user = User.objects.create_user(username='Jackie',
#                                  email='jlennon@beatles.com',
#                                  password='jackietest')
# class Profile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     email = models.TextField(max_length=500, blank=True)
#     location = models.CharField(max_length=30, blank=True)
#     birth_date = models.DateField(null=True, blank=True)
