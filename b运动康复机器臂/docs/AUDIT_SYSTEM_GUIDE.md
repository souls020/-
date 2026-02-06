# 审核系统使用指南

## 概述

审核系统为运动康复机器臂提供全面的配置验证、患者数据审核和训练记录管理功能，确保系统安全可靠地运行。

## 功能模块

### 1. 配置审核器 (ConfigAuditor)

验证系统配置文件的正确性和安全性。

**支持的审核类型：**
- 控制器参数配置 (`controller_params.yaml`)
- 训练协议配置 (`training_protocols.yaml`)
- 关节限制验证
- PID增益合理性检查
- 安全参数验证

**使用方法：**

```python
from src.audit.config_auditor import ConfigAuditor

auditor = ConfigAuditor()

# 审核控制器配置
results = auditor.audit_controller_config('path/to/controller_params.yaml')
print(auditor.generate_report())

# 审核训练协议
results = auditor.audit_training_protocol('path/to/training_protocols.yaml')
print(auditor.generate_report())
```

**命令行使用：**

```bash
# 使用系统配置验证脚本
python scripts/verify_system_config.py

# 生成详细报告
python scripts/verify_system_config.py --detailed-report report.txt

# 严格模式（警告也视为失败）
python scripts/verify_system_config.py --strict
```

### 2. 患者数据审核器 (PatientDataAuditor)

验证患者评估数据的完整性、一致性和合理性。

**验证项目：**
- 患者基本信息（ID、姓名、年龄）
- 评估数据（肌肉强度、活动范围、疼痛水平、疲劳水平）
- 数据一致性检查
- 异常值检测

**使用方法：**

```python
from src.audit.patient_data_auditor import PatientDataAuditor, PatientRecord

auditor = PatientDataAuditor()

# 创建患者记录
record = PatientRecord(
    patient_id="P001",
    name="张三",
    age=65,
    diagnosis="脑卒中后偏瘫",
    injury_date="2024-01-01",
    assessment_date="2024-02-01",
    muscle_strength=[0.3, 0.4, 0.35, 0.5, 0.45, 0.4],
    range_of_motion=[45.0, 60.0, 50.0, 70.0, 55.0, 65.0],
    pain_level=4.5,
    fatigue_level=0.6
)

# 验证记录
result = auditor.validate_patient_record(record)
print(auditor.generate_validation_report(result))

# 比较两次评估
previous_record = ...  # 前一次评估
current_record = ...   # 当前评估
progress = auditor.compare_assessments(previous_record, current_record)
```

### 3. 训练记录审核器 (TrainingRecordAuditor)

管理和审核训练会话记录，导出训练数据。

**功能：**
- 训练记录验证
- 患者历史统计
- 趋势分析
- 导出CSV格式
- 生成综合报告

**使用方法：**

```python
from src.audit.training_record_auditor import TrainingRecordAuditor

auditor = TrainingRecordAuditor()

# 审核单条记录
record = {
    'session_id': 'S001',
    'patient_id': 'P001',
    'exercise_type': '肩部外展',
    'start_time': '2024-02-01T10:00:00',
    'end_time': '2024-02-01T10:30:00',
    'parameters': {
        'target_sets': 3,
        'completed_sets': 3
    }
}
result = auditor.audit_training_record(record)

# 保存记录
filepath = auditor.save_record(record)

# 加载患者所有记录
records = auditor.load_patient_records('P001')

# 审核患者历史
history = auditor.audit_patient_history('P001', records)

# 导出CSV
auditor.export_to_csv(records, 'patient_records.csv')

# 生成综合报告
auditor.export_patient_report('P001', records, 'patient_report.txt')
```

### 4. 安全审核器 (SafetyAuditor)

审核安全系统配置和监控安全违规。

**功能：**
- 安全参数验证
- 实时安全检查
- 违规记录分析
- 安全报告生成

**使用方法：**

```python
from src.audit.safety_auditor import SafetyAuditor
import numpy as np

auditor = SafetyAuditor()

# 审核安全配置
config = {
    'max_force': 30.0,
    'max_velocity': 0.5,
    'max_torque': 8.0,
    'collision_threshold': 15.0,
    'e_stop_enabled': True
}
result = auditor.audit_safety_config(config)

# 实时安全检查
joint_positions = np.array([0.5, 0.3, -0.2, 0.1, 0.4, -0.1])
joint_velocities = np.array([0.1, 0.2, 0.15, 0.1, 0.05, 0.1])
forces = np.array([10.0, 5.0, 3.0, 2.0, 1.0, 1.5])
joint_limits = {
    'min': np.array([-3.14] * 6),
    'max': np.array([3.14] * 6),
    'velocity': np.array([2.0] * 6)
}

safety_result = auditor.check_realtime_safety(
    joint_positions, joint_velocities, forces, joint_limits
)

# 审核违规记录
violations = [...]  # 违规记录列表
violations_result = auditor.audit_safety_violations(violations)
```

## GUI界面使用

系统GUI提供了完整的审核界面。

### 启动GUI

```bash
python src/human_interaction/gui/main_window.py
```

### 审核功能

1. **切换到"审核"标签页**

2. **患者数据审核**
   - 输入患者基本信息
   - 点击"审核患者数据"按钮
   - 查看审核结果和建议

3. **加载历史记录**
   - 输入患者ID
   - 点击"加载历史记录"
   - 查看统计信息和趋势

4. **配置文件审核**
   - 点击"审核控制器配置"或"审核训练协议"
   - 选择配置文件
   - 查看详细审核报告

5. **导出功能**
   - 点击"导出训练记录(CSV)"导出数据
   - 点击"生成患者报告"生成综合报告

## 安全标准

### 力和扭矩限制

| 参数 | 标准限制 | 康复推荐 | 单位 |
|------|---------|---------|------|
| 最大线性力 | 50.0 | 30.0 | N |
| 最大扭矩 | 10.0 | 8.0 | Nm |
| 碰撞阈值 | 20.0 | 15.0 | N |

### 运动限制

| 参数 | 标准限制 | 康复推荐 | 单位 |
|------|---------|---------|------|
| 最大速度 | 1.0 | 0.5 | rad/s |
| 最大加速度 | 2.0 | 1.0 | rad/s² |

### 患者评估标准

| 指标 | 正常范围 | 警报阈值 |
|------|---------|---------|
| 疼痛水平 | 0-10 | ≥7.0 |
| 疲劳水平 | 0-1 | ≥0.8 |
| 肌肉强度 | 0-1 | <0.2 |
| 活动范围 | 0-180° | <30° |

## 运行测试

### 单元测试

```bash
# 运行所有审核系统测试
python tests/test_audit_system.py

# 使用pytest（如果已安装）
pytest tests/test_audit_system.py -v
```

### 配置验证测试

```bash
# 快速验证
python scripts/verify_system_config.py

# 详细报告
python scripts/verify_system_config.py --detailed-report audit_report.txt
```

## 最佳实践

### 1. 启动前验证

每次启动系统前运行配置验证：

```bash
python scripts/verify_system_config.py
```

### 2. 定期审核患者数据

- 每次训练会话后审核患者状态
- 比较前后评估，跟踪康复进度
- 根据审核建议调整训练参数

### 3. 安全事件处理

- 发生安全事件后立即审核
- 分析违规类型和频率
- 调整安全参数或操作流程

### 4. 记录管理

- 定期导出训练记录备份
- 生成月度/季度患者报告
- 归档历史数据

### 5. 持续改进

- 根据审核报告优化配置
- 追踪警告趋势
- 更新安全标准

## 故障排除

### 配置文件找不到

**问题：** 审核时提示配置文件不存在

**解决方案：**
1. 检查文件路径是否正确
2. 确保配置文件已创建
3. 参考示例配置创建必需文件

### 导入错误

**问题：** 运行时出现模块导入错误

**解决方案：**
1. 确保在项目根目录运行
2. 检查Python路径设置
3. 安装必需依赖：`pip install -r requirements.txt`

### 数据格式错误

**问题：** 患者数据或训练记录格式不正确

**解决方案：**
1. 参考文档中的数据结构示例
2. 使用提供的数据类（PatientRecord等）
3. 查看单元测试中的示例

## 技术支持

如有问题或建议，请：
1. 查看本文档
2. 运行单元测试诊断
3. 查看详细错误信息
4. 参考代码注释和文档字符串

## 更新日志

### v1.0.0 (2024-02-05)

- ✅ 配置审核器
- ✅ 患者数据审核器
- ✅ 训练记录审核器
- ✅ 安全审核器
- ✅ GUI集成
- ✅ 系统验证脚本
- ✅ 单元测试
- ✅ 使用文档
