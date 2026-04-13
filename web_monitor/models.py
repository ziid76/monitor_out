from django.db import models
from django.utils import timezone

class MonitorTarget(models.Model):
    STATUS_CHOICES = [
        ('UP', 'UP'),
        ('DOWN', 'DOWN'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="사이트 이름")
    url = models.URLField(verbose_name="모니터링 대상 URL")
    check_interval = models.IntegerField(default=300, verbose_name="체크 주기 (초)")
    
    # 낱개 필드로 분리
    signature_title = models.CharField(max_length=200, null=True, blank=True, verbose_name="시그니처: Title")
    signature_text = models.TextField(null=True, blank=True, verbose_name="시그니처: Text (쉼표로 구분)")
    signature_dom = models.TextField(null=True, blank=True, verbose_name="시그니처: DOM Selector (쉼표로 구분)")
    
    # 레거시 호환성을 위해 유지하거나 마이그레이션용으로 둠
    signatures = models.JSONField(default=dict, verbose_name="정상 판단 시그니처 (레거시)", blank=True)
    
    # 알림 대상자 (사용자 목록에서 선택)
    from django.contrib.auth.models import User
    recipients = models.ManyToManyField(User, related_name='monitoring_targets', verbose_name="알림 수신 대상자")
    
    is_active = models.BooleanField(default=True, verbose_name="활성 여부")
    log_retention_days = models.IntegerField(default=7, verbose_name="로그 보관 주기 (일)")
    
    last_status = models.CharField(max_length=10, choices=STATUS_CHOICES, null=True, blank=True, verbose_name="마지막 상태")
    last_checked_at = models.DateTimeField(null=True, blank=True, verbose_name="마지막 체크 시간")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "모니터링 대상"
        verbose_name_plural = "모니터링 대상"

    def __str__(self):
        return f"{self.name} ({self.url})"

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
