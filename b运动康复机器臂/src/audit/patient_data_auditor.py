#!/usr/bin/env python3
"""
患者数据审核器
验证患者评估数据的合理性和完整性
"""

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict
from enum import Enum


class DataQuality(Enum):
    """数据质量等级"""
    EXCELLENT = "优秀"
    GOOD = "良好"
    ACCEPTABLE = "可接受"
    POOR = "较差"
    INVALID = "无效"


@dataclass
class PatientRecord:
    """患者记录"""
    patient_id: str
    name: str
    age: int
    diagnosis: str
    injury_date: str
    assessment_date: str
    muscle_strength: List[float]
    range_of_motion: List[float]
    pain_level: float
    fatigue_level: float
    notes: Optional[str] = None


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    quality: DataQuality
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]


class PatientDataAuditor:
    """
    患者数据审核器
    验证患者数据的完整性、一致性和合理性
    """

    def __init__(self):
        """初始化审核器"""
        # 正常范围标准
        self.normal_ranges = {
            'age': (0, 120),
            'muscle_strength': (0.0, 1.0),  # 归一化强度
            'range_of_motion': (0.0, 180.0),  # 度
            'pain_level': (0.0, 10.0),  # 疼痛评分
            'fatigue_level': (0.0, 1.0)  # 归一化疲劳度
        }
        
        # 异常阈值
        self.alert_thresholds = {
            'pain_high': 7.0,
            'fatigue_high': 0.8,
            'strength_low': 0.2,
            'rom_low': 30.0
        }

    def validate_patient_record(self, record: PatientRecord) -> ValidationResult:
        """
        验证患者记录
        
        Args:
            record: 患者记录
            
        Returns:
            验证结果
        """
        issues = []
        warnings = []
        recommendations = []
        
        # 验证基本信息
        self._validate_basic_info(record, issues, warnings)
        
        # 验证评估数据
        self._validate_assessment_data(record, issues, warnings, recommendations)
        
        # 验证数据一致性
        self._validate_data_consistency(record, issues, warnings)
        
        # 判断整体质量
        quality = self._determine_quality(issues, warnings)
        is_valid = len(issues) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            quality=quality,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations
        )

    def _validate_basic_info(self, record: PatientRecord, issues: List[str], warnings: List[str]):
        """验证基本信息"""
        # 验证患者ID
        if not record.patient_id or len(record.patient_id) < 3:
            issues.append("患者ID无效或过短")
        
        # 验证姓名
        if not record.name or len(record.name) < 2:
            issues.append("患者姓名无效")
        
        # 验证年龄
        age_min, age_max = self.normal_ranges['age']
        if record.age < age_min or record.age > age_max:
            issues.append(f"年龄({record.age})超出合理范围({age_min}-{age_max})")
        elif record.age < 18:
            warnings.append("患者为未成年人，需要特殊关注")
        elif record.age > 80:
            warnings.append("患者为高龄患者，需要特别注意安全")
        
        # 验证诊断
        if not record.diagnosis:
            warnings.append("缺少诊断信息")
        
        # 验证日期
        try:
            injury_date = datetime.fromisoformat(record.injury_date)
            assessment_date = datetime.fromisoformat(record.assessment_date)
            
            if injury_date > assessment_date:
                issues.append("受伤日期晚于评估日期")
            
            days_since_injury = (assessment_date - injury_date).days
            if days_since_injury < 0:
                issues.append("受伤日期不合理")
            elif days_since_injury > 365 * 5:
                warnings.append(f"受伤已超过5年({days_since_injury}天)，可能需要调整康复策略")
                
        except ValueError as e:
            issues.append(f"日期格式错误: {str(e)}")

    def _validate_assessment_data(self, record: PatientRecord, 
                                  issues: List[str], 
                                  warnings: List[str],
                                  recommendations: List[str]):
        """验证评估数据"""
        # 验证肌肉强度
        if not record.muscle_strength or len(record.muscle_strength) == 0:
            issues.append("缺少肌肉强度数据")
        else:
            min_val, max_val = self.normal_ranges['muscle_strength']
            for i, strength in enumerate(record.muscle_strength):
                if strength < min_val or strength > max_val:
                    issues.append(f"关节{i}肌肉强度({strength})超出范围({min_val}-{max_val})")
                elif strength < self.alert_thresholds['strength_low']:
                    warnings.append(f"关节{i}肌肉强度较低({strength:.2f})")
                    recommendations.append(f"关节{i}建议从被动训练开始")
        
        # 验证活动范围
        if not record.range_of_motion or len(record.range_of_motion) == 0:
            issues.append("缺少活动范围数据")
        else:
            min_val, max_val = self.normal_ranges['range_of_motion']
            for i, rom in enumerate(record.range_of_motion):
                if rom < min_val or rom > max_val:
                    issues.append(f"关节{i}活动范围({rom})超出范围({min_val}-{max_val}度)")
                elif rom < self.alert_thresholds['rom_low']:
                    warnings.append(f"关节{i}活动范围受限({rom:.1f}度)")
                    recommendations.append(f"关节{i}需要重点提高ROM")
        
        # 验证疼痛水平
        min_val, max_val = self.normal_ranges['pain_level']
        if record.pain_level < min_val or record.pain_level > max_val:
            issues.append(f"疼痛水平({record.pain_level})超出范围({min_val}-{max_val})")
        elif record.pain_level >= self.alert_thresholds['pain_high']:
            warnings.append(f"疼痛水平较高({record.pain_level})")
            recommendations.append("建议降低训练强度或暂停训练")
        
        # 验证疲劳水平
        min_val, max_val = self.normal_ranges['fatigue_level']
        if record.fatigue_level < min_val or record.fatigue_level > max_val:
            issues.append(f"疲劳水平({record.fatigue_level})超出范围({min_val}-{max_val})")
        elif record.fatigue_level >= self.alert_thresholds['fatigue_high']:
            warnings.append(f"疲劳水平较高({record.fatigue_level:.2f})")
            recommendations.append("建议增加休息时间")

    def _validate_data_consistency(self, record: PatientRecord, 
                                   issues: List[str], 
                                   warnings: List[str]):
        """验证数据一致性"""
        # 检查数组长度一致性
        if record.muscle_strength and record.range_of_motion:
            if len(record.muscle_strength) != len(record.range_of_motion):
                warnings.append(
                    f"肌肉强度数据({len(record.muscle_strength)}个)与ROM数据"
                    f"({len(record.range_of_motion)}个)数量不一致"
                )
        
        # 检查逻辑一致性：高疲劳+低疼痛可能异常
        if record.fatigue_level > 0.7 and record.pain_level < 2.0:
            warnings.append("疲劳度高但疼痛度低，请确认数据准确性")
        
        # 检查极端情况：所有关节强度都很低
        if record.muscle_strength:
            if all(s < 0.3 for s in record.muscle_strength):
                warnings.append("所有关节肌肉强度都较低，建议确认评估准确性")

    def _determine_quality(self, issues: List[str], warnings: List[str]) -> DataQuality:
        """判断数据质量"""
        if len(issues) > 0:
            return DataQuality.INVALID
        elif len(warnings) == 0:
            return DataQuality.EXCELLENT
        elif len(warnings) <= 2:
            return DataQuality.GOOD
        elif len(warnings) <= 4:
            return DataQuality.ACCEPTABLE
        else:
            return DataQuality.POOR

    def audit_training_session(self, session_data: Dict) -> ValidationResult:
        """
        审核训练会话数据
        
        Args:
            session_data: 训练会话数据
            
        Returns:
            验证结果
        """
        issues = []
        warnings = []
        recommendations = []
        
        # 验证必需字段
        required_fields = ['session_id', 'patient_id', 'start_time', 'exercise_type']
        for field in required_fields:
            if field not in session_data:
                issues.append(f"缺少必需字段: {field}")
        
        # 验证训练参数
        if 'parameters' in session_data:
            params = session_data['parameters']
            
            # 验证组数和次数
            if 'sets' in params:
                if params['sets'] < 1 or params['sets'] > 20:
                    warnings.append(f"训练组数({params['sets']})超出常见范围(1-20)")
            
            if 'reps' in params:
                if params['reps'] < 1 or params['reps'] > 100:
                    warnings.append(f"训练次数({params['reps']})超出常见范围(1-100)")
            
            # 验证速度
            if 'speed' in params:
                if params['speed'] <= 0 or params['speed'] > 2.0:
                    warnings.append(f"训练速度({params['speed']})不在建议范围(0-2.0)")
        
        # 验证训练时长
        if 'start_time' in session_data and 'end_time' in session_data:
            try:
                start = datetime.fromisoformat(session_data['start_time'])
                end = datetime.fromisoformat(session_data['end_time'])
                duration = (end - start).total_seconds() / 60  # 分钟
                
                if duration < 0:
                    issues.append("结束时间早于开始时间")
                elif duration > 120:
                    warnings.append(f"训练时长过长({duration:.1f}分钟)，可能导致疲劳")
                elif duration < 5:
                    warnings.append(f"训练时长过短({duration:.1f}分钟)")
            except:
                issues.append("时间格式错误")
        
        # 验证完成情况
        if 'completion_rate' in session_data:
            rate = session_data['completion_rate']
            if rate < 0 or rate > 1:
                issues.append(f"完成率({rate})超出范围(0-1)")
            elif rate < 0.5:
                warnings.append(f"完成率较低({rate*100:.0f}%)，需要调查原因")
                recommendations.append("考虑降低训练难度或调整参数")
        
        quality = self._determine_quality(issues, warnings)
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            quality=quality,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations
        )

    def compare_assessments(self, 
                           previous: PatientRecord, 
                           current: PatientRecord) -> Dict:
        """
        比较两次评估，生成进度报告
        
        Args:
            previous: 前一次评估
            current: 当前评估
            
        Returns:
            进度报告字典
        """
        report = {
            'patient_id': current.patient_id,
            'comparison_date': datetime.now().isoformat(),
            'time_between_assessments': None,
            'strength_changes': [],
            'rom_changes': [],
            'pain_change': 0.0,
            'fatigue_change': 0.0,
            'overall_progress': 'stable',
            'notes': []
        }
        
        # 计算时间间隔
        try:
            prev_date = datetime.fromisoformat(previous.assessment_date)
            curr_date = datetime.fromisoformat(current.assessment_date)
            days_between = (curr_date - prev_date).days
            report['time_between_assessments'] = days_between
            
            if days_between < 7:
                report['notes'].append("评估间隔较短，可能不足以观察显著变化")
        except:
            report['notes'].append("日期格式错误")
        
        # 比较肌肉强度
        if previous.muscle_strength and current.muscle_strength:
            if len(previous.muscle_strength) == len(current.muscle_strength):
                for i, (prev, curr) in enumerate(zip(previous.muscle_strength, 
                                                     current.muscle_strength)):
                    change = curr - prev
                    report['strength_changes'].append({
                        'joint': i,
                        'previous': prev,
                        'current': curr,
                        'change': change,
                        'change_percent': (change / prev * 100) if prev > 0 else 0
                    })
        
        # 比较活动范围
        if previous.range_of_motion and current.range_of_motion:
            if len(previous.range_of_motion) == len(current.range_of_motion):
                for i, (prev, curr) in enumerate(zip(previous.range_of_motion, 
                                                     current.range_of_motion)):
                    change = curr - prev
                    report['rom_changes'].append({
                        'joint': i,
                        'previous': prev,
                        'current': curr,
                        'change': change,
                        'change_percent': (change / prev * 100) if prev > 0 else 0
                    })
        
        # 比较疼痛和疲劳
        report['pain_change'] = current.pain_level - previous.pain_level
        report['fatigue_change'] = current.fatigue_level - previous.fatigue_level
        
        # 判断总体进度
        avg_strength_change = np.mean([c['change'] for c in report['strength_changes']]) if report['strength_changes'] else 0
        avg_rom_change = np.mean([c['change'] for c in report['rom_changes']]) if report['rom_changes'] else 0
        
        if avg_strength_change > 0.1 or avg_rom_change > 10:
            report['overall_progress'] = 'improving'
            report['notes'].append("患者康复进展良好")
        elif avg_strength_change < -0.1 or avg_rom_change < -10:
            report['overall_progress'] = 'declining'
            report['notes'].append("患者状态下降，需要重新评估训练方案")
        else:
            report['overall_progress'] = 'stable'
            report['notes'].append("患者状态稳定")
        
        # 疼痛变化分析
        if report['pain_change'] > 2:
            report['notes'].append("疼痛水平显著增加，建议降低训练强度")
        elif report['pain_change'] < -2:
            report['notes'].append("疼痛水平显著降低，康复效果良好")
        
        return report

    def generate_validation_report(self, result: ValidationResult) -> str:
        """生成验证报告"""
        report = "=" * 60 + "\n"
        report += "患者数据验证报告\n"
        report += "=" * 60 + "\n\n"
        
        report += f"验证状态: {'通过' if result.is_valid else '未通过'}\n"
        report += f"数据质量: {result.quality.value}\n\n"
        
        if result.issues:
            report += f"问题 ({len(result.issues)}项):\n"
            report += "-" * 60 + "\n"
            for i, issue in enumerate(result.issues, 1):
                report += f"  {i}. {issue}\n"
            report += "\n"
        
        if result.warnings:
            report += f"警告 ({len(result.warnings)}项):\n"
            report += "-" * 60 + "\n"
            for i, warning in enumerate(result.warnings, 1):
                report += f"  {i}. {warning}\n"
            report += "\n"
        
        if result.recommendations:
            report += f"建议 ({len(result.recommendations)}项):\n"
            report += "-" * 60 + "\n"
            for i, rec in enumerate(result.recommendations, 1):
                report += f"  {i}. {rec}\n"
            report += "\n"
        
        return report


def main():
    """测试患者数据审核器"""
    auditor = PatientDataAuditor()
    
    # 创建测试记录
    test_record = PatientRecord(
        patient_id="P001",
        name="测试患者",
        age=65,
        diagnosis="脑卒中后偏瘫",
        injury_date="2024-01-01",
        assessment_date="2024-02-01",
        muscle_strength=[0.3, 0.4, 0.35, 0.5, 0.45, 0.4],
        range_of_motion=[45.0, 60.0, 50.0, 70.0, 55.0, 65.0],
        pain_level=4.5,
        fatigue_level=0.6,
        notes="初次评估"
    )
    
    # 验证记录
    result = auditor.validate_patient_record(test_record)
    print(auditor.generate_validation_report(result))


if __name__ == "__main__":
    main()
