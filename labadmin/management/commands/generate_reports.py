"""
自动生成报表的管理命令
使用方法：python manage.py generate_reports [--type week|month|year] [--date YYYY-MM-DD]
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, date, timedelta
from labadmin.models import Report
from decimal import Decimal
from django.db.models import Count, Sum, Q
from booking.models import Booking
from devices.models import Device
from user.models import UserInfo


class Command(BaseCommand):
    help = '自动生成周报表、月报表或年报表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['week', 'month', 'year', 'custom'],
            help='报表类型：week（周报表）、month（月报表）、year（年报表）、custom（自定义时间段）',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='日期（格式：YYYY-MM-DD 或 YYYY-MM 或 YYYY）',
        )
        parser.add_argument(
            '--auto',
            action='store_true',
            help='自动生成：周报表（上周）、月报表（上月）、年报表（去年）',
        )

    def handle(self, *args, **options):
        report_type = options.get('type')
        date_input = options.get('date')
        auto = options.get('auto', False)
        
        if auto:
            # 自动生成模式：只在需要的时候生成
            today = timezone.now().date()
            
            # 周报表：每周一生成上一周报表
            if today.weekday() == 0:  # 周一
                last_week_start = today - timedelta(days=7)
                last_week_end = last_week_start + timedelta(days=6)
                self.generate_week_report(last_week_start, last_week_end)
                self.stdout.write(self.style.SUCCESS(f'已生成上周周报表：{last_week_start} 至 {last_week_end}'))
            
            # 月报表：每月1号生成上一月报表
            if today.day == 1:  # 每月1号
                if today.month == 1:
                    last_month = 12
                    last_year = today.year - 1
                else:
                    last_month = today.month - 1
                    last_year = today.year
                last_month_start = date(last_year, last_month, 1)
                if last_month == 12:
                    last_month_end = date(last_year + 1, 1, 1) - timedelta(days=1)
                else:
                    last_month_end = date(last_year, last_month + 1, 1) - timedelta(days=1)
                self.generate_month_report(last_year, last_month, last_month_start, last_month_end)
                self.stdout.write(self.style.SUCCESS(f'已生成上月月报表：{last_year}年{last_month:02d}月'))
            
            # 年报表：每年1月1号生成上一年报表
            if today.month == 1 and today.day == 1:  # 每年1月1号
                last_year = today.year - 1
                last_year_start = date(last_year, 1, 1)
                last_year_end = date(last_year, 12, 31)
                self.generate_year_report(last_year, last_year_start, last_year_end)
                self.stdout.write(self.style.SUCCESS(f'已生成去年年报表：{last_year}年'))
            
            self.stdout.write(self.style.SUCCESS('自动生成报表检查完成！'))
        else:
            # 手动指定模式
            if not report_type or not date_input:
                self.stdout.write(self.style.ERROR('请指定报表类型和日期！'))
                return
            
            try:
                if report_type == 'week':
                    input_date = datetime.strptime(date_input, '%Y-%m-%d').date()
                    start_date = input_date - timedelta(days=input_date.weekday())
                    end_date = start_date + timedelta(days=6)
                    self.generate_week_report(start_date, end_date)
                elif report_type == 'month':
                    input_date = datetime.strptime(date_input, '%Y-%m').date()
                    year, month = input_date.year, input_date.month
                    start_date = date(year, month, 1)
                    if month == 12:
                        end_date = date(year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_date = date(year, month + 1, 1) - timedelta(days=1)
                    self.generate_month_report(year, month, start_date, end_date)
                elif report_type == 'year':
                    year = int(date_input)
                    start_date = date(year, 1, 1)
                    end_date = date(year, 12, 31)
                    self.generate_year_report(year, start_date, end_date)
                    
                self.stdout.write(self.style.SUCCESS(f'成功生成{report_type}报表！'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'生成报表失败：{str(e)}'))
    
    def generate_week_report(self, start_date, end_date):
        """生成周报表"""
        report_name = f"{start_date.strftime('%Y年%m月%d日')} 至 {end_date.strftime('%Y年%m月%d日')} 周报表"
        
        # 检查是否已存在
        if Report.objects.filter(
            report_type='week',
            start_date=start_date,
            end_date=end_date
        ).exists():
            self.stdout.write(self.style.WARNING(f'周报表已存在：{report_name}'))
            return
        
        # 生成报表数据
        report_data = self._generate_report_data('week', start_date, end_date)
        
        # 创建报表
        Report.objects.create(
            report_type='week',
            report_name=report_name,
            start_date=start_date,
            end_date=end_date,
            report_data=report_data,
            total_bookings=report_data['summary']['total_bookings'],
            total_devices=report_data['summary']['total_devices'],
            total_users=report_data['summary']['total_users'],
            total_revenue=Decimal(str(report_data['summary']['total_revenue'])),
        )
        self.stdout.write(self.style.SUCCESS(f'已生成周报表：{report_name}'))
    
    def generate_month_report(self, year, month, start_date, end_date):
        """生成月报表"""
        report_name = f"{year}年{month:02d}月报表"
        
        # 检查是否已存在
        if Report.objects.filter(
            report_type='month',
            start_date=start_date,
            end_date=end_date
        ).exists():
            self.stdout.write(self.style.WARNING(f'月报表已存在：{report_name}'))
            return
        
        # 生成报表数据
        report_data = self._generate_report_data('month', start_date, end_date)
        
        # 创建报表
        Report.objects.create(
            report_type='month',
            report_name=report_name,
            start_date=start_date,
            end_date=end_date,
            report_data=report_data,
            total_bookings=report_data['summary']['total_bookings'],
            total_devices=report_data['summary']['total_devices'],
            total_users=report_data['summary']['total_users'],
            total_revenue=Decimal(str(report_data['summary']['total_revenue'])),
        )
        self.stdout.write(self.style.SUCCESS(f'已生成月报表：{report_name}'))
    
    def generate_year_report(self, year, start_date, end_date):
        """生成年报表"""
        report_name = f"{year}年报表"
        
        # 检查是否已存在
        if Report.objects.filter(
            report_type='year',
            start_date=start_date,
            end_date=end_date
        ).exists():
            self.stdout.write(self.style.WARNING(f'年报表已存在：{report_name}'))
            return
        
        # 生成报表数据
        report_data = self._generate_report_data('year', start_date, end_date)
        
        # 创建报表
        Report.objects.create(
            report_type='year',
            report_name=report_name,
            start_date=start_date,
            end_date=end_date,
            report_data=report_data,
            total_bookings=report_data['summary']['total_bookings'],
            total_devices=report_data['summary']['total_devices'],
            total_users=report_data['summary']['total_users'],
            total_revenue=Decimal(str(report_data['summary']['total_revenue'])),
        )
        self.stdout.write(self.style.SUCCESS(f'已生成年报表：{report_name}'))
    
    def _generate_report_data(self, report_type, start_date, end_date):
        """生成报表数据（与views.py中的逻辑相同）"""
        # 获取时间范围内的预约数据
        bookings = Booking.objects.filter(
            booking_date__gte=start_date,
            booking_date__lte=end_date
        )
        
        # 获取已审批通过的预约
        approved_bookings = bookings.filter(status='manager_approved')
        
        # 基础统计
        total_bookings = bookings.count()
        approved_count = approved_bookings.count()
        rejected_count = bookings.filter(Q(status='admin_rejected') | Q(status='manager_rejected')).count()
        pending_count = bookings.filter(status='pending').count()
        
        # 按设备统计
        device_stats = approved_bookings.values('device__device_code', 'device__model').annotate(
            booking_count=Count('id'),
            revenue=Sum('device__price_external')
        ).order_by('-booking_count')
        
        # 按用户类型统计
        user_type_stats = approved_bookings.values('applicant__user_type').annotate(
            booking_count=Count('id'),
            user_count=Count('applicant', distinct=True)
        )
        
        # 按日期统计（用于图表）
        date_stats = approved_bookings.values('booking_date').annotate(
            booking_count=Count('id')
        ).order_by('booking_date')
        
        # 计算总收入（仅校外人员）
        total_revenue = approved_bookings.filter(
            applicant__user_type='external'
        ).aggregate(
            total=Sum('device__price_external')
        )['total'] or Decimal('0')
        
        # 设备使用率统计
        device_usage = []
        for device in Device.objects.all():
            device_bookings = approved_bookings.filter(device=device)
            booking_count = device_bookings.count()
            # 假设每个预约使用2小时
            usage_hours = booking_count * 2
            # 计算使用率（假设每天可用8小时）
            days = (end_date - start_date).days + 1
            total_hours = days * 8
            usage_rate = (usage_hours / total_hours * 100) if total_hours > 0 else 0
            
            device_usage.append({
                'device_code': device.device_code,
                'device_model': device.model,
                'booking_count': booking_count,
                'usage_hours': usage_hours,
                'usage_rate': round(usage_rate, 2),
                'revenue': float(device_bookings.filter(applicant__user_type='external').aggregate(
                    total=Sum('device__price_external')
                )['total'] or Decimal('0'))
            })
        
        # 构建报表数据
        report_data = {
            'summary': {
                'total_bookings': total_bookings,
                'approved_count': approved_count,
                'rejected_count': rejected_count,
                'pending_count': pending_count,
                'total_devices': Device.objects.count(),
                'total_users': UserInfo.objects.filter(booking__in=approved_bookings).distinct().count(),
                'total_revenue': float(total_revenue),
            },
            'device_stats': list(device_stats),
            'user_type_stats': list(user_type_stats),
            'date_stats': list(date_stats),
            'device_usage': device_usage,
        }
        
        return report_data
