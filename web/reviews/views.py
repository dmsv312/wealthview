# -*- coding: utf-8 -*-
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django_filters.views import FilterView

from core.views import catch_error
from core.utils.lazy_pagination import PaginateAbleView, get_page_processed
from query_tools.filters import DateFilter
from .forms import CommentForm, ReviewForm
from .filters import ReviewFilter
from .models import Review, Comment, Status

# Create your views here.
TEMPLATE_LIST_DETAIL = "reviews/reviews_page.html"
TEMPLATE_REVIEWS_GENERATOR = 'reviews/includes/reviews.html',

"""
..............................................................................................................
................................................ REVIEWS .....................................................
..............................................................................................................
"""


class ReviewListView(FilterView, PaginateAbleView):
    model = Review
    filterset_class = ReviewFilter
    template_name = TEMPLATE_LIST_DETAIL
    per_page = 3

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        response = get_page_processed(request=self.request,
                                      limit=self.per_page,
                                      list_view=self.__class__,
                                      instance_filter=self.filterset_class)
        # package response
        context['reviews_data'] = get_reviews_data(response["instances"], self.request.user)
        context['has_next'] = response["has_next"]
        context['comment_form'] = CommentForm()
        context['review_form'] = ReviewForm()
        context['statuses'] = get_statuses_data()
        context['published_reviews_count'] = sum([x[-1] for x in context["statuses"]])
        return context


def get_statuses_data():
    statuses = Status.objects.all()
    data = []
    for status in statuses:
        count = Review.objects.filter(status=status, pub_state="PB").count()
        data.append((status.slug, status.title, count))
    return data


def get_reviews_data(reviews, user):
    data = []
    for review in reviews:
        data.append((
            review,
            review.is_liked(user),
            review.is_disliked(user),
            review.is_my(user)
        ))

    return data


"""
...................................................
.................... LazyLoad .....................
...................................................
"""


def lazy_load_reviews(request):
    from core.utils.lazy_pagination import lazy_load_instances
    return lazy_load_instances(request, ReviewListView.get_paginator(),
                               instances_generator_template=TEMPLATE_REVIEWS_GENERATOR,
                               instances_name="reviews",
                               instance_data_generator=get_reviews_data,
                               extra_data_for_render={"comment_form": CommentForm()})


"""
..............................................................................................................
................................................ FUNCTIONALITY ...............................................
..............................................................................................................
"""
"""
...................................................
........................ Rating ...................
...................................................
"""


# @login_required
@catch_error
def like_review(request, pk):
    if request.is_ajax():
        review = Review.objects.get(pk=pk)
        author = request.user

        disliked_delta = 0
        is_rating_sort = False
        if review.is_liked(author):
            review.likes.remove(author)
            liked_delta = -1
        else:
            if review.is_disliked(author):
                review.dislikes.remove(author)
                disliked_delta = -1
            review.likes.add(author)
            liked_delta = 1

        if request.META.get("HTTP_REFERER").__contains__("rating"):
            is_rating_sort = True

        output_data = {
            "liked_delta": liked_delta,
            "disliked_delta": disliked_delta,
            "is_rating_sort": is_rating_sort,
        }
        return JsonResponse(output_data)
    else:
        return redirect_last_url(request)


# TODO: DRY?
# @login_required
@catch_error
def dislike_review(request, pk):
    if request.is_ajax():
        review = Review.objects.get(pk=pk)
        author = request.user

        liked_delta = 0
        is_rating_sort = False
        if review.is_disliked(author):
            review.dislikes.remove(author)
            disliked_delta = -1
        else:
            if review.is_liked(author):
                review.likes.remove(author)
                liked_delta = -1
            review.dislikes.add(author)
            disliked_delta = 1

        if request.META.get("HTTP_REFERER").__contains__("rating"):
            is_rating_sort = True

        output_data = {
            "liked_delta": liked_delta,
            "disliked_delta": disliked_delta,
            "is_rating_sort": is_rating_sort,
        }
        return JsonResponse(output_data)
    else:
        return redirect_last_url(request)


"""
...................................................
........................ Comment ..................
...................................................
"""


# @login_required
@catch_error
def add_comment(request):
    if request.POST:
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.review = Review.objects.get(pk=request.POST["review_id"])
            comment.save()
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    else:
        form = CommentForm()
    return render(request, TEMPLATE_LIST_DETAIL, {"comment_form": form})


"""
...................................................
........................ Feedback .................
...................................................
"""


@catch_error
def send_review(request):
    if request.POST:
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.type = request.POST["type"]
            review.author = request.user
            review.save()
            return JsonResponse({"success": True})

        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    else:
        form = ReviewForm()

    return render(request, TEMPLATE_LIST_DETAIL, {"review_form": form})


"""
...................................................
...................... REDIRECT PREV URL ..........
...................................................
"""


def redirect_last_url(request):
    """ Protected implementations """
    url = request.META.get("HTTP_REFERER")
    if url is None:
        return redirect("/reviews/")
    else:
        return redirect(url)
