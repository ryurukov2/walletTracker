from django.urls import path
from . import views

urlpatterns = (
    path('search/', views.wallet_search, name='wallet search'),
)