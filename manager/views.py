from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.hashers import make_password  # 密码加密
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# 跨应用模型与视图导入
from user.models import UserInfo
from user.forms import UserInfoForm
from booking.models import Booking, ApprovalRecord
from labadmin.views import handle_approval

# Create your views here.

# ---------------------- 负责人主页 ----------------------
def manager_home(request):
    return render(request, 'manager/home.html')

# ---------------------- 1. 设备预约审批 ----------------------
@login_required
def booking_approve(request):
    """设备预约审批（管理员/负责人）"""
    # 校验是否是管理员/负责人
    is_admin = request.user.groups.filter(name='设备管理员').exists()
    is_manager = request.user.groups.filter(name='实验室负责人').exists()
    if not is_admin and not is_manager:
        messages.error(request, '你无审批权限！')
        return redirect('manager_home')
    
    # 获取筛选条件
    user_type_filter = request.GET.get('user_type', 'all')
    
    # ========== 精准限定各角色的查询范围 ==========
    if is_admin:
        # 管理员：只看「待管理员审批（pending）」的申请
        bookings = Booking.objects.filter(
            status='pending'
        ).order_by('-create_time')
    else:  # 实验室负责人
        # 负责人：只看「管理员已批准（admin_approved）」的申请（且仅校外人员）
        bookings = Booking.objects.filter(
            status='admin_approved',
            applicant__user_type='external'
        ).order_by('-create_time')
    
    # 筛选用户类型
    if user_type_filter != 'all':
        if is_admin:  # 管理员可筛选所有类型
            bookings = bookings.filter(applicant__user_type=user_type_filter)
        elif user_type_filter == 'external': # 负责人强制限定为校外
            bookings = bookings.filter(applicant__user_type='external')
    
    # 处理审批操作
    if request.method == 'POST':
        if 'approve' in request.POST:
            booking_id = request.POST.get('approve')
            handle_approval(request, booking_id, 'approve')
        elif 'reject' in request.POST:
            booking_id = request.POST.get('reject')
            handle_approval(request, booking_id, 'reject')
        elif 'batch_approve' in request.POST or 'batch_reject' in request.POST:
            booking_ids = request.POST.getlist('booking_ids')
            action = 'approve' if 'batch_approve' in request.POST else 'reject'
            for booking_id in booking_ids:
                handle_approval(request, booking_id, action)
        
        return redirect('booking_approve')
    
    context = {
        'bookings': bookings,
        'user_type_filter': user_type_filter,
        'is_admin': is_admin,
        'is_manager': is_manager
    }
    return render(request, 'manager/booking_approve.html', context)

# ---------------------- 2. 报表统计 ----------------------
@login_required
def manager_report_stat(request):
    """负责人报表统计页面（含生成逻辑）"""
    from labadmin.models import Report
    from labadmin.views import generate_report_data
    from datetime import datetime, timedelta, date
    from decimal import Decimal
    
    # 获取已生成的报表列表
    reports = Report.objects.all().order_by('-generated_at')[:20]
    report_type_filter = request.GET.get('report_type', '')
    
    if report_type_filter:
        reports = reports.filter(report_type=report_type_filter)
    
    # 处理报表生成请求
    if request.method == 'POST' and 'generate' in request.POST:
        report_type = request.POST.get('report_type')
        date_input = request.POST.get('date_input', '').strip()
        start_date_input = request.POST.get('start_date', '').strip()
        end_date_input = request.POST.get('end_date', '').strip()
        
        if report_type == 'custom' and (not start_date_input or not end_date_input):
            messages.error(request, '自定义时间段需要填写起止日期！')
            return redirect('manager_report_stat')
        elif report_type != 'custom' and not date_input:
            messages.error(request, '请选择日期！')
            return redirect('manager_report_stat')
        
        try:
            # 日期解析逻辑
            if report_type == 'week':
                input_date = datetime.strptime(date_input, '%Y-%m-%d').date()
                start_date = input_date - timedelta(days=input_date.weekday())
                end_date = start_date + timedelta(days=6)
                report_name = f"{start_date} 至 {end_date} 周报表"
            elif report_type == 'month':
                if '-' in date_input and len(date_input) <= 7:
                    year, month = map(int, date_input.split('-'))
                else:
                    idate = datetime.strptime(date_input, '%Y-%m-%d').date()
                    year, month = idate.year, idate.month
                start_date = date(year, month, 1)
                next_month = start_date.replace(day=28) + timedelta(days=4)
                end_date = next_month.replace(day=1) - timedelta(days=1)
                report_name = f"{year}年{month:02d}月报表"
            elif report_type == 'year':
                year = int(date_input[:4])
                start_date = date(year, 1, 1)
                end_date = date(year, 12, 31)
                report_name = f"{year}年报表"
            else: # custom
                start_date = datetime.strptime(start_date_input, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_input, '%Y-%m-%d').date()
                report_name = f"{start_date} 至 {end_date} 自定义报表"

            # 生成并保存报表
            report_data = generate_report_data(report_type, start_date, end_date)
            report = Report.objects.create(
                report_type=report_type,
                report_name=report_name,
                start_date=start_date,
                end_date=end_date,
                report_data=report_data,
                total_bookings=report_data['summary']['total_bookings'],
                total_revenue=Decimal(str(report_data['summary']['total_revenue'])),
                generated_by=request.user
            )
            messages.success(request, f'报表生成成功：{report_name}')
            return redirect(f'manager_report_stat?view={report.id}')
            
        except Exception as e:
            messages.error(request, f'操作失败：{str(e)}')
            return redirect('manager_report_stat')

    # 查看报表详情
    report_id = request.GET.get('view')
    current_report = Report.objects.filter(id=report_id).first() if report_id else None
    
    context = {
        'reports': reports,
        'current_report': current_report,
        'report_type_filter': report_type_filter,
    }
    return render(request, 'manager/report_stat.html', context)

# ---------------------- 3. 用户管理 ----------------------
@login_required
def user_manage(request):
    """用户管理：展示、搜索、新增（自动生成账号）"""
    user_type = request.GET.get('user_type', '')
    keyword = request.GET.get('keyword', '')
    users = UserInfo.objects.all()
    
    if user_type:
        users = users.filter(user_type=user_type)
    if keyword:
        users = users.filter(Q(name__icontains=keyword) | Q(user_code__icontains=keyword))
    
    if request.method == 'POST':
        form = UserInfoForm(request.POST)
        if form.is_valid():
            user_info = form.save(commit=False)
            username = user_info.user_code
            if User.objects.filter(username=username).exists():
                form.add_error('user_code', '该用户编号已存在！')
            else:
                auth_user = User.objects.create(
                    username=username,
                    password=make_password(username),
                    first_name=user_info.name,
                    is_active=user_info.is_active
                )
                user_info.auth_user = auth_user
                user_info.save()
                # 关联到普通用户组
                group, _ = Group.objects.get_or_create(name='普通用户')
                auth_user.groups.add(group)
                return redirect('user_manage')
    else:
        form = UserInfoForm()
    
    return render(request, 'manager/user_manage.html', {
        'users': users, 'form': form, 'keyword': keyword, 'user_type': user_type
    })

@login_required
def user_edit(request, pk):
    """编辑用户并同步账号状态"""
    user_info = get_object_or_404(UserInfo, pk=pk)
    if request.method == 'POST':
        form = UserInfoForm(request.POST, instance=user_info)
        if form.is_valid():
            user_info = form.save(commit=False)
            if user_info.auth_user:
                user_info.auth_user.username = user_info.user_code
                user_info.auth_user.is_active = user_info.is_active
                if request.POST.get('reset_to_code'):
                    user_info.auth_user.password = make_password(user_info.user_code)
                user_info.auth_user.save()
            user_info.save()
            return redirect('user_manage')
    else:
        form = UserInfoForm(instance=user_info)
    return render(request, 'manager/user_edit.html', {'form': form, 'user': user_info})

@login_required
def user_delete(request, pk):
    """删除用户及其登录账号"""
    user_info = get_object_or_404(UserInfo, pk=pk)
    if user_info.auth_user:
        user_info.auth_user.delete()
    user_info.delete()
    return redirect('user_manage')

@login_required
def user_toggle_status(request, pk):
    """快速禁用/启用用户"""
    user_info = get_object_or_404(UserInfo, pk=pk)
    user_info.is_active = not user_info.is_active
    if user_info.auth_user:
        user_info.auth_user.is_active = user_info.is_active
        user_info.auth_user.save()
    user_info.save()
    return redirect('user_manage')