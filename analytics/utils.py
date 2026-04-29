import pandas as pd
from django.db.models import Avg

# =========================
# REQUIRED COLUMNS
# =========================
REQUIRED_COLUMNS = [
    'USN',
    'Name',
    'Branch',
    'Batch',
    'Semester',
    'Subject Code',
    'Subject Name',
    'Marks',
    'SGPA',
    'Category',
    'Admission Quota'
]


# =========================
# CSV / EXCEL PARSER
# =========================
def parse_csv(file):
    valid = []
    rejected = []
    errors = []

    # ===== READ FILE =====
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
    except Exception as e:
        return [], [], [f"File read error: {str(e)}"]

    # ===== COLUMN VALIDATION =====
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return [], [], [f"Missing columns: {', '.join(missing)}"]

    # ===== CLEAN DATA =====
    df = df.dropna(subset=['USN', 'Subject Code', 'Marks', 'SGPA'])

    # ===== PROCESS ROWS =====
    for index, row in df.iterrows():
        try:
            marks = float(row['Marks'])
            sgpa = float(row['SGPA'])

            # ===== VALIDATION RULES =====
            if not (0 <= marks <= 100):
                rejected.append({**row.to_dict(), "error": "Invalid Marks"})
                continue

            if not (0 <= sgpa <= 10):
                rejected.append({**row.to_dict(), "error": "Invalid SGPA"})
                continue

            valid.append({
                "usn": str(row['USN']).strip(),
                "name": str(row['Name']).strip(),
                "branch": str(row['Branch']).strip(),
                "batch": str(row['Batch']).strip(),
                "semester": int(row['Semester']),
                "subject_code": str(row['Subject Code']).strip(),
                "subject_name": str(row['Subject Name']).strip(),
                "marks": marks,
                "sgpa": sgpa,
                "category": str(row['Category']).strip(),
                "quota": str(row['Admission Quota']).strip()
            })

        except Exception as e:
            rejected.append({**row.to_dict(), "error": str(e)})

    return valid, rejected, errors


# =========================
# METRICS CALCULATION
# =========================
def get_metrics(queryset):
    total = queryset.count()

    if total == 0:
        return {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'avg_marks': 0,
            'avg_sgpa': 0,
            'pass_pct': 0
        }

    passed = queryset.filter(marks__gte=35).count()
    failed = total - passed

    avg_marks = queryset.aggregate(avg=Avg('marks'))['avg']
    avg_sgpa = queryset.aggregate(avg=Avg('sgpa'))['avg']

    return {
        'total': total,
        'passed': passed,
        'failed': failed,
        'avg_marks': round(avg_marks or 0, 2),
        'avg_sgpa': round(avg_sgpa or 0, 2),
        'pass_pct': round((passed / total) * 100, 2)
    }


# =========================
# OPTIONAL: BULK SAVE HELPER
# =========================
def save_valid_data(valid_data, Student, Subject, Result):
    for row in valid_data:

        student, _ = Student.objects.get_or_create(
            usn=row['usn'],
            defaults={
                'name': row['name'],
                'branch': row['branch'],
                'batch': row['batch']
            }
        )

        subject, _ = Subject.objects.get_or_create(
            code=row['subject_code'],
            defaults={'name': row['subject_name']}
        )

        Result.objects.create(
            student=student,
            subject=subject,
            marks=row['marks'],
            sgpa=row['sgpa'],
            category=row['category'],
            admission_quota=row['quota'],
            semester=row['semester']
        )