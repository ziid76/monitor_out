from django.db import models
from django.utils import timezone

class TargetRecipient(models.Model):
    name = models.CharField(max_length=100, verbose_name="이름")
    email = models.EmailField(verbose_name="이메일", unique=True)
    
    def __str__(self):
        return f"{self.name} ({self.email})"

class MonitorTarget(models.Model):
    STATUS_CHOICES = [
        ('UP', 'UP'),
        ('DOWN', 'DOWN'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="사이트 이름")
    url = models.URLField(verbose_name="모니터링 대상 URL")
    check_interval = models.IntegerField(default=300, verbose_name="체크 주기 (초)")
    timeout = models.IntegerField(default=20, verbose_name="타임아웃 (초)")
    
    # 낱개 필드로 분리
    signature_title = models.CharField(max_length=200, null=True, blank=True, verbose_name="시그니처: Title")
    signature_text = models.TextField(null=True, blank=True, verbose_name="시그니처: Text (쉼표로 구분)")
    signature_dom = models.TextField(null=True, blank=True, verbose_name="시그니처: DOM Selector (쉼표로 구분)")
    
    # 레거시 호환성을 위해 유지하거나 마이그레이션용으로 둠
    signatures = models.JSONField(default=dict, verbose_name="정상 판단 시그니처 (레거시)", blank=True)
    
    # 알림 대상자 (외부 API에서 가져와 저장됨)
    recipients = models.ManyToManyField(TargetRecipient, related_name='monitoring_targets', verbose_name="알림 수신 대상자")
    
    is_active = models.BooleanField(default=True, verbose_name="활성 여부")
    log_retention_days = models.IntegerField(default=7, verbose_name="로그 보관 주기 (일)")
    
    last_status = models.CharField(max_length=10, choices=STATUS_CHOICES, null=True, blank=True, verbose_name="마지막 상태")
    last_status_changed_at = models.DateTimeField(null=True, blank=True, verbose_name="상태 변경 시간")
    last_checked_at = models.DateTimeField(null=True, blank=True, verbose_name="마지막 체크 시간")
    
    # 사이즈 측정 정보
    last_size_bytes = models.BigIntegerField(null=True, blank=True, verbose_name="마지막 측정 사이즈 (Bytes)")
    last_size_checked_at = models.DateTimeField(null=True, blank=True, verbose_name="마지막 사이즈 측정 시간")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "모니터링 대상"
        verbose_name_plural = "모니터링 대상"

    def __str__(self):
        return f"{self.name} ({self.url})"

    @property
    def formatted_last_size(self):
        if self.last_size_bytes is None:
            return "-"
        return format_bytes_human(self.last_size_bytes)

class MonitoringLog(models.Model):
    target = models.ForeignKey(MonitorTarget, on_delete=models.CASCADE, related_name='logs', verbose_name="대상 사이트")
    status = models.CharField(max_length=10, verbose_name="상태")
    response_time = models.FloatField(verbose_name="응답 시간 (초)")
    error_message = models.TextField(null=True, blank=True, verbose_name="에러 메시지")
    checked_at = models.DateTimeField(default=timezone.now, verbose_name="체크 시간")
    pinned_file = models.CharField(max_length=255, null=True, blank=True, verbose_name="박제된 파일명")

    class Meta:
        verbose_name = "모니터링 로그"
        verbose_name_plural = "모니터링 로그"
        ordering = ['-checked_at']

def format_bytes_human(size_bytes):
    if size_bytes is None:
        return "-"
    size_bytes = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0 or unit == 'TB':
            break
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} {unit}"

class WebsiteSizeLog(models.Model):
    STATUS_CHOICES = [
        ('SUCCESS', '성공'),
        ('FAILED', '실패'),
    ]

    target = models.ForeignKey(MonitorTarget, on_delete=models.CASCADE, related_name='size_logs', verbose_name="대상 사이트")
    total_size_bytes = models.BigIntegerField(default=0, verbose_name="총 사이즈 (Bytes)")
    html_size = models.BigIntegerField(default=0, verbose_name="HTML 사이즈 (Bytes)")
    resource_size = models.BigIntegerField(default=0, verbose_name="리소스 사이즈 (Bytes)")
    resource_count = models.IntegerField(default=0, verbose_name="리소스 개수")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='SUCCESS', verbose_name="상태")
    error_message = models.TextField(null=True, blank=True, verbose_name="에러 메시지")
    checked_at = models.DateTimeField(default=timezone.now, verbose_name="측정 시간")

    class Meta:
        verbose_name = "웹사이트 사이즈 로그"
        verbose_name_plural = "웹사이트 사이즈 로그"
        ordering = ['-checked_at']

    def __str__(self):
        return f"{self.target.name} - {self.formatted_total_size} ({self.checked_at.strftime('%Y-%m-%d %H:%M')})"

    @property
    def formatted_total_size(self):
        return format_bytes_human(self.total_size_bytes)

    @property
    def formatted_html_size(self):
        return format_bytes_human(self.html_size)

    @property
    def formatted_resource_size(self):
        return format_bytes_human(self.resource_size)

