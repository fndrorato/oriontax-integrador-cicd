from django.urls import path
from shopsim.views import (
    PriceQuoteCreateView,
    PriceQuoteSimulationListView,
    PriceQuoteSimulationDeleteView,
    PriceQuoteSimulationUpdateView,
)


urlpatterns = [
    path('simulacao-compras/', PriceQuoteSimulationListView.as_view(), name='simulation_shop_list'),
    path('simulacao-compras/new/', PriceQuoteCreateView.as_view(), name='pricequote_create'),
    path('simulacao-compras/<int:pk>/editar/', PriceQuoteSimulationUpdateView.as_view(), name='simulation_edit_shop'),
    path('simulacao-compras/<int:pk>/delete/', PriceQuoteSimulationDeleteView.as_view(), name='simulation_delete_shop'),
        
]
