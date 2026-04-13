from django import forms
from .models import MonitorTarget

class MonitorTargetForm(forms.ModelForm):
    class Meta:
        model = MonitorTarget
        fields = ['name', 'url', 'check_interval', 'log_retention_days', 'signature_title', 'signature_text', 'signature_dom', 'recipients', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-primary/50 outline-none'}),
            'url': forms.URLInput(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-primary/50 outline-none', 'placeholder': 'https://'}),
            'check_interval': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-primary/50 outline-none'}),
            'log_retention_days': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-primary/50 outline-none'}),
            'signature_title': forms.TextInput(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-primary/50 outline-none', 'placeholder': '브라우저 탭 제목'}),
            'signature_text': forms.TextInput(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-primary/50 outline-none', 'placeholder': '포함되어야 할 텍스트 (쉼표 구분)'}),
            'signature_dom': forms.TextInput(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-primary/50 outline-none', 'placeholder': '#app, .content (쉼표 구분)'}),
            'recipients': forms.SelectMultiple(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-primary/50 outline-none h-32'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded text-primary focus:ring-primary'}),
        }
        help_texts = {
            'url': 'https://www.samchully.co.kr 형식으로 입력하세요',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # recipients 쿼리셋 정렬
        self.fields['recipients'].queryset = self.fields['recipients'].queryset.order_by('username')
