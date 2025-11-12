from django.urls import path

from . import views

urlpatterns = [
    path('', views.InputDataView.as_view(), name="backtest"),
    path('input_data/', views.InputDataView.as_view(), name="backtest-input-page"),
    path('analyze_portfolio/', views.view_analyze, name="backtest-analyze-page"),
    path('save_result/', views.view_save, name="backtest-save-page"),
    # re_path('^ajax/autocomplete/', views.ajax_autocomplete, name="backtest-autocomplete"),
    path('ajax/autocomplete/', views.autocomplete, name="backtest-autocomplete"),
    path('ajax/add_asset/', views.add_asset, name="add-asset"),
    path('ajax/select_box/', views.search_asset, name="search-asset"),
    path('ajax/analyze_portfolio/relative_values/', views.portfolio_relative_values, name="portfolio-relative-values"),
    path('ajax/ajax_compare/', views.ajax_compare, name="ajax_compare"),
    # path('populate/', views.populate_db),
]

