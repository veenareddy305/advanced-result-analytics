from django import forms
from .models import Student, Subject
class UploadFileForm(forms.Form):
    file = forms.FileField(
        label="Upload CSV or Excel File",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    

    def clean_file(self):
        file = self.cleaned_data.get('file')

        if not file:
            raise forms.ValidationError("No file selected")

        if not file.name.endswith(('.csv', '.xlsx', '.xls')):
            raise forms.ValidationError("Only CSV or Excel files allowed")

        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("File too large (max 5MB)")

        return file


# =========================
# 2. DASHBOARD FILTER FORM
# =========================
class DashboardFilterForm(forms.Form):

    year = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    semester = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    branch = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    section = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


# =========================
# 3. SUBJECT ANALYSIS FORM
# =========================
class SubjectFilterForm(forms.Form):

    year = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    subject_code = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    branch = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


# =========================
# 4. CATEGORY ANALYSIS FORM
# =========================
class CategoryFilterForm(forms.Form):

    year = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    category = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All'),
            ('GM', 'GM'),
            ('OBC', 'OBC'),
            ('SC', 'SC'),
            ('ST', 'ST'),
            ('EWS', 'EWS')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


# =========================
# 5. BRANCH COMPARISON FORM
# =========================
class BranchCompareForm(forms.Form):

    year = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    branches = forms.CharField(
        required=True,
        help_text="Enter branches separated by comma",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def clean_branches(self):
        data = self.cleaned_data.get('branches')
        branch_list = [b.strip().upper() for b in data.split(',') if b.strip()]

        if len(branch_list) < 2:
            raise forms.ValidationError("Enter at least 2 branches")

        return branch_list


# =========================
# 6. CLASS (SECTION) FORM
# =========================
class ClassFilterForm(forms.Form):

    year = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    semester = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    branch = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    section = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


# =========================
# 7. BACKLOG SEARCH FORM
# =========================
class BacklogSearchForm(forms.Form):

    usn = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    subject = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    branch = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )