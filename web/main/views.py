from django.shortcuts import render


from articles.models import Article

from core.views import catch_error


@catch_error
def index(request):
    context = {}
    context["articles_list"] = Article.objects.all().order_by("-date")[:6]
    return render(request, "main/main.html", context)


def error_page(request):

    return render(request, "main/error-page.html")
