from django.urls import path, include, re_path
from . import views
from articles.views import ArticleListView, ArticleDetailView

urlpatterns = [
    path('', ArticleListView.as_view(), name="articles-page"),
    path("lazy_load/", views.lazy_load_articles, name='lazy_load_articles'),
    path("search/", views.search_articles, name='search_articles'),
    path("<str:category>/<str:slug>/", ArticleDetailView.as_view(), name="article-page"),
    path("<str:category>/", views.article_filter_view, name="category-page"),
]
