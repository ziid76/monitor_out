from django.core.management.base import BaseCommand
from web_monitor.models import MonitorTarget
from web_monitor.utils import perform_size_check

class Command(BaseCommand):
    help = 'Executes website size check batch for active monitoring targets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--target-id',
            type=int,
            help='Check size for a specific MonitorTarget ID only',
        )

    def handle(self, *args, **options):
        target_id = options.get('target_id')
        
        if target_id:
            targets = MonitorTarget.objects.filter(id=target_id)
            if not targets.exists():
                self.stderr.write(self.style.ERROR(f"Target ID {target_id} not found."))
                return
        else:
            targets = MonitorTarget.objects.filter(is_active=True)

        self.stdout.write(self.style.NOTICE(f"Starting website size check for {targets.count()} target(s)..."))
        
        success_count = 0
        fail_count = 0
        
        for target in targets:
            self.stdout.write(f"Measuring size for [{target.name}] ({target.url})...")
            log = perform_size_check(target.id)
            if log and log.status == "SUCCESS":
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  -> SUCCESS: Total {log.formatted_total_size} (HTML: {log.formatted_html_size}, Resources: {log.resource_count} items / {log.formatted_resource_size})"
                    )
                )
            else:
                fail_count += 1
                err = log.error_message if log else "Unknown error"
                self.stdout.write(self.style.ERROR(f"  -> FAILED: {err}"))
                
        self.stdout.write(
            self.style.SUCCESS(f"Completed size check batch. Success: {success_count}, Failed: {fail_count}")
        )
