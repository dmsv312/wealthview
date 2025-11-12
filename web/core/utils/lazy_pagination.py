from typing import Type

from django.core.paginator import PageNotAnInteger, EmptyPage, Paginator
from django.views.generic import ListView

# Create your views here.
from django_filters import FilterSet

from reviews.models import *

"""
..............................................................................................................
................................................ VIEWS  ......................................................
..............................................................................................................
"""
"""
...................................................
...................... PaginateAbleView  ..........
...................................................
"""


class PaginateAbleView(ListView):
    class Meta:
        paginator = None

    @classmethod
    def get_paginator(cls, **kwargs):
        return cls.Meta.paginator

    @classmethod
    def set_paginator(cls, paginator):
        cls.Meta.paginator = paginator


"""
..............................................................................................................
................................................ FUNCTIONS ...................................................
..............................................................................................................
"""
"""
...................................................
...................... Paginate  ..................
...................................................
"""


def paginate(request, queryset, limit: int, list_view: Type[PaginateAbleView]):
    # get paginator
    paginator = Paginator(queryset, limit)
    list_view.set_paginator(paginator)
    # get page response
    page = request.GET.get('page')
    response = get_page(request, paginator, page, default_page=1)
    # package response
    return {"instances": response, "has_next": response.has_next()}


"""
...................................................
...................... Page Response  .............
...................................................
"""


def get_page_processed(request, limit: int,
                       list_view: Type[PaginateAbleView],
                       instance_filter: Type[FilterSet],
                       ):
    import query_tools.views as query_tools
    model = instance_filter.Meta.model
    # Get query set
    qs = model.objects.all()
    # filter qs
    qs = query_tools.get_filtered_qs(request, qs, instance_filter)
    # sort qs
    qs = query_tools.get_sorted_qs(request, qs)
    # paginate qs
    response = paginate(request, qs, limit=limit, list_view=list_view)
    return response


def get_page(request, paginator, page, default_page=1):
    try:
        return paginator.page(page)
    except PageNotAnInteger:
        return paginator.page(default_page)
    except EmptyPage:
        return paginator.page(paginator.num_pages)


"""
...................................................
...................... Lazy Load Instances  .......
...................................................
"""


def lazy_load_instances(request, paginator,
                        instances_generator_template, instances_name, instance_data_generator=None,
                        extra_data_for_render=None):
    from django.template import loader
    from django.http import JsonResponse
    # get response
    user = request.user
    page = request.POST.get('page')
    response = get_page(request, paginator, page, default_page=2)
    # generate data by response
    instances_data = response if instance_data_generator is None else instance_data_generator(response, user)
    extra_data_for_render = {} if extra_data_for_render is None else extra_data_for_render
    render_data = {instances_name + '_data': instances_data, "user": user, **extra_data_for_render}
    # build a html instances list with the paginated posts
    instances_html = loader.render_to_string(
        template_name=instances_generator_template,
        context=render_data,
        request=request
    )
    # package output data and return it as a JSON object
    output_data = {
        'instances_html': instances_html,
        'has_next': response.has_next()
    }
    return JsonResponse(output_data)
