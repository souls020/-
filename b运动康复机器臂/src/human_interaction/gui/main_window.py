#!/usr/bin/env python3
"""
Main GUI Window for Rehabilitation Robot Interface
PyQt6-based graphical user interface
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QProgressBar, QGroupBox, QGridLayout, QFrame, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QTextEdit, QSplitter, QStackedWidget, QMessageBox, QFileDialog
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QBrush
import numpy as np
import json
import sys
import os

# 添加项目路径以导入审核模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))
from src.audit.patient_data_auditor import PatientDataAuditor, PatientRecord
from src.audit.config_auditor import ConfigAuditor
from src.audit.training_record_auditor import TrainingRecordAuditor


class RehabilitationGUI(QMainWindow):
    """
    Main GUI window for rehabilitation robot control.
    Provides patient management, exercise selection, and real-time monitoring.
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Rehabilitation Robot Control System")
        self.setMinimumSize(1200, 800)

        # State
        self.is_connected = False
        self.is_training = False
        self.current_patient = None
        self.current_exercise = None

        # Real-time data
        self.joint_positions = [0.0] * 6
        self.joint_velocities = [0.0] * 6
        self.fatigue_level = 0.0
        self.comfort_level = 1.0

        # Setup UI
        self.setup_ui()
        self.setup_timers()

    def setup_ui(self):
        """Setup main UI structure."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Left panel - Controls
        left_panel = self.create_control_panel()
        main_layout.addWidget(left_panel, 1)

        # Right panel - Visualization
        right_panel = self.create_visualization_panel()
        main_layout.addWidget(right_panel, 2)

    def create_control_panel(self) -> QWidget:
        """Create control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Connection status
        status_group = QGroupBox("System Status")
        status_layout = QVBoxLayout()

        self.connection_label = QLabel("Disconnected")
        self.connection_label.setStyleSheet("color: red; font-weight: bold;")
        status_layout.addWidget(self.connection_label)

        self.e_stop_label = QLabel("E-Stop: Ready")
        self.e_stop_label.setStyleSheet("color: green;")
        status_layout.addWidget(self.e_stop_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Patient selection
        patient_group = QGroupBox("Patient")
        patient_layout = QVBoxLayout()

        self.patient_combo = QComboBox()
        self.patient_combo.addItems(["Select Patient...", "Patient 001", "Patient 002", "Patient 003"])
        patient_layout.addWidget(self.patient_combo)

        self.new_patient_btn = QPushButton("New Patient")
        patient_layout.addWidget(self.new_patient_btn)

        patient_group.setLayout(patient_layout)
        layout.addWidget(patient_group)

        # Exercise selection
        exercise_group = QGroupBox("Exercise")
        exercise_layout = QVBoxLayout()

        self.limb_combo = QComboBox()
        self.limb_combo.addItems(["Upper Limb", "Lower Limb"])
        exercise_layout.addWidget(self.limb_combo)

        self.exercise_combo = QComboBox()
        self.exercise_combo.addItems([
            "Shoulder Abduction",
            "Elbow Flexion",
            "Forearm Rotation",
            "Shoulder Rotation"
        ])
        exercise_layout.addWidget(self.exercise_combo)

        exercise_group.setLayout(exercise_layout)
        layout.addWidget(exercise_group)

        # Training parameters
        params_group = QGroupBox("Parameters")
        params_layout = QGridLayout()

        params_layout.addWidget(QLabel("Sets:"), 0, 0)
        self.sets_spin = QSpinBox()
        self.sets_spin.setRange(1, 10)
        self.sets_spin.setValue(3)
        params_layout.addWidget(self.sets_spin, 0, 1)

        params_layout.addWidget(QLabel("Reps:"), 1, 0)
        self.reps_spin = QSpinBox()
        self.reps_spin.setRange(1, 50)
        self.reps_spin.setValue(10)
        params_layout.addWidget(self.reps_spin, 1, 1)

        params_layout.addWidget(QLabel("Speed:"), 2, 0)
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 1.0)
        self.speed_spin.setValue(0.3)
        self.speed_spin.setStep(0.1)
        params_layout.addWidget(self.speed_spin, 2, 1)

        params_layout.addWidget(QLabel("ROM %:"), 3, 0)
        self.rom_spin = QSpinBox()
        self.rom_spin.setRange(50, 100)
        self.rom_spin.setValue(80)
        params_layout.addWidget(self.rom_spin, 3, 1)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Training mode
        mode_group = QGroupBox("Mode")
        mode_layout = QVBoxLayout()

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Passive", "Active-Assisted", "Active-Resisted"])
        mode_layout.addWidget(self.mode_combo)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Control buttons
        button_layout = QVBoxLayout()

        self.start_btn = QPushButton("START")
        self.start_btn.setStyleSheet(
            "background-color: green; color: white; font-weight: bold; padding: 15px;"
        )
        button_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("PAUSE")
        self.pause_btn.setStyleSheet(
            "background-color: orange; color: white; padding: 10px;"
        )
        self.pause_btn.setEnabled(False)
        button_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setStyleSheet(
            "background-color: red; color: white; padding: 10px;"
        )
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)

        self.e_stop_btn = QPushButton("EMERGENCY STOP")
        self.e_stop_btn.setStyleSheet(
            "background-color: darkred; color: white; font-weight: bold; padding: 15px;"
        )
        button_layout.addWidget(self.e_stop_btn)

        layout.addLayout(button_layout)

        # Spacer
        layout.addStretch()

        return panel

    def create_visualization_panel(self) -> QWidget:
        """Create visualization panel with tabs."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Tabs
        self.tabs = QTabWidget()

        # Joint visualization tab
        joint_tab = self.create_joint_visualization()
        self.tabs.addTab(joint_tab, "Joint Positions")

        # Progress tab
        progress_tab = self.create_progress_visualization()
        self.tabs.addTab(progress_tab, "Progress")

        # Patient history tab
        history_tab = self.create_patient_history()
        self.tabs.addTab(history_tab, "History")

        # Settings tab
        settings_tab = self.create_settings_tab()
        self.tabs.addTab(settings_tab, "Settings")
        
        # Audit tab (审核标签页)
        audit_tab = self.create_audit_tab()
        self.tabs.addTab(audit_tab, "审核")

        layout.addWidget(self.tabs)

        # Status bar at bottom
        status_layout = QHBoxLayout()

        self.fatigue_bar = QProgressBar()
        self.fatigue_bar.setRange(0, 100)
        self.fatigue_bar.setValue(0)
        self.fatigue_bar.setFormat("Fatigue: %p%")
        status_layout.addWidget(self.fatigue_bar)

        self.comfort_bar = QProgressBar()
        self.comfort_bar.setRange(0, 100)
        self.comfort_bar.setValue(100)
        self.comfort_bar.setFormat("Comfort: %p%")
        status_layout.addWidget(self.comfort_bar)

        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)

        layout.addLayout(status_layout)

        return panel

    def create_joint_visualization(self) -> QWidget:
        """Create joint position visualization."""
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # Left: Joint position bars
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        left_layout.addWidget(QLabel("<b>Joint Positions (rad)</b>"))

        self.joint_bars = []
        for i in range(6):
            bar_layout = QHBoxLayout()
            bar_layout.addWidget(QLabel(f"J{i}:"))
            bar = QProgressBar()
            bar.setRange(-180, 180)
            bar.setValue(0)
            bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
            bar_layout.addWidget(bar)
            self.joint_bars.append(bar)
            left_layout.addLayout(bar_layout)

        tab.setLayout(layout)
        return tab

    def create_progress_visualization(self) -> QWidget:
        """Create progress visualization."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Current session info
        info_group = QGroupBox("Current Session")
        info_layout = QGridLayout()

        info_layout.addWidget(QLabel("Exercise:"), 0, 0)
        self.session_exercise_label = QLabel("-")
        info_layout.addWidget(self.session_exercise_label, 0, 1)

        info_layout.addWidget(QLabel("Set:"), 1, 0)
        self.session_set_label = QLabel("0/3")
        info_layout.addWidget(self.session_set_label, 1, 1)

        info_layout.addWidget(QLabel("Rep:"), 2, 0)
        self.session_rep_label = QLabel("0/10")
        info_layout.addWidget(self.session_rep_label, 2, 1)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Progress bars
        progress_group = QGroupBox("Session Progress")
        progress_layout = QVBoxLayout()

        self.session_progress = QProgressBar()
        self.session_progress.setRange(0, 100)
        self.session_progress.setValue(0)
        progress_layout.addWidget(self.session_progress)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Feedback text
        self.feedback_text = QTextEdit()
        self.feedback_text.setReadOnly(True)
        self.feedback_text.setMaximumHeight(200)
        layout.addWidget(self.feedback_text)

        return tab

    def create_patient_history(self) -> QWidget:
        """Create patient history table."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Date", "Exercise", "Sets", "Duration", "Fatigue", "Score"
        ])
        self.history_table.horizontalHeader().setStretchLastSection(True)

        # Add sample data
        self.history_table.insertRow(0)
        self.history_table.setItem(0, 0, QTableWidgetItem("2024-01-15"))
        self.history_table.setItem(0, 1, QTableWidgetItem("Elbow Flexion"))
        self.history_table.setItem(0, 2, QTableWidgetItem("3"))
        self.history_table.setItem(0, 3, QTableWidgetItem("15 min"))
        self.history_table.setItem(0, 4, QTableWidgetItem("35%"))
        self.history_table.setItem(0, 5, QTableWidgetItem("8.5"))

        layout.addWidget(self.history_table)

        return tab

    def create_settings_tab(self) -> QWidget:
        """Create settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Robot settings
        robot_group = QGroupBox("Robot Settings")
        robot_layout = QVBoxLayout()

        self.robot_combo = QComboBox()
        self.robot_combo.addItems(["UR5", "UR10"])
        robot_layout.addWidget(QLabel("Robot Type:"))
        robot_layout.addWidget(self.robot_combo)

        robot_group.setLayout(robot_layout)
        layout.addWidget(robot_group)

        # Safety settings
        safety_group = QGroupBox("Safety Settings")
        safety_layout = QVBoxLayout()

        self.e_stop_enable_check = QPushButton("E-Stop Enabled")
        self.e_stop_enable_check.setCheckable(True)
        self.e_stop_enable_check.setChecked(True)
        safety_layout.addWidget(self.e_stop_enable_check)

        safety_group.setLayout(safety_layout)
        layout.addWidget(safety_group)

        # Audio settings
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QVBoxLayout()

        self.voice_enable_check = QPushButton("Voice Control")
        self.voice_enable_check.setCheckable(True)
        self.voice_enable_check.setChecked(True)
        audio_layout.addWidget(self.voice_enable_check)

        self.tts_enable_check = QPushButton("Text-to-Speech Feedback")
        self.tts_enable_check.setCheckable(True)
        self.tts_enable_check.setChecked(True)
        audio_layout.addWidget(self.tts_enable_check)

        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        return tab

    def create_audit_tab(self) -> QWidget:
        """创建审核标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 审核器实例
        self.patient_auditor = PatientDataAuditor()
        self.config_auditor = ConfigAuditor()
        self.training_auditor = TrainingRecordAuditor()
        
        # 患者数据审核组
        patient_audit_group = QGroupBox("患者数据审核")
        patient_audit_layout = QVBoxLayout()
        
        # 患者数据输入
        patient_info_layout = QGridLayout()
        patient_info_layout.addWidget(QLabel("患者ID:"), 0, 0)
        self.audit_patient_id = QLineEdit()
        self.audit_patient_id.setText("P001")
        patient_info_layout.addWidget(self.audit_patient_id, 0, 1)
        
        patient_info_layout.addWidget(QLabel("姓名:"), 1, 0)
        self.audit_patient_name = QLineEdit()
        self.audit_patient_name.setText("测试患者")
        patient_info_layout.addWidget(self.audit_patient_name, 1, 1)
        
        patient_info_layout.addWidget(QLabel("年龄:"), 2, 0)
        self.audit_patient_age = QSpinBox()
        self.audit_patient_age.setRange(0, 120)
        self.audit_patient_age.setValue(65)
        patient_info_layout.addWidget(self.audit_patient_age, 2, 1)
        
        patient_info_layout.addWidget(QLabel("疼痛水平(0-10):"), 3, 0)
        self.audit_pain_level = QDoubleSpinBox()
        self.audit_pain_level.setRange(0, 10)
        self.audit_pain_level.setValue(4.5)
        patient_info_layout.addWidget(self.audit_pain_level, 3, 1)
        
        patient_info_layout.addWidget(QLabel("疲劳水平(0-1):"), 4, 0)
        self.audit_fatigue_level = QDoubleSpinBox()
        self.audit_fatigue_level.setRange(0, 1)
        self.audit_fatigue_level.setSingleStep(0.1)
        self.audit_fatigue_level.setValue(0.6)
        patient_info_layout.addWidget(self.audit_fatigue_level, 4, 1)
        
        patient_audit_layout.addLayout(patient_info_layout)
        
        # 审核按钮
        audit_buttons_layout = QHBoxLayout()
        self.audit_patient_btn = QPushButton("审核患者数据")
        self.audit_patient_btn.clicked.connect(self.on_audit_patient_data)
        audit_buttons_layout.addWidget(self.audit_patient_btn)
        
        self.load_patient_history_btn = QPushButton("加载历史记录")
        self.load_patient_history_btn.clicked.connect(self.on_load_patient_history)
        audit_buttons_layout.addWidget(self.load_patient_history_btn)
        
        patient_audit_layout.addLayout(audit_buttons_layout)
        patient_audit_group.setLayout(patient_audit_layout)
        layout.addWidget(patient_audit_group)
        
        # 配置审核组
        config_audit_group = QGroupBox("系统配置审核")
        config_audit_layout = QHBoxLayout()
        
        self.audit_controller_config_btn = QPushButton("审核控制器配置")
        self.audit_controller_config_btn.clicked.connect(self.on_audit_controller_config)
        config_audit_layout.addWidget(self.audit_controller_config_btn)
        
        self.audit_training_protocol_btn = QPushButton("审核训练协议")
        self.audit_training_protocol_btn.clicked.connect(self.on_audit_training_protocol)
        config_audit_layout.addWidget(self.audit_training_protocol_btn)
        
        config_audit_group.setLayout(config_audit_layout)
        layout.addWidget(config_audit_group)
        
        # 训练记录审核组
        training_audit_group = QGroupBox("训练记录审核")
        training_audit_layout = QHBoxLayout()
        
        self.export_records_btn = QPushButton("导出训练记录(CSV)")
        self.export_records_btn.clicked.connect(self.on_export_records)
        training_audit_layout.addWidget(self.export_records_btn)
        
        self.generate_report_btn = QPushButton("生成患者报告")
        self.generate_report_btn.clicked.connect(self.on_generate_patient_report)
        training_audit_layout.addWidget(self.generate_report_btn)
        
        training_audit_group.setLayout(training_audit_layout)
        layout.addWidget(training_audit_group)
        
        # 审核结果显示
        result_group = QGroupBox("审核结果")
        result_layout = QVBoxLayout()
        
        self.audit_result_text = QTextEdit()
        self.audit_result_text.setReadOnly(True)
        self.audit_result_text.setMinimumHeight(300)
        result_layout.addWidget(self.audit_result_text)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        return tab

    def on_audit_patient_data(self):
        """审核患者数据"""
        try:
            # 创建患者记录
            from datetime import datetime, timedelta
            
            record = PatientRecord(
                patient_id=self.audit_patient_id.text(),
                name=self.audit_patient_name.text(),
                age=self.audit_patient_age.value(),
                diagnosis="脑卒中后偏瘫",  # 可以从界面输入
                injury_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                assessment_date=datetime.now().strftime("%Y-%m-%d"),
                muscle_strength=[0.3, 0.4, 0.35, 0.5, 0.45, 0.4],  # 示例数据
                range_of_motion=[45.0, 60.0, 50.0, 70.0, 55.0, 65.0],  # 示例数据
                pain_level=self.audit_pain_level.value(),
                fatigue_level=self.audit_fatigue_level.value(),
                notes="GUI审核"
            )
            
            # 执行审核
            result = self.patient_auditor.validate_patient_record(record)
            
            # 显示结果
            report = self.patient_auditor.generate_validation_report(result)
            self.audit_result_text.setText(report)
            
            # 根据结果显示消息
            if result.is_valid:
                QMessageBox.information(self, "审核通过", 
                    f"患者数据验证通过\n数据质量: {result.quality.value}")
            else:
                QMessageBox.warning(self, "审核未通过",
                    f"患者数据存在问题\n请查看详细报告")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"审核失败: {str(e)}")
            self.audit_result_text.setText(f"错误: {str(e)}")

    def on_load_patient_history(self):
        """加载患者历史记录"""
        patient_id = self.audit_patient_id.text()
        if not patient_id:
            QMessageBox.warning(self, "警告", "请输入患者ID")
            return
        
        try:
            records = self.training_auditor.load_patient_records(patient_id)
            if records:
                history = self.training_auditor.audit_patient_history(patient_id, records)
                
                report = f"患者 {patient_id} 历史记录审核\n"
                report += "=" * 60 + "\n"
                report += f"总训练次数: {history['total_sessions']}\n"
                report += f"总时长: {history['total_duration_hours']:.1f} 小时\n"
                report += f"平均完成率: {history['avg_completion_rate']*100:.1f}%\n"
                report += f"平均疲劳水平: {history['avg_fatigue_level']:.2f}\n"
                report += f"安全事件: {history['total_safety_events']} 次\n\n"
                
                if history['recommendations']:
                    report += "建议:\n"
                    for i, rec in enumerate(history['recommendations'], 1):
                        report += f"  {i}. {rec}\n"
                
                self.audit_result_text.setText(report)
            else:
                self.audit_result_text.setText(f"未找到患者 {patient_id} 的训练记录")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载失败: {str(e)}")

    def on_audit_controller_config(self):
        """审核控制器配置"""
        # 文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择控制器配置文件", 
            "src/robot_control/config/",
            "YAML Files (*.yaml *.yml)"
        )
        
        if file_path:
            try:
                results = self.config_auditor.audit_controller_config(file_path)
                report = self.config_auditor.generate_report()
                self.audit_result_text.setText(report)
                
                if self.config_auditor.has_critical_issues():
                    QMessageBox.critical(self, "严重问题", 
                        "配置文件存在严重问题，请立即修复！")
                elif self.config_auditor.has_errors():
                    QMessageBox.warning(self, "配置错误", 
                        "配置文件存在错误，建议修复后使用")
                else:
                    QMessageBox.information(self, "审核通过", 
                        "配置文件审核通过")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"审核失败: {str(e)}")

    def on_audit_training_protocol(self):
        """审核训练协议"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择训练协议配置文件",
            "src/rehabilitation/config/",
            "YAML Files (*.yaml *.yml)"
        )
        
        if file_path:
            try:
                results = self.config_auditor.audit_training_protocol(file_path)
                report = self.config_auditor.generate_report()
                self.audit_result_text.setText(report)
                
                if self.config_auditor.has_errors():
                    QMessageBox.warning(self, "配置问题", 
                        "训练协议存在问题，请检查")
                else:
                    QMessageBox.information(self, "审核通过", 
                        "训练协议审核通过")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"审核失败: {str(e)}")

    def on_export_records(self):
        """导出训练记录"""
        patient_id = self.audit_patient_id.text()
        if not patient_id:
            QMessageBox.warning(self, "警告", "请输入患者ID")
            return
        
        try:
            records = self.training_auditor.load_patient_records(patient_id)
            if not records:
                QMessageBox.information(self, "提示", 
                    f"未找到患者 {patient_id} 的训练记录")
                return
            
            # 选择保存位置
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存训练记录",
                f"{patient_id}_training_records.csv",
                "CSV Files (*.csv)"
            )
            
            if file_path:
                self.training_auditor.export_to_csv(records, file_path)
                QMessageBox.information(self, "成功", 
                    f"成功导出 {len(records)} 条记录到:\n{file_path}")
                self.audit_result_text.setText(
                    f"训练记录已导出到: {file_path}\n"
                    f"共 {len(records)} 条记录"
                )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def on_generate_patient_report(self):
        """生成患者综合报告"""
        patient_id = self.audit_patient_id.text()
        if not patient_id:
            QMessageBox.warning(self, "警告", "请输入患者ID")
            return
        
        try:
            records = self.training_auditor.load_patient_records(patient_id)
            if not records:
                QMessageBox.information(self, "提示",
                    f"未找到患者 {patient_id} 的训练记录")
                return
            
            # 选择保存位置
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存患者报告",
                f"{patient_id}_report.txt",
                "Text Files (*.txt)"
            )
            
            if file_path:
                self.training_auditor.export_patient_report(
                    patient_id, records, file_path
                )
                
                # 显示在界面上
                with open(file_path, 'r', encoding='utf-8') as f:
                    report_content = f.read()
                self.audit_result_text.setText(report_content)
                
                QMessageBox.information(self, "成功",
                    f"患者报告已生成:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成报告失败: {str(e)}")

    def setup_timers(self):
        """Setup update timers."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)  # 10 Hz

    def update_display(self):
        """Update display with real-time data."""
        # Update joint position bars
        for i, bar in enumerate(self.joint_bars):
            value = int(np.degrees(self.joint_positions[i]))
            bar.setValue(value)

        # Update fatigue and comfort bars
        self.fatigue_bar.setValue(int(self.fatigue_level * 100))
        self.comfort_bar.setValue(int(self.comfort_level * 100))

        # Update status label
        if self.is_training:
            self.status_label.setText("Training Active")
        elif self.is_connected:
            self.status_label.setText("Connected")
        else:
            self.status_label.setText("Disconnected")

    def connect_robot(self):
        """Connect to robot."""
        self.is_connected = True
        self.connection_label.setText("Connected")
        self.connection_label.setStyleSheet("color: green; font-weight: bold;")

    def disconnect_robot(self):
        """Disconnect from robot."""
        self.is_connected = False
        self.connection_label.setText("Disconnected")
        self.connection_label.setStyleSheet("color: red; font-weight: bold;")

    def start_training(self):
        """Start training session."""
        self.is_training = True
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.feedback_text.append("Training started.")

    def pause_training(self):
        """Pause training."""
        self.is_training = False
        self.pause_btn.setEnabled(False)
        self.feedback_text.append("Training paused.")

    def stop_training(self):
        """Stop training."""
        self.is_training = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.feedback_text.append("Training stopped.")

    def emergency_stop(self):
        """Trigger emergency stop."""
        self.is_training = False
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.e_stop_label.setText("E-Stop: ACTIVE")
        self.e_stop_label.setStyleSheet("color: red; font-weight: bold;")
        self.feedback_text.append("EMERGENCY STOP ACTIVATED!")

    def reset_emergency_stop(self):
        """Reset emergency stop."""
        self.e_stop_label.setText("E-Stop: Ready")
        self.e_stop_label.setStyleSheet("color: green;")
        self.start_btn.setEnabled(True)
        self.feedback_text.append("Emergency stop reset.")

    def closeEvent(self, event):
        """Handle window close."""
        reply = QMessageBox.question(
            self, "Exit",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)

    # Set style
    app.setStyle('Fusion')

    window = RehabilitationGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
