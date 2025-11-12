from django import forms
from django_filters import FilterSet, MultipleChoiceFilter, ModelMultipleChoiceFilter
from .models import *


class ReviewFilter(FilterSet):
    type = MultipleChoiceFilter(field_name='type', choices=Review.TYPES_CHOICES, widget=forms.CheckboxSelectMultiple)
    status = ModelMultipleChoiceFilter(widget=forms.CheckboxSelectMultiple, field_name='status', to_field_name="slug",
                                       queryset=Status.objects.all())

    class Meta:
        model = Review
        fields = ['status']
