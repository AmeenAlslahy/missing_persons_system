"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
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
    # Django Admin
    path('admin/', admin.site.urls),
    
    # API Endpoints - إصدار واحد فقط
    path('api/accounts/', include('accounts.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/analytics/', include('analytics.urls')),  # مرة واحدة فقط
    path('api/matching/', include('matching.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/locations/', include('locations.urls')),
    path('api/audit/', include('audit.urls')),
    
    # API Documentation
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Administrative Dashboard - كل مسارات لوحة التحكم في مكان واحد
    path('admin-dashboard/', include('admin_dashboard.urls')),
    
    # Redirects
    path('accounts/login/', RedirectView.as_view(
        url='/admin-dashboard/login/', 
        query_string=True,
        permanent=False
    )),
    
    # Home redirect to dashboard
    path('', RedirectView.as_view(
        url='/admin-dashboard/', 
        permanent=False
    ), name='home'),
    
    # Dashboard redirects - توحيد جميع المسارات
    path('dashboard/', RedirectView.as_view(
        url='/admin-dashboard/', 
        permanent=True
    ), name='dashboard'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # إضافة مسارات للتطوير فقط
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()