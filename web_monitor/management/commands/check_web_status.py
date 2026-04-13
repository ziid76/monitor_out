from django.core.management.base import BaseCommand
from web_monitor.models import MonitorTarget
from web_monitor.utils import perform_monitoring
from django.utils import timezone

class Command(BaseCommand):
    help = 'Manually triggers monitoring check for all active sites'

    def handle(self, *args, **options):
        targets = MonitorTarget.objects.filter(is_active=True)
        count = targets.count()
        self.stdout.write(f"Starting check for {count} active sites at {timezone.now()}")
        
        for target in targets:
            self.stdout.write(f"Checking {target.name} ({target.url})...")
            try:
                result = perform_monitoring(target.id)
                self.stdout.write(self.style.SUCCESS(f"  Result: {result.status} ({result.response_time:.3f}s)"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Completed checks for all sites."))
