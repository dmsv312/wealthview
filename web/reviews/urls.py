from django.urls import path
from . import views

urlpatterns = [
    path('', views.ReviewListView.as_view(), name="reviews-page"),
    path('<int:pk>/like/', views.like_review, name="like-review"),
    path('<int:pk>/dislike/', views.dislike_review, name="dislike-review"),
    path('send_review/', views.send_review, name="send-review"),
    path('add_comment/', views.add_comment, name="add-comment"),
    path("lazy_load/", views.lazy_load_reviews, name='lazy_load_reviews'),
]
