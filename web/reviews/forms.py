from django.forms import ModelForm, TextInput, Textarea
from .models import *


class ReviewForm(ModelForm):
    class Meta:
        model = Review
        fields = ["title", "content"]
        widgets = {
            "title": TextInput(attrs={"placeholder": "Заголовок", "required": "required"}),
            "content": Textarea(attrs={"placeholder": "Распишите ваш отзыв здесь...", "cols": 30, "rows": 10,
                                       "required": "required"}),
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": Textarea(
                attrs={"placeholder": "Ваш комментарий...", "cols": 30, "rows": 10, "required": "required"}),
        }
