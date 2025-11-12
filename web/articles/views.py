from django.db.models import Q
from django.shortcuts import redirect
from django.views.generic import DetailView

from articles.filters import ArticleFilter
from core.views import BaseCatchErrorView, catch_error
from core.utils.lazy_pagination import PaginateAbleView, get_page_processed
from .models import Article, Category
from django_filters.views import FilterView
from django.shortcuts import render

TEMPLATE_LIST = "articles/articles_page.html"
TEMPLATE_DETAIL = "articles/article_page.html"
TEMPLATE_FILTER = "articles/categories.html"
TEMPLATE_ARTICLES_GENERATOR = 'articles/includes/articles.html',
# Create your views here.

"""
..............................................................................................................
................................................ ARTICLES (MANY) .............................................
..............................................................................................................
"""
"""
...................................................
.................... ArticleListView ..............
...................................................
"""


class ArticleListView(FilterView, PaginateAbleView, BaseCatchErrorView):
    model = Article
    filterset_class = ArticleFilter
    template_name = TEMPLATE_LIST
    per_page = 2

    class Meta:
        paginator = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        response = get_page_processed(request=self.request,
                                      limit=self.per_page,
                                      list_view=self.__class__,
                                      instance_filter=self.filterset_class)
        context['articles_data'] = response["instances"]
        context['has_next'] = response["has_next"]
        context['categories'] = Category.objects.filter(parent=None)
        return context


"""
...................................................
.................... LazyLoad .....................
...................................................
"""


@catch_error
def lazy_load_articles(request):
    from core.utils.lazy_pagination import lazy_load_instances
    return lazy_load_instances(request, ArticleListView.get_paginator(), TEMPLATE_ARTICLES_GENERATOR, "articles")


"""
...................................................
.................... Search_Articles ..............
...................................................
"""


@catch_error
def search_articles(request):
    from django.shortcuts import render

    template_name = TEMPLATE_LIST
    if request.POST:
        search_req = request.POST["search_req"]
        # print(search_req)
        if search_req:
            # articles_list = Article.objects.filter(title__contains=search_req).order_by("-date")
            # print(Article.objects.filter(title__icontains=search_reqrt))
            articles_list = Article.objects.filter(
                Q(title__icontains=search_req) | Q(content__icontains=search_req)
            ).order_by("-date")
            # print(articles_list)
            return render(request, template_name, {"articles_data": articles_list, "search_req": search_req})
        else:
            return redirect("/articles/")
    return render(request, template_name)


"""
..............................................................................................................
................................................ ARTICLE (SINGLE) ............................................
..............................................................................................................
"""
"""
...................................................
.................... ArticleDetailView ............
...................................................
"""


class ArticleDetailView(DetailView, BaseCatchErrorView):
    model = Article
    template_name = TEMPLATE_DETAIL
    filterset_class = ArticleFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(parent=None)
        context['related_articles'] = self.get_related(count=3)
        return context

    def get_related(self, count):
        cur = self.get_object()
        related_articles = []
        for article in Article.objects.all():
            if len(related_articles) == count:
                break
            elif article.category.title == cur.category.title and article != cur:
                related_articles.append(article)
        return related_articles


@catch_error
def article_detail_view(request, pk):
    """Не встроенная view для детального отображения статьи"""
    article = Article.objects.get(pk=pk)

    related_articles = []
    for post in Article.objects.all():
        if len(related_articles) == 3:
            break
        elif post.category.id == article.category.id and post != article:
            related_articles.append(post)

    context = {'article': article,
               'categories': Category.objects.filter(parent=None),
               'related_articles': related_articles}

    return render(request, TEMPLATE_DETAIL, context)


@catch_error
def article_filter_view(request, category):
    """view для фильтра статей"""
    filter_category = Category.objects.get(slug=category)
    articles_data = Article.objects.filter(category=filter_category)
    categories = Category.objects.all()
    return render(request, TEMPLATE_FILTER, {'category': category, 'articles_data': articles_data,
                                             'categories': categories, 'filter_category': filter_category})
