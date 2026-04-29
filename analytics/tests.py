"""
tests.py
--------
Test suite for Advanced Result Analytics Suite.
Run with:  python manage.py test analytics
"""
import io
import json
import csv

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Result, UploadLog, compute_grade
from .forms import CSVUploadForm
from .utils import (
    build_queryset_from_filters,
    compute_stats,
    subject_averages_json,
    grade_distribution_json,
    import_csv_to_db,
)


# ---------------------------------------------------------------------------
# Helper: build a minimal in-memory CSV file
# ---------------------------------------------------------------------------

def make_csv_file(rows, headers=None):
    """Return a BytesIO object that looks like an uploaded CSV file."""
    if headers is None:
        headers = ['usn', 'student_name', 'branch', 'semester',
                   'subject', 'marks', 'exam_type', 'academic_year']
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    content = buf.getvalue().encode('utf-8')
    f = io.BytesIO(content)
    f.name = 'test_results.csv'
    f.size = len(content)
    return f


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class ResultModelTest(TestCase):

    def _make_result(self, marks):
        return Result.objects.create(
            usn='1CS21CS001',
            branch='CSE',
            semester='5',
            subject='DBMS',
            marks=marks,
        )

    def test_grade_outstanding(self):
        r = self._make_result(95)
        self.assertEqual(r.grade, 'O')

    def test_grade_fail(self):
        r = self._make_result(30)
        self.assertEqual(r.grade, 'F')

    def test_grade_absent(self):
        r = self._make_result(None)
        self.assertEqual(r.grade, 'AB')

    def test_is_pass_true(self):
        r = self._make_result(50)
        self.assertTrue(r.is_pass)

    def test_is_pass_false(self):
        r = self._make_result(38)
        self.assertFalse(r.is_pass)

    def test_percentage(self):
        r = self._make_result(75)
        self.assertAlmostEqual(r.percentage, 75.0)

    def test_str(self):
        r = self._make_result(80)
        self.assertIn('1CS21CS001', str(r))

    def test_grade_boundaries(self):
        cases = [(100, 'O'), (90, 'O'), (89, 'A+'), (80, 'A+'),
                 (79, 'A'), (70, 'A'), (69, 'B+'), (60, 'B+'),
                 (59, 'B'), (55, 'B'), (54, 'C'), (50, 'C'),
                 (49, 'P'), (40, 'P'), (39, 'F'), (0, 'F')]
        for marks, expected in cases:
            self.assertEqual(compute_grade(marks), expected, f"marks={marks}")


class UploadLogModelTest(TestCase):

    def test_create_log(self):
        log = UploadLog.objects.create(filename='test.csv', rows_success=10)
        self.assertEqual(str(log), 'test.csv @ ' + log.uploaded_at.strftime('%Y-%m-%d %H:%M'))


# ---------------------------------------------------------------------------
# Form tests (CO2)
# ---------------------------------------------------------------------------

class CSVUploadFormTest(TestCase):

    def _submit_form(self, csv_file, branch='CSE', semester='5'):
        return CSVUploadForm(
            data={'branch': branch, 'semester': semester, 'overwrite_existing': False},
            files={'csv_file': csv_file},
        )

    def test_valid_csv(self):
        f = make_csv_file([
            ['1CS21CS001', 'Alice', 'CSE', '5', 'DBMS', 78, 'SEE', '2024-25'],
            ['1CS21CS002', 'Bob',   'CSE', '5', 'DBMS', 55, 'SEE', '2024-25'],
        ])
        form = self._submit_form(f)
        self.assertTrue(form.is_valid(), form.errors)
        df = form.get_dataframe()
        self.assertEqual(len(df), 2)

    def test_missing_required_column(self):
        # CSV without 'marks' column
        buf = io.BytesIO(b'usn,subject\n1CS001,DBMS\n')
        buf.name = 'bad.csv'
        buf.size = len(b'usn,subject\n1CS001,DBMS\n')
        form = self._submit_form(buf)
        self.assertFalse(form.is_valid())
        self.assertIn('marks', str(form.errors))

    def test_non_csv_file_rejected(self):
        buf = io.BytesIO(b'not a csv')
        buf.name = 'file.xlsx'
        buf.size = 9
        form = self._submit_form(buf)
        self.assertFalse(form.is_valid())

    def test_empty_csv_rejected(self):
        buf = io.BytesIO(b'usn,subject,marks\n')
        buf.name = 'empty.csv'
        buf.size = 18
        form = self._submit_form(buf)
        self.assertFalse(form.is_valid())

    def test_invalid_marks_rejected(self):
        f = make_csv_file([['1CS001', 'Alice', 'CSE', '5', 'DBMS', 150, 'SEE', '2024-25']])
        form = self._submit_form(f)
        self.assertFalse(form.is_valid())

    def test_column_alias_normalisation(self):
        # Use 'roll_number' instead of 'usn', 'score' instead of 'marks'
        buf = io.BytesIO(b'roll_number,subject,score\n1CS001,DBMS,70\n')
        buf.name = 'alias.csv'
        buf.size = len(buf.getvalue())
        form = self._submit_form(buf)
        self.assertTrue(form.is_valid(), form.errors)
        df = form.get_dataframe()
        self.assertIn('usn', df.columns)
        self.assertIn('marks', df.columns)


# ---------------------------------------------------------------------------
# Utils tests
# ---------------------------------------------------------------------------

class UtilsTest(TestCase):

    def setUp(self):
        self.log = UploadLog.objects.create(filename='seed.csv')
        for usn, subject, marks in [
            ('S001', 'Math', 85), ('S002', 'Math', 40),
            ('S003', 'Math', 30), ('S004', 'Physics', 70),
            ('S005', 'Physics', 90),
        ]:
            Result.objects.create(
                usn=usn, branch='CSE', semester='3',
                subject=subject, marks=marks,
                upload_log=self.log,
            )

    def test_compute_stats_total(self):
        qs = Result.objects.all()
        stats = compute_stats(qs)
        self.assertEqual(stats['total'], 5)

    def test_compute_stats_pass_pct(self):
        qs = Result.objects.all()
        stats = compute_stats(qs)
        # S001, S002, S004, S005 pass → 4/5 = 80%
        self.assertEqual(stats['pass_count'], 4)
        self.assertAlmostEqual(stats['pass_pct'], 80.0)

    def test_compute_stats_toppers(self):
        qs = Result.objects.all()
        stats = compute_stats(qs)
        self.assertEqual(stats['toppers'][0]['marks'], 90)

    def test_compute_stats_empty(self):
        stats = compute_stats(Result.objects.none())
        self.assertEqual(stats['total'], 0)
        self.assertIsNone(stats['average'])

    def test_subject_averages_json(self):
        qs = Result.objects.all()
        data = json.loads(subject_averages_json(qs))
        self.assertIn('Math', data['labels'])
        self.assertIn('Physics', data['labels'])

    def test_grade_distribution_json(self):
        qs = Result.objects.all()
        data = json.loads(grade_distribution_json(qs))
        self.assertIn('labels', data)
        self.assertIn('data', data)

    def test_build_queryset_branch_filter(self):
        Result.objects.create(usn='E001', branch='ECE', semester='1', subject='Circuits', marks=60)
        qs = build_queryset_from_filters({'branch': 'ECE'})
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().branch, 'ECE')

    def test_build_queryset_subject_filter(self):
        qs = build_queryset_from_filters({'subject': 'Math'})
        self.assertEqual(qs.count(), 3)

    def test_import_csv_to_db(self):
        import pandas as pd
        df = pd.DataFrame([
            {'usn': 'N001', 'subject': 'Chemistry', 'marks': 65,
             'student_name': 'New Student', 'exam_type': 'SEE', 'academic_year': '2024-25'},
        ])
        log = UploadLog.objects.create(filename='import_test.csv')
        success, failures = import_csv_to_db(df, {'branch': 'CSE', 'semester': '3'}, log)
        self.assertEqual(success, 1)
        self.assertEqual(failures, [])
        self.assertTrue(Result.objects.filter(usn='N001', subject='Chemistry').exists())

    def test_import_csv_duplicate_skipped(self):
        import pandas as pd
        df = pd.DataFrame([{'usn': 'S001', 'subject': 'Math', 'marks': 99}])
        log = UploadLog.objects.create(filename='dup_test.csv')
        success, failures = import_csv_to_db(df, {}, log, overwrite=False)
        self.assertEqual(success, 0)
        self.assertEqual(len(failures), 1)
        self.assertIn('Duplicate', failures[0]['reason'])

    def test_import_csv_overwrite(self):
        import pandas as pd
        df = pd.DataFrame([{'usn': 'S001', 'subject': 'Math', 'marks': 99}])
        log = UploadLog.objects.create(filename='overwrite_test.csv')
        success, failures = import_csv_to_db(df, {}, log, overwrite=True)
        self.assertEqual(success, 1)
        self.assertEqual(failures, [])
        r = Result.objects.get(usn='S001', subject='Math')
        self.assertEqual(float(r.marks), 99.0)


# ---------------------------------------------------------------------------
# View tests (CO1, CO3, CO4)
# ---------------------------------------------------------------------------

class ViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.log = UploadLog.objects.create(filename='view_seed.csv')
        for usn, branch, sem, subject, marks in [
            ('V001', 'CSE', '5', 'DBMS', 78),
            ('V002', 'CSE', '5', 'DBMS', 45),
            ('V003', 'ISE', '3', 'DS',   60),
        ]:
            Result.objects.create(
                usn=usn, branch=branch, semester=sem,
                subject=subject, marks=marks, upload_log=self.log,
            )

    # --- Home ---
    def test_home_loads(self):
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Result Analytics')

    # --- Upload ---
    def test_upload_get(self):
        resp = self.client.get(reverse('upload'))
        self.assertEqual(resp.status_code, 200)

    def test_upload_valid_csv(self):
        f = make_csv_file([
            ['T001', 'Tester', 'ME', '2', 'Thermo', 72, 'SEE', '2024-25'],
        ])
        resp = self.client.post(reverse('upload'), {
            'branch': 'ME', 'semester': '2',
            'csv_file': f, 'overwrite_existing': False,
        })
        # Should redirect to dashboard
        self.assertRedirects(resp, reverse('dashboard'))
        self.assertTrue(Result.objects.filter(usn='T001').exists())

    def test_upload_invalid_csv_shows_error(self):
        buf = io.BytesIO(b'name,score\nAlice,80\n')
        buf.name = 'bad.csv'
        buf.size = len(b'name,score\nAlice,80\n')
        resp = self.client.post(reverse('upload'), {
            'branch': '', 'semester': '',
            'csv_file': buf, 'overwrite_existing': False,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'missing required columns')

    # --- Dashboard (CO3) ---
    def test_dashboard_loads(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_filter_branch(self):
        resp = self.client.get(reverse('dashboard') + '?branch=CSE')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'V001')
        self.assertNotContains(resp, 'V003')

    def test_dashboard_filter_semester(self):
        resp = self.client.get(reverse('dashboard') + '?semester=3')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'V003')
        self.assertNotContains(resp, 'V001')

    def test_dashboard_shows_stats(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertIn('stats', resp.context)
        self.assertEqual(resp.context['stats']['total'], 3)

    # --- Export (CO4) ---
    def test_export_csv(self):
        resp = self.client.get(reverse('export') + '?format=csv')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        self.assertIn('attachment', resp['Content-Disposition'])
        self.assertIn('.csv', resp['Content-Disposition'])

    def test_export_csv_with_filter(self):
        resp = self.client.get(reverse('export') + '?branch=CSE&format=csv')
        self.assertEqual(resp.status_code, 200)
        content = b''.join(resp.streaming_content).decode()
        self.assertIn('V001', content)
        self.assertNotIn('V003', content)

    def test_export_no_results_redirects(self):
        resp = self.client.get(reverse('export') + '?branch=INVALID&format=csv')
        self.assertRedirects(resp, reverse('dashboard'))

    # --- AJAX (CO5) ---
    def test_ajax_chart_data(self):
        resp = self.client.get(reverse('ajax_chart_data'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('subject_averages', data)
        self.assertIn('grade_distribution', data)
        self.assertIn('stats', data)

    def test_ajax_chart_data_filtered(self):
        resp = self.client.get(reverse('ajax_chart_data') + '?branch=ISE')
        data = resp.json()
        self.assertEqual(data['stats']['total'], 1)

    def test_ajax_subject_list(self):
        resp = self.client.get(reverse('ajax_subject_list') + '?branch=CSE')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('DBMS', data['subjects'])

    # --- CRUD ---
    def test_result_detail(self):
        r = Result.objects.first()
        resp = self.client.get(reverse('result_detail', args=[r.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, r.usn)

    def test_result_edit_get(self):
        r = Result.objects.first()
        resp = self.client.get(reverse('result_edit', args=[r.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_result_edit_post(self):
        r = Result.objects.first()
        resp = self.client.post(reverse('result_edit', args=[r.pk]), {
            'usn': r.usn,
            'student_name': 'Updated Name',
            'branch': r.branch,
            'semester': r.semester,
            'subject': r.subject,
            'subject_code': '',
            'marks': '88',
            'max_marks': 100,
            'exam_type': r.exam_type,
            'academic_year': r.academic_year,
        })
        self.assertRedirects(resp, reverse('dashboard'))
        r.refresh_from_db()
        self.assertEqual(r.student_name, 'Updated Name')
        self.assertEqual(float(r.marks), 88.0)

    def test_result_delete(self):
        r = Result.objects.first()
        pk = r.pk
        resp = self.client.post(reverse('result_delete', args=[pk]))
        self.assertRedirects(resp, reverse('dashboard'))
        self.assertFalse(Result.objects.filter(pk=pk).exists())

    # --- Upload Log ---
    def test_upload_log_list(self):
        resp = self.client.get(reverse('upload_log_list'))
        self.assertEqual(resp.status_code, 200)

    def test_upload_log_detail(self):
        resp = self.client.get(reverse('upload_log_detail', args=[self.log.pk]))
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Edge-case / integration tests
# ---------------------------------------------------------------------------

class EdgeCaseTests(TestCase):

    def test_dashboard_empty_db(self):
        resp = Client().get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No results found')

    def test_upload_then_filter_then_export(self):
        """Full pipeline: upload → filter → export."""
        client = Client()

        # 1. Upload
        f = make_csv_file([
            ['E001', 'Eve', 'EEE', '4', 'Power', 80, 'SEE', '2024-25'],
            ['E002', 'Frank', 'EEE', '4', 'Power', 35, 'SEE', '2024-25'],
        ])
        resp = client.post(reverse('upload'), {
            'branch': 'EEE', 'semester': '4',
            'csv_file': f, 'overwrite_existing': False,
        })
        self.assertRedirects(resp, reverse('dashboard'))

        # 2. Filter
        resp = client.get(reverse('dashboard') + '?branch=EEE&semester=4')
        self.assertContains(resp, 'E001')
        stats = resp.context['stats']
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['pass_count'], 1)

        # 3. Export
        resp = client.get(reverse('export') + '?branch=EEE&semester=4&format=csv')
        self.assertEqual(resp.status_code, 200)
        content = b''.join(resp.streaming_content).decode()
        self.assertIn('E001', content)
        self.assertIn('E002', content)
        self.assertNotIn('V001', content)  # other branch not included