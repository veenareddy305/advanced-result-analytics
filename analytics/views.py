import json
import logging
import pandas as pd
from .forms import ManualEntryForm
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.db.models import Avg
from django.core.paginator import Paginator

from .models import Result, UploadLog
from .forms import CSVUploadForm, ResultFilterForm
from .utils import (
    build_queryset_from_filters,
    compute_stats,
    import_csv_to_db,
    export_queryset_to_csv,
    export_queryset_to_pdf,
    subject_averages_json,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HOME
# ---------------------------------------------------------------------------

def home(request):
    return redirect("dashboard")


# ---------------------------------------------------------------------------
# CSV UPLOAD
# ---------------------------------------------------------------------------

class UploadCSVView(View):
    template_name = "analytics/upload.html"

    def get(self, request):
        form = CSVUploadForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CSVUploadForm(request.POST, request.FILES)

        if form.is_valid():
            file = request.FILES["csv_file"]
            df = pd.read_csv(file)

            upload_log = UploadLog.objects.create(
                filename=file.name,
                uploaded_by=request.user if request.user.is_authenticated else None,
            )

            success, errors = import_csv_to_db(
                df, form.cleaned_data, upload_log
            )

            upload_log.rows_success = success
            upload_log.rows_failed = len(errors)
            upload_log.save()

            if success:
                messages.success(request, f"{success} records uploaded")

            if errors:
                messages.warning(request, f"{len(errors)} rows failed")

            return redirect("dashboard")

        return render(request, self.template_name, {"form": form})


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------

class DashboardView(View):

    template_name = "analytics/dashboard.html"

    def get(self, request):

        qs = build_queryset_from_filters(request.GET)

        paginator = Paginator(qs, 50)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        if not qs.exists():
            stats = {
                "mode": "overall",
                "average": 0,
                "pass_pct": 0,
                "total": 0,
                "toppers": [],
                "alert": False,
            }
            chart_data = '{"labels": [], "data": []}'
        else:
            stats = compute_stats(qs, request.GET)
            chart_data = subject_averages_json(qs)

        return render(request, self.template_name, {
            "results": page_obj,
            "page_obj": page_obj,
            "stats": stats,
            "chart_data": chart_data,
            "query_string": request.GET.urlencode(),
        })


# ---------------------------------------------------------------------------
# EXPORT (CSV + PDF)
# ---------------------------------------------------------------------------

class ExportView(View):

    def get(self, request):

        qs = build_queryset_from_filters(request.GET)
        fmt = request.GET.get("format", "csv")

        # 🔴 SAFETY
        if not qs.exists():
            messages.warning(request, "No data to export")
            return redirect("dashboard")

        if fmt == "pdf":
            stats = compute_stats(qs, request.GET)

            context = {
                "results": qs,
                "stats": stats,
                "filters": request.GET,
            }

            return export_queryset_to_pdf(qs, context)

        # 🔹 CSV EXPORT
        response = export_queryset_to_csv(qs)

        if response:
            return response

        messages.error(request, "CSV export failed")
        return redirect("dashboard")


# ---------------------------------------------------------------------------
# AJAX CHART
# ---------------------------------------------------------------------------

def ajax_chart_data(request):
    qs = build_queryset_from_filters(request.GET)

    data = {
        "chart": json.loads(subject_averages_json(qs)),
        "stats": compute_stats(qs, request.GET),
    }

    return JsonResponse(data)


# ---------------------------------------------------------------------------
# BRANCH COMPARISON
# ---------------------------------------------------------------------------

def compare_branches(request):

    b1 = request.GET.get("branch1")
    b2 = request.GET.get("branch2")

    year = request.GET.get("academic_year")
    semester = request.GET.get("semester")

    if not b1 or not b2:
        return JsonResponse({"error": "branch1 and branch2 required"}, status=400)

    def compute(branch):

        qs = Result.objects.filter(branch=branch)

        if year:
            qs = qs.filter(academic_year=year)

        if semester:
            qs = qs.filter(semester=semester)

        total = qs.values("usn").distinct().count()
        passed = qs.filter(marks__gte=40).values("usn").distinct().count()

        student_avg = qs.values("usn").annotate(avg_marks=Avg("marks"))

        topper = student_avg.order_by("-avg_marks").first()

        avg_val = student_avg.aggregate(avg=Avg("avg_marks"))["avg"]
        avg = float(avg_val) if avg_val else 0

        pass_pct = (passed / total * 100) if total else 0

        return {
            "avg": round(avg, 2),
            "pass_pct": round(pass_pct, 2),
            "total": total,
            "topper": round(float(topper["avg_marks"]), 2) if topper else 0,
        }

    return JsonResponse({
        b1: compute(b1),
        b2: compute(b2),
    })



class ManualEntryView(View):
    template_name = "analytics/manual_entry.html"

    def get(self, request):
        form = ManualEntryForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = ManualEntryForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Student record added successfully")
            return redirect("dashboard")

        return render(request, self.template_name, {"form": form})
