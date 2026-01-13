from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Count, Sum, Avg
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import timedelta, datetime, date
import json
from decimal import Decimal

# 跨应用模型导入
from user.models import UserInfo
from user.forms import UserInfoForm
from booking.models import Booking, ApprovalRecord
from devices.models import Device
from ledger.models import DeviceLedger
from .models import Report

# --- 基础视图 ---

def admin_home(request):
    return render(request, 'admin/home.html')

def device_list(request):
    """用户端设备查询视图"""
    keyword = request.GET.get('keyword', '')
    devices = Device.objects.all().order_by('device_code')
    
    if keyword:
        devices = devices.filter(
            Q(device_code__icontains=keyword) | 
            Q(model__icontains=keyword) |        
            Q(manufacturer__icontains=keyword) | 
            Q(purpose__icontains=keyword)        
        )

    context = {
        'devices': devices,
        'keyword': keyword,
    }
    return render(request, 'user/device_list.html', context)

def booking_apply(request):
    if request.method == 'POST':
        return redirect('my_booking')
    return render(request, 'user/booking_apply.html')

def my_booking(request):
    return render(request, 'user/my_booking.html')


# --- 报表与统计功能 (保留他人增加的功能) ---

def generate_report_data(report_type, start_date, end_date):
    """生成报表核心统计数据"""
    bookings = Booking.objects.filter(
        booking_date__gte=start_date,
        booking_date__lte=end_date
    )
    
    approved_bookings = bookings.filter(status='manager_approved')
    
    # 基础计数
    total_bookings = bookings.count()
    approved_count = approved_bookings.count()
    rejected_count = bookings.filter(Q(status='admin_rejected') | Q(status='manager_rejected')).count()
    pending_count = bookings.filter(status='pending').count()
    
    # 设备统计
    device_usage = []
    for device in Device.objects.all():
        device_bookings = approved_bookings.filter(device=device)
        booking_count = device_bookings.count()
        usage_hours = booking_count * 2
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
    
    # 汇总数据
    report_data = {
        'summary': {
            'total_bookings': total_bookings,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'pending_count': pending_count,
            'total_devices': Device.objects.count(),
            'total_users': UserInfo.objects.filter(booking__in=approved_bookings).distinct().count(),
            'total_revenue': float(sum(d['revenue'] for d in device_usage)),
        },
        'device_usage': device_usage,
        'date_stats': list(approved_bookings.values('booking_date').annotate(count=Count('id')).order_by('booking_date')),
    }
    return report_data

@login_required
def report_stat(request):
    """报表统计管理视图"""
    reports = Report.objects.all().order_by('-generated_at')[:20]
    report_type_filter = request.GET.get('report_type', '')
    
    if report_type_filter:
        reports = reports.filter(report_type=report_type_filter)
    
    if request.method == 'POST' and 'generate' in request.POST:
        report_type = request.POST.get('report_type')
        date_input = request.POST.get('date_input')
        
        try:
            # 简化日期解析逻辑（支持周/月/年）
            if report_type == 'week':
                input_date = datetime.strptime(date_input, '%Y-%m-%d').date()
                start_date = input_date - timedelta(days=input_date.weekday())
                end_date = start_date + timedelta(days=6)
            elif report_type == 'month':
                input_date = datetime.strptime(date_input + "-01", '%Y-%m-%d').date()
                start_date = input_date
                end_date = (input_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            else:
                start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
                end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date()

            data = generate_report_data(report_type, start_date, end_date)
            report = Report.objects.create(
                report_type=report_type,
                report_name=f"{start_date}至{end_date}统计报表",
                start_date=start_date,
                end_date=end_date,
                report_data=data,
                total_bookings=data['summary']['total_bookings'],
                total_revenue=Decimal(str(data['summary']['total_revenue'])),
                generated_by=request.user
            )
            messages.success(request, '报表生成成功！')
            return redirect(f'/labadmin/report/stat/?view={report.id}')
        except Exception as e:
            messages.error(request, f'生成失败：{str(e)}')

    current_report = None
    view_id = request.GET.get('view')
    if view_id:
        current_report = Report.objects.filter(id=view_id).first()

    return render(request, 'admin/report_stat.html', {
        'reports': reports,
        'current_report': current_report,
        'report_type_filter': report_type_filter
    })


# --- 审核功能 (保留您的审批界面与核心逻辑) ---

@login_required
def booking_approve(request):
    """设备预约审批视图（整合了您的多级审核与他人的类型筛选）"""
    is_admin = request.user.groups.filter(name='设备管理员').exists()
    is_manager = request.user.groups.filter(name='实验室负责人').exists()
    
    if not is_admin and not is_manager:
        messages.error(request, '您没有审批权限！')
        return redirect('admin_home')

    # 保留他人的用户类型筛选功能
    user_type_filter = request.GET.get('user_type', 'all')

    # 您的核心筛选逻辑：管理员看待审，负责人看校外待终审
    if is_admin:
        bookings = Booking.objects.filter(status='pending').order_by('-create_time')
    else:
        bookings = Booking.objects.filter(status='admin_approved', applicant__user_type='external').order_by('-create_time')

    if user_type_filter != 'all':
        bookings = bookings.filter(applicant__user_type=user_type_filter)

    # 处理审批提交
    if request.method == 'POST':
        if 'approve' in request.POST:
            handle_approval(request, request.POST.get('approve'), 'approve')
        elif 'reject' in request.POST:
            handle_approval(request, request.POST.get('reject'), 'reject')
        elif 'batch_approve' in request.POST or 'batch_reject' in request.POST:
            ids = request.POST.getlist('booking_ids')
            action = 'approve' if 'batch_approve' in request.POST else 'reject'
            for b_id in ids:
                handle_approval(request, b_id, action)
                
        return redirect('booking_approve')

    return render(request, 'admin/booking_approve.html', {
        'bookings': bookings,
        'is_admin': is_admin,
        'is_manager': is_manager,
        'user_type_filter': user_type_filter
    })

def handle_approval(request, booking_id, action):
    """核心审批处理逻辑：整合了审批记录与台账记录"""
    booking = get_object_or_404(Booking, id=booking_id)
    is_admin = request.user.groups.filter(name='设备管理员').exists()
    
    # 1. 您的状态流转逻辑
    if action == 'approve':
        if is_admin:
            # 如果是校内人员，管理员审批即通过；校外人员则转为待负责人审
            if booking.applicant.user_type in ['student', 'teacher']:
                booking.status = 'manager_approved'
                create_borrow_ledger(booking, request.user) # 合并台账功能
            else:
                booking.status = 'admin_approved' 
        else:
            booking.status = 'manager_approved'
            create_borrow_ledger(booking, request.user) # 合并台账功能
    else:
        booking.status = 'admin_rejected' if is_admin else 'manager_rejected'

    booking.save()

    # 2. 您的备注获取逻辑
    comment_key = f'comment_{booking.booking_code}'
    comment_val = request.POST.get(comment_key, '')
    if not comment_val:
        comment_val = '批量操作' if 'batch' in request.body.decode() else '无备注'

    # 3. 记录审批日志
    ApprovalRecord.objects.create(
        booking=booking,
        approver=request.user,
        approval_level='admin' if is_admin else 'manager',
        action=action,
        comment=comment_val
    )
    
    action_text = '批准' if action == 'approve' else '拒绝'
    messages.success(request, f'已{action_text}预约：{booking.booking_code}')

def create_borrow_ledger(booking, operator):
    """他人的台账记录功能：审批通过时自动创建"""
    try:
        DeviceLedger.objects.create(
            device=booking.device,
            device_name=booking.device.model,
            user=booking.applicant,
            operation_type='borrow',
            operation_date=timezone.now(),
            expected_return_date=booking.booking_date,
            status_after_operation='unavailable',
            description=f'预约编号：{booking.booking_code}，用途：{booking.purpose or "未填写"}',
            operator=operator
        )
        # 更新设备状态
        booking.device.status = 'unavailable'
        booking.device.save()
    except Exception as e:
        print(f"台账记录失败: {e}")