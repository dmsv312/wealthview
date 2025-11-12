from django.urls import path, re_path
from . import views, utils
from django.conf.urls import url
from account.views import change_password_success

urlpatterns = [
    path('login/', views.login_user, name="login"),
    path('logout/', views.logout_user, name="logout"),
    url(r'^signup/$', views.signup_user, name='signup'),
    url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,50}-[0-9A-Za-z]{1,50})/$',
        views.activate, name='activate'),
    url(r'^forget_password/$', views.forget_password, name='forget_password'),
    path('ajax/is_exist_username/', utils.is_exist_username, name='is_exist_username'),
    path('ajax/is_exist_email/', utils.is_exist_email, name='is_exist_email'),
    path('change_password_success/', change_password_success, name="change_password_success"),
]
