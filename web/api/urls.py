from rest_framework import routers

from account.api.views import ProfileTelegramViewset
from .views import *

router = routers.DefaultRouter()
router.register(r'assets', AssetViewset)
router.register(r'profile', ProfileTelegramViewset)


urlpatterns = []

urlpatterns += router.urls
