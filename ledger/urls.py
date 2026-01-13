from django.urls import path
from . import views

app_name = 'ledger'

urlpatterns = [
    path('', views.ledger_home, name='ledger_home'),
    # 设备台账（设备信息）
    path('device/info/', views.device_ledger_list, name='device_ledger_list'),
    path('device/info/export/csv/', views.export_device_ledger_csv, name='export_device_ledger_csv'),
    # 设备操作历史（保留原有功能）
    path('device/operation/history/', views.device_operation_history_list, name='device_operation_history_list'),
    path('device/operation/<int:pk>/', views.device_ledger_detail, name='device_ledger_detail'),
    path('device/operation/export/csv/', views.export_ledger_csv, name='export_ledger_csv'),
    # 教师台账
    path('teacher/', views.teacher_ledger_list, name='teacher_ledger_list'),
    path('teacher/export/csv/', views.export_teacher_ledger_csv, name='export_teacher_ledger_csv'),
    # 学生台账
    path('student/', views.student_ledger_list, name='student_ledger_list'),
    path('student/export/csv/', views.export_student_ledger_csv, name='export_student_ledger_csv'),
    # 校外人员台账
    path('external/', views.external_ledger_list, name='external_ledger_list'),
    path('external/export/csv/', views.export_external_ledger_csv, name='export_external_ledger_csv'),
    # 预约台账
    path('booking/', views.booking_ledger_list, name='booking_ledger_list'),
    path('booking/export/csv/', views.export_booking_ledger_csv, name='export_booking_ledger_csv'),
]