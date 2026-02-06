# Rehabilitation Robot Control System

## 概述

运动康复具身智能机器臂系统，支持上肢和下肢康复训练，具备AI优化能力和多模态交互界面。

## 功能特性

### 核心模块

- **机器人控制**: 关节控制、轨迹规划、正/逆运动学
- **康复训练**: 上肢训练、下肢训练、训练协议管理
- **具身智能**: 患者评估、自适应控制、AI优化
- **人机交互**: 图形界面、语音控制、实时反馈
- **安全系统**: 碰撞检测、紧急停止、状态监控
- **审核系统**: 【新增】配置验证、数据审核、记录管理、报告生成

### 支持的训练类型

#### 上肢训练
- 肩部外展/内收
- 肘部屈伸
- 前臂旋前/旋后
- 肩部旋转

#### 下肢训练
- 髋关节屈伸
- 膝关节屈伸
- 踝关节背屈/跖屈

### 训练模式

- **被动训练**: 机器人引导运动
- **主动辅助**: 机器人辅助患者运动
- **抗阻训练**: 机器人提供阻力

## 安装

```bash
# 创建工作空间
mkdir -p ~/rehab_ws/src
cd ~/rehab_ws/src

# 克隆代码
git clone <repository_url> rehabilitation_robot

# 安装依赖
pip install -r requirements.txt

# 构建
cd ~/rehab_ws
colcon build --packages-select rehabilitation_robot

# Source
source install/setup.bash
```

## 快速开始

### 验证系统配置

首次使用前，建议先验证系统配置：

```bash
python scripts/verify_system_config.py
```

### 运行测试

```bash
python tests/test_audit_system.py
```

## 使用

### 启动系统

```bash
# 仿真模式
ros2 launch rehabilitation_robot simulation.launch.py

# 硬件模式
ros2 launch rehabilitation_robot robot_control.launch.py
```

### 启动GUI

```bash
ros2 run rehabilitation_robot gui_main
```

### 语音控制

```bash
ros2 run rehabilitation_robot voice_controller
```

## 审核系统

系统现已集成完整的审核功能，用于验证配置、审核患者数据、管理训练记录。

### 主要功能

1. **配置审核**
   - 控制器参数验证
   - 训练协议检查
   - 安全参数验证

2. **患者数据审核**
   - 数据完整性验证
   - 异常值检测
   - 评估比较和进度跟踪

3. **训练记录管理**
   - 记录保存和加载
   - 历史统计分析
   - CSV导出和报告生成

4. **安全监控**
   - 实时安全检查
   - 违规记录分析
   - 安全报告生成

### 使用GUI进行审核

1. 启动GUI：`python src/human_interaction/gui/main_window.py`
2. 切换到"审核"标签页
3. 使用各项审核功能

### 命令行工具

```bash
# 验证系统配置
python scripts/verify_system_config.py

# 生成详细报告
python scripts/verify_system_config.py --detailed-report report.txt
```

### 详细文档

- 📖 [快速启动指南](docs/QUICK_START.md)
- 📖 [审核系统使用指南](docs/AUDIT_SYSTEM_GUIDE.md)
- 📖 [项目改进总结](docs/PROJECT_IMPROVEMENTS.md)

## 配置

### 控制器参数

修改 `src/robot_control/config/controller_params.yaml`:
- PID增益
- 关节限制
- 安全参数
- 轨迹规划参数

### 训练协议

修改 `src/rehabilitation/config/training_protocols.yaml`:
- 训练类型定义
- ROM参数
- 速度设置
- 训练模式

## 系统架构

```
rehabilitation_robot/
├── src/
│   ├── robot_control/       # 运动控制
│   ├── rehabilitation/      # 康复训练
│   ├── embodied_ai/         # 具身智能
│   ├── human_interaction/   # 人机交互
│   ├── safety/              # 安全系统
│   └── audit/               # 【新增】审核系统
├── scripts/                 # 启动脚本
│   └── verify_system_config.py  # 【新增】配置验证
├── tests/                   # 【新增】测试套件
│   └── test_audit_system.py
└── docs/                    # 文档
    ├── QUICK_START.md       # 【新增】快速启动
    ├── AUDIT_SYSTEM_GUIDE.md  # 【新增】审核指南
    └── PROJECT_IMPROVEMENTS.md  # 【新增】改进说明
```

## 开发

### 运行测试

```bash
# ROS2包测试
colcon test --packages-select rehabilitation_robot

# Python单元测试
python tests/test_audit_system.py

# 使用pytest
pytest tests/ -v
```

### 代码检查

```bash
flake8 src/robot_control/src/kinematics.py
```

### 配置验证

在部署前始终运行配置验证：

```bash
python scripts/verify_system_config.py --detailed-report pre_deploy_audit.txt
```

## 安全注意事项

1. **紧急停止**: 始终确保紧急停止按钮可用
2. **力限制**: 不要超过安全力限制
3. **患者监控**: 实时监控患者状态
4. **训练参数**: 根据患者能力调整参数

## 许可证

Apache License 2.0
