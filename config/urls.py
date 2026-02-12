"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="Missing Persons System API",
      default_version='v1',
      description="API documentation for Missing Persons System",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@missing.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Endpoints
    path('api/accounts/', include('accounts.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/matching/', include('matching.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/analytics/', include('analytics.urls')),
    
    # Documentation
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Administrative Dashboard
    path('admin-dashboard/', include('admin_dashboard.urls')),
    
    # Redirection for default login path
    path('accounts/login/', RedirectView.as_view(url='/admin-dashboard/login/', query_string=True)),
    
    # Dashboard
    path('', RedirectView.as_view(url='admin-dashboard/'), name='home'),
    path('dashboard/', RedirectView.as_view(url='/admin-dashboard/'), name='dashboard'),
    path('dashboard/reports/', TemplateView.as_view(template_name='reports/reports.html'), name='dashboard-reports'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
