from django.urls import path

from . import views

urlpatterns = [
    path('', views.start, name="risk-page"),
    path('ajax/risk_profile_result/', views.risk_profile_result, name='ajax_text'),
]

