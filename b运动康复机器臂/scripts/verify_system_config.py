#!/usr/bin/env python3
"""
系统配置验证脚本
自动检查所有系统配置文件的正确性
"""

import os
import sys
from pathlib import Path
import argparse
from typing import List, Dict

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.audit.config_auditor import ConfigAuditor, AuditLevel
from src.audit.safety_auditor import SafetyAuditor, SafetyStatus


class SystemConfigVerifier:
    """系统配置验证器"""
    
    def __init__(self, project_root: Path):
        """
        初始化验证器
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root
        self.config_auditor = ConfigAuditor()
        self.safety_auditor = SafetyAuditor()
        
        # 配置文件路径
        self.config_files = {
            'controller': self.project_root / 'src/robot_control/config/controller_params.yaml',
            'training': self.project_root / 'src/rehabilitation/config/training_protocols.yaml'
        }
        
        self.all_passed = True
        self.results = {}

    def verify_all(self) -> bool:
        """
        验证所有配置文件
        
        Returns:
            是否全部通过
        """
        print("=" * 70)
        print("运动康复机器臂系统 - 配置验证")
        print("=" * 70)
        print()
        
        # 验证控制器配置
        self._verify_controller_config()
        
        # 验证训练协议配置
        self._verify_training_protocol()
        
        # 验证目录结构
        self._verify_directory_structure()
        
        # 验证依赖
        self._verify_dependencies()
        
        # 生成总结
        self._print_summary()
        
        return self.all_passed

    def _verify_controller_config(self):
        """验证控制器配置"""
        print("-" * 70)
        print("1. 验证控制器配置")
        print("-" * 70)
        
        config_path = self.config_files['controller']
        
        if not config_path.exists():
            print(f"❌ 配置文件不存在: {config_path}")
            self.all_passed = False
            self.results['controller'] = {'status': 'missing', 'issues': 1}
            return
        
        # 执行审核
        results = self.config_auditor.audit_controller_config(str(config_path))
        
        # 统计问题
        critical_count = sum(1 for r in results if r.level == AuditLevel.CRITICAL)
        error_count = sum(1 for r in results if r.level == AuditLevel.ERROR)
        warning_count = sum(1 for r in results if r.level == AuditLevel.WARNING)
        
        self.results['controller'] = {
            'status': 'checked',
            'critical': critical_count,
            'errors': error_count,
            'warnings': warning_count
        }
        
        if critical_count > 0 or error_count > 0:
            print(f"❌ 控制器配置存在问题:")
            print(f"   严重错误: {critical_count}")
            print(f"   错误: {error_count}")
            print(f"   警告: {warning_count}")
            self.all_passed = False
            
            # 显示前5个问题
            print("\n   主要问题:")
            for i, result in enumerate(results[:5], 1):
                print(f"   {i}. [{result.level.value}] {result.message}")
        else:
            if warning_count > 0:
                print(f"⚠️  控制器配置通过，但有 {warning_count} 个警告")
            else:
                print("✅ 控制器配置验证通过")
        
        print()

    def _verify_training_protocol(self):
        """验证训练协议配置"""
        print("-" * 70)
        print("2. 验证训练协议配置")
        print("-" * 70)
        
        config_path = self.config_files['training']
        
        if not config_path.exists():
            print(f"❌ 配置文件不存在: {config_path}")
            self.all_passed = False
            self.results['training'] = {'status': 'missing', 'issues': 1}
            return
        
        # 执行审核
        results = self.config_auditor.audit_training_protocol(str(config_path))
        
        # 统计问题
        critical_count = sum(1 for r in results if r.level == AuditLevel.CRITICAL)
        error_count = sum(1 for r in results if r.level == AuditLevel.ERROR)
        warning_count = sum(1 for r in results if r.level == AuditLevel.WARNING)
        
        self.results['training'] = {
            'status': 'checked',
            'critical': critical_count,
            'errors': error_count,
            'warnings': warning_count
        }
        
        if critical_count > 0 or error_count > 0:
            print(f"❌ 训练协议配置存在问题:")
            print(f"   严重错误: {critical_count}")
            print(f"   错误: {error_count}")
            print(f"   警告: {warning_count}")
            self.all_passed = False
        else:
            if warning_count > 0:
                print(f"⚠️  训练协议配置通过，但有 {warning_count} 个警告")
            else:
                print("✅ 训练协议配置验证通过")
        
        print()

    def _verify_directory_structure(self):
        """验证目录结构"""
        print("-" * 70)
        print("3. 验证项目目录结构")
        print("-" * 70)
        
        required_dirs = [
            'src/robot_control',
            'src/rehabilitation',
            'src/embodied_ai',
            'src/human_interaction',
            'src/safety',
            'src/audit',
            'scripts'
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
                print(f"❌ 缺少目录: {dir_path}")
        
        if missing_dirs:
            self.all_passed = False
            self.results['directory'] = {'status': 'incomplete', 'missing': len(missing_dirs)}
        else:
            print("✅ 目录结构完整")
            self.results['directory'] = {'status': 'complete', 'missing': 0}
        
        print()

    def _verify_dependencies(self):
        """验证Python依赖"""
        print("-" * 70)
        print("4. 验证Python依赖")
        print("-" * 70)
        
        required_packages = [
            'numpy',
            'scipy',
            'PyYAML',
            'PyQt6'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
                print(f"✅ {package}")
            except ImportError:
                print(f"❌ {package} (未安装)")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n⚠️  请安装缺失的依赖:")
            print(f"   pip install {' '.join(missing_packages)}")
            # 不将依赖问题标记为严重错误，只是警告
            self.results['dependencies'] = {
                'status': 'incomplete',
                'missing': len(missing_packages)
            }
        else:
            self.results['dependencies'] = {'status': 'complete', 'missing': 0}
        
        print()

    def _print_summary(self):
        """打印总结"""
        print("=" * 70)
        print("验证总结")
        print("=" * 70)
        
        if self.all_passed:
            print("✅ 所有配置验证通过！系统可以安全使用。")
        else:
            print("❌ 配置验证未通过，存在以下问题:")
            
            for name, result in self.results.items():
                if result.get('status') == 'missing':
                    print(f"   - {name}: 配置文件缺失")
                elif result.get('critical', 0) > 0:
                    print(f"   - {name}: {result['critical']} 个严重错误")
                elif result.get('errors', 0) > 0:
                    print(f"   - {name}: {result['errors']} 个错误")
                elif result.get('missing', 0) > 0 and name == 'directory':
                    print(f"   - {name}: {result['missing']} 个目录缺失")
            
            print("\n建议:")
            print("   1. 修复所有严重错误和错误项")
            print("   2. 检查并补全缺失的配置文件")
            print("   3. 运行详细审核以获取具体修复建议")
        
        print("=" * 70)

    def generate_detailed_report(self, output_path: str):
        """
        生成详细报告
        
        Args:
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("系统配置详细验证报告\n")
            f.write("=" * 70 + "\n\n")
            
            # 控制器配置详细报告
            f.write("控制器配置审核:\n")
            f.write("-" * 70 + "\n")
            if self.config_files['controller'].exists():
                self.config_auditor.audit_controller_config(
                    str(self.config_files['controller'])
                )
                f.write(self.config_auditor.generate_report())
            else:
                f.write("配置文件不存在\n")
            
            f.write("\n\n")
            
            # 训练协议详细报告
            f.write("训练协议配置审核:\n")
            f.write("-" * 70 + "\n")
            if self.config_files['training'].exists():
                self.config_auditor.audit_training_protocol(
                    str(self.config_files['training'])
                )
                f.write(self.config_auditor.generate_report())
            else:
                f.write("配置文件不存在\n")
        
        print(f"\n详细报告已保存到: {output_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='验证系统配置')
    parser.add_argument('--detailed-report', type=str,
                       help='生成详细报告并保存到指定文件')
    parser.add_argument('--strict', action='store_true',
                       help='严格模式：警告也视为失败')
    args = parser.parse_args()
    
    # 创建验证器
    verifier = SystemConfigVerifier(project_root)
    
    # 执行验证
    passed = verifier.verify_all()
    
    # 生成详细报告
    if args.detailed_report:
        verifier.generate_detailed_report(args.detailed_report)
    
    # 返回退出码
    if not passed:
        sys.exit(1)
    elif args.strict:
        # 严格模式下检查警告
        has_warnings = any(
            r.get('warnings', 0) > 0 
            for r in verifier.results.values()
        )
        if has_warnings:
            print("\n⚠️  严格模式：存在警告，视为失败")
            sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
