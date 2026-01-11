"""
清理过期报表的管理命令（自动删除超过一个月的报表）
使用方法：python manage.py cleanup_reports
建议通过定时任务每天运行一次
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from labadmin.models import Report


class Command(BaseCommand):
    help = '清理超过一个月的过期报表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要删除的报表，不实际删除',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        # 计算一个月前的日期
        one_month_ago = timezone.now() - timedelta(days=30)
        
        # 查找过期的报表
        expired_reports = Report.objects.filter(generated_at__lt=one_month_ago)
        count = expired_reports.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('没有需要清理的过期报表。'))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'将删除 {count} 个过期报表：'))
            for report in expired_reports:
                self.stdout.write(f'  - {report.report_name} (生成于 {report.generated_at.strftime("%Y-%m-%d %H:%M")})')
        else:
            # 删除过期报表
            deleted_count = expired_reports.delete()[0]
            self.stdout.write(self.style.SUCCESS(f'已删除 {deleted_count} 个过期报表。'))
