from django.urls import path
from cattles.views import (
    MatrixSimulationCreateView, 
    MatrixSimulationListView,
    MatrixSimulationUpdateView,
    MatrixSimulationDeleteView,
    
    UpdateButcheryView,
    CreateMeatCutView,
    OperationGadoView,
)

urlpatterns = [
    path('cattles/simulation/', MatrixSimulationListView.as_view(), name='simulation_list'),
    path('cattles/simulation/new/', MatrixSimulationCreateView.as_view(), name='simulation_create_matrix_cattle'),
    path('cattles/simulation/<int:pk>/editar/', MatrixSimulationUpdateView.as_view(), name='simulation_edit_matrix_cattle'),
    path('cattles/simulation/<int:pk>/delete/', MatrixSimulationDeleteView.as_view(), name='simulation_delete_matrix_cattle'),
    
    path('cattles/butchery/', UpdateButcheryView.as_view(), name='update_butchery'),
    path('meatcut/create/', CreateMeatCutView.as_view(), name='create_meatcut'),
    path('operacao-gado/', OperationGadoView.as_view(), name='operation_gado')


]
