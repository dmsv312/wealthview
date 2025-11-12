from django import template
from django.contrib.auth.models import User

from reviews.models import Review

register = template.Library()


@register.simple_tag
def is_liked(review: Review, user: User):
    print("IS LIKED???")
    return review.likes.filter(id=user.id).exists()
