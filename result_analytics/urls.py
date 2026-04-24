from django.contrib import admin
from django.urls import path, include
from analytics.views import DashboardView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Home → dashboard
    path('', DashboardView.as_view(), name='home'),

    # API routes
    path('api/', include('analytics.urls')),
]