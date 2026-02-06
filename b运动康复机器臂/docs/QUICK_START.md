# 快速启动指南

## 前置要求

- Python 3.8+
- ROS2 Humble（可选，用于硬件连接）

## 安装步骤

### 1. 安装Python依赖

```bash
cd /Users/Zhuanz1/Desktop/b运动康复机器臂
pip install -r requirements.txt
```

### 2. 验证安装

```bash
python scripts/verify_system_config.py
```

如果看到 "✅ 所有配置验证通过！系统可以安全使用。" 说明安装成功。

## 基本使用

### 方式一：使用GUI界面（推荐）

```bash
python src/human_interaction/gui/main_window.py
```

#### GUI功能介绍

1. **左侧控制面板**
   - 系统状态显示
   - 患者选择
   - 训练类型选择
   - 训练参数设置
   - 控制按钮（开始/暂停/停止/紧急停止）

2. **右侧可视化面板**
   - **关节位置**：实时显示6个关节的位置
   - **训练进度**：当前训练的进度和反馈
   - **历史记录**：查看患者训练历史
   - **设置**：系统设置和配置
   - **审核**：【新功能】数据审核和报告生成

3. **审核功能使用**
   - 切换到"审核"标签页
   - 输入患者信息
   - 点击"审核患者数据"查看验证结果
   - 使用"加载历史记录"查看统计信息
   - 使用"导出训练记录"保存数据
   - 使用"生成患者报告"创建综合报告

### 方式二：命令行使用

#### 审核配置文件

```bash
# 运行配置验证
python scripts/verify_system_config.py

# 生成详细报告
python scripts/verify_system_config.py --detailed-report audit_report.txt
```

#### 审核患者数据

```python
from src.audit.patient_data_auditor import PatientDataAuditor, PatientRecord
from datetime import datetime

# 创建审核器
auditor = PatientDataAuditor()

# 创建患者记录
record = PatientRecord(
    patient_id="P001",
    name="张三",
    age=65,
    diagnosis="脑卒中后偏瘫",
    injury_date="2024-01-01",
    assessment_date=datetime.now().strftime("%Y-%m-%d"),
    muscle_strength=[0.3, 0.4, 0.35, 0.5, 0.45, 0.4],
    range_of_motion=[45.0, 60.0, 50.0, 70.0, 55.0, 65.0],
    pain_level=4.5,
    fatigue_level=0.6,
    notes="初次评估"
)

# 验证记录
result = auditor.validate_patient_record(record)
print(auditor.generate_validation_report(result))
```

#### 管理训练记录

```python
from src.audit.training_record_auditor import TrainingRecordAuditor

# 创建审核器
auditor = TrainingRecordAuditor()

# 创建训练记录
record = {
    'session_id': 'S001',
    'patient_id': 'P001',
    'exercise_type': '肩部外展',
    'start_time': '2024-02-05T10:00:00',
    'end_time': '2024-02-05T10:30:00',
    'parameters': {
        'target_sets': 3,
        'completed_sets': 3,
        'target_reps': 10,
        'completed_reps': 10
    },
    'performance_data': {
        'max_rom': 75.0,
        'avg_force': 15.5,
        'fatigue_level': 0.65
    },
    'safety_events': []
}

# 保存记录
filepath = auditor.save_record(record)
print(f"记录已保存: {filepath}")

# 加载患者所有记录
records = auditor.load_patient_records('P001')
print(f"找到 {len(records)} 条记录")

# 导出CSV
auditor.export_to_csv(records, 'patient_P001_records.csv')

# 生成报告
auditor.export_patient_report('P001', records, 'patient_P001_report.txt')
```

## 运行测试

```bash
# 运行所有测试
python tests/test_audit_system.py

# 使用pytest（如果已安装）
pytest tests/test_audit_system.py -v
```

## 配置文件

### 控制器参数配置

位置：`src/robot_control/config/controller_params.yaml`

主要配置项：
- 关节数量和名称
- 关节限制（位置、速度、加速度）
- PID增益
- 安全参数

### 训练协议配置

位置：`src/rehabilitation/config/training_protocols.yaml`

主要配置项：
- 上肢训练协议
- 下肢训练协议
- 训练模式
- 难度等级
- 康复阶段

## 常见问题

### Q: 提示配置文件不存在
A: 确保配置文件已创建在正确位置：
- `src/robot_control/config/controller_params.yaml`
- `src/rehabilitation/config/training_protocols.yaml`

### Q: 导入模块失败
A: 确保在项目根目录运行命令，并已安装所有依赖：
```bash
cd /Users/Zhuanz1/Desktop/b运动康复机器臂
pip install -r requirements.txt
```

### Q: GUI无法启动
A: 检查PyQt6是否正确安装：
```bash
pip install PyQt6
```

### Q: 测试失败
A: 检查所有依赖是否安装：
```bash
pip install numpy scipy PyYAML pytest
```

## 典型工作流程

### 1. 系统启动前

```bash
# 验证配置
python scripts/verify_system_config.py
```

### 2. 启动系统

```bash
# 启动GUI
python src/human_interaction/gui/main_window.py
```

### 3. 训练会话

1. 选择或创建患者
2. 选择训练类型
3. 设置训练参数
4. 开始训练
5. 监控实时数据
6. 训练结束后保存记录

### 4. 数据审核

1. 切换到"审核"标签页
2. 审核患者数据
3. 查看历史记录
4. 导出训练数据
5. 生成综合报告

### 5. 定期维护

```bash
# 每周运行一次配置验证
python scripts/verify_system_config.py --detailed-report weekly_audit.txt

# 每月备份训练记录
# 使用GUI的"导出训练记录"功能
```

## 安全提示

⚠️ **重要安全提醒**

1. **紧急停止**：始终确保紧急停止按钮可用
2. **力限制**：不要超过配置的安全力限制
3. **患者监控**：实时监控患者状态，注意疼痛和疲劳水平
4. **参数调整**：根据患者能力谨慎调整训练参数
5. **定期审核**：定期使用审核功能检查系统状态

## 获取帮助

- 📖 详细文档：`docs/AUDIT_SYSTEM_GUIDE.md`
- 📝 改进说明：`docs/PROJECT_IMPROVEMENTS.md`
- 🧪 测试代码：`tests/test_audit_system.py`
- 💻 示例配置：`src/*/config/*.yaml`

## 下一步

- 阅读完整的 [审核系统使用指南](AUDIT_SYSTEM_GUIDE.md)
- 查看 [项目改进总结](PROJECT_IMPROVEMENTS.md)
- 浏览示例配置文件
- 运行单元测试熟悉系统

祝您使用愉快！
