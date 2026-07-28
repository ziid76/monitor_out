from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from web_monitor.models import MonitorTarget, MonitoringLog, WebsiteSizeLog

class Command(BaseCommand):
    help = 'Cleans up old monitoring logs and website size logs exceeding retention period'

    def handle(self, *args, **options):
        self.stdout.write("Starting cleanup of old logs...")
        targets = MonitorTarget.objects.all()
        total_monitoring_deleted = 0
        total_size_deleted = 0

        for target in targets:
            cutoff_date = timezone.now() - timedelta(days=target.log_retention_days)
            
            # Delete old monitoring logs
            deleted_mon, _ = MonitoringLog.objects.filter(target=target, checked_at__lt=cutoff_date).delete()
            if deleted_mon > 0:
                total_monitoring_deleted += deleted_mon
                
            # Delete old website size logs
            deleted_size, _ = WebsiteSizeLog.objects.filter(target=target, checked_at__lt=cutoff_date).delete()
            if deleted_size > 0:
                total_size_deleted += deleted_size

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully cleaned up logs: {total_monitoring_deleted} status log(s), {total_size_deleted} size log(s) deleted."
            )
        )
