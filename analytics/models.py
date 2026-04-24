from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


BRANCH_CHOICES = [
    ('CSE', 'Computer Science & Engineering'),
    ('ISE', 'Information Science & Engineering'),
    ('ECE', 'Electronics & Communication Engineering'),
    ('ME',  'Mechanical Engineering'),
    ('CV',  'Civil Engineering'),
    ('EEE', 'Electrical & Electronics Engineering'),
]

SEMESTER_CHOICES = [(str(i), f'Semester {i}') for i in range(1, 9)]

GRADE_CHOICES = [
    ('O',  'Outstanding (90-100)'),
    ('A+', 'Excellent (80-89)'),
    ('A',  'Very Good (70-79)'),
    ('B+', 'Good (60-69)'),
    ('B',  'Above Average (55-59)'),
    ('C',  'Average (50-54)'),
    ('P',  'Pass (40-49)'),
    ('F',  'Fail (< 40)'),
    ('AB', 'Absent'),
]


def compute_grade(marks):
    """Return letter grade for a numeric mark."""
    if marks is None:
        return 'AB'
    if marks >= 90:
        return 'O'
    if marks >= 80:
        return 'A+'
    if marks >= 70:
        return 'A'
    if marks >= 60:
        return 'B+'
    if marks >= 55:
        return 'B'
    if marks >= 50:
        return 'C'
    if marks >= 40:
        return 'P'
    return 'F'


class UploadLog(models.Model):
    """Audit trail for every CSV upload attempt."""
    filename        = models.CharField(max_length=255)
    uploaded_at     = models.DateTimeField(auto_now_add=True)
    rows_success    = models.PositiveIntegerField(default=0)
    rows_failed     = models.PositiveIntegerField(default=0)
    error_summary   = models.TextField(blank=True)
    uploaded_by     = models.ForeignKey(
        'auth.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='uploads'
    )

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.filename} @ {self.uploaded_at:%Y-%m-%d %H:%M}"


class Result(models.Model):
    """
    Core model: one row = one student's marks in one subject for one exam.
    CO2 – modelled + validated via CSVUploadForm.
    """
    usn         = models.CharField(max_length=20, verbose_name='USN')
    student_name = models.CharField(max_length=120, blank=True)
    branch      = models.CharField(max_length=10, choices=BRANCH_CHOICES)
    semester    = models.CharField(max_length=2,  choices=SEMESTER_CHOICES)
    subject     = models.CharField(max_length=100)
    subject_code = models.CharField(max_length=20, blank=True)
    marks       = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True, blank=True
    )
    max_marks   = models.PositiveSmallIntegerField(default=100)
    grade       = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True)
    exam_type   = models.CharField(
        max_length=20,
        choices=[('IA', 'Internal Assessment'), ('SEE', 'Semester End Exam')],
        default='SEE'
    )
    academic_year = models.CharField(max_length=9, default='2024-25')
    upload_log  = models.ForeignKey(
        UploadLog, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='results'
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['branch', 'semester', 'subject', 'usn']
        indexes = [
            models.Index(fields=['branch', 'semester']),
            models.Index(fields=['subject']),
            models.Index(fields=['usn']),
        ]

    def save(self, *args, **kwargs):
        if self.marks is not None:
            self.grade = compute_grade(float(self.marks))
        else:
            self.grade = 'AB'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usn} | {self.subject} | {self.marks}"

    @property
    def is_pass(self):
        return self.marks is not None and self.marks >= 40

    @property
    def percentage(self):
        if self.marks is None or self.max_marks == 0:
            return None
        return round(float(self.marks) / self.max_marks * 100, 2)