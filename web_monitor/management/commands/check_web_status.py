import os
import sys
import tempfile
from django.core.management.base import BaseCommand
from web_monitor.models import MonitorTarget
from web_monitor.utils import perform_monitoring
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Triggers monitoring check respecting intervals and preventing overlaps'

    def handle(self, *args, **options):
        # 1. Prevent overlapping runs using a lock file
        lock_file_path = os.path.join(tempfile.gettempdir(), 'web_monitor_check.lock')
        if os.path.exists(lock_file_path):
            # Check if the process is still alive (optional but good)
            self.stdout.write("Another check is already in progress. Skipping...")
            return

        try:
            # Create lock file
            with open(lock_file_path, 'w') as f:
                f.write(str(os.getpid()))

            now = timezone.now()
            self.stdout.write(f"Starting check cycle at {now}")

            # 2. Filter targets that are due for checking
            # last_checked_at is null OR last_checked_at + check_interval <= now
            active_targets = MonitorTarget.objects.filter(is_active=True)
            targets_to_check = []
            
            for target in active_targets:
                if not target.last_checked_at:
                    targets_to_check.append(target)
                else:
                    due_time = target.last_checked_at + timedelta(seconds=target.check_interval)
                    if now >= due_time:
                        targets_to_check.append(target)

            count = len(targets_to_check)
            self.stdout.write(f"Found {count} targets due for check (out of {active_targets.count()} active).")
            
            for target in targets_to_check:
                self.stdout.write(f"Checking {target.name} ({target.url})...")
                try:
                    result = perform_monitoring(target.id)
                    self.stdout.write(self.style.SUCCESS(f"  Result: {result.status} ({result.response_time:.3f}s)"))
                except Exception as e:
                    safe_err = str(e).encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
                    self.stdout.write(self.style.ERROR(f"  Error: {safe_err}"))
            
            self.stdout.write(self.style.SUCCESS(f"Completed check cycle."))

        finally:
            # Always remove the lock file after completion
            if os.path.exists(lock_file_path):
                os.remove(lock_file_path)
