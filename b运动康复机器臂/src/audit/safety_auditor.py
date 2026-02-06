#!/usr/bin/env python3
"""
安全系统审核器
审核安全监控系统的配置和运行状态
"""

import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from enum import Enum


class SafetyStatus(Enum):
    """安全状态"""
    SAFE = "安全"
    CAUTION = "注意"
    WARNING = "警告"
    DANGER = "危险"


class SafetyAuditor:
    """
    安全系统审核器
    检查安全配置和监控安全违规
    """

    def __init__(self):
        """初始化安全审核器"""
        # 标准安全限制
        self.standard_limits = {
            'max_force': 50.0,  # N
            'max_velocity': 1.0,  # rad/s  
            'max_acceleration': 2.0,  # rad/s^2
            'max_torque': 10.0,  # Nm
            'collision_threshold': 20.0  # N
        }
        
        # 康复训练推荐限制（更保守）
        self.rehab_limits = {
            'max_force': 30.0,
            'max_velocity': 0.5,
            'max_acceleration': 1.0,
            'max_torque': 8.0,
            'collision_threshold': 15.0
        }

    def audit_safety_config(self, config: Dict) -> Dict:
        """
        审核安全配置
        
        Args:
            config: 安全配置字典
            
        Returns:
            审核结果
        """
        issues = []
        warnings = []
        recommendations = []
        status = SafetyStatus.SAFE
        
        # 检查必需字段
        required_fields = [
            'max_force', 'max_velocity', 'max_torque', 'collision_threshold'
        ]
        
        for field in required_fields:
            if field not in config:
                issues.append(f"缺少必需的安全参数: {field}")
                status = SafetyStatus.DANGER
        
        # 检查各项安全限制
        for param, value in config.items():
            if param in self.standard_limits:
                standard_max = self.standard_limits[param]
                rehab_max = self.rehab_limits[param]
                
                # 检查是否超过标准限制
                if value > standard_max:
                    issues.append(
                        f"{param}({value})超过标准安全限制({standard_max})"
                    )
                    status = SafetyStatus.DANGER
                
                # 检查是否超过康复推荐限制
                elif value > rehab_max:
                    warnings.append(
                        f"{param}({value})超过康复训练推荐限制({rehab_max})"
                    )
                    if status == SafetyStatus.SAFE:
                        status = SafetyStatus.CAUTION
                    recommendations.append(
                        f"建议将{param}降低至{rehab_max}以下"
                    )
        
        # 检查紧急停止配置
        if 'e_stop_enabled' in config:
            if not config['e_stop_enabled']:
                issues.append("紧急停止功能未启用")
                status = SafetyStatus.DANGER
        else:
            warnings.append("未找到紧急停止配置")
        
        # 检查力限制持续时间
        if 'force_limit_duration' in config:
            duration = config['force_limit_duration']
            if duration > 1.0:
                warnings.append(
                    f"力限制持续时间({duration}s)较长，可能反应不够及时"
                )
                recommendations.append("建议将force_limit_duration设置为0.5s以下")
        
        return {
            'status': status,
            'issues': issues,
            'warnings': warnings,
            'recommendations': recommendations
        }

    def audit_safety_violations(self, violations: List[Dict]) -> Dict:
        """
        审核安全违规记录
        
        Args:
            violations: 违规记录列表
            
        Returns:
            分析报告
        """
        if not violations:
            return {
                'total_violations': 0,
                'status': SafetyStatus.SAFE,
                'message': '无安全违规记录'
            }
        
        # 按类型统计
        violation_types = {}
        severity_counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
        
        recent_violations = 0
        now = datetime.now()
        
        for violation in violations:
            # 统计类型
            v_type = violation.get('type', 'unknown')
            violation_types[v_type] = violation_types.get(v_type, 0) + 1
            
            # 统计严重程度
            severity = violation.get('severity', 'medium')
            if severity in severity_counts:
                severity_counts[severity] += 1
            
            # 统计最近违规（24小时内）
            if 'timestamp' in violation:
                try:
                    v_time = datetime.fromtimestamp(violation['timestamp'])
                    if (now - v_time) < timedelta(hours=24):
                        recent_violations += 1
                except:
                    pass
        
        # 确定状态
        status = SafetyStatus.SAFE
        if severity_counts['critical'] > 0:
            status = SafetyStatus.DANGER
        elif severity_counts['high'] > 0 or recent_violations > 5:
            status = SafetyStatus.WARNING
        elif severity_counts['medium'] > 0 or recent_violations > 0:
            status = SafetyStatus.CAUTION
        
        # 生成建议
        recommendations = []
        if severity_counts['critical'] > 0:
            recommendations.append("存在严重安全违规，建议立即停止使用并检查系统")
        if recent_violations > 5:
            recommendations.append("24小时内违规次数较多，建议检查安全配置和操作规范")
        
        # 分析频繁违规类型
        if violation_types:
            most_common = max(violation_types.items(), key=lambda x: x[1])
            if most_common[1] > len(violations) * 0.3:
                recommendations.append(
                    f"'{most_common[0]}'类型违规占比较高({most_common[1]}次)，"
                    f"建议重点检查相关参数"
                )
        
        return {
            'total_violations': len(violations),
            'status': status,
            'violation_types': violation_types,
            'severity_counts': severity_counts,
            'recent_violations_24h': recent_violations,
            'recommendations': recommendations
        }

    def check_realtime_safety(self, 
                             joint_positions: np.ndarray,
                             joint_velocities: np.ndarray,
                             forces: np.ndarray,
                             joint_limits: Dict) -> Dict:
        """
        实时安全检查
        
        Args:
            joint_positions: 关节位置
            joint_velocities: 关节速度
            forces: 力传感器数据
            joint_limits: 关节限制
            
        Returns:
            安全检查结果
        """
        alerts = []
        status = SafetyStatus.SAFE
        
        # 检查关节位置限制
        if 'min' in joint_limits and 'max' in joint_limits:
            min_limits = np.array(joint_limits['min'])
            max_limits = np.array(joint_limits['max'])
            
            # 检查是否接近限制（90%）
            min_margin = joint_positions - min_limits
            max_margin = max_limits - joint_positions
            range_size = max_limits - min_limits
            
            for i, (min_m, max_m, rng) in enumerate(zip(min_margin, max_margin, range_size)):
                if min_m < 0 or max_m < 0:
                    alerts.append(f"关节{i}超出位置限制")
                    status = SafetyStatus.DANGER
                elif min_m < rng * 0.1 or max_m < rng * 0.1:
                    alerts.append(f"关节{i}接近位置限制")
                    if status == SafetyStatus.SAFE:
                        status = SafetyStatus.CAUTION
        
        # 检查速度限制
        if 'velocity' in joint_limits:
            vel_limits = np.array(joint_limits['velocity'])
            vel_violations = np.abs(joint_velocities) > vel_limits
            
            if np.any(vel_violations):
                violated_joints = np.where(vel_violations)[0]
                alerts.append(f"关节{violated_joints.tolist()}超出速度限制")
                status = SafetyStatus.WARNING
        
        # 检查力限制
        linear_force = np.linalg.norm(forces[:3])
        if linear_force > self.rehab_limits['max_force']:
            if linear_force > self.standard_limits['max_force']:
                alerts.append(f"线性力({linear_force:.1f}N)超出标准限制")
                status = SafetyStatus.DANGER
            else:
                alerts.append(f"线性力({linear_force:.1f}N)超出康复推荐限制")
                if status == SafetyStatus.SAFE:
                    status = SafetyStatus.WARNING
        
        return {
            'status': status,
            'alerts': alerts,
            'metrics': {
                'joint_positions': joint_positions.tolist(),
                'joint_velocities': joint_velocities.tolist(),
                'linear_force': float(linear_force)
            }
        }

    def generate_safety_report(self, 
                              config_audit: Dict,
                              violations_audit: Dict) -> str:
        """
        生成安全审核报告
        
        Args:
            config_audit: 配置审核结果
            violations_audit: 违规审核结果
            
        Returns:
            格式化报告
        """
        report = []
        report.append("=" * 70)
        report.append("安全系统审核报告")
        report.append("=" * 70)
        report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 配置审核部分
        report.append("\n" + "-" * 70)
        report.append("安全配置审核")
        report.append("-" * 70)
        report.append(f"状态: {config_audit['status'].value}")
        
        if config_audit['issues']:
            report.append(f"\n问题 ({len(config_audit['issues'])}项):")
            for i, issue in enumerate(config_audit['issues'], 1):
                report.append(f"  {i}. {issue}")
        
        if config_audit['warnings']:
            report.append(f"\n警告 ({len(config_audit['warnings'])}项):")
            for i, warning in enumerate(config_audit['warnings'], 1):
                report.append(f"  {i}. {warning}")
        
        if config_audit['recommendations']:
            report.append(f"\n建议 ({len(config_audit['recommendations'])}项):")
            for i, rec in enumerate(config_audit['recommendations'], 1):
                report.append(f"  {i}. {rec}")
        
        # 违规审核部分
        report.append("\n" + "-" * 70)
        report.append("安全违规记录审核")
        report.append("-" * 70)
        report.append(f"状态: {violations_audit['status'].value}")
        report.append(f"总违规次数: {violations_audit['total_violations']}")
        
        if violations_audit['total_violations'] > 0:
            report.append(f"24小时内违规: {violations_audit['recent_violations_24h']}次")
            
            report.append("\n按严重程度统计:")
            for severity, count in violations_audit['severity_counts'].items():
                if count > 0:
                    report.append(f"  {severity}: {count}次")
            
            report.append("\n按类型统计:")
            for v_type, count in violations_audit['violation_types'].items():
                report.append(f"  {v_type}: {count}次")
            
            if violations_audit['recommendations']:
                report.append("\n建议:")
                for i, rec in enumerate(violations_audit['recommendations'], 1):
                    report.append(f"  {i}. {rec}")
        else:
            report.append("未发现安全违规")
        
        report.append("\n" + "=" * 70)
        
        return '\n'.join(report)


def main():
    """测试安全审核器"""
    auditor = SafetyAuditor()
    
    # 测试配置审核
    test_config = {
        'max_force': 35.0,
        'max_velocity': 0.8,
        'max_torque': 9.0,
        'collision_threshold': 18.0,
        'e_stop_enabled': True,
        'force_limit_duration': 0.3
    }
    
    config_result = auditor.audit_safety_config(test_config)
    print("配置审核结果:")
    print(f"  状态: {config_result['status'].value}")
    print(f"  问题: {config_result['issues']}")
    print(f"  警告: {config_result['warnings']}")
    
    # 测试违规审核
    test_violations = [
        {'type': 'force', 'severity': 'medium', 'timestamp': datetime.now().timestamp()},
        {'type': 'velocity', 'severity': 'low', 'timestamp': datetime.now().timestamp()},
    ]
    
    violations_result = auditor.audit_safety_violations(test_violations)
    print("\n违规审核结果:")
    print(f"  状态: {violations_result['status'].value}")
    print(f"  总数: {violations_result['total_violations']}")
    
    # 生成报告
    print("\n" + auditor.generate_safety_report(config_result, violations_result))


if __name__ == "__main__":
    main()
