
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from home.views import HomeView
from clients.views import CitySearchView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('erp.urls')),
    path('', include('clients.urls')),
    path('', include('items.urls')),
    path('', include('impostos.urls')),
    path('', include('tasks.urls')),
    path('', include('accountings.urls')),
    path('', HomeView.as_view(), name='home'),
    path('ajax/cities/', CitySearchView.as_view(), name='city_search'),    
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
