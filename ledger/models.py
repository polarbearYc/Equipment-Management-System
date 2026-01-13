from django.db import models
from django.contrib.auth.models import User
from devices.models import Device
from user.models import UserInfo

class DeviceLedger(models.Model):
    """设备台账模型，记录设备的操作历史"""
    OPERATION_TYPES = (
        ('borrow', '借出'),
        ('return', '归还'),
        ('maintenance', '维护'),
        ('repair', '维修'),
        ('discard', '报废'),
        ('other', '其他'),
    )

    DEVICE_STATUS = (
        ('available', '可用'),
        ('unavailable', '不可用'),
        ('maintenance', '维修中'),
        ('discarded', '已报废'),
    )

    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='设备')
    device_name = models.CharField(max_length=100, verbose_name='设备名称', help_text='操作时的设备名称快照')
    user = models.ForeignKey(UserInfo, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='操作用户/借用人')
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES, verbose_name='操作类型')
    operation_date = models.DateTimeField(verbose_name='操作日期')
    expected_return_date = models.DateTimeField(blank=True, null=True, verbose_name='预期归还时间')
    actual_return_date = models.DateTimeField(blank=True, null=True, verbose_name='实际归还时间')
    status_after_operation = models.CharField(max_length=20, choices=DEVICE_STATUS, verbose_name='操作后设备状态')
    description = models.TextField(blank=True, null=True, verbose_name='操作描述')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='操作员')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='记录创建时间')

    class Meta:
        verbose_name = '设备台账'
        verbose_name_plural = '设备台账'
        ordering = ['-operation_date']

    def __str__(self):
        return f"{self.device.device_code} - {self.device_name} - {self.get_operation_type_display()} - {self.operation_date.strftime('%Y-%m-%d %H:%M')}"