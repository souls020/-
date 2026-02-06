#!/usr/bin/env python3
"""
训练记录审核器
审核和导出训练记录数据
"""

import json
import csv
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import numpy as np


class TrainingRecordAuditor:
    """
    训练记录审核器
    审核训练记录的完整性、导出报告
    """

    def __init__(self, records_dir: str = "training_records"):
        """
        初始化审核器
        
        Args:
            records_dir: 训练记录存储目录
        """
        self.records_dir = Path(records_dir)
        self.records_dir.mkdir(exist_ok=True)

    def audit_training_record(self, record: Dict) -> Dict:
        """
        审核单条训练记录
        
        Args:
            record: 训练记录字典
            
        Returns:
            审核结果
        """
        issues = []
        warnings = []
        metrics = {}
        
        # 检查必需字段
        required_fields = [
            'session_id', 'patient_id', 'exercise_type',
            'start_time', 'end_time', 'parameters'
        ]
        
        for field in required_fields:
            if field not in record:
                issues.append(f"缺少必需字段: {field}")
        
        # 计算训练指标
        if 'start_time' in record and 'end_time' in record:
            try:
                start = datetime.fromisoformat(record['start_time'])
                end = datetime.fromisoformat(record['end_time'])
                duration_minutes = (end - start).total_seconds() / 60
                metrics['duration_minutes'] = duration_minutes
                
                if duration_minutes < 0:
                    issues.append("结束时间早于开始时间")
                elif duration_minutes < 5:
                    warnings.append(f"训练时长过短: {duration_minutes:.1f}分钟")
                elif duration_minutes > 120:
                    warnings.append(f"训练时长过长: {duration_minutes:.1f}分钟")
            except:
                issues.append("时间格式错误")
        
        # 检查完成情况
        if 'parameters' in record:
            params = record['parameters']
            if 'target_sets' in params and 'completed_sets' in params:
                target = params['target_sets']
                completed = params['completed_sets']
                completion_rate = completed / target if target > 0 else 0
                metrics['completion_rate'] = completion_rate
                
                if completion_rate < 0.7:
                    warnings.append(f"完成率较低: {completion_rate*100:.0f}%")
        
        # 检查性能数据
        if 'performance_data' in record:
            perf = record['performance_data']
            
            if 'max_rom' in perf:
                metrics['max_rom'] = perf['max_rom']
            
            if 'avg_force' in perf:
                metrics['avg_force'] = perf['avg_force']
                if perf['avg_force'] > 50:
                    warnings.append(f"平均力过大: {perf['avg_force']:.1f}N")
            
            if 'fatigue_level' in perf:
                metrics['final_fatigue'] = perf['fatigue_level']
                if perf['fatigue_level'] > 0.8:
                    warnings.append(f"疲劳水平过高: {perf['fatigue_level']:.2f}")
        
        # 检查安全事件
        if 'safety_events' in record and len(record['safety_events']) > 0:
            warnings.append(f"发生{len(record['safety_events'])}次安全事件")
            metrics['safety_events_count'] = len(record['safety_events'])
        else:
            metrics['safety_events_count'] = 0
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'metrics': metrics
        }

    def audit_patient_history(self, patient_id: str, 
                             records: List[Dict]) -> Dict:
        """
        审核患者历史记录
        
        Args:
            patient_id: 患者ID
            records: 训练记录列表
            
        Returns:
            审核报告
        """
        if not records:
            return {
                'patient_id': patient_id,
                'total_sessions': 0,
                'message': '无训练记录'
            }
        
        # 统计信息
        total_sessions = len(records)
        total_duration = 0
        completion_rates = []
        fatigue_levels = []
        safety_events = 0
        exercise_types = {}
        
        for record in records:
            audit_result = self.audit_training_record(record)
            
            # 累计时长
            if 'duration_minutes' in audit_result['metrics']:
                total_duration += audit_result['metrics']['duration_minutes']
            
            # 收集完成率
            if 'completion_rate' in audit_result['metrics']:
                completion_rates.append(audit_result['metrics']['completion_rate'])
            
            # 收集疲劳水平
            if 'final_fatigue' in audit_result['metrics']:
                fatigue_levels.append(audit_result['metrics']['final_fatigue'])
            
            # 统计安全事件
            safety_events += audit_result['metrics'].get('safety_events_count', 0)
            
            # 统计训练类型
            if 'exercise_type' in record:
                ex_type = record['exercise_type']
                exercise_types[ex_type] = exercise_types.get(ex_type, 0) + 1
        
        # 计算平均值
        avg_completion = np.mean(completion_rates) if completion_rates else 0
        avg_fatigue = np.mean(fatigue_levels) if fatigue_levels else 0
        
        # 趋势分析
        trends = self._analyze_trends(records)
        
        return {
            'patient_id': patient_id,
            'total_sessions': total_sessions,
            'total_duration_hours': total_duration / 60,
            'avg_completion_rate': avg_completion,
            'avg_fatigue_level': avg_fatigue,
            'total_safety_events': safety_events,
            'exercise_distribution': exercise_types,
            'trends': trends,
            'recommendations': self._generate_recommendations(
                avg_completion, avg_fatigue, safety_events, total_sessions
            )
        }

    def _analyze_trends(self, records: List[Dict]) -> Dict:
        """分析训练趋势"""
        if len(records) < 3:
            return {'message': '数据不足以分析趋势'}
        
        # 按时间排序
        sorted_records = sorted(
            records, 
            key=lambda x: x.get('start_time', ''),
            reverse=False
        )
        
        # 提取完成率趋势
        completion_trend = []
        fatigue_trend = []
        
        for record in sorted_records:
            result = self.audit_training_record(record)
            if 'completion_rate' in result['metrics']:
                completion_trend.append(result['metrics']['completion_rate'])
            if 'final_fatigue' in result['metrics']:
                fatigue_trend.append(result['metrics']['final_fatigue'])
        
        trends = {}
        
        # 计算完成率趋势
        if len(completion_trend) >= 3:
            recent_avg = np.mean(completion_trend[-3:])
            early_avg = np.mean(completion_trend[:3])
            completion_change = recent_avg - early_avg
            
            trends['completion_rate'] = {
                'recent_average': recent_avg,
                'early_average': early_avg,
                'change': completion_change,
                'direction': 'improving' if completion_change > 0.05 else 
                           ('declining' if completion_change < -0.05 else 'stable')
            }
        
        # 计算疲劳趋势
        if len(fatigue_trend) >= 3:
            recent_avg = np.mean(fatigue_trend[-3:])
            early_avg = np.mean(fatigue_trend[:3])
            fatigue_change = recent_avg - early_avg
            
            trends['fatigue_level'] = {
                'recent_average': recent_avg,
                'early_average': early_avg,
                'change': fatigue_change,
                'direction': 'increasing' if fatigue_change > 0.1 else 
                           ('decreasing' if fatigue_change < -0.1 else 'stable')
            }
        
        return trends

    def _generate_recommendations(self, avg_completion: float, 
                                  avg_fatigue: float,
                                  safety_events: int,
                                  total_sessions: int) -> List[str]:
        """生成训练建议"""
        recommendations = []
        
        if avg_completion < 0.7:
            recommendations.append("平均完成率较低，建议调整训练难度或参数")
        elif avg_completion > 0.9:
            recommendations.append("完成率优秀，可以考虑增加训练难度")
        
        if avg_fatigue > 0.7:
            recommendations.append("平均疲劳水平较高，建议增加休息时间或降低强度")
        
        if safety_events > 0:
            event_rate = safety_events / total_sessions if total_sessions > 0 else 0
            if event_rate > 0.1:
                recommendations.append(
                    f"安全事件发生率较高({event_rate*100:.1f}%)，需要重点关注安全设置"
                )
        
        if total_sessions < 5:
            recommendations.append("训练次数较少，建议坚持规律训练")
        
        return recommendations

    def export_to_csv(self, records: List[Dict], output_path: str):
        """
        导出记录到CSV文件
        
        Args:
            records: 训练记录列表
            output_path: 输出文件路径
        """
        if not records:
            print("没有记录可导出")
            return
        
        # 定义CSV字段
        fieldnames = [
            'session_id', 'patient_id', 'exercise_type',
            'start_time', 'end_time', 'duration_minutes',
            'target_sets', 'completed_sets', 'completion_rate',
            'max_rom', 'avg_force', 'final_fatigue',
            'safety_events_count', 'notes'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in records:
                # 审核记录并提取指标
                audit_result = self.audit_training_record(record)
                metrics = audit_result['metrics']
                
                # 准备导出行
                row = {
                    'session_id': record.get('session_id', ''),
                    'patient_id': record.get('patient_id', ''),
                    'exercise_type': record.get('exercise_type', ''),
                    'start_time': record.get('start_time', ''),
                    'end_time': record.get('end_time', ''),
                    'duration_minutes': metrics.get('duration_minutes', 0),
                    'target_sets': record.get('parameters', {}).get('target_sets', 0),
                    'completed_sets': record.get('parameters', {}).get('completed_sets', 0),
                    'completion_rate': metrics.get('completion_rate', 0),
                    'max_rom': metrics.get('max_rom', 0),
                    'avg_force': metrics.get('avg_force', 0),
                    'final_fatigue': metrics.get('final_fatigue', 0),
                    'safety_events_count': metrics.get('safety_events_count', 0),
                    'notes': record.get('notes', '')
                }
                
                writer.writerow(row)
        
        print(f"成功导出{len(records)}条记录到: {output_path}")

    def export_patient_report(self, patient_id: str, 
                             records: List[Dict],
                             output_path: str):
        """
        生成患者综合报告
        
        Args:
            patient_id: 患者ID
            records: 训练记录列表
            output_path: 输出文件路径
        """
        # 审核患者历史
        history = self.audit_patient_history(patient_id, records)
        
        # 生成报告
        report = []
        report.append("=" * 70)
        report.append(f"患者训练记录综合报告")
        report.append("=" * 70)
        report.append(f"\n患者ID: {patient_id}")
        report.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("\n" + "-" * 70)
        report.append("总体统计")
        report.append("-" * 70)
        report.append(f"总训练次数: {history['total_sessions']}")
        report.append(f"总训练时长: {history['total_duration_hours']:.1f} 小时")
        report.append(f"平均完成率: {history['avg_completion_rate']*100:.1f}%")
        report.append(f"平均疲劳水平: {history['avg_fatigue_level']:.2f}")
        report.append(f"安全事件总数: {history['total_safety_events']}")
        
        report.append("\n" + "-" * 70)
        report.append("训练类型分布")
        report.append("-" * 70)
        for ex_type, count in history['exercise_distribution'].items():
            percentage = count / history['total_sessions'] * 100
            report.append(f"  {ex_type}: {count}次 ({percentage:.1f}%)")
        
        if 'trends' in history and 'message' not in history['trends']:
            report.append("\n" + "-" * 70)
            report.append("趋势分析")
            report.append("-" * 70)
            
            if 'completion_rate' in history['trends']:
                cr = history['trends']['completion_rate']
                report.append(f"\n完成率趋势: {cr['direction']}")
                report.append(f"  最近平均: {cr['recent_average']*100:.1f}%")
                report.append(f"  早期平均: {cr['early_average']*100:.1f}%")
                report.append(f"  变化: {cr['change']*100:+.1f}%")
            
            if 'fatigue_level' in history['trends']:
                fl = history['trends']['fatigue_level']
                report.append(f"\n疲劳水平趋势: {fl['direction']}")
                report.append(f"  最近平均: {fl['recent_average']:.2f}")
                report.append(f"  早期平均: {fl['early_average']:.2f}")
                report.append(f"  变化: {fl['change']:+.2f}")
        
        if history['recommendations']:
            report.append("\n" + "-" * 70)
            report.append("训练建议")
            report.append("-" * 70)
            for i, rec in enumerate(history['recommendations'], 1):
                report.append(f"  {i}. {rec}")
        
        report.append("\n" + "=" * 70)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"患者报告已生成: {output_path}")

    def save_record(self, record: Dict) -> str:
        """
        保存训练记录
        
        Args:
            record: 训练记录
            
        Returns:
            保存的文件路径
        """
        # 生成文件名
        session_id = record.get('session_id', datetime.now().strftime('%Y%m%d%H%M%S'))
        patient_id = record.get('patient_id', 'unknown')
        
        filename = f"{patient_id}_{session_id}.json"
        filepath = self.records_dir / filename
        
        # 添加时间戳
        record['saved_at'] = datetime.now().isoformat()
        
        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        
        return str(filepath)

    def load_patient_records(self, patient_id: str) -> List[Dict]:
        """
        加载患者所有记录
        
        Args:
            patient_id: 患者ID
            
        Returns:
            记录列表
        """
        records = []
        
        # 查找所有该患者的记录文件
        pattern = f"{patient_id}_*.json"
        for filepath in self.records_dir.glob(pattern):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    record = json.load(f)
                    records.append(record)
            except Exception as e:
                print(f"加载记录失败 {filepath}: {str(e)}")
        
        # 按时间排序
        records.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        
        return records


def main():
    """测试训练记录审核器"""
    auditor = TrainingRecordAuditor()
    
    # 创建测试记录
    test_record = {
        'session_id': 'S001',
        'patient_id': 'P001',
        'exercise_type': '肩部外展',
        'start_time': '2024-02-01T10:00:00',
        'end_time': '2024-02-01T10:30:00',
        'parameters': {
            'target_sets': 3,
            'completed_sets': 3,
            'target_reps': 10,
            'completed_reps': 10,
            'speed': 0.3,
            'rom_percentage': 80
        },
        'performance_data': {
            'max_rom': 75.0,
            'avg_force': 15.5,
            'fatigue_level': 0.65
        },
        'safety_events': [],
        'notes': '训练顺利完成'
    }
    
    # 审核记录
    result = auditor.audit_training_record(test_record)
    print("审核结果:")
    print(f"  有效: {result['is_valid']}")
    print(f"  问题: {result['issues']}")
    print(f"  警告: {result['warnings']}")
    print(f"  指标: {result['metrics']}")


if __name__ == "__main__":
    main()
