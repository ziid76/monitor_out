import io
import os
from django.conf import settings
from django.core.management import call_command
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .models import MonitorTarget, MonitoringLog
from .forms import MonitorTargetForm
from django_celery_beat.models import PeriodicTask

class AdminOrLeaderRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        # Allow everyone to manage in the lightweight version without login
        return True

class DashboardView(ListView):
    model = MonitorTarget
    template_name = 'web_monitor/dashboard.html'
    context_object_name = 'targets'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add summary stats
        context['total_count'] = MonitorTarget.objects.filter(is_active=True).count()
        context['up_count'] = MonitorTarget.objects.filter(is_active=True, last_status='UP').count()
        context['down_count'] = MonitorTarget.objects.filter(is_active=True, last_status='DOWN').count()
        context['form'] = MonitorTargetForm()
        # No profile needed for lightweight version
        context['can_manage'] = self.request.user.is_superuser or self.request.user.is_staff
        return context

class TargetCreateView(AdminOrLeaderRequiredMixin, CreateView):
    model = MonitorTarget
    form_class = MonitorTargetForm
    success_url = reverse_lazy('web_monitor:dashboard')

    def form_valid(self, form):
        messages.success(self.request, "새로운 모니터링 대상이 추가되었습니다.")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "데이터 입력 중 오류가 발생했습니다. 입력을 확인해주세요.")
        return super().form_invalid(form)

class TargetDetailView(DetailView):
    model = MonitorTarget
    template_name = 'web_monitor/target_detail.html'
    context_object_name = 'target'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['logs'] = self.object.logs.all()[:50]
        context['form'] = MonitorTargetForm(instance=self.object)
        context['can_manage'] = self.request.user.is_superuser or self.request.user.is_staff
        return context

class TargetUpdateView(AdminOrLeaderRequiredMixin, UpdateView):
    model = MonitorTarget
    form_class = MonitorTargetForm

    def get_success_url(self):
        return reverse_lazy('web_monitor:target_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "설정이 변경되었습니다.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "설정 변경 중 오류가 발생했습니다.")
        return super().form_invalid(form)

class RunCommandView(AdminOrLeaderRequiredMixin, View):
    def post(self, request, command_name):
        out = io.StringIO()
        try:
            if command_name not in ['setup_tasks', 'check_web_status']:
                return JsonResponse({'success': False, 'message': '허용되지 않은 명령어입니다.'})
            
            call_command(command_name, stdout=out)
            return JsonResponse({'success': True, 'output': out.getvalue()})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e), 'output': out.getvalue()})

class LogListView(ListView):
    model = MonitoringLog
    template_name = 'web_monitor/log_list.html'
    context_object_name = 'logs'
    paginate_by = 100

    def get_queryset(self):
        queryset = super().get_queryset()
        site_name = self.request.GET.get('site_name')
        status = self.request.GET.get('status')
        
        if site_name:
            queryset = queryset.filter(target__name__icontains=site_name)
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset.select_related('target')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['targets'] = MonitorTarget.objects.all()
        return context

class PeriodicTaskStatusView(AdminOrLeaderRequiredMixin, View):
    def get(self, request):
        tasks = PeriodicTask.objects.filter(name__icontains='Web Monitor').values(
            'name', 'task', 'interval__every', 'interval__period', 
            'crontab__minute', 'crontab__hour', 'enabled', 'last_run_at'
        )
        return JsonResponse({'success': True, 'tasks': list(tasks)})

@method_decorator(xframe_options_exempt, name='dispatch')
class ViewLastResponseView(View):
    def get(self, request, pk):
        # pk is target_id
        target = get_object_or_404(MonitorTarget, pk=pk)
        safe_name = "".join([c for c in target.name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_')
        filename = f"last_response_{target.id}_{safe_name}.html"
        filepath = os.path.join(settings.BASE_DIR, 'logs', 'monitoring_debug', filename)
        
        if not os.path.exists(filepath):
            return JsonResponse({'success': False, 'message': '최근 응답 파일이 없습니다.'}, status=404)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return JsonResponse({'success': True, 'content': html_content})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class ViewPinnedResponseView(View):
    def get(self, request, pk):
        # pk is log_id
        log = get_object_or_404(MonitoringLog, pk=pk)
        if not log.pinned_file:
            return JsonResponse({'success': False, 'message': '이 로그에는 박제된 응답이 없습니다.'}, status=404)
            
        filepath = os.path.join(settings.BASE_DIR, 'logs', 'pinned_responses', log.pinned_file)
        if not os.path.exists(filepath):
            return JsonResponse({'success': False, 'message': '파일을 찾을 수 없습니다.'}, status=404)
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return JsonResponse({'success': True, 'content': html_content})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class PinResponseView(View):
    def post(self, request, pk):
        # pk is log_id
        log = get_object_or_404(MonitoringLog, pk=pk)
        target = log.target
        import shutil
        from django.utils import timezone
        
        # 소스 파일 (최근 응답 파일)
        safe_name = "".join([c for c in target.name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_')
        src_filename = f"last_response_{target.id}_{safe_name}.html"
        src_path = os.path.join(settings.BASE_DIR, 'logs', 'monitoring_debug', src_filename)
        
        if not os.path.exists(src_path):
            return JsonResponse({'success': False, 'message': '박제할 최근 응답 파일이 없습니다.'})
            
        # 대상 폴더 생성
        pin_dir = os.path.join(settings.BASE_DIR, 'logs', 'pinned_responses')
        if not os.path.exists(pin_dir):
            os.makedirs(pin_dir)
            
        # 새 파일명 (유니크한 이름: 로그 ID 및 타임스탬프)
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        dst_filename = f"pinned_log_{log.id}_{timestamp}_{safe_name}.html"
        dst_path = os.path.join(pin_dir, dst_filename)
        
        try:
            shutil.copy2(src_path, dst_path)
            # 로그 객체에 파일명 저장
            log.pinned_file = dst_filename
            log.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'성공적으로 박제되었습니다.',
                'filename': dst_filename
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
