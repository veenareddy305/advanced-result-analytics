from django.urls import path
from . import views

urlpatterns = [
    # Home (redirects to dashboard)
    path('', views.home, name='home'),

    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # Upload CSV
    path('upload/', views.UploadCSVView.as_view(), name='upload'),

    # Export (CSV / PDF)
    path('export/', views.ExportView.as_view(), name='export'),

    # AJAX (charts)
    path('ajax/chart-data/', views.ajax_chart_data, name='ajax_chart_data'),

    # Branch comparison
    path('compare/', views.compare_branches, name='compare'),

    path('manual/', views.ManualEntryView.as_view(), name='manual_entry'),
]