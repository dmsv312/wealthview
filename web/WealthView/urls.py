"""WealthView URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.conf.urls import url
from django.urls import path, include
from django.views.static import serve

from WealthView import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('', include('auth_sys.urls')),
    path('account/', include('account.urls')),
    path('articles/', include('articles.urls')),
    path('backtest/', include('backtest.urls')),
    path('risk_profile/', include('rprofile.urls')),
    path('faq/', include('faq.urls')),
    # Пока решили не использовать данный функционал
    # path('reviews/', include('reviews.urls')),
    path('tinymce/', include('tinymce.urls')),
    url(r'^api/', include('api.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
   url(r'^staticfiles/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT, 'show_indexes': settings.DEBUG}),
   url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT, 'show_indexes': settings.DEBUG}),
]

# import debug_toolbar
# urlpatterns += [
#     path('__debug__/', include(debug_toolbar.urls)),
# ]
