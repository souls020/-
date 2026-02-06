#!/usr/bin/env python3
"""
配置文件审核器
验证系统配置文件的正确性和安全性
"""

import yaml
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import os


class AuditLevel(Enum):
    """审核级别"""
    PASS = "通过"
    WARNING = "警告"
    ERROR = "错误"
    CRITICAL = "严重错误"


@dataclass
class AuditResult:
    """审核结果"""
    level: AuditLevel
    category: str
    message: str
    details: Optional[Dict] = None


class ConfigAuditor:
    """
    配置文件审核器
    检查关节限制、PID参数、安全参数等配置的合理性
    """

    def __init__(self):
        """初始化审核器"""
        self.results: List[AuditResult] = []
        
        # 安全限制标准
        self.safety_standards = {
            'max_force': (0.1, 100.0),  # N (最小, 最大)
            'max_torque': (0.1, 50.0),  # Nm
            'max_velocity': (0.01, 5.0),  # rad/s
            'max_acceleration': (0.01, 10.0),  # rad/s^2
            'collision_threshold': (1.0, 80.0)  # N
        }
        
        # PID增益合理范围
        self.pid_ranges = {
            'p': (0.1, 10000.0),
            'i': (0.0, 1000.0),
            'd': (0.0, 500.0)
        }

    def audit_controller_config(self, config_path: str) -> List[AuditResult]:
        """
        审核控制器配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            审核结果列表
        """
        self.results = []
        
        # 检查文件是否存在
        if not os.path.exists(config_path):
            self.results.append(AuditResult(
                level=AuditLevel.CRITICAL,
                category="文件存在性",
                message=f"配置文件不存在: {config_path}"
            ))
            return self.results
        
        try:
            # 加载配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 检查必需字段
            self._check_required_fields(config)
            
            # 检查机器人配置
            if 'robot' in config:
                self._check_robot_config(config['robot'])
            
            # 检查关节限制
            if 'joint_limits' in config:
                self._check_joint_limits(config['joint_limits'])
            
            # 检查PID增益
            if 'pid_gains' in config:
                self._check_pid_gains(config['pid_gains'])
            
            # 检查安全参数
            if 'safety' in config:
                self._check_safety_params(config['safety'])
                
        except yaml.YAMLError as e:
            self.results.append(AuditResult(
                level=AuditLevel.CRITICAL,
                category="文件格式",
                message=f"YAML解析错误: {str(e)}"
            ))
        except Exception as e:
            self.results.append(AuditResult(
                level=AuditLevel.ERROR,
                category="审核异常",
                message=f"审核过程中发生错误: {str(e)}"
            ))
        
        return self.results

    def _check_required_fields(self, config: Dict):
        """检查必需字段"""
        required_fields = ['robot', 'joint_limits', 'pid_gains', 'safety']
        
        for field in required_fields:
            if field not in config:
                self.results.append(AuditResult(
                    level=AuditLevel.ERROR,
                    category="必需字段",
                    message=f"缺少必需字段: {field}"
                ))

    def _check_robot_config(self, robot_config: Dict):
        """检查机器人配置"""
        # 检查关节数量
        if 'num_joints' not in robot_config:
            self.results.append(AuditResult(
                level=AuditLevel.ERROR,
                category="机器人配置",
                message="缺少num_joints字段"
            ))
        else:
            num_joints = robot_config['num_joints']
            if not isinstance(num_joints, int) or num_joints < 1 or num_joints > 12:
                self.results.append(AuditResult(
                    level=AuditLevel.ERROR,
                    category="机器人配置",
                    message=f"num_joints值不合理: {num_joints} (应在1-12之间)"
                ))
        
        # 检查关节名称
        if 'joint_names' not in robot_config:
            self.results.append(AuditResult(
                level=AuditLevel.WARNING,
                category="机器人配置",
                message="缺少joint_names字段"
            ))
        else:
            joint_names = robot_config['joint_names']
            if not isinstance(joint_names, list):
                self.results.append(AuditResult(
                    level=AuditLevel.ERROR,
                    category="机器人配置",
                    message="joint_names应为列表类型"
                ))
            elif len(joint_names) != robot_config.get('num_joints', 0):
                self.results.append(AuditResult(
                    level=AuditLevel.WARNING,
                    category="机器人配置",
                    message=f"joint_names数量({len(joint_names)})与num_joints不匹配"
                ))

    def _check_joint_limits(self, limits: Dict):
        """检查关节限制"""
        required_limit_fields = ['min', 'max', 'velocity', 'acceleration']
        
        for field in required_limit_fields:
            if field not in limits:
                self.results.append(AuditResult(
                    level=AuditLevel.ERROR,
                    category="关节限制",
                    message=f"缺少{field}限制"
                ))
                continue
            
            values = limits[field]
            if not isinstance(values, list):
                self.results.append(AuditResult(
                    level=AuditLevel.ERROR,
                    category="关节限制",
                    message=f"{field}应为列表类型"
                ))
                continue
            
            # 检查数值合理性
            if field == 'min' and 'max' in limits:
                max_values = limits['max']
                if len(values) == len(max_values):
                    for i, (min_val, max_val) in enumerate(zip(values, max_values)):
                        if min_val >= max_val:
                            self.results.append(AuditResult(
                                level=AuditLevel.ERROR,
                                category="关节限制",
                                message=f"关节{i}: 最小值({min_val})应小于最大值({max_val})"
                            ))
            
            # 检查速度和加速度限制
            if field in ['velocity', 'acceleration']:
                for i, val in enumerate(values):
                    if val <= 0:
                        self.results.append(AuditResult(
                            level=AuditLevel.ERROR,
                            category="关节限制",
                            message=f"关节{i}的{field}值应为正数: {val}"
                        ))
                    elif field == 'velocity' and val > 10.0:
                        self.results.append(AuditResult(
                            level=AuditLevel.WARNING,
                            category="关节限制",
                            message=f"关节{i}的速度限制过高({val} rad/s)，建议小于10 rad/s"
                        ))

    def _check_pid_gains(self, pid_gains: Dict):
        """检查PID增益"""
        for joint_id, gains in pid_gains.items():
            if not isinstance(gains, dict):
                self.results.append(AuditResult(
                    level=AuditLevel.ERROR,
                    category="PID增益",
                    message=f"{joint_id}的增益应为字典类型"
                ))
                continue
            
            for gain_type in ['p', 'i', 'd']:
                if gain_type not in gains:
                    self.results.append(AuditResult(
                        level=AuditLevel.ERROR,
                        category="PID增益",
                        message=f"{joint_id}缺少{gain_type}增益"
                    ))
                    continue
                
                value = gains[gain_type]
                min_val, max_val = self.pid_ranges[gain_type]
                
                if not isinstance(value, (int, float)):
                    self.results.append(AuditResult(
                        level=AuditLevel.ERROR,
                        category="PID增益",
                        message=f"{joint_id}的{gain_type}增益应为数值类型"
                    ))
                elif value < min_val or value > max_val:
                    self.results.append(AuditResult(
                        level=AuditLevel.WARNING,
                        category="PID增益",
                        message=f"{joint_id}的{gain_type}增益({value})超出建议范围({min_val}-{max_val})"
                    ))
                elif gain_type == 'i' and value > 500.0:
                    self.results.append(AuditResult(
                        level=AuditLevel.WARNING,
                        category="PID增益",
                        message=f"{joint_id}的积分增益过高({value})，可能导致积分饱和"
                    ))

    def _check_safety_params(self, safety: Dict):
        """检查安全参数"""
        for param, (min_val, max_val) in self.safety_standards.items():
            if param not in safety:
                self.results.append(AuditResult(
                    level=AuditLevel.CRITICAL,
                    category="安全参数",
                    message=f"缺少关键安全参数: {param}"
                ))
                continue
            
            value = safety[param]
            if not isinstance(value, (int, float)):
                self.results.append(AuditResult(
                    level=AuditLevel.CRITICAL,
                    category="安全参数",
                    message=f"{param}应为数值类型"
                ))
            elif value < min_val or value > max_val:
                self.results.append(AuditResult(
                    level=AuditLevel.CRITICAL,
                    category="安全参数",
                    message=f"{param}值({value})超出安全范围({min_val}-{max_val})"
                ))
            elif param == 'max_force' and value > 50.0:
                self.results.append(AuditResult(
                    level=AuditLevel.WARNING,
                    category="安全参数",
                    message=f"最大力限制({value}N)较高，建议在康复应用中设置为50N以下"
                ))

    def audit_training_protocol(self, protocol_path: str) -> List[AuditResult]:
        """
        审核训练协议配置
        
        Args:
            protocol_path: 训练协议配置文件路径
            
        Returns:
            审核结果列表
        """
        self.results = []
        
        if not os.path.exists(protocol_path):
            self.results.append(AuditResult(
                level=AuditLevel.CRITICAL,
                category="文件存在性",
                message=f"训练协议文件不存在: {protocol_path}"
            ))
            return self.results
        
        try:
            with open(protocol_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 检查上肢训练协议
            if 'upper_limb' in config:
                self._check_limb_protocols(config['upper_limb'], "上肢")
            
            # 检查下肢训练协议
            if 'lower_limb' in config:
                self._check_limb_protocols(config['lower_limb'], "下肢")
                
        except Exception as e:
            self.results.append(AuditResult(
                level=AuditLevel.ERROR,
                category="审核异常",
                message=f"审核训练协议时发生错误: {str(e)}"
            ))
        
        return self.results

    def _check_limb_protocols(self, protocols: Dict, limb_type: str):
        """检查肢体训练协议"""
        for exercise_name, params in protocols.items():
            if not isinstance(params, dict):
                self.results.append(AuditResult(
                    level=AuditLevel.ERROR,
                    category="训练协议",
                    message=f"{limb_type}-{exercise_name}: 参数应为字典类型"
                ))
                continue
            
            # 检查ROM参数
            if 'rom' in params:
                rom = params['rom']
                if isinstance(rom, (int, float)):
                    if rom < 0 or rom > 180:
                        self.results.append(AuditResult(
                            level=AuditLevel.WARNING,
                            category="训练协议",
                            message=f"{limb_type}-{exercise_name}: ROM({rom}度)超出常见范围(0-180度)"
                        ))
            
            # 检查速度参数
            if 'speed' in params:
                speed = params['speed']
                if isinstance(speed, (int, float)):
                    if speed <= 0 or speed > 2.0:
                        self.results.append(AuditResult(
                            level=AuditLevel.WARNING,
                            category="训练协议",
                            message=f"{limb_type}-{exercise_name}: 速度({speed} rad/s)建议在0-2.0之间"
                        ))

    def generate_report(self) -> str:
        """
        生成审核报告
        
        Returns:
            格式化的审核报告
        """
        if not self.results:
            return "审核完成：未发现问题"
        
        # 统计各级别数量
        level_counts = {
            AuditLevel.PASS: 0,
            AuditLevel.WARNING: 0,
            AuditLevel.ERROR: 0,
            AuditLevel.CRITICAL: 0
        }
        
        for result in self.results:
            level_counts[result.level] += 1
        
        # 生成报告
        report = "=" * 60 + "\n"
        report += "配置审核报告\n"
        report += "=" * 60 + "\n\n"
        
        report += f"总问题数: {len(self.results)}\n"
        report += f"  严重错误: {level_counts[AuditLevel.CRITICAL]}\n"
        report += f"  错误: {level_counts[AuditLevel.ERROR]}\n"
        report += f"  警告: {level_counts[AuditLevel.WARNING]}\n"
        report += f"  通过: {level_counts[AuditLevel.PASS]}\n\n"
        
        # 按级别分组显示
        for level in [AuditLevel.CRITICAL, AuditLevel.ERROR, AuditLevel.WARNING, AuditLevel.PASS]:
            level_results = [r for r in self.results if r.level == level]
            if level_results:
                report += f"\n[{level.value}] ({len(level_results)}项)\n"
                report += "-" * 60 + "\n"
                for result in level_results:
                    report += f"  类别: {result.category}\n"
                    report += f"  信息: {result.message}\n"
                    if result.details:
                        report += f"  详情: {result.details}\n"
                    report += "\n"
        
        return report

    def has_critical_issues(self) -> bool:
        """检查是否存在严重问题"""
        return any(r.level == AuditLevel.CRITICAL for r in self.results)

    def has_errors(self) -> bool:
        """检查是否存在错误"""
        return any(r.level in [AuditLevel.CRITICAL, AuditLevel.ERROR] for r in self.results)


def main():
    """测试审核器"""
    auditor = ConfigAuditor()
    
    # 测试控制器配置审核
    config_path = "src/robot_control/config/controller_params.yaml"
    if os.path.exists(config_path):
        print("审核控制器配置...")
        results = auditor.audit_controller_config(config_path)
        print(auditor.generate_report())
    
    # 测试训练协议审核
    protocol_path = "src/rehabilitation/config/training_protocols.yaml"
    if os.path.exists(protocol_path):
        print("\n审核训练协议...")
        results = auditor.audit_training_protocol(protocol_path)
        print(auditor.generate_report())


if __name__ == "__main__":
    main()
