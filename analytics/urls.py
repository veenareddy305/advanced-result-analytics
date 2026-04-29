from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('subject/', views.subject_view, name='subject'),
    path('category/', views.category, name='category'),
    path('branch/', views.branch, name='branch'),
    path('backlog/', views.backlog, name='backlog'),
    path('upload/', views.upload, name='upload'),
    path('quota/', views.quota, name='quota'),
    path('download-report/', views.download_report, name='download_report'),
    path('download-report-excel/', views.download_report_excel),
    path('single-cumulative-backlog/', views.single_student_cumulative_backlog),
    path('download-subject-report/', views.download_subject_report),
    path('download-category-report/', views.download_category_report),
    path('download-branch-report/', views.download_branch_report),
    path('download-backlog-report/', views.download_backlog_report),
]