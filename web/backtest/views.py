import re
import traceback
from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import TemplateView

from .analyze import AnalyzePortfolio
from .models import Type, Asset, Currency, Exchange
from core.views import catch_error, catch_api_error, BaseCatchErrorView
from algorithm.asset_estimator import asset_estimator
from json import dumps


TEMPLATE_INPUT = "backtest/input_data/input_data.html"
TEMPLATE_ANALYZE = "backtest/analyze/analyze.html"
TEMPLATE_SAVE = "backtest/save_result/save_result.html"
PORTFOLIO_CONTEXT = None  # TODO: more correct way
# Create your views here.
"""
..............................................................................................................
................................................ INPUT DATA VIEW .............................................
..............................................................................................................
"""


class InputDataView(TemplateView, BaseCatchErrorView):
    template_name = TEMPLATE_INPUT

    def get(self, request, **kwargs):
        context = {"currencies": Currency.objects.filter(ticker__in=Currency.AVAILABLE_CURRENCIES),
                   "benchmarks": Asset.get_available_benchmarks(), }

        return render(request, "backtest/input_data/input_data.html", context)


def view(request):
    return redirect("input_data/")


def dump_asset(asset):
    return {"value": asset.as_suggestion, "data": asset.id}


@catch_api_error
def autocomplete(request):
    MAX_RESULTS = 30
    instance_type = request.GET["instance_type"]
    keyword = request.GET["keyword"]
    term = request.GET["term"]
    if request.is_ajax():
        # init available types'
        if instance_type == "assets":
            available_types = Type.BACKTEST_ASSETS_TYPES if keyword == "all" else [keyword]
        elif instance_type == "benchmarks":
            available_types = Type.BENCHMARKS_TYPES if keyword == "all" else [keyword]
        else:
            available_types = []
        # init search
        from django.db.models import Q
        if term == "":  # if empty term
            assets = tuple(Asset.objects.filter(type__in=available_types, status__in=Asset.ACTUAL_STATUSES)[:MAX_RESULTS])
        else:
            assets = tuple(Asset.objects.filter(type__in=available_types, status__in=Asset.ACTUAL_STATUSES).filter(
                Q(name__icontains=term) | Q(exchange_ticker__icontains=term)))[:MAX_RESULTS]
        # dump suggestions
        suggestions = tuple(dump_asset(a) for a in assets)
        # dump results
        output_data = {
            "query": "Unit",
            "suggestions": suggestions
        }
        return JsonResponse(output_data)
    return redirect(reverse("backtest-input-page"))


@catch_api_error
def add_asset(request):
    if request.is_ajax():
        from django.template import loader
        asset_template = "backtest/input_data/includes/asset_field.html"
        share_template = "backtest/input_data/includes/share_field.html"
        asset = loader.render_to_string(
            template_name=asset_template,
            request=request
        )
        share = loader.render_to_string(
            template_name=share_template,
            request=request
        )
        output_data = {
            "asset": asset,
            "share": share,
        }

        return JsonResponse(output_data)
    return redirect(reverse("backtest-input-page"))


@catch_api_error
def search_asset(request):
    if request.is_ajax():
        from django.template import loader
        template = "backtest/input_data/includes/select_box.html"
        # load assets options
        context = {"types": Type.objects.filter(slug__in=Type.BACKTEST_ASSETS_TYPES)}
        assets_options = loader.render_to_string(
            template_name=template,
            request=request,
            context=context
        )
        # load benchmarks options
        context = {"types": Type.objects.filter(slug__in=Type.BENCHMARKS_TYPES)}
        benchmarks_options = loader.render_to_string(
            template_name=template,
            request=request,
            context=context
        )
        output_data = {
            "assets": assets_options,
            "benchmarks": benchmarks_options,
        }
        return JsonResponse(output_data)
    return redirect(reverse("backtest-input-page"))


"""
..............................................................................................................
................................................ ANALYZE PORTFOLIO VIEW ......................................
..............................................................................................................
"""


def parse_asset_string(asset_string):
    asset_name = asset_string.split("(")[0].strip()  # parse name
    asset_ticker = re.findall("\(.+:\s(\w+)", asset_string)[0]  # parse ticker
    return asset_name, asset_ticker


@catch_api_error
def portfolio_relative_values(request):
    """Get relative portfolio values by user selected period"""
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    backtest_cache = request.session["backtest_cache"]
    new_values = AnalyzePortfolio.get_relative_values_by_period(start_date, end_date, **backtest_cache)
    if not new_values:
        return JsonResponse(status=404, data={"result": False})
    while len(new_values) > 400:
        del new_values[::2]
    return JsonResponse({"values": new_values, "result": True})


@catch_error
def view_analyze(request):
    # init
    context = {}
    benchmark, benchmark_exchange_ticker, benchmark_exchange_id = "", "", ""

    args = request.GET
    # map portfolio
    portfolio = {
        "start_date": datetime.strptime(args["start_date"], '%d-%m-%Y'),
        "end_date": datetime.strptime(args["end_date"], '%d-%m-%Y'),
        "rebalancing": str(args["rebalancing"]),
        "currency": args["currency"],
    }
    # get benchmark info
    benchmark = Asset.objects.get(id=int(request.GET["benchmark"]))
    benchmark_exchange_ticker = benchmark.exchange_ticker
    benchmark_exchange_id = benchmark.exchange_id
    benchmark_name = benchmark.name

    # get input_data for context
    input_rebalance_value = get_rebalance_value(str(args["rebalancing"]))
    input_rebalance_id = str(args["rebalancing"])
    input_start_date = args["start_date"]
    input_end_date = args["end_date"]
    input_currency = args["currency"]
    input_benchmark_id = int(request.GET["benchmark"])
    input_assets = args.getlist("asset")
    input_shares = args.getlist("share")
    count_empty_field = range(5 - len(input_assets))

    analyze_data = {
        "rebalance_value": input_rebalance_value,
        "rebalance_id": input_rebalance_id,
        "start_date": input_start_date,
        "end_date": input_end_date,
        "currency": input_currency,
        "benchmark_id": input_benchmark_id,
        "benchmark_name": benchmark.name,
        "assets": input_assets,
        "shares": input_shares,
        "count_empty_field": count_empty_field,
    }

    # fill assets array
    assets = []
    for asset, share in zip(args.getlist("asset"), args.getlist("share")):
        asset_name, asset_ticker = parse_asset_string(asset)
        asset_queryset = Asset.objects.filter(name__contains=asset_name, exchange_ticker=asset_ticker)  # get asset
        if asset_queryset.exists():
            asset = asset_queryset[0]
            asset_info = {"id": asset.id, "share": float(share), "name": asset.name}
            assets.append(asset_info)

    if benchmark and assets:
        arr_tickets, arr_exchange, arr_tickets_share = [], [], []
        input_start_date = portfolio["start_date"].strftime("%Y-%m-%d")
        input_end_date = portfolio["end_date"].strftime("%Y-%m-%d")

        # map investments
        asset_names = {}
        for asset in assets:
            asset_object = Asset.objects.get(id=asset["id"])
            name = asset_object.name
            exchange_id = asset_object.exchange_id
            exchange_ticker = asset_object.exchange_ticker
            arr_tickets.append(exchange_ticker)
            arr_exchange.append(exchange_id)
            arr_tickets_share.append(asset["share"])
            asset_names.update({exchange_ticker: name})
        asset_names.update({benchmark_exchange_ticker: benchmark_name})
        context.update({"portfolio": portfolio, "assets": assets, "input_start_date": input_start_date})
        try:
            analyze_portfolio = AnalyzePortfolio(arr_tickets, arr_exchange, arr_tickets_share, input_start_date,
                                                 input_end_date, benchmark_exchange_ticker, benchmark_exchange_id,
                                                 portfolio['currency'], asset_names, portfolio["rebalancing"])
            # get base information for template
            analysis_data = analyze_portfolio.get_analysis_data()
            if not analysis_data["analysis_errors"]:
                # cash absolute values and base params
                backtest_cache = {"dates": analysis_data["ptf_price_change"]["dates"],
                                  "abs_values": analysis_data["ptf_price_change"]["values"]}
                request.session[f'backtest_cache'] = backtest_cache
                # remove unnecessary vars from context
                analysis_data.pop("abs_values")
                analysis_data.pop("cash_tickers_share")
                max_start_date = analysis_data.pop("max_start_date")

                analysis_data["benchmark_name"] = benchmark_name

                risk_free_exchange = Asset.objects.get(name=analysis_data["no_risk_rate"]["name"])

                default_asset = {"asset_ticker": "MSCIWORLD",
                                 "asset_exchange": "INDX", }
                new_analysis_data = compare_asset(default_asset["asset_ticker"], default_asset["asset_exchange"],
                                                  benchmark_exchange_ticker, benchmark_exchange_id,
                                                  analysis_data["no_risk_rate"]["ticker"], risk_free_exchange.exchange_id,
                                                  analysis_data["all_dates"][0], analysis_data["all_dates"][-1], portfolio['currency'])
                risk_profile_number = 0
                if len(analysis_data) == 14:
                    risk_profile_number = analysis_data["risk_profile_number"]

                probe_json_dictionary = {"risk_profile_number": risk_profile_number,
                                         "benchmark_ticker": benchmark_exchange_ticker,
                                         "benchmark_exchange": benchmark_exchange_id,
                                         "input_start_date": analysis_data["all_dates"][0],
                                         "input_end_date": analysis_data["all_dates"][-1],
                                         "currency": portfolio["currency"]}

                dataJSON = dumps(probe_json_dictionary)

                context.update({"portfolio_analysis_data": analysis_data,
                                "asset_analysis": new_analysis_data["stats_param"],
                                "compare_asset": new_analysis_data["compare_asset"],
                                "max_start_date": max_start_date,
                                "benchmark_ticker": benchmark_exchange_ticker,
                                "data": dataJSON,
                                "analyze_data": analyze_data,
                                "currencies": Currency.objects.filter(ticker__in=Currency.AVAILABLE_CURRENCIES),
                                "benchmarks": Asset.get_available_benchmarks(),
                                })
            else:
                context.update({"error_text": analysis_data["analysis_errors"],
                                "analyze_data": analyze_data,
                                "currencies": Currency.objects.filter(ticker__in=Currency.AVAILABLE_CURRENCIES),
                                "benchmarks": Asset.get_available_benchmarks(),
                                "portfolio_analysis_data": "",
                                })

        except (ValueError, IndexError) as error:
            # TODO поставить везде отлов ошибок алгоритма в сентри
            from sentry_sdk import capture_exception
            capture_exception(error)

            context.update({"error": 'Произошла ошибка', "error_detail": error})
    else:
        context.update({"error": "Incorrect input data"})

    return render(request, TEMPLATE_ANALYZE, context)


"""
..............................................................................................................
................................................ SAVE RESULT VIEW ............................................
..............................................................................................................
"""


@catch_error
def view_save(request):
    user = request.user
    if user.is_authenticated:
        return render(request, "backtest/save_result/save_result.html")
    else:
        return redirect("/")


def default_assets(benchmark_ticker):
    if benchmark_ticker == "IMOEX" or benchmark_ticker == "MCFTR":
        asset_ticker = "FXRL"
        asset_exchange = "MCX"
    else:
        asset_ticker = "SPY"
        asset_exchange = "NYSE ARCA"
    return {"asset_ticker": asset_ticker,
            "asset_exchange": asset_exchange,}


def compare_asset(asset_ticker, asset_exchange, benchmark_ticker, benchmark_exchange, risk_free_ticker, risk_free_exchange,
                    start_date, end_date, forex):

    result = asset_estimator(asset_ticker, asset_exchange, benchmark_ticker, benchmark_exchange,
                             risk_free_ticker, risk_free_exchange, start_date, end_date, forex)

    stats_param = {}
    stats_param_names = ["gagr", "vol", "sharp", "alpha", "beta", "cor", "r_square"]
    stats_param_values = result
    stats_param.update(dict(zip(stats_param_names, stats_param_values)))

    return {"stats_param": stats_param, "compare_asset": asset_ticker}


def ajax_compare(request):
    if not request.is_ajax():
        return render(request, "backtest/input_data/input_data.html")

    benchmark = str(request.GET.get("benchmark", None))
    exchange = request.GET.get("exchange", None)
    start_date = request.GET.get("start_date", None)
    end_date = request.GET.get("end_date", None)
    currency = request.GET.get("currency", None)
    data_pk = request.GET.get("data_pk", None)

    if currency == "RUB":
        risk_free_ticker = "RGBITR"
        risk_free_exchange = "INDX"
    else:
        risk_free_ticker = "IDCOT10TR"
        risk_free_exchange = "INDX"

    exchange = Exchange.objects.get(code=exchange)
    installed_benchmark = Asset.objects.get(exchange_ticker=benchmark, exchange=exchange)

    if data_pk != "":
        asset = Asset.objects.get(id=data_pk)
    else:
        asset = "Пусто"

    result = asset_estimator(asset.exchange_ticker, asset.exchange_id, installed_benchmark.exchange_ticker,
                             installed_benchmark.exchange_id, risk_free_ticker, risk_free_exchange,
                             start_date, end_date, currency)

    if isinstance(result, str):
        data = {"is_success": False,
                "error_text": str(result)}
    else:
        stats_param = {}
        stats_param_names = ["gagr", "vol", "sharp", "alpha", "beta", "cor", "r_square"]
        stats_param_values = result
        stats_param.update(dict(zip(stats_param_names, stats_param_values)))

        data = {
            "is_success": True,
            "asset": str(asset.exchange_ticker),
            "gagr": str(smart_round(stats_param["gagr"]["value"])) + stats_param["gagr"]["unit"],
            "vol": str(smart_round(stats_param["vol"]["value"])) + stats_param["vol"]["unit"],
            "sharp": str(smart_round(stats_param["sharp"]["value"])) + stats_param["sharp"]["unit"],
            "alpha": str(smart_round(stats_param["alpha"]["value"])) + stats_param["alpha"]["unit"],
            "beta": str(smart_round(stats_param["beta"]["value"])) + stats_param["beta"]["unit"],
            "cor": str(smart_round(stats_param["cor"]["value"])) + stats_param["cor"]["unit"],
            "r_square": str(smart_round(stats_param["r_square"]["value"])) + stats_param["r_square"]["unit"],
        }
    return JsonResponse(data)


def get_rebalance_value(rebalance):
    rebalance_values = ["Без ребалансировки", "Ежемесячная", "Ежеквартальная", "Полугодовая", "Годовая"]
    rebalance_ids = ["None", "month", "quartal", "half_year", "year"]
    i = 0
    for rebalance_id in rebalance_ids:
        if rebalance_id == rebalance:
            return rebalance_values[i]
        i = i + 1


def smart_round(value):
    no_valid_values = [float("inf"), float("-inf"), "-", ""]
    if not str(value).isalpha() and value not in no_valid_values:
        value = float(value)
        if 10 < abs(value) < 100:
            value = "%.1f" % round(value, 1)
        elif abs(value) < 10:
            value = "%.2f" % round(value, 2)
        else:
            value = int(value)
        return value
    return ""
# """
# ..............................................................................................................
# ................................................ FILL DB .....................................................
# ..............................................................................................................
# """
#
# def populate_db(request):
#     from .populate import populate
#     # from .models import Asset
#     print(Asset.objects.filter(country_id="DEU"))
#     # response = populate()
#     response = None
#     # response = Asset.objects.all()[0]
#     # print(Asset.objects.filter(type_id="AC").count())
#     # print(Asset.objects.filter(type_id="ET").count())
#     # print(Asset.objects.filter(type_id="ST").count())
#     # print(Asset.objects.filter(type_id="MF").count())
#     # print(Asset.objects.filter(type_id="CS").count())
#     # for i, asset in enumerate(Asset.objects.filter(type_id="AC")):
#     #     print(i, asset.pk)
#     # print(Asset.objects.filter(type_id="ETF").count())
#     output_data = {
#         "Process": "Database checking populate",
#         "Response": response,
#     }
#     return JsonResponse(output_data, json_dumps_params={'indent': 4, "ensure_ascii": False})
