# -*- coding: utf-8 -*-
from datetime import timedelta, datetime, date
from json import dumps

from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.forms import model_to_dict
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, reverse
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode
from django.views import generic
from sentry_sdk import capture_exception

from algorithm.common_utils import check_errors_dictionary
from algorithm.risk_profile import get_risk_matrix
from auth_sys.email import send_change_password_mail
from auth_sys.tokens import account_activation_token
from auth_sys.views import logout_user
from backtest.models import Asset
from backtest.views import compare_asset
from core.views import BaseCatchErrorView, catch_api_error
from rprofile.models import Answer, Question, RTestResult, RiskProfileVersion
from .analyze import AnalyzePortfolio
from .cache import PortfolioCache
from .filters import PortfolioFilter
from .forms import OperationAddForm, PortfolioChangeSettingsForm
from .models import Operation, OperationType, Portfolio, Currency
from .serializers import ModelToCacheSerializer


class AnalyzeMixin:
    """
    Mixin for analyzing portfolio
    - manage cache
    - handle errors
    - decide how to call Analyze class
    """

    @staticmethod
    def get_portfolio(request, portfolios):
        """get default portfolio"""
        portfolio = PortfolioFilter(request.GET, queryset=portfolios).qs.first()
        if not portfolio:
            portfolio = portfolios.first()
        return portfolio

    @staticmethod
    def populate_open_positions(open_positions):
        """add asset instance to the each open position"""
        if open_positions:
            for open_position in open_positions:
                try:
                    asset = Asset.objects.get(
                        exchange_ticker=open_position["ticker"], exchange__code=open_position["exchange_code"]
                    )
                    asset_dict = model_to_dict(asset)
                    if hasattr(asset, 'fund_attributes'):
                        # use custom serializer to dump datetime field
                        attrs = ModelToCacheSerializer.dumps(asset.fund_attributes)
                        asset_dict.update(attrs)
                    for i in ["split_update_date", "price_update_date", "fund_attributes_update_date"]:
                        asset_dict.pop(i)
                    open_position.update({"asset": asset_dict})
                except ObjectDoesNotExist as e:
                    capture_exception(e)
                    continue

    @staticmethod
    def check_new_operations(dynamic_prices_cache, portfolio):
        """check if portfolio has new operations"""
        if dynamic_prices_cache:
            operations_ids = dynamic_prices_cache.get("operations_ids")
            return set(operations_ids) != set(
                list(portfolio.portfolio_operations.all().values_list("id", flat=True)))
        return False

    @staticmethod
    def check_new_settings(settings_cache, portfolio):
        """check if portfolio has new settings"""
        if settings_cache:
            old_benchmark_id = settings_cache.get("benchmark_id")
            old_currency_ticker = settings_cache.get("currency_ticker")
            return old_benchmark_id != portfolio.benchmark.id or old_currency_ticker != portfolio.currency.ticker
        return False

    def check_analyze_conditions(self, update_cache, extra_operations, portfolio):
        """
        Start analysis again if:
        1) Portfolio settings changed (currency, benchmark)
        2) Add operations to the Portfolio
        3) Load portfolio for the first time (dynamic_prices_cache not exists)
        """
        dynamic_prices_cache = self.ptf_cache.get("dynamic_prices_cache")
        settings_cache = self.ptf_cache.get("settings_cache")
        new_operations_exists = self.check_new_operations(dynamic_prices_cache, portfolio)
        new_settings = self.check_new_settings(settings_cache, portfolio)
        analysis_date = self.ptf_cache.get('analysis_date')
        analysis_date_change = datetime.strptime(analysis_date, '%d-%m-%Y').date() != timezone.now().date() if analysis_date else True
        return analysis_date_change or not dynamic_prices_cache or new_operations_exists or new_settings or extra_operations or update_cache

    def set_base_cache(self, data):
        """Cache base data to use it later"""
        cache_data = {key: value for key, value in data.items() if key in AnalyzePortfolio.BASE_CACHE_VARS}
        self.ptf_cache.set(**cache_data)

    def analyze(self, session, portfolio, update_cache=None, extra_operations=None):
        """Base method for determination of which part of base analyze class should be used"""
        analysis_data = {}
        if extra_operations is None:
            extra_operations = []
        # get condition value
        analyze_condition = self.check_analyze_conditions(update_cache, extra_operations, portfolio)
        # base on conditions call appropriate analyze methods
        if analyze_condition:
            # run full analyze
            analyze_portfolio = AnalyzePortfolio(portfolio)
            analyze_portfolio.operations += extra_operations
            data = analyze_portfolio.get_analysis_data()
            if not data.get("analysis_errors"):
                # update cache and return new values
                open_positions = data.get("open_positions")
                analysis_data.update(data)
                self.set_base_cache(data)
            else:
                # handle errors and return old values
                open_positions = self.ptf_cache.get("open_positions")
                ptf_total_cash = self.ptf_cache.get("ptf_total_cash")
                analysis_data.update({"open_positions": open_positions, "ptf_total_cash": ptf_total_cash})
                analysis_data.update(data)
                return analysis_data
        else:
            # update just open positions values
            total_cash, open_positions = AnalyzePortfolio.get_updated_operations_info(
                self.ptf_cache.get("dynamic_prices_cache"))
            self.ptf_cache.set(ptf_total_cash=float(total_cash))
            analysis_data.update({"ptf_total_cash": total_cash})

        self.populate_open_positions(open_positions)  # add asset instances to open positions

        analysis_data.update({"open_positions": open_positions})
        self.ptf_cache.set(open_positions=open_positions)
        return analysis_data


class AccountHomeView(LoginRequiredMixin, generic.View):
    http_method_names = ("get",)

    def get(self, request, *args, **kwargs):
        if self.request.user.profile.profile_portfolios.first():
            portfolio = self.request.user.profile.profile_portfolios.first()
            return redirect(portfolio)
        else:
            return render(request, 'account/risk_profile.html', get_risk_profile_context(request))


class PortfoliosDetailView(LoginRequiredMixin, AnalyzeMixin, generic.DetailView, BaseCatchErrorView):
    """View for base portfolio page and operations history page"""
    queryset = Portfolio.objects.all()
    tabs = ["home", "operations_history"]
    active_tab = "home"
    data_vars = ["open_positions", "ptf_total_cash", "analysis_errors"]

    def get_queryset(self):
        return self.queryset.filter(profile=self.request.user.profile)

    def get(self, request, *args, **kwargs):
        context = {}
        update_cache = request.GET.get("update_cache")
        portfolio = self.get_object()
        operations = portfolio.portfolio_operations.all()
        currencies = Currency.objects.filter(ticker__in=Currency.AVAILABLE_CURRENCIES)
        benchmarks = Asset.get_available_benchmarks()

        if operations:
            self.ptf_cache = PortfolioCache(portfolio)
            analysis_data = self.analyze(request.session, portfolio, update_cache)
            context.update({key: value for key, value in analysis_data.items() if key in self.data_vars})

        context.update({
            "active_tab": self.active_tab,
            "portfolio": portfolio,
            "operation_types": OperationType.objects.all(),
            "currencies": currencies,
            "benchmarks": benchmarks,
            "new_risk_profile_version": check_risk_profile_version(request),
        })
        return render(request, "account/account.html", context=context)


class OperationsDeleteView(AnalyzeMixin, generic.DeleteView, BaseCatchErrorView):
    """View for removing operation from portfolio"""
    model = Operation
    queryset = Operation.objects.all()

    def get_queryset(self):
        return self.queryset.filter(portfolio__profile=self.request.user.profile)

    def delete(self, request, *args, **kwargs):
        operation = self.get_object()
        portfolio = operation.portfolio
        operation.delete()
        self.ptf_cache = PortfolioCache(portfolio)
        if portfolio.portfolio_operations.all().count() == 0:
            self.ptf_cache.clear()
        return JsonResponse({}, status=200)


def ajax_delete_operation(request):
    try:
        operation = Operation.objects.get(id=int(request.GET.get("operation_id", None)))
        portfolio = operation.portfolio
        if not request.is_ajax():
            currencies = Currency.objects.filter(ticker__in=Currency.AVAILABLE_CURRENCIES)
            benchmarks = Asset.get_available_benchmarks()
            context = ({
                "active_tab": "operations_history",
                "portfolio": portfolio,
                "operation_types": OperationType.objects.all(),
                "currencies": currencies,
                "benchmarks": benchmarks,
            })
            return render(request, "account/account.html", context=context)
        delete_operation_result = try_delete_operation(portfolio, operation)
        if delete_operation_result["is_success"]:
            return JsonResponse({})
        else:
            return JsonResponse({"delete_error": delete_operation_result["error_message"]})
    except Exception as ex:
        return JsonResponse({"delete_error": "Произошла ошибка. Операция уже удалена"})


@transaction.atomic()
def try_delete_operation(portfolio, operation):
    """Использование atomic transactions"""
    result = {"is_success": True}
    sid = transaction.savepoint()
    try:
        operation.delete()
        analysis_data = {}
        if portfolio.portfolio_operations.count():
            analyze_portfolio = AnalyzePortfolio(portfolio)
            analysis_data = analyze_portfolio.get_analysis_data()

        if analysis_data.get("analysis_errors"):
            transaction.savepoint_rollback(sid)
            result["is_success"] = False
            result["error_message"] = "Невозможно удалить данную транзакцию, т.к. это приведет к " \
                                      "ошибкам в обработке последующих операций"
            return result
        else:
            transaction.savepoint_commit(sid)
            return result
    except Exception:
        transaction.savepoint_rollback(sid)
        result["is_success"] = False
        result["error_message"] = "Произошла ошибка. Попробуйте еще раз"
        return result


class OperationsListCreateView(LoginRequiredMixin, AnalyzeMixin, generic.DetailView, generic.CreateView,
                               BaseCatchErrorView):
    """View for creating new operations and getting list of operations"""
    model = Portfolio
    queryset = Portfolio.objects.all()
    template_name = "account/account.html"
    form_class = OperationAddForm
    active_tab = "home"

    def get_context_data(self, **kwargs):
        """Insert the form into the context dict."""
        kwargs.update({
            "portfolio": self.portfolio,
            "operation_types": OperationType.objects.all()})
        return kwargs

    def get_queryset(self):
        return self.queryset.filter(profile=self.request.user.profile)

    def get(self, request, *args, **kwargs):
        self.portfolio = self.get_object()
        operations = self.portfolio.portfolio_operations.all()
        currencies = Currency.objects.filter(ticker__in=Currency.AVAILABLE_CURRENCIES)
        benchmarks = Asset.get_available_benchmarks()
        context = {
            "operations": operations,
            "active_tab": "operations_history",
            "currencies": currencies,
            "benchmarks": benchmarks,
            "new_risk_profile_version": check_risk_profile_version(request),
        }
        context.update(self.get_context_data())

        return render(request, "account/account.html", context=context)

    def post(self, request, *args, **kwargs):
        self.portfolio = self.get_object()
        self.ptf_cache = PortfolioCache(self.portfolio)
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.portfolio = self.get_object()
        kwargs.update({"portfolio": self.portfolio})
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        asset = form.cleaned_data.get("asset")
        asset_type = form.cleaned_data.get("asset_type")
        asset_pk = form.cleaned_data.get("asset_pk")
        date = form.cleaned_data.get("date")
        operation_type = form.cleaned_data.get("operation_type")
        self.object = form.save(commit=False)

        operation = {
            "date": date,
            "asset": asset,
            "type": operation_type,
            "count": self.object.count,
            "price": self.object.price,
            "cost": self.object.cost,
        }

        if operation_type.name == "пополнение" or operation_type.name == "вывод" \
                or operation_type.name == "дивиденд":
            data_operation = {
                "date": date,
                "type": operation_type,
                "asset": asset,
                "asset_type": asset_type,
                "asset_pk": asset_pk,
                "cost": str(self.object.cost).replace(',', '.'),
                "operation_date": str(date),
            }
        else:
            data_operation = {
                "date": date,
                "type": operation_type,
                "asset": asset,
                "asset_type": asset_type,
                "asset_pk": asset_pk,
                "count": int(self.object.count),
                "price": str(self.object.price).replace(',', '.'),
                "cost": str(self.object.cost).replace(',', '.'),
                "operation_date": str(date),
            }

        analysis_data = self.analyze(self.request.session, self.portfolio, extra_operations=[operation])
        context.update(analysis_data)
        context.update(data_operation)
        context["active_tab"] = "home"

        if asset and asset.fund_attributes_update_date < (timezone.now() - timedelta(days=1)).date():
            try:
                asset.update_attributes()
            except Exception as e:
                from backtest.tasks import reparse_attribs
                reparse_attribs.delay([asset.id])

        if not analysis_data.get("analysis_errors"):
            for key, value in operation.items():
                setattr(self.object, key, value)
            self.object.save()
            dynamic_prices_cache = self.ptf_cache.get("dynamic_prices_cache")
            operations_ids = dynamic_prices_cache.get("operations_ids")
            operations_ids.append(self.object.id)
            dynamic_prices_cache.update({"operations_ids": operations_ids})
            self.ptf_cache.set(dynamic_prices_cache=dynamic_prices_cache)

            return redirect(self.portfolio)
        else:
            error = analysis_data.get("analysis_errors")

            if check_errors_dictionary(error["text_detail"]):
                context.update({"error_text": error["text_detail"]})
            else:
                context.update({"error_text": error["text"]})

            return render(self.request, "account/account.html", context=context)

    def form_invalid(self, form):
        context = self.get_context_data()
        open_positions = self.ptf_cache.get("open_positions")
        ptf_total_cash = self.ptf_cache.get("ptf_total_cash")
        context.update({
            "analysis_errors": {"text": form.errors["analysis_errors"]},
            "open_positions": open_positions,
            "ptf_total_cash": ptf_total_cash,
            "active_tab": "home",
        })

        asset = form.cleaned_data.get("asset")
        asset_type = form.cleaned_data.get("asset_type")
        asset_pk = form.cleaned_data.get("asset_pk")
        date = form.cleaned_data.get("date")
        operation_type = form.cleaned_data.get("operation_type")
        count = form.cleaned_data.get("count")
        price = form.cleaned_data.get("price")
        cost = form.cleaned_data.get("cost")

        if operation_type.name == "пополнение" or operation_type.name == "вывод" \
                or operation_type.name == "дивиденд":
            data_operation = {
                "date": date,
                "type": operation_type,
                "asset": asset,
                "asset_type": asset_type,
                "asset_pk": asset_pk,
                "cost": str(cost).replace(',', '.'),
                "operation_date": str(date),
            }
        else:
            data_operation = {
                "date": date,
                "type": operation_type,
                "asset": asset,
                "asset_type": asset_type,
                "asset_pk": asset_pk,
                "count": int(count),
                "price": str(price).replace(',', '.'),
                "cost": str(cost).replace(',', '.'),
                "operation_date": str(date),
            }
        context.update(data_operation)

        return render(self.request, "account/account.html", context=context)


class PortfolioChangeSettingsView(LoginRequiredMixin, generic.UpdateView, BaseCatchErrorView):
    """View for changing base portfolio settings (benchmark, currency)"""
    queryset = Portfolio.objects.all()
    http_method_names = ("post",)
    form_class = PortfolioChangeSettingsForm

    def get_queryset(self):
        return self.queryset.filter(profile=self.request.user.profile)

    def get_form_kwargs(self):
        kwargs = {}
        if hasattr(self, 'object'):
            kwargs.update({'instance': self.object})
        benchmark = self.request.POST.get("benchmark")
        currency = self.request.POST.get("currency")
        kwargs.update({"data": {"benchmark": int(benchmark), "currency": currency}})
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({})

    def form_invalid(self, form):
        return JsonResponse(form.errors, status=400)


class MyPortfolioChangeSettingsView(LoginRequiredMixin, generic.UpdateView, BaseCatchErrorView):
    """My view for creating portfolio"""
    queryset = Portfolio.objects.all()
    http_method_names = ("get",)

    def get(self, request, *args, **kwargs):
        portfolio = Portfolio.objects.get(id=int(request.GET["portfolio_pk"]))

        portfolio.name = request.GET["portfolio_name"]
        portfolio.currency = Currency.objects.get(ticker=str(request.GET["currency"]))
        portfolio.benchmark = Asset.objects.get(id=int(request.GET["benchmark"]))
        portfolio.save()

        return redirect(portfolio)


class PortfolioAnalyzeView(LoginRequiredMixin, AnalyzeMixin, generic.DetailView, BaseCatchErrorView):
    """View for getting values for the charts"""
    queryset = Portfolio.objects.all()
    http_method_names = ("get",)

    def get_queryset(self):
        return self.queryset.filter(profile=self.request.user.profile)

    def get(self, request, *args, **kwargs):
        portfolio = self.get_object()
        self.ptf_cache = PortfolioCache(portfolio)
        currencies = Currency.objects.filter(ticker__in=Currency.AVAILABLE_CURRENCIES)
        benchmarks = Asset.get_available_benchmarks()
        context = {"active_tab": "portfolio_analyze",
                   "portfolio": portfolio,
                   "currencies": currencies,
                   "benchmarks": benchmarks,
                   "new_risk_profile_version": check_risk_profile_version(request),
                   }
        if portfolio.portfolio_operations.all().count() > 0:
            context.update(get_analyze_data(self, portfolio))
        else:
            context.update({"errors": "Для построения графика в портфеле должна быть хотя бы одна операция"})
        return render(request, "account/account.html", context=context)


class PortfolioRelativeValues(LoginRequiredMixin, AnalyzeMixin, generic.DetailView, BaseCatchErrorView):
    """Ajax view for getting new portfolio values for the new selected period"""
    queryset = Portfolio.objects.all()

    def get_queryset(self):
        return self.queryset.filter(profile=self.request.user.profile)

    def get(self, request, *args, **kwargs):
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        portfolio = self.get_object()
        self.ptf_cache = PortfolioCache(portfolio)
        portfolio_cache = self.ptf_cache.get("portfolio_cache")
        new_values = AnalyzePortfolio.get_relative_values_by_period(start_date, end_date, portfolio, portfolio_cache)
        if not new_values:
            return JsonResponse(status=404, data={"result": False})
        while len(new_values) > 400:
            del new_values[::2]
        return JsonResponse({"values": new_values, "result": True})


class PortfolioAddView(LoginRequiredMixin, generic.CreateView, BaseCatchErrorView):
    """View for creating new portfolio"""
    queryset = Portfolio.objects.all()
    http_method_names = ("get",)

    def get(self, request, *args, **kwargs):
        portfolios = request.user.profile.profile_portfolios.all()
        if portfolios.count() == Portfolio.MAX_PORTFOLIOS_COUNT:
            return redirect("account-page")
        default_params = Portfolio.get_default_settings()
        new_portfolio = Portfolio.objects.create(profile=request.user.profile, **default_params)
        return redirect(new_portfolio)


class MyPortfolioAddView(LoginRequiredMixin, AnalyzeMixin, generic.CreateView, BaseCatchErrorView):
    """My view for creating portfolio"""
    queryset = Portfolio.objects.all()
    http_method_names = ("get",)

    def get(self, request, *args, **kwargs):
        portfolios = request.user.profile.profile_portfolios.all()
        if portfolios.count() == Portfolio.MAX_PORTFOLIOS_COUNT:
            return redirect("account-page")
        currency = Currency.objects.get(ticker=str(request.GET["currency"]))
        benchmark = Asset.objects.get(id=int(request.GET["benchmark"]))
        start_date = request.GET["date"]
        cost = request.GET["add_portfolio_asset_cost"]

        name = request.GET["add_portfolio_name"]
        if name == "":
            name = "Портфель " + str(portfolios.count() + 1)

        new_portfolio = Portfolio.objects.create(profile=request.user.profile, name=name, currency=currency,
                                                 benchmark=benchmark)
        portfolio = Portfolio.objects.get(profile=new_portfolio.profile, id=new_portfolio.id)

        if start_date and cost:
            self.ptf_cache = PortfolioCache(portfolio)
            context = {}
            if currency.name == "Рубль":
                asset_name = "Russian Ruble"
            else:
                asset_name = "United States Dollar"
            asset = Asset.objects.get(name=asset_name)
            operation_type = OperationType.objects.get(name="пополнение")
            start_date = start_date.split("-")
            operation_date = date(int(start_date[2]), int(start_date[1]), int(start_date[0]))
            cost = float(cost)

            operation = {
                "date": operation_date,
                "asset": asset,
                "type": operation_type,
                "count": None,
                "price": None,
                "cost": cost,
            }

            analysis_data = self.analyze(self.request.session, portfolio, extra_operations=[operation])

            if not analysis_data.get("analysis_errors"):
                context.update(analysis_data)
                context["active_tab"] = "home"
                context["portfolio"] = portfolio
                data_base_operation = Operation.objects.create(date=operation_date, asset=asset, type=operation_type,
                                                               count=None, price=None, cost=cost, portfolio=portfolio)
                dynamic_prices_cache = self.ptf_cache.get("dynamic_prices_cache")
                operations_ids = dynamic_prices_cache.get("operations_ids")
                operations_ids.append(data_base_operation.id)
                dynamic_prices_cache.update({"operations_ids": operations_ids})
                self.ptf_cache.set(dynamic_prices_cache=dynamic_prices_cache)
            else:
                add_portfolio_data_operation = {
                    "portfolio_name": name,
                    "currency": currency.pk,
                    "benchmark": benchmark.name,
                    "cost": str(cost).replace(',', '.'),
                    "operation_date": str(operation_date),
                }
                json_dictionary = {"add_portfolio_data_operation": add_portfolio_data_operation}
                dataJSON = dumps(json_dictionary)

                portfolios_count = len(Portfolio.objects.filter(profile=portfolio.profile))
                first_portfolio = Portfolio.objects.filter(profile=portfolio.profile).first()
                portfolio.delete()

                origin_location = request.META["HTTP_REFERER"]

                if portfolios_count == 1 or origin_location.find("change_user_settings") != -1:
                    # Если у пользователя нет портфелей или пользователь добавлял портфель со страницы аккаунт
                    currencies = Currency.objects.filter(ticker__in=Currency.AVAILABLE_CURRENCIES)
                    benchmarks = Asset.get_available_benchmarks()
                    context = {
                        "data": dataJSON,
                        "add_portfolio_analysis_errors": analysis_data.get("analysis_errors"),
                        "benchmarks": benchmarks,
                        "currencies": currencies,
                    }
                    return render(request, "account/change_user.html", context=context)
                else:
                    # Общие данные во все вкладки (home, portfolio_analyze и operations)
                    data_vars = ["open_positions", "ptf_total_cash", "analysis_errors"]
                    update_cache = request.GET.get("update_cache")
                    operations = first_portfolio.portfolio_operations.all()
                    self.ptf_cache = PortfolioCache(first_portfolio)

                    context = {"operation_types": OperationType.objects.all(),
                               "error": dataJSON,
                               "add_portfolio_analysis_errors": analysis_data.get("analysis_errors"),
                               "portfolio": first_portfolio,
                               "operations": operations, }

                    if operations:
                        analysis_data = self.analyze(request.session, first_portfolio, update_cache)
                        context.update({key: value for key, value in analysis_data.items() if key in data_vars})

                    if origin_location.find("analyze") != -1:
                        # Собираем дополнительный контекст для вкладки portfolio_analyze
                        context["active_tab"] = "portfolio_analyze"
                        if first_portfolio.portfolio_operations.all().count() > 0:
                            context.update(get_analyze_data(self, first_portfolio))
                        else:
                            context.update(
                                {"errors": "Для построения графика в портфеле должна быть хотя бы одна операция"})
                    else:
                        if origin_location.find("operations") != -1:
                            # Для вкладки operations не требуется дополнительного контекста
                            context["active_tab"] = "operations_history"
                        else:
                            context["active_tab"] = "home"

                    return render(request, "account/account.html", context=context)

        return redirect(new_portfolio)


class PortfolioDeleteView(LoginRequiredMixin, AnalyzeMixin, generic.DeleteView, BaseCatchErrorView):
    """View for removing portfolio"""
    queryset = Portfolio.objects.all()
    http_method_names = ("post",)

    def get_queryset(self):
        return self.queryset.filter(profile=self.request.user.profile)

    def delete(self, request, *args, **kwargs):
        if request.user.profile.profile_portfolios.all().count() == Portfolio.MIN_PORTFOLIOS_COUNT:
            return JsonResponse({"error": "Profile must have at least one portfolio"}, status=400)
        self.object = self.get_object()
        self.object.delete()
        return JsonResponse({}, status=200)


def dump_asset(currency):
    return {"value": currency.ticker, "data": currency.ticker}


# autocomplete for currency assets
@catch_api_error
def autocomplete(request):
    MAX_RESULTS = 30
    term = request.GET["term"]
    if request.is_ajax():
        available_currencies = Portfolio.PORTFOLIO_CURRENCIES
        if term == "":  # if empty term
            assets = tuple(Currency.objects.filter(ticker__in=available_currencies)[:MAX_RESULTS])
        else:
            assets = tuple(Currency.objects.filter(ticker__in=available_currencies).filter(
                name__icontains=term))[:MAX_RESULTS]
        # dump suggestions
        suggestions = tuple(dump_asset(a) for a in assets)
        # dump results
        output_data = {
            "query": "Unit",
            "suggestions": suggestions
        }
        return JsonResponse(output_data)
    return redirect(reverse("account-home"))


@catch_api_error
def get_portfolio_params(request):
    if not request.is_ajax():
        return redirect(reverse("account-home"))

    value = int(request.GET.get("portfolio", None))
    portfolio = Portfolio.objects.get(id=value)
    data = {
        "portfolio_pk": str(portfolio.pk),
        "portfolio_name": str(portfolio.name),
        "currency": str(portfolio.currency.pk),
        "benchmark_name": str(portfolio.benchmark.name),
        "benchmark_pk": str(portfolio.benchmark_id),
    }
    return JsonResponse(data)


@catch_api_error
def change_user_settings(request):
    if request.user.is_anonymous:
        return redirect(reverse('login') + '?next=' + request.path)
    portfolio = request.user.profile.profile_portfolios.first()
    currencies = Currency.objects.filter(ticker__in=Currency.AVAILABLE_CURRENCIES)
    benchmarks = Asset.get_available_benchmarks()
    context = {
        "benchmarks": benchmarks,
        "currencies": currencies,
        "portfolio": portfolio,
        "new_risk_profile_version": check_risk_profile_version(request),
    }
    return render(request, "account/change_user.html", context=context)


@catch_api_error
def change_password_mail(request):
    send_change_password_mail(request, request.user)
    return render(request, "account/change_user.html")


@catch_api_error
def change_password(request, uidb64, token):
    try:
        args = {}
        uid = force_text(urlsafe_base64_decode(uidb64))
        new_user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        new_user = None

    if new_user is not None and account_activation_token.check_token(new_user, token):
        logout_user(request)
        args['process'] = "change_settings"
        args['email'] = new_user.email
        return render(request, 'auth_sys/login_page.html', args)
    else:
        return redirect('/')


@catch_api_error
def change_password_success(request):
    args = {}
    if request.POST:
        args['process'] = "change_settings_success"
        args['user_active'] = True
        e_mail = request.POST['email']
        password = request.POST['password']
        user = User.objects.get(email=e_mail)
        user.set_password(password)
        user.save()

    return render(request, 'auth_sys/login_page.html', args)


@catch_api_error
def risk_profile(request):
    return render(request, 'account/risk_profile.html', get_risk_profile_context(request))


def get_risk_profile_context(request):
    portfolio = request.user.profile.profile_portfolios.first()
    currencies = Currency.objects.filter(ticker__in=Currency.AVAILABLE_CURRENCIES)
    benchmarks = Asset.get_available_benchmarks()

    questions = Question.objects.order_by("number")
    risk_matrix = get_risk_matrix()
    quiz_information = {}
    i = 0
    for question in questions:
        all_answers = Answer.objects.filter(question=question)
        filtered_answers = all_answers.order_by("number")
        quiz_information[i] = {
            "question": question,
            "answers": filtered_answers,
        }
        i = i + 1

    context = {
        "quiz_information": quiz_information.values(),
        "risk_matrix": risk_matrix,
        "benchmarks": benchmarks,
        "currencies": currencies,
        "portfolio": portfolio,
        "new_risk_profile_version": check_risk_profile_version(request),
    }

    if request.user.profile.actual_r_test:
        user_risk_profile = RTestResult.objects.filter(profile=request.user.profile).last()
        dataJSON = user_risk_profile_to_json(user_risk_profile)
        context.update({"riskprofile": dataJSON})

    return context

def user_risk_profile_to_json(r_test_result):
    context = {'profile_number': r_test_result.number,
               'profile_name': r_test_result.result_name,
               'profile_description': r_test_result.description,
               'profile_tolerance': r_test_result.tolerance,
               'profile_capacity': r_test_result.capacity,
               'profile_year': r_test_result.acceptable_risk_value,
               'portfolio_description': r_test_result.portfolio_description,
               'profile_portfolio': r_test_result.portfolio,
               'profile_indexRT': str(r_test_result.indexRT),
               'profile_indexRC': str(r_test_result.indexRC), }
    dataJSON = dumps(context)
    return dataJSON


def check_risk_profile_version(request):
    if request.user.profile.actual_r_test:
        user_risk_profile = RTestResult.objects.get(id=request.user.profile.actual_r_test.id)

        if user_risk_profile:
            if user_risk_profile.version != RiskProfileVersion.get_current_version():
                if not user_risk_profile.notification_date or \
                        (relativedelta(datetime.today(), user_risk_profile.notification_date.date()).days >
                         settings.RISK_PROFILE_NOTIFICATION_INTERVAL):
                    user_risk_profile.notification_date = datetime.now()
                    user_risk_profile.save()
                    return True
    return False


def get_analyze_data(self, portfolio):
    context = {}

    mixin = AnalyzeMixin()
    mixin.ptf_cache = ptf_cache = PortfolioCache(portfolio)

    mixin.analyze(session=None, portfolio=portfolio, update_cache=True)

    portfolio_analysis_data = ptf_cache.get("portfolio_analysis_data")
    analysis_date = ptf_cache.get("analysis_date")
    if portfolio_analysis_data:
        risk_free_exchange = Asset.objects.get(name=portfolio_analysis_data["no_risk_rate"]["name"])
        default_asset = {"asset_ticker": "MSCIWORLD",
                         "asset_exchange": "INDX", }

        if len(portfolio_analysis_data) == 13:
            analyze_portfolio = AnalyzePortfolio(portfolio)
            portfolio_analysis_data = analyze_portfolio.get_analysis_data()["portfolio_analysis_data"]

        asset_estimator_start_date = max(portfolio_analysis_data["all_dates"][0],
                                         portfolio_analysis_data["bench_dates_days"][0],
                                         portfolio_analysis_data["nr_dates_days"][0])
        new_analysis_data = compare_asset(default_asset["asset_ticker"], default_asset["asset_exchange"],
                                          portfolio.benchmark.exchange_ticker, portfolio.benchmark.exchange_id,
                                          portfolio_analysis_data["no_risk_rate"]["ticker"],
                                          risk_free_exchange.exchange_id,
                                          asset_estimator_start_date,
                                          portfolio_analysis_data["all_dates"][-1],
                                          portfolio.currency.ticker)

        if len(portfolio_analysis_data) == 15:
            risk_profile_number = portfolio_analysis_data["risk_profile_number"]

        probe_json_dictionary = {"risk_profile_number": risk_profile_number,
                                 "benchmark_ticker": portfolio.benchmark.exchange_ticker,
                                 "benchmark_exchange": portfolio.benchmark.exchange_id,
                                 "input_start_date": asset_estimator_start_date,
                                 "input_end_date": portfolio_analysis_data["all_dates"][-1],
                                 "currency": portfolio.currency.ticker}
        dataJSON = dumps(probe_json_dictionary)

        context.update({
            "portfolio_analysis_data": portfolio_analysis_data,
            "analysis_date": analysis_date,
            "asset_analysis": new_analysis_data["stats_param"],
            "compare_asset": new_analysis_data["compare_asset"],
            "benchmark_ticker": portfolio.benchmark.exchange_ticker,
            "data": dataJSON,
            "charts_data": {
                "ptf_price_change": portfolio_analysis_data.get("ptf_price_change"),
                "bench_price_change": portfolio_analysis_data.get("bench_price_change"),
                "nr_price_change": portfolio_analysis_data.get("nr_price_change"),
                "no_risk_rate": portfolio_analysis_data.get("no_risk_rate"),
                "cash_by_asset_ticker": portfolio_analysis_data.get("cash_by_asset_ticker"),
                "cash_by_asset_type": portfolio_analysis_data.get("cash_by_asset_type"),
                "benchmark_name": portfolio.benchmark.name
            }})

    return context


def bot_revoke(request):
    if request.method.upper() != 'POST':
        raise Http404

    request.user.profile.tg_token = None
    request.user.profile.tg_chat_id = ''
    request.user.profile.save()
    return redirect(reverse('change_user_settings'))
