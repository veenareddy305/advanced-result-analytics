import io
import pandas as pd
from django import forms
from django.core.exceptions import ValidationError

from .models import BRANCH_CHOICES, SEMESTER_CHOICES

from django import forms
from .models import Result

class ManualEntryForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = [
            'usn', 'student_name', 'branch', 'semester',
            'subject', 'marks', 'academic_year'
        ]

# Columns that MUST be present in the uploaded CSV
REQUIRED_COLUMNS = {'usn', 'subject', 'marks'}

# All recognised column names (case-insensitive mapping)
COLUMN_ALIASES = {
    'usn':           'usn',
    'student_usn':   'usn',
    'roll_number':   'usn',
    'roll no':       'usn',
    'name':          'student_name',
    'student_name':  'student_name',
    'branch':        'branch',
    'dept':          'branch',
    'department':    'branch',
    'semester':      'semester',
    'sem':           'semester',
    'subject':       'subject',
    'subject_name':  'subject',
    'subject_code':  'subject_code',
    'code':          'subject_code',
    'marks':         'marks',
    'mark':          'marks',
    'score':         'marks',
    'max_marks':     'max_marks',
    'maximum':       'max_marks',
    'exam_type':     'exam_type',
    'academic_year': 'academic_year',
}


class CSVUploadForm(forms.Form):
    """
    CO2 – Validated CSV upload form.
    Accepts a .csv file, normalises headers, checks required columns,
    and returns a cleaned DataFrame via self.get_dataframe().
    """
    branch   = forms.ChoiceField(
        choices=[('', '— Select Branch —')] + BRANCH_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    semester = forms.ChoiceField(
        choices=[('', '— Select Semester —')] + SEMESTER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    csv_file = forms.FileField(
        label='CSV File',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.csv'})
    )
    overwrite_existing = forms.BooleanField(
        required=False,
        initial=False,
        label='Replace existing records for same USN + Subject',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']

        # --- Extension check ---
        if not csv_file.name.lower().endswith('.csv'):
            raise ValidationError("Only .csv files are accepted.")

        # --- Size check (5 MB) ---
        if csv_file.size > 5 * 1024 * 1024:
            raise ValidationError("File too large. Maximum size is 5 MB.")

        # --- Try to parse ---
        try:
            content = csv_file.read().decode('utf-8-sig')  # handle BOM
            csv_file.seek(0)
            df = pd.read_csv(io.StringIO(content))
        except Exception as e:
            raise ValidationError(f"Cannot parse CSV: {e}")

        if df.empty:
            raise ValidationError("The uploaded CSV has no data rows.")

        # --- Normalise column names ---
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        rename_map = {}
        for col in df.columns:
            normalised = col.replace('_', ' ').replace('-', ' ')
            if col in COLUMN_ALIASES:
                rename_map[col] = COLUMN_ALIASES[col]
            elif normalised in COLUMN_ALIASES:
                rename_map[col] = COLUMN_ALIASES[normalised]
        df.rename(columns=rename_map, inplace=True)

        # --- Required column check ---
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValidationError(
                f"CSV is missing required columns: {', '.join(sorted(missing))}. "
                f"Found columns: {', '.join(df.columns.tolist())}"
            )

        # --- Marks validation ---
        # --- STRICT Marks validation (NO NaN allowed) ---
        marks_converted = pd.to_numeric(df['marks'], errors='coerce')

        # ❌ Case 1: non-numeric (abc, %, etc.)
        invalid_format = marks_converted.isnull()
        if invalid_format.any():
            bad = df.loc[invalid_format].head(3)
            errors = [
                f"Row {i+2}: USN {r['usn']} → invalid marks '{r['marks']}'"
                for i, r in bad.iterrows()
            ]
            raise ValidationError(" ; ".join(errors))

        # ❌ Case 2: out of range
        invalid_range = (marks_converted < 0) | (marks_converted > 100)
        if invalid_range.any():
            bad = df.loc[invalid_range].head(3)
            errors = [
                f"Row {i+2}: USN {r['usn']} → marks {r['marks']} out of range"
                for i, r in bad.iterrows()
            ]
            raise ValidationError(" ; ".join(errors))

        # ✅ assign only after validation passes
        df['marks'] = marks_converted

        # --- USN format check (warn, don't reject) ---
        df['usn'] = df['usn'].astype(str).str.strip().str.upper()

        # Store cleaned DF for use in the view
        self._cleaned_df = df
        return csv_file

    def get_dataframe(self):
        """Return the validated, normalised DataFrame."""
        return getattr(self, '_cleaned_df', None)


class ResultFilterForm(forms.Form):
    """
    CO3 – Dashboard filter form.
    All fields optional; empty = show all.
    """
    branch   = forms.ChoiceField(
        choices=[('', 'All Branches')] + BRANCH_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    semester = forms.ChoiceField(
        choices=[('', 'All Semesters')] + SEMESTER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    subject  = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Subject name…'
        })
    )
    exam_type = forms.ChoiceField(
        choices=[
            ('', 'All Exam Types'),
            ('IA', 'Internal Assessment'),
            ('SEE', 'Semester End Exam'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    academic_year = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'e.g. 2024-25'
        })
    )
    search_usn = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Search USN…'
        })
    )