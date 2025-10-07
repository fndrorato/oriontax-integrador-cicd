from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from home.views import HomeView, SearchResultsView, SelectModuleView, SetActiveModuleView
from clients.views import CitySearchView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('', include('accounts.urls')),
    path('', include('erp.urls')),
    path('', include('clients.urls')),
    path('', include('items.urls')),
    path('', include('impostos.urls')),
    path('', include('tasks.urls')),
    path('', include('accountings.urls')),
    path('', include('notifications.urls')),
    path('', include('cattles.urls')),
    path('', include('shopsim.urls')),
    path('', include('pricing.urls')),
    path('', HomeView.as_view(), name='home'),
    path('search/', SearchResultsView.as_view(), name='search'),
    path('select-module/<str:module_key>/', SetActiveModuleView.as_view(), name='set_active_module'),
    path('select-module/', SelectModuleView.as_view(), name='select_module'),
    path('ajax/cities/', CitySearchView.as_view(), name='city_search'),    
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)