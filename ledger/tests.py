from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from devices.models import Device
from user.models import UserInfo
from ledger.models import DeviceLedger

class DeviceLedgerTestCase(TestCase):
    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.user_info = UserInfo.objects.create(
            user_code='S001',
            name='测试用户',
            user_type='student',
            department='测试学院',
            phone='12345678901',
            auth_user=self.user
        )

        # 创建测试设备
        self.device = Device.objects.create(
            device_code='DEV001',
            model='测试设备',
            manufacturer='测试厂商'
        )

        # 创建测试台账记录
        self.ledger = DeviceLedger.objects.create(
            device=self.device,
            device_name=self.device.model,
            user=self.user_info,
            operation_type='borrow',
            operation_date=timezone.now(),
            expected_return_date=timezone.now() + timezone.timedelta(days=7),
            status_after_operation='unavailable',
            description='测试借出',
            operator=self.user
        )

    def test_device_ledger_creation(self):
        """测试台账记录创建"""
        self.assertEqual(self.ledger.device.device_code, 'DEV001')
        self.assertEqual(self.ledger.device_name, '测试设备')
        self.assertEqual(self.ledger.user.name, '测试用户')
        self.assertEqual(self.ledger.operation_type, 'borrow')
        self.assertEqual(self.ledger.status_after_operation, 'unavailable')
        self.assertIsNotNone(self.ledger.expected_return_date)