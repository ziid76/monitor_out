from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json

class Command(BaseCommand):
    help = 'Initializes periodic tasks for web monitoring'

    def handle(self, *args, **options):
        # 1. 1분마다 웹사이트 체크 스케줄
        schedule_1m, _ = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.MINUTES,
        )

        PeriodicTask.objects.get_or_create(
            interval=schedule_1m,
            name='Web Monitor: Check all websites (1m)',
            task='web_monitor.tasks.check_all_websites',
        )
        self.stdout.write(self.style.SUCCESS('Successfully created check_all_websites task (1m)'))

        # 2. 매일 새벽 3시에 로그 정리 스케줄
        schedule_daily_3am, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='3',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )

        PeriodicTask.objects.get_or_create(
            crontab=schedule_daily_3am,
            name='Web Monitor: Cleanup old logs (Daily 3AM)',
            task='web_monitor.tasks.cleanup_old_logs',
        )
        self.stdout.write(self.style.SUCCESS('Successfully created cleanup_old_logs task (Daily 3AM)'))
