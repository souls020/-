#!/usr/bin/env python3
"""
审核系统单元测试
测试所有审核器的功能
"""

import unittest
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os
import yaml

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.audit.config_auditor import ConfigAuditor, AuditLevel
from src.audit.patient_data_auditor import (
    PatientDataAuditor, PatientRecord, DataQuality
)
from src.audit.training_record_auditor import TrainingRecordAuditor
from src.audit.safety_auditor import SafetyAuditor, SafetyStatus


class TestConfigAuditor(unittest.TestCase):
    """测试配置审核器"""
    
    def setUp(self):
        """测试前准备"""
        self.auditor = ConfigAuditor()
        self.temp_dir = tempfile.mkdtemp()
    
    def test_valid_config(self):
        """测试有效配置"""
        valid_config = {
            'robot': {
                'num_joints': 6,
                'joint_names': ['j0', 'j1', 'j2', 'j3', 'j4', 'j5']
            },
            'joint_limits': {
                'min': [-3.14, -3.14, -3.14, -3.14, -3.14, -3.14],
                'max': [3.14, 3.14, 3.14, 3.14, 3.14, 3.14],
                'velocity': [2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
                'acceleration': [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
            },
            'pid_gains': {
                'joint_0': {'p': 1000.0, 'i': 100.0, 'd': 50.0},
                'joint_1': {'p': 1000.0, 'i': 100.0, 'd': 50.0},
                'joint_2': {'p': 1000.0, 'i': 100.0, 'd': 50.0},
                'joint_3': {'p': 1000.0, 'i': 100.0, 'd': 50.0},
                'joint_4': {'p': 1000.0, 'i': 100.0, 'd': 50.0},
                'joint_5': {'p': 1000.0, 'i': 100.0, 'd': 50.0}
            },
            'safety': {
                'max_force': 30.0,
                'max_torque': 8.0,
                'max_velocity': 0.5,
                'max_acceleration': 1.0,
                'collision_threshold': 15.0
            }
        }
        
        # 写入临时文件
        config_path = os.path.join(self.temp_dir, 'test_config.yaml')
        with open(config_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        # 审核
        results = self.auditor.audit_controller_config(config_path)
        
        # 不应该有严重错误或错误
        self.assertFalse(self.auditor.has_critical_issues())
        self.assertFalse(self.auditor.has_errors())
    
    def test_missing_required_fields(self):
        """测试缺少必需字段"""
        invalid_config = {
            'robot': {
                'num_joints': 6
            }
            # 缺少 joint_limits, pid_gains, safety
        }
        
        config_path = os.path.join(self.temp_dir, 'invalid_config.yaml')
        with open(config_path, 'w') as f:
            yaml.dump(invalid_config, f)
        
        results = self.auditor.audit_controller_config(config_path)
        
        # 应该有错误
        self.assertTrue(self.auditor.has_errors())
    
    def test_unsafe_limits(self):
        """测试不安全的限制"""
        unsafe_config = {
            'robot': {'num_joints': 6},
            'joint_limits': {
                'min': [-3.14] * 6,
                'max': [3.14] * 6,
                'velocity': [2.0] * 6,
                'acceleration': [1.0] * 6
            },
            'pid_gains': {f'joint_{i}': {'p': 1000, 'i': 100, 'd': 50} for i in range(6)},
            'safety': {
                'max_force': 150.0,  # 超出安全范围
                'max_torque': 60.0,  # 超出安全范围
                'collision_threshold': 100.0
            }
        }
        
        config_path = os.path.join(self.temp_dir, 'unsafe_config.yaml')
        with open(config_path, 'w') as f:
            yaml.dump(unsafe_config, f)
        
        results = self.auditor.audit_controller_config(config_path)
        
        # 应该有严重问题
        self.assertTrue(self.auditor.has_critical_issues())


class TestPatientDataAuditor(unittest.TestCase):
    """测试患者数据审核器"""
    
    def setUp(self):
        """测试前准备"""
        self.auditor = PatientDataAuditor()
    
    def test_valid_patient_record(self):
        """测试有效患者记录"""
        record = PatientRecord(
            patient_id="P001",
            name="测试患者",
            age=50,
            diagnosis="脑卒中后偏瘫",
            injury_date="2024-01-01",
            assessment_date="2024-02-01",
            muscle_strength=[0.5, 0.6, 0.55, 0.6, 0.5, 0.55],
            range_of_motion=[60.0, 70.0, 65.0, 75.0, 60.0, 70.0],
            pain_level=3.0,
            fatigue_level=0.4
        )
        
        result = self.auditor.validate_patient_record(record)
        
        self.assertTrue(result.is_valid)
        self.assertIn(result.quality, [DataQuality.EXCELLENT, DataQuality.GOOD])
    
    def test_invalid_age(self):
        """测试无效年龄"""
        record = PatientRecord(
            patient_id="P002",
            name="测试患者",
            age=150,  # 无效年龄
            diagnosis="测试",
            injury_date="2024-01-01",
            assessment_date="2024-02-01",
            muscle_strength=[0.5] * 6,
            range_of_motion=[60.0] * 6,
            pain_level=3.0,
            fatigue_level=0.4
        )
        
        result = self.auditor.validate_patient_record(record)
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.quality, DataQuality.INVALID)
    
    def test_high_pain_level(self):
        """测试高疼痛水平"""
        record = PatientRecord(
            patient_id="P003",
            name="测试患者",
            age=60,
            diagnosis="测试",
            injury_date="2024-01-01",
            assessment_date="2024-02-01",
            muscle_strength=[0.5] * 6,
            range_of_motion=[60.0] * 6,
            pain_level=8.5,  # 高疼痛
            fatigue_level=0.4
        )
        
        result = self.auditor.validate_patient_record(record)
        
        # 应该有警告
        self.assertGreater(len(result.warnings), 0)
        # 应该有降低强度的建议
        self.assertTrue(any('降低' in r or '暂停' in r for r in result.recommendations))
    
    def test_compare_assessments(self):
        """测试评估比较"""
        previous = PatientRecord(
            patient_id="P004",
            name="测试患者",
            age=55,
            diagnosis="测试",
            injury_date="2024-01-01",
            assessment_date="2024-02-01",
            muscle_strength=[0.3] * 6,
            range_of_motion=[40.0] * 6,
            pain_level=5.0,
            fatigue_level=0.7
        )
        
        current = PatientRecord(
            patient_id="P004",
            name="测试患者",
            age=55,
            diagnosis="测试",
            injury_date="2024-01-01",
            assessment_date="2024-03-01",
            muscle_strength=[0.5] * 6,  # 改善
            range_of_motion=[60.0] * 6,  # 改善
            pain_level=3.0,  # 改善
            fatigue_level=0.5  # 改善
        )
        
        report = self.auditor.compare_assessments(previous, current)
        
        # 应该显示进步
        self.assertEqual(report['overall_progress'], 'improving')
        self.assertTrue(any('进展良好' in n for n in report['notes']))


class TestTrainingRecordAuditor(unittest.TestCase):
    """测试训练记录审核器"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.auditor = TrainingRecordAuditor(self.temp_dir)
    
    def test_valid_training_record(self):
        """测试有效训练记录"""
        record = {
            'session_id': 'S001',
            'patient_id': 'P001',
            'exercise_type': '肩部外展',
            'start_time': '2024-02-01T10:00:00',
            'end_time': '2024-02-01T10:30:00',
            'parameters': {
                'target_sets': 3,
                'completed_sets': 3,
                'speed': 0.3
            },
            'performance_data': {
                'max_rom': 75.0,
                'avg_force': 15.5,
                'fatigue_level': 0.65
            },
            'safety_events': []
        }
        
        result = self.auditor.audit_training_record(record)
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['issues']), 0)
    
    def test_short_duration_warning(self):
        """测试训练时长过短警告"""
        record = {
            'session_id': 'S002',
            'patient_id': 'P001',
            'exercise_type': '测试',
            'start_time': '2024-02-01T10:00:00',
            'end_time': '2024-02-01T10:03:00',  # 只有3分钟
            'parameters': {'target_sets': 1, 'completed_sets': 1},
            'performance_data': {},
            'safety_events': []
        }
        
        result = self.auditor.audit_training_record(record)
        
        # 应该有时长警告
        self.assertGreater(len(result['warnings']), 0)
    
    def test_save_and_load_records(self):
        """测试保存和加载记录"""
        record = {
            'session_id': 'S003',
            'patient_id': 'P005',
            'exercise_type': '测试',
            'start_time': '2024-02-01T10:00:00',
            'end_time': '2024-02-01T10:30:00',
            'parameters': {'target_sets': 3, 'completed_sets': 3}
        }
        
        # 保存
        filepath = self.auditor.save_record(record)
        self.assertTrue(os.path.exists(filepath))
        
        # 加载
        loaded_records = self.auditor.load_patient_records('P005')
        self.assertEqual(len(loaded_records), 1)
        self.assertEqual(loaded_records[0]['session_id'], 'S003')


class TestSafetyAuditor(unittest.TestCase):
    """测试安全审核器"""
    
    def setUp(self):
        """测试前准备"""
        self.auditor = SafetyAuditor()
    
    def test_safe_config(self):
        """测试安全配置"""
        config = {
            'max_force': 25.0,
            'max_velocity': 0.4,
            'max_torque': 7.0,
            'collision_threshold': 12.0,
            'e_stop_enabled': True
        }
        
        result = self.auditor.audit_safety_config(config)
        
        self.assertEqual(result['status'], SafetyStatus.SAFE)
        self.assertEqual(len(result['issues']), 0)
    
    def test_unsafe_config(self):
        """测试不安全配置"""
        config = {
            'max_force': 120.0,  # 超过标准限制
            'max_velocity': 0.4,
            'max_torque': 7.0,
            'collision_threshold': 12.0,
            'e_stop_enabled': False  # 紧急停止未启用
        }
        
        result = self.auditor.audit_safety_config(config)
        
        self.assertEqual(result['status'], SafetyStatus.DANGER)
        self.assertGreater(len(result['issues']), 0)
    
    def test_realtime_safety_check(self):
        """测试实时安全检查"""
        joint_positions = np.array([0.5, 0.3, -0.2, 0.1, 0.4, -0.1])
        joint_velocities = np.array([0.1, 0.2, 0.15, 0.1, 0.05, 0.1])
        forces = np.array([10.0, 5.0, 3.0, 2.0, 1.0, 1.5])
        joint_limits = {
            'min': np.array([-3.14] * 6),
            'max': np.array([3.14] * 6),
            'velocity': np.array([2.0] * 6)
        }
        
        result = self.auditor.check_realtime_safety(
            joint_positions, joint_velocities, forces, joint_limits
        )
        
        # 这些参数应该是安全的
        self.assertIn(result['status'], [SafetyStatus.SAFE, SafetyStatus.CAUTION])
    
    def test_violations_audit(self):
        """测试违规审核"""
        violations = [
            {'type': 'force', 'severity': 'medium', 'timestamp': datetime.now().timestamp()},
            {'type': 'velocity', 'severity': 'high', 'timestamp': datetime.now().timestamp()},
            {'type': 'force', 'severity': 'medium', 'timestamp': datetime.now().timestamp()},
        ]
        
        result = self.auditor.audit_safety_violations(violations)
        
        self.assertEqual(result['total_violations'], 3)
        self.assertEqual(result['violation_types']['force'], 2)
        self.assertEqual(result['violation_types']['velocity'], 1)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestConfigAuditor))
    suite.addTests(loader.loadTestsFromTestCase(TestPatientDataAuditor))
    suite.addTests(loader.loadTestsFromTestCase(TestTrainingRecordAuditor))
    suite.addTests(loader.loadTestsFromTestCase(TestSafetyAuditor))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
