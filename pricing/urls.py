from django.urls import path
from pricing.views import (
    UpdateFixedExpensesView,
    CreateCostsView,
    PricingCreateView,
    PricingUpdateView,
    PricingDeleteView,
    PricingListView,
)

urlpatterns = [   
    path('precificacao/', PricingListView.as_view(), name='pricing_list'),
    path('precificacao/new/', PricingCreateView.as_view(), name='pricing_simulation'),               
    path('precificacao/<int:pk>/editar/', PricingUpdateView.as_view(), name='pricing_edit'),
    path('precificacao/<int:pk>/delete/', PricingDeleteView.as_view(), name='pricing_delete'),
    path('precificacao/despesas-fixas/', UpdateFixedExpensesView.as_view(), name='update_fixed_expenses'),    
    path('costs/create/', CreateCostsView.as_view(), name='create_user_costs'),
]
