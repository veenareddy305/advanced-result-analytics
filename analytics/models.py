from django.db import models


class Student(models.Model):
    usn = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    branch = models.CharField(max_length=50)
    section = models.CharField(max_length=10, blank=True)
    batch_year = models.IntegerField()

    actual_category = models.CharField(max_length=20, blank=True)
    admission_quota = models.CharField(max_length=20, blank=True)
    cet_rank = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.usn} - {self.name}"


class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    branch = models.CharField(max_length=50)
    semester = models.IntegerField()
    faculty = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.code


class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    semester = models.IntegerField()
    year = models.IntegerField()

    marks = models.FloatField()
    grade = models.CharField(max_length=5, blank=True)

    is_pass = models.BooleanField(default=True)
    is_backlog = models.BooleanField(default=False)

    sgpa = models.FloatField(null=True, blank=True)
    attempt = models.IntegerField(default=1)

    def save(self, *args, **kwargs):
        self.is_pass = self.marks >= 35
        self.is_backlog = self.marks < 35

        # optional grade
        if self.marks >= 75:
            self.grade = "A"
        elif self.marks >= 60:
            self.grade = "B"
        elif self.marks >= 35:
            self.grade = "C"
        else:
            self.grade = "F"

        super().save(*args, **kwargs)

    class Meta:
        unique_together = ['student', 'subject', 'semester']
        indexes = [
            models.Index(fields=['year', 'semester']),
        ]

    def __str__(self):
        return f"{self.student.usn} - {self.subject.code}"



class Backlog(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    semester = models.IntegerField()
    year = models.IntegerField()

    cleared = models.BooleanField(default=False)
    cleared_year = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.usn} - {self.subject.code}"


class UploadLog(models.Model):
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    records_added = models.IntegerField(default=0)
    records_rejected = models.IntegerField(default=0)

    rejected_rows = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='pending')
    errors = models.TextField(blank=True)

    def __str__(self):
        return self.filename