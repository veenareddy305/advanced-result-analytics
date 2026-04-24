"""
utils.py
--------
Helper functions used by views.py:
  - build_queryset_from_filters   : applies GET params to Result queryset
  - compute_stats                 : calculates avg, pass%, toppers from a queryset
  - import_csv_to_db              : saves validated DataFrame rows to Result model
  - export_queryset_to_csv        : streams a CSV HttpResponse
  - export_queryset_to_pdf        : generates a PDF via WeasyPrint (optional dep)
  - subject_averages_json         : data payload for Chart.js bar/line chart
"""
import io
import json
import logging
from decimal import Decimal
from django.db import transaction
import pandas as pd
from django.db.models import Avg, Count, Q, FloatField
from django.db.models.functions import Cast
from django.http import HttpResponse, StreamingHttpResponse

from .models import Result, UploadLog, compute_grade

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Queryset helpers (CO3)
# ---------------------------------------------------------------------------

def build_queryset_from_filters(params):
    qs = Result.objects.all()

    if params.get('academic_year'):
        qs = qs.filter(academic_year=params['academic_year'])

    if params.get('branch'):
        qs = qs.filter(branch=params['branch'])

    if params.get('semester'):
        qs = qs.filter(semester=params['semester'])

    if params.get('subject'):
        qs = qs.filter(subject__icontains=params['subject'])

    if params.get('usn'):
        qs = qs.filter(usn__icontains=params['usn'])

    if params.get('student_name'):
        qs = qs.filter(student_name__icontains=params['student_name'])

    if params.get('min_marks'):
        qs = qs.filter(marks__gte=params['min_marks'])

    if params.get('max_marks'):
        qs = qs.filter(marks__lte=params['max_marks'])

    return qs

# ---------------------------------------------------------------------------
# Statistics (CO3)
# ---------------------------------------------------------------------------

def compute_stats(qs, params):

    subject = params.get('subject')

    # total students (distinct)
    total = qs.values('usn').distinct().count()

    # pass %
    passed = qs.filter(marks__gte=40).values('usn').distinct().count()
    pass_pct = (passed / total * 100) if total else 0

    # 🔴 ALERT FLAG
    alert = pass_pct < 40

    # 🔹 SUBJECT MODE
    if subject:
        avg_val = qs.aggregate(avg=Avg('marks'))['avg']
        avg = float(avg_val) if avg_val else 0

        toppers = qs.order_by('-marks').values('usn', 'marks')[:5]

        return {
            "mode": "subject",
            "average": round(avg, 2),
            "pass_pct": round(pass_pct, 2),
            "total": total,
            "toppers": toppers,
            "alert": alert,
        }

    # 🔹 OVERALL MODE
    student_avg = qs.values('usn').annotate(avg_marks=Avg('marks'))

    avg_val = student_avg.aggregate(avg=Avg('avg_marks'))['avg']
    avg = float(avg_val) if avg_val else 0

    toppers = student_avg.order_by('-avg_marks')[:5]

    return {
        "mode": "overall",
        "average": round(avg, 2),
        "pass_pct": round(pass_pct, 2),
        "total": total,
        "toppers": toppers,
        "alert": alert,
    }

def subject_averages_json(queryset):
    """
    Returns a JSON-serialisable dict suitable for Chart.js:
    { labels: [...], data: [...], pass_pcts: [...] }
    CO3 + CO5
    """
    rows = (
        queryset
        .values('subject')
        .annotate(avg=Avg('marks'), total=Count('id'))
        .order_by('subject')
    )

    labels, averages, pass_pcts = [], [], []
    for row in rows:
        pass_count = queryset.filter(subject=row['subject'], marks__gte=40).count()
        pct = round(pass_count / row['total'] * 100, 1) if row['total'] else 0
        labels.append(row['subject'])
        averages.append(round(float(row['avg']), 2) if row['avg'] else 0)
        pass_pcts.append(pct)

    return json.dumps({'labels': labels, 'data': averages, 'pass_pcts': pass_pcts})


def grade_distribution_json(queryset):
    """Returns grade distribution data for pie/doughnut chart."""
    grade_order = ['O', 'A+', 'A', 'B+', 'B', 'C', 'P', 'F', 'AB']
    rows = (
        queryset
        .values('grade')
        .annotate(count=Count('id'))
    )
    grade_map = {r['grade']: r['count'] for r in rows}
    labels = [g for g in grade_order if g in grade_map]
    data   = [grade_map[g] for g in labels]
    return json.dumps({'labels': labels, 'data': data})


# ---------------------------------------------------------------------------
# CSV Import (CO2)
# ---------------------------------------------------------------------------

def import_csv_to_db(df, form_data, upload_log, overwrite=False):
    """
    Atomic CSV import:
    Any error → NOTHING saved
    All valid → EVERYTHING saved
    """

    if df is None or df.empty:
        return 0, [{"error": "Empty file"}]

    success = 0

    branch_override   = form_data.get('branch')
    semester_override = form_data.get('semester')

    try:
        with transaction.atomic():

            for idx, row in df.iterrows():

                branch   = branch_override or str(row.get('branch', '')).strip().upper()
                semester = semester_override or str(row.get('semester', '')).strip()
                subject  = str(row.get('subject', '')).strip()
                usn      = str(row.get('usn', '')).strip().upper()

                # ❌ STRICT VALIDATION
                if not usn or not subject:
                    raise ValueError(f"Row {idx+2}: Empty USN or Subject")

                marks_raw = row.get('marks')
                if pd.isna(marks_raw):
                    raise ValueError(f"Row {idx+2}: Missing marks")

                marks = Decimal(str(float(marks_raw))).quantize(Decimal('0.01'))

                defaults = {
                    'student_name': str(row.get('student_name', '')).strip(),
                    'branch':       branch,
                    'semester':     semester,
                    'subject_code': str(row.get('subject_code', '')).strip(),
                    'marks':        marks,
                    'max_marks':    int(row.get('max_marks', 100)),
                    'exam_type':    str(row.get('exam_type', 'SEE')).strip().upper(),
                    'academic_year': str(row.get('academic_year', '2024-25')).strip(),
                    'upload_log':   upload_log,
                }

                if overwrite:
                    Result.objects.update_or_create(
                        usn=usn, subject=subject,
                        defaults=defaults
                    )
                else:
                    obj, created = Result.objects.get_or_create(
                        usn=usn, subject=subject,
                        defaults=defaults
                    )
                    if not created:
                        raise ValueError(f"Row {idx+2}: Duplicate {usn}/{subject}")

                success += 1

    except Exception as e:
        # 🔴 ANY ERROR → ROLLBACK EVERYTHING
        return 0, [{"error": str(e)}]

    return success, []


# ---------------------------------------------------------------------------
# CSV Export (CO4)
# ---------------------------------------------------------------------------

class _EchoBuffer:
    """Minimal write() wrapper for StreamingHttpResponse."""
    def write(self, value):
        return value


def export_queryset_to_csv(queryset, filename='results_export.csv'):
    """
    Stream a CSV file from a queryset.
    CO4 – HttpResponse with content_type='text/csv'.
    """
    import csv

    fields = [
        'usn', 'student_name', 'branch', 'semester',
        'subject', 'subject_code', 'marks', 'max_marks',
        'grade', 'exam_type', 'academic_year',
    ]
    headers = [f.replace('_', ' ').title() for f in fields]

    pseudo_buffer = _EchoBuffer()
    writer = csv.writer(pseudo_buffer)

    def generate():
        yield writer.writerow(headers)
        for r in queryset.values_list(*fields):
            yield writer.writerow(r)

    response = StreamingHttpResponse(generate(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# PDF Export (CO4) – requires WeasyPrint
# ---------------------------------------------------------------------------

def export_queryset_to_pdf(queryset, context, template_name='analytics/export_pdf.html'):
    """
    Render a Django template to PDF using WeasyPrint.
    Falls back gracefully if WeasyPrint is not installed.
    """
    try:
        from weasyprint import HTML
        from django.template.loader import render_to_string

        html_string = render_to_string(template_name, context)
        pdf_bytes = HTML(string=html_string).write_pdf()

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="results_report.pdf"'
        return response

    except ImportError:
        logger.error("WeasyPrint not installed. Falling back to CSV export.")
        return None
    except Exception as e:
        logger.error("PDF generation failed: %s", e)
        return None