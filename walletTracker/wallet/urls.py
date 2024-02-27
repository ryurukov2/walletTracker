from django.urls import path
from . import views

urlpatterns = (
    path('search/', views.wallet_search, name='wallet search'),
    path('<str:wallet_address>/transactions/', views.TransactionsListView.as_view(), name='transactions list'),
)