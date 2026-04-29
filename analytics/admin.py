from django.contrib import admin
from .models import Student, Subject, Result, Backlog, UploadLog


# =========================
# INLINE (Result inside Student)
# =========================
class ResultInline(admin.TabularInline):
    model = Result
    extra = 0
    autocomplete_fields = ['subject']
    fields = ('subject', 'semester', 'year', 'marks', 'grade', 'is_pass', 'attempt')
    readonly_fields = ('is_pass',)


# =========================
# STUDENT ADMIN
# =========================
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):

    inlines = [ResultInline]

    list_display = (
        'usn', 'name', 'branch', 'section',
        'batch_year', 'actual_category', 'cet_rank'
    )

    search_fields = ('usn', 'name')

    list_filter = (
        'branch', 'section', 'batch_year',
        'actual_category', 'admission_quota'
    )

    ordering = ('usn',)

    list_per_page = 25


# =========================
# SUBJECT ADMIN
# =========================
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):

    list_display = (
        'code', 'name', 'branch', 'semester', 'faculty'
    )

    search_fields = ('code', 'name')

    list_filter = ('branch', 'semester')

    ordering = ('semester', 'code')


# =========================
# RESULT ADMIN (CORE TABLE)
# =========================
@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):

    list_display = (
        'student', 'subject', 'semester', 'year',
        'marks', 'grade', 'is_pass', 'is_backlog', 'attempt'
    )

    search_fields = (
        'student__usn', 'student__name',
        'subject__code', 'subject__name'
    )

    list_filter = (
        'semester', 'year', 'is_pass',
        'is_backlog', 'attempt'
    )

    ordering = ('-year', 'semester')

    list_editable = ('marks', 'grade')

    autocomplete_fields = ['student', 'subject']

    list_per_page = 50


# =========================
# SGPA ADMIN
# =========================

# =========================
# BACKLOG ADMIN
# =========================
@admin.register(Backlog)
class BacklogAdmin(admin.ModelAdmin):

    list_display = (
        'student', 'subject', 'semester',
        'year', 'cleared', 'cleared_year'
    )

    search_fields = (
        'student__usn', 'student__name',
        'subject__code', 'subject__name'
    )

    list_filter = (
        'semester', 'year', 'cleared'
    )

    ordering = ('-year',)

    list_per_page = 25


# =========================
# UPLOAD LOG ADMIN
# =========================
@admin.register(UploadLog)
class UploadLogAdmin(admin.ModelAdmin):

    list_display = (
        'filename', 'uploaded_at',
        'records_added', 'records_rejected', 'status'
    )

    search_fields = ('filename',)

    list_filter = ('status', 'uploaded_at')

    readonly_fields = (
        'uploaded_at',
        'records_added',
        'records_rejected',
        'rejected_rows',
        'errors'
    )

    ordering = ('-uploaded_at',)

    list_per_page = 20