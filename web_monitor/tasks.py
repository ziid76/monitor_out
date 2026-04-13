from celery import shared_task
from .utils import perform_monitoring
from .models import MonitorTarget, MonitoringLog
import logging
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task(name="web_monitor.tasks.check_all_websites")
def check_all_websites():
    """
    Task to find active websites that are due for a check.
    Honors the check_interval defined for each target.
    """
    now = timezone.now()
    targets = MonitorTarget.objects.filter(is_active=True)
    triggered_count = 0
    
    for target in targets:
        # 마지막 체크 시간이 없거나, (마지막 체크 + 주기)가 현재 시간보다 지났으면 실행
        should_check = False
        if not target.last_checked_at:
            should_check = True
        else:
            next_check_time = target.last_checked_at + timedelta(seconds=target.check_interval)
            # 5초 정도의 오차범위(Slack)를 두어 실행 누락 방지
            if next_check_time <= now + timedelta(seconds=5):
                should_check = True
        
        if should_check:
            check_single_website.delay(target.id)
            triggered_count += 1
            
    if triggered_count > 0:
        logger.info(f"Triggered check for {triggered_count} sites due for monitoring.")

@shared_task(name="web_monitor.tasks.check_single_website")
def check_single_website(target_id):
    logger.info(f"Triggering monitor check for target ID: {target_id}")
    perform_monitoring(target_id)

@shared_task(name="web_monitor.tasks.cleanup_old_logs")
def cleanup_old_logs():
    """
    Deletes logs older than the retention period defined in each target.
    """
    targets = MonitorTarget.objects.all()
    total_deleted = 0
    for target in targets:
        cutoff_date = timezone.now() - timedelta(days=target.log_retention_days)
        deleted_count, _ = MonitoringLog.objects.filter(target=target, checked_at__lt=cutoff_date).delete()
        if deleted_count > 0:
            total_deleted += deleted_count
    
    if total_deleted > 0:
        logger.info(f"Cleaned up {total_deleted} old monitoring logs.")
    return total_deleted
