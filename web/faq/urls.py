from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name="faq-page"),
    path('send_form/', views.send_form, name="send_form"),
]