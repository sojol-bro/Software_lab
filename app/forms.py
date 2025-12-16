from django import forms
from .models import Job
from .models import Quiz

BASE_INPUT_CLASS = 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring focus:border-blue-300'
BASE_TEXTAREA_CLASS = 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring focus:border-blue-300'
BASE_SELECT_CLASS = 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring focus:border-blue-300 bg-white'

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            'title', 'company', 'location', 'salary_min', 'salary_max',
            'job_type', 'experience_level', 'work_mode', 'description',
            'requirements', 'skills_required', 'category'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5, 'class': BASE_TEXTAREA_CLASS}),
            'requirements': forms.Textarea(attrs={'rows': 5, 'class': BASE_TEXTAREA_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            # preserve widget class if explicitly set above
            cls = field.widget.attrs.get('class')
            if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs['class'] = cls or BASE_SELECT_CLASS
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = cls or BASE_TEXTAREA_CLASS
            else:
                field.widget.attrs['class'] = cls or BASE_INPUT_CLASS

class JobQuizForm(forms.Form):
    quiz = forms.ModelChoiceField(
        queryset=Quiz.objects.filter(is_active=True),
        required=False,
        help_text='Optional: Select a quiz candidates must take before applying.'
    )
