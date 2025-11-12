from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers
from sentry_sdk import capture_exception

from account.cache import PortfolioCache
from account.models import Profile
from backtest.models import Asset
from backtest.tasks import update_bot_profile
from backtest.templatetags.backtest import smart_round


class ProfileTelegramSerializer(serializers.ModelSerializer):
    portfolios = serializers.SerializerMethodField(source='get_portfolios')

    class Meta:
        model = Profile
        fields = ('id', 'tg_chat_id', 'portfolios', 'send_notify_dividends', 'send_notify_report_date')

    def get_portfolios(self, profile):
        """
            Возвращает список портфелей и их тексстовое представление для бота
            #
            # Риск портфеля: агрессивный
            # Ваш инвестиционный профиль: умеренный
            # «Портфель не соответсвует Вашему профилю» или «Портфель «соответсвует Вашему профилю»
            #
            # Изменение за вчера = ; за месяц =
            # Доходность (CAGR) =
            # Риск (волатильность) =
            # Коэф. Шарпа =
            #
            # • Бенчмарк | {portfolio.benchmark.name}
            # Изменение за вчера = ; за месяц =
            # Доходность (CAGR) =
            # Риск (волатильность) =
            # Коэф. Шарпа =
        """
        data = {}
        portfolios = profile.profile_portfolios.all()

        all_dividends_assets_one_day_remaining = set()
        all_reports_assets_one_day_remaining = set()

        all_dividends_assets = set()
        all_reports_assets = set()

        for portfolio in portfolios:
            warning = None

            ptf_cache = self.ptf_cache = PortfolioCache(portfolio)
            cache = ptf_cache.get()
            if cache is None:
                update_bot_profile(portfolio.id)

                ptf_cache = self.ptf_cache = PortfolioCache(portfolio)
                cache = ptf_cache.get()

            base_warning = "Портфельные коэффициенты и корреляционная матрица не рассчитываются для портфелей с периодом существования менее 30 недель."

            risk_profile_name = None
            risk_profile_number = None
            gagr = None
            gagr_bench = None
            vol = None
            vol_bench = None
            sharp = None
            sharp_bench = None

            abs_ptf_all = portfolio.get_ptf_all()
            abs_ptf_month = portfolio.get_ptf_month()
            abs_ptf_yesterday = portfolio.get_ptf_yesterday()
            abs_bench_all = portfolio.get_bench_all()
            abs_bench_month = portfolio.get_bench_month()
            abs_bench_yesterday = portfolio.get_bench_yesterday()

            portfolio_analysis_data = cache.get('portfolio_analysis_data') if cache else None

            if portfolio_analysis_data:
                risk_profile_name = portfolio_analysis_data.get('risk_profile_name')
                risk_profile_number = portfolio_analysis_data.get('risk_profile_number')

                stats_param = portfolio_analysis_data.get('stats_param')
                if stats_param:
                    base_gagr_data = stats_param['gagr']
                    base_vol_data = stats_param['vol']
                    base_sharp_data = stats_param['sharp']

                    gagr = str(smart_round(base_gagr_data['value_portfolio'])) + base_gagr_data['unit']
                    gagr_bench = str(smart_round(base_gagr_data['value_benchmark'])) + base_gagr_data['unit']
                    vol = str(smart_round(base_vol_data['value_portfolio'])) + base_vol_data['unit']
                    vol_bench = str(smart_round(base_vol_data['value_benchmark'])) + base_vol_data['unit']
                    sharp = str(smart_round(base_sharp_data['value_portfolio']))
                    sharp_bench = str(smart_round(base_sharp_data['value_benchmark']))
                else:
                    warning = base_warning
            else:
                warning = base_warning

            text_message = f"<b>Название портфеля</b>: {portfolio.get_name()}"
            text_message += f"\n<b>Риск портфеля</b>: {risk_profile_name}"
            if risk_profile_number:
                text_message += f' ({risk_profile_number}/5)'
            text_message += f"\n<b>Ваш риск-профиль</b>: {profile.actual_r_test.result_name if profile.actual_r_test else 'не определен'}"
            if profile.actual_r_test:
                text_message += f' ({profile.actual_r_test.number}/5)'

            if warning:
                text_message += '\n\n❗️ Внимание'
                text_message += f'\n{warning}'

            text_message += '\n'
            text_message += '\n'
            text_message += f'🔹 Ваш портфель | 🔸 {portfolio.benchmark.name}'
            text_message += '\n'

            if abs_ptf_yesterday and abs_bench_yesterday:
                text_message += f'\n • Изменение за вчера = {abs_ptf_yesterday} | {abs_bench_yesterday}'

            if abs_ptf_month and abs_bench_month:
                text_message += f'\n • Изменение за месяц = {abs_ptf_month} | {abs_bench_month}'

            if abs_ptf_all and abs_bench_all:
                text_message += f'\n • Изменение за всё время = {abs_ptf_all} | {abs_bench_all}'

            if gagr and gagr_bench:
                text_message += f'\n • Доходность (CAGR) = {gagr} | {gagr_bench}'

            if vol and vol_bench:
                text_message += f'\n • Риск (волатильность) = {vol} | {vol_bench}'

            if sharp and sharp_bench:
                text_message += f'\n • Коэф. Шарпа = {sharp} | {sharp_bench}'

            dividends_assets_one_day_remaining = set()
            reports_assets_one_day_remaining = set()

            dividends_assets = set()
            reports_assets = set()
            open_positions = cache.get('open_positions', [])
            for open_position in open_positions:
                asset = open_position['asset']

                if asset['name'] in ['USD', 'RUB']:
                    continue

                try:
                    asset = Asset.objects.get(exchange__code=asset['exchange'], exchange_ticker=asset['exchange_ticker'])
                except Asset.DoesNotExist:
                    continue
                if not asset or not asset.fund_attributes:
                    continue
                if asset.fund_attributes.ex_dividend_date and asset.fund_attributes.ex_dividend_date > timezone.now().date():
                    dividends_assets.add(asset)
                    all_dividends_assets.add(asset)

                if asset.fund_attributes.report_date:
                    all_reports_assets.add(asset)
                    reports_assets.add(asset)

                if asset.fund_attributes and asset.fund_attributes.ex_dividend_date and asset.fund_attributes.ex_dividend_date == (timezone.now() + timedelta(days=1)).date():
                    dividends_assets_one_day_remaining.add(asset)
                    all_dividends_assets_one_day_remaining.add(asset)
                if asset.fund_attributes and asset.fund_attributes.report_date and asset.fund_attributes.report_date == (timezone.now() + timedelta(days=1)).date():
                    reports_assets_one_day_remaining.add(asset)
                    all_reports_assets_one_day_remaining.add(asset)

            dividends_text, reports_text = self.get_notify_text(dividends_assets, reports_assets, portfolio)
            dividends_text_one_day_remaining, reports_text_one_day_remaining = self.get_notify_text(
                dividends_assets_one_day_remaining, reports_assets_one_day_remaining, portfolio
            )

            data[str(portfolio.id)] = {
                'name': portfolio.get_name(),
                'id': portfolio.id,
                'text': text_message,
                'dividends_text': dividends_text,
                'reports_text': reports_text,
                'dividends_text_one_day_remaining': dividends_text_one_day_remaining,
                'reports_text_one_day_remaining': reports_text_one_day_remaining,
            }

        all_dividends_text_one_day_remaining, all_reports_text_one_day_remaining = self.get_notify_text(
            all_dividends_assets_one_day_remaining, all_reports_assets_one_day_remaining, is_periodic=True
        )

        all_dividends_text, all_reports_text = self.get_notify_text(
            all_dividends_assets, all_reports_assets
        )

        total_data = {
            'all_dividends_text': all_dividends_text,
            'all_reports_text': all_reports_text,
            'all_dividends_text_one_day_remaining': all_dividends_text_one_day_remaining,
            'all_reports_text_one_day_remaining': all_reports_text_one_day_remaining
        }

        return {'data': data, 'total_data': total_data}

    @staticmethod
    def get_notify_text(dividends_assets, reports_assets, portfolio=None, is_periodic=False):
        dividends_header = '#Дивиденды: '
        reports_header = '#Отчетность: '
        if portfolio:
            dividends_header += f'график выплат по портфелю <b>{portfolio.get_name()}</b>'
            reports_header += f'график по портфелю <b>{portfolio.get_name()}</b>'
        elif is_periodic is True:
            dividends_header += 'остался 1 день'
            reports_header += 'остался 1 день'
        else:
            dividends_header += 'график выплат по всем портфелям'
            reports_header += 'график по всем портфелям'

        dividends_header += '\n'
        reports_header += '\n'

        reports_text = ''
        dividends_text = ''

        reports_assets = sorted(reports_assets, key=lambda i: i.fund_attributes.report_date)
        dividends_assets = sorted(dividends_assets, key=lambda i: i.fund_attributes.ex_dividend_date)

        for asset in reports_assets:
            reports_text += f'\n • #{asset.exchange_ticker} - {asset.fund_attributes.report_date.strftime("%d-%m-%Y")}'

        for asset in dividends_assets:
            dividends_text += f'\n • #{asset.exchange_ticker} - {asset.fund_attributes.ex_dividend_date.strftime("%d-%m-%Y")}'
            dividends_text += f'\n Тек. размер дивиденда = {asset.fund_attributes.dividend_share}, доходность = {asset.fund_attributes.dividend_yield}%'

        if dividends_text:
            dividends_text = f'\n\n{dividends_header}' + dividends_text
        else:
            if is_periodic is False:
                dividends_text = '\n\n ❗️ Запрашиваемая информация не найдена'

        if reports_text:
            reports_text = f'\n\n{reports_header}' + reports_text
        else:
            if is_periodic is False:
                reports_text = '\n\n ❗️ Запрашиваемая информация не найдена'

        return dividends_text, reports_text
