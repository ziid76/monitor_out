import io
import os
import requests
from django.conf import settings
from django.core.management import call_command
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils import timezone
from django.utils.decorators import method_decorator
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .models import MonitorTarget, MonitoringLog, TargetRecipient
from .forms import MonitorTargetForm



class ManagerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.session.get('manager_authenticated', False)
    
    def handle_no_permission(self):
        return redirect('web_monitor:manager_auth')

class AdminOrLeaderRequiredMixin(ManagerRequiredMixin):
    pass

class ManagerAuthView(TemplateView):
    template_name = 'web_monitor/manager_auth.html'
    
    def get(self, request, *args, **kwargs):
        if request.session.get('manager_authenticated'):
            return redirect('web_monitor:dashboard')
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        code = request.POST.get('access_code')
        env_code = os.getenv('ACCESS_CODE', '1234')
        if code == env_code:
            request.session['manager_authenticated'] = True
            messages.success(request, "관리자 인증에 성공했습니다.")
            return redirect('web_monitor:dashboard')
        else:
            messages.error(request, "인증코드가 올바르지 않습니다.")
            return redirect('web_monitor:manager_auth')

class ManagerLogoutView(View):
    def get(self, request):
        request.session['manager_authenticated'] = False
        messages.info(request, "관리자 모드에서 로그아웃되었습니다.")
        return redirect('web_monitor:dashboard')

class DashboardView(LoginRequiredMixin, ListView):
    model = MonitorTarget
    template_name = 'web_monitor/dashboard.html'
    context_object_name = 'targets'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_count'] = MonitorTarget.objects.filter(is_active=True).count()
        context['up_count'] = MonitorTarget.objects.filter(is_active=True, last_status='UP').count()
        context['down_count'] = MonitorTarget.objects.filter(is_active=True, last_status='DOWN').count()
        context['is_manager'] = self.request.session.get('manager_authenticated', False)
        return context

class TargetCreateView(AdminOrLeaderRequiredMixin, CreateView):
    model = MonitorTarget
    form_class = MonitorTargetForm
    template_name = 'web_monitor/target_form.html'
    success_url = reverse_lazy('web_monitor:dashboard')

    def form_valid(self, form):
        messages.success(self.request, "새로운 모니터링 대상이 추가되었습니다.")
        return super().form_valid(form)
    
class TargetDetailView(LoginRequiredMixin, DetailView):
    model = MonitorTarget
    template_name = 'web_monitor/target_detail.html'
    context_object_name = 'target'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['logs'] = self.object.logs.all()[:50]
        context['is_manager'] = self.request.session.get('manager_authenticated', False)
        return context

class TargetUpdateView(AdminOrLeaderRequiredMixin, UpdateView):
    model = MonitorTarget
    form_class = MonitorTargetForm
    template_name = 'web_monitor/target_form.html'

    def get_success_url(self):
        return reverse_lazy('web_monitor:target_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "설정이 변경되었습니다.")
        return super().form_valid(form)

class TargetDeleteView(AdminOrLeaderRequiredMixin, View):
    def post(self, request, pk):
        target = get_object_or_404(MonitorTarget, pk=pk)
        target.delete()
        messages.warning(request, f"{target.name} 대상이 삭제되었습니다.")
        return redirect('web_monitor:dashboard')

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

class LogListView(LoginRequiredMixin, ListView):
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

@method_decorator(xframe_options_exempt, name='dispatch')
class ViewLastResponseView(LoginRequiredMixin, View):
    def get(self, request, pk):
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

class ViewPinnedResponseView(LoginRequiredMixin, View):
    def get(self, request, pk):
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

class AddRecipientView(ManagerRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name')
        email = request.POST.get('email')
        if not name or not email:
            return JsonResponse({'success': False, 'message': '필수 정보가 누락되었습니다.'}, status=400)
        
        recipient, created = TargetRecipient.objects.get_or_create(email=email, defaults={'name': name})
        return JsonResponse({
            'success': True, 
            'id': recipient.id, 
            'name': recipient.name, 
            'email': recipient.email,
            'created': created
        })

class FetchRecipientsView(ManagerRequiredMixin, View):
    def get(self, request):
        api_url = os.getenv('RECIPIENT_API_URL')
        api_token = os.getenv('RECIPIENT_API_TOKEN')
        
        if not api_url or not api_token:
            return JsonResponse({'success': False, 'message': 'API 설정이 완료되지 않았습니다.'}, status=500)
            
        try:
            headers = {
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json'
            }
            # 실제 API 호출 (timeout 5초)
            response = requests.get(api_url, headers=headers, timeout=5, verify=False)
            response.raise_for_status()
            data = response.json()
            
            # 응답 형식이 리스트라고 가정하고 [{name: '...', email: '...'}, ...] 형태여야 함
            # 만약 다른 형식이면 여기서 조정 필요
            return JsonResponse({'success': True, 'data': data})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'API 호출 실패: {str(e)}'}, status=500)

class PinResponseView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        log = get_object_or_404(MonitoringLog, pk=pk)
        target = log.target
        import shutil
        safe_name = "".join([c for c in target.name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_')
        src_filename = f"last_response_{target.id}_{safe_name}.html"
        src_path = os.path.join(settings.BASE_DIR, 'logs', 'monitoring_debug', src_filename)
        if not os.path.exists(src_path):
            return JsonResponse({'success': False, 'message': '박제할 최근 응답 파일이 없습니다.'})
        pin_dir = os.path.join(settings.BASE_DIR, 'logs', 'pinned_responses')
        if not os.path.exists(pin_dir):
            os.makedirs(pin_dir)
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        dst_filename = f"pinned_log_{log.id}_{timestamp}_{safe_name}.html"
        dst_path = os.path.join(pin_dir, dst_filename)
        try:
            shutil.copy2(src_path, dst_path)
            log.pinned_file = dst_filename
            log.save()
            return JsonResponse({'success': True, 'message': f'성공적으로 박제되었습니다.', 'filename': dst_filename})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})


@method_decorator(xframe_options_exempt, name='dispatch')
class EmbedDashboardView(View):
    """
    외부사이트 embed 용 대시보드.
    요청 헤더 X-Embed-Key 또는 쿼리스트링 key= 로 인증.
    """

    def _is_authorized(self, request):
        expected_key = os.getenv('EMBED_ACCESS_KEY', '')
        if not expected_key:
            return False
        # 1순위: 헤더에서 확인
        header_key = request.META.get('HTTP_X_EMBED_KEY', '')
        if header_key and header_key == expected_key:
            return True
        # 2순위: 쿼리스트링에서 확인 (?key=...)
        query_key = request.GET.get('key', '')
        if query_key and query_key == expected_key:
            return True
        return False

    def get(self, request):
        if not self._is_authorized(request):
            return render(request, 'web_monitor/embed_forbidden.html', status=403)

        targets = MonitorTarget.objects.filter(is_active=True)
        context = {
            'targets': targets,
            'total_count': targets.count(),
            'up_count': targets.filter(last_status='UP').count(),
            'down_count': targets.filter(last_status='DOWN').count(),
        }
        return render(request, 'web_monitor/web_monitor_out.html', context)


def api_dashboard_data(request):
    """
    외부 대시보드 데이터용 JSON API.
    URL 파라미터 ?key= 를 통해 인증.
    """
    # 1. Key Verification
    expected_key = os.environ.get('EMBED_ACCESS_KEY', '')
    req_key = request.GET.get('key', '')
    if expected_key and req_key != expected_key:
         return JsonResponse({'error': 'Unauthorized'}, status=403)
         
    # 2. 통계 쿼리 연산
    total_count = MonitorTarget.objects.count()
    up_count = MonitorTarget.objects.filter(last_status='UP').count()
    down_count = MonitorTarget.objects.filter(last_status='DOWN').count()
    
    # 3. 디테일 리스트 직렬화
    targets = MonitorTarget.objects.all().order_by('-pk')
    target_data = []
    for t in targets:
        target_data.append({
            'id': t.id,
            'name': t.name,
            'url': t.url,
            'last_status': t.last_status or "PENDING",
            'last_status_changed_at': timezone.localtime(t.last_status_changed_at).strftime('%Y-%m-%d %H:%M:%S') if t.last_status_changed_at else None,
            'last_checked_at': timezone.localtime(t.last_checked_at).strftime('%Y-%m-%d %H:%M:%S') if t.last_checked_at else None,
            'check_interval': t.check_interval,
        })
        
    # 4. JSON 응답
    return JsonResponse({
        'total_count': total_count,
        'up_count': up_count,
        'down_count': down_count,
        'targets': target_data
    })


def api_target_detail(request, pk):
    """
    특정 대상 사이트의 상세 정보를 제공하는 JSON API.
    URL 파라미터 ?key= 를 통해 인증.
    """
    # 1. Key Verification
    expected_key = os.environ.get('EMBED_ACCESS_KEY', '')
    req_key = request.GET.get('key', '')
    if expected_key and req_key != expected_key:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    target = get_object_or_404(MonitorTarget, pk=pk)
    
    # 2. Uptime calculation (last 24h)
    from datetime import timedelta
    now = timezone.now()
    last_24h = now - timedelta(days=1)
    logs_24h = MonitoringLog.objects.filter(target=target, checked_at__gte=last_24h)
    total_logs_count = logs_24h.count()
    up_logs_count = logs_24h.filter(status='UP').count()
    uptime_24h = (up_logs_count / total_logs_count * 100) if total_logs_count > 0 else 100.0
    
    # 3. Recent logs (last 50)
    recent_logs = []
    for log in target.logs.all()[:50]:
        recent_logs.append({
            'timestamp': timezone.localtime(log.checked_at).strftime('%Y-%m-%d %H:%M:%S'),
            'status': log.status,
            'response_time': int(log.response_time * 1000), # seconds to ms
            'message': log.error_message or ""
        })
        
    # 4. Recipients
    recipients = []
    for r in target.recipients.all():
        recipients.append({
            'name': r.name,
            'email': r.email
        })

    # 5. 24시간 로그 데이터 for 차트
    logs_24h_data = []
    for log in logs_24h:
        logs_24h_data.append({
            'timestamp': timezone.localtime(log.checked_at).strftime('%Y-%m-%d %H:%M:%S'),
            'status': log.status,
            'response_time': int(log.response_time * 1000), # seconds to ms
        })        

    # 6. Last response time (from most recent log)
    last_log = target.logs.first()
    last_response_time = int(last_log.response_time * 1000) if last_log else 0

    return JsonResponse({
        "id": target.id,
        "name": target.name,
        "url": target.url,
        "last_status": target.last_status or "PENDING",
        "last_checked_at": timezone.localtime(target.last_checked_at).strftime('%Y-%m-%d %H:%M:%S') if target.last_checked_at else None,
        "last_status_changed_at": timezone.localtime(target.last_status_changed_at).strftime('%Y-%m-%d %H:%M:%S') if target.last_status_changed_at else None,
        "check_interval": target.check_interval,
        "timeout": target.timeout,
        "uptime_24h": round(uptime_24h, 2),
        "last_response_time": last_response_time,
        "recent_logs": recent_logs,
        "recipients": recipients,
        "logs_24h_data": logs_24h_data,
    })

