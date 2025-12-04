from django import forms
from reports.models import Report


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        exclude = ['severity', 'repoted_by', 'created_at', 'updated_at']

    