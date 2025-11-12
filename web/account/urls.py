from django.urls import path
from django.conf.urls import url
from . import views

urlpatterns = [
    path('', views.AccountHomeView.as_view(), name="account-page"),
    path('portfolios/<int:pk>/', views.PortfoliosDetailView.as_view(), name="account-page-portfolios-detail"),
    path('portfolios/<int:pk>/change_settings/', views.PortfolioChangeSettingsView.as_view(),
         name="account-portfolio-change-settings"),
    path('portfolios/change_settings/', views.MyPortfolioChangeSettingsView.as_view(),
         name="my-account-portfolio-change-settings"),
    path('portfolios/<int:pk>/analyze/', views.PortfolioAnalyzeView.as_view(),
         name="account-portfolio-analyze"),
    path('portfolios/<int:pk>/delete/', views.PortfolioDeleteView.as_view(),
         name="account-portfolio-delete"),
    path('portfolios/<int:pk>/relative_values/', views.PortfolioRelativeValues.as_view(),
         name="account-portfolio-relative-values"),
    path('portfolios/add/', views.MyPortfolioAddView.as_view(),
         name="account-portfolio-add"),
    path('portfolios/<int:pk>/operations/', views.OperationsListCreateView.as_view(), name="account-operations"),
    # path('portfolios/<int:pk>/operations/', views.OperationAddView.as_view(), name="account-operations-add"),
    path('operations/<int:pk>/delete/', views.OperationsDeleteView.as_view(),
         name="account-operations-delete"),
    path('ajax/ajax_delete_operation/', views.ajax_delete_operation, name="my_delete_operation"),
    path('ajax/autocomplete/', views.autocomplete, name="account-autocomplete"),
    path('ajax/get_portfolio_params/', views.get_portfolio_params, name="portfolio_params"),
    path('change_user_settings/', views.change_user_settings, name="change_user_settings"),
    path('risk_profile/', views.risk_profile, name="risk_profile"),
    path('bot_revoke/', views.bot_revoke, name="bot_revoke"),
    path('change_password_mail/', views.change_password_mail, name="change_password_mail"),
    url(r'^change_password/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,50}-[0-9A-Za-z]{1,50})/$',
        views.change_password, name='change_password'),
]
