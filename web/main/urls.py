from django.urls import path, include
from django.conf.urls import url, include
from . import views


urlpatterns = [
    # path('', views.index, name="index"),
    path('', views.index, name="main-page"),
    path('auth/', include('auth_sys.urls')),
    path('error-page/', views.error_page, name="error-page"),
]
