#!/usr/bin/env python3
"""
Training Manager
Coordinates rehabilitation sessions and manages training protocols
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import String, Float64MultiArray, Int32
from diagnosis_msgs.msg import DiagnosticArray
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import time


class SessionState(Enum):
    """Session state enumeration."""
    IDLE = "idle"
    WARMUP = "warmup"
    TRAINING = "training"
    COOLDOWN = "cooldown"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SessionConfig:
    """Configuration for a training session."""
    patient_id: str
    exercise_type: str  # "upper_limb" or "lower_limb"
    specific_exercise: str
    mode: str  # "passive", "active_assisted", "active_resisted"
    sets: int = 3
    reps_per_set: int = 10
    speed: float = 0.3
    rom_percentage: float = 1.0  # Percentage of full ROM to use
    resistance: float = 0.0


@dataclass
class SessionMetrics:
    """Metrics for a training session."""
    session_id: str
    patient_id: str
    exercise: str
    start_time: float
    end_time: float = 0.0
    completed_sets: int = 0
    completed_reps: int = 0
    avg_fatigue: float = 0.0
    avg_comfort: float = 1.0
    pause_duration: float = 0.0
    status: SessionState = SessionState.IDLE


class TrainingManager(Node):
    """
    Central manager for rehabilitation training sessions.
    Coordinates exercises, tracks progress, and manages session lifecycle.
    """

    def __init__(self):
        super().__init__('training_manager')

        # Session state
        self.current_session: Optional[SessionConfig] = None
        self.current_metrics: Optional[SessionMetrics] = None
        self.current_session_id: Optional[str] = None
        self.session_state = SessionState.IDLE

        # Session tracking
        self.session_counter = 0
        self.sessions: Dict[str, SessionMetrics] = {}

        # Patient tracking
        self.current_patient_id = None
        self.patient_history: Dict[str, List[SessionMetrics]] = {}

        # Real-time metrics
        self.fatigue_history: List[float] = []
        self.comfort_history: List[float] = []
        self.effort_history: List[float] = []

        # Publishers and Subscribers
        self._setup_communications()

        # Session timer
        self.metrics_timer = self.create_timer(1.0, self.update_metrics)

        self.get_logger().info("Training Manager initialized")

    def _setup_communications(self):
        """Setup ROS publishers and subscribers."""
        qos = QoSProfile(depth=10)

        # Publishers
        self.status_pub = self.create_publisher(
            String,
            '/training_manager/status',
            qos
        )

        self.session_pub = self.create_publisher(
            String,
            '/training_manager/session',
            qos
        )

        self.metrics_pub = self.create_publisher(
            Float64MultiArray,
            '/training_manager/metrics',
            qos
        )

        self.command_pub = self.create_publisher(
            String,
            '/rehabilitation/exercise_command',
            qos
        )

        # Subscribers
        self.status_sub = self.create_subscription(
            String,
            '/rehabilitation/status',
            self.rehab_status_callback,
            qos
        )

        self.patient_sub = self.create_subscription(
            Float64MultiArray,
            '/patient/state',
            self.patient_state_callback,
            qos
        )

    def rehab_status_callback(self, msg: String):
        """Receive status from rehabilitation modules."""
        try:
            status = json.loads(msg.data)
            self.get_logger().debug(f"Rehab status: {status}")
        except:
            pass

    def patient_state_callback(self, msg: Float64MultiArray):
        """Receive patient state updates."""
        if len(msg.data) >= 3:
            self.effort_history.append(msg.data[0])
            self.fatigue_history.append(msg.data[1])
            self.comfort_history.append(msg.data[2])

            # Keep only recent history
            max_history = 3600  # 1 hour
            if len(self.fatigue_history) > max_history:
                self.fatigue_history = self.fatigue_history[-max_history:]
                self.comfort_history = self.comfort_history[-max_history:]
                self.effort_history = self.effort_history[-max_history:]

    def create_session(self, config: SessionConfig) -> str:
        """
        Create a new training session.

        Args:
            config: Session configuration

        Returns:
            Session ID
        """
        self.session_counter += 1
        session_id = f"session_{self.session_counter}_{int(time.time())}"

        # Create metrics
        metrics = SessionMetrics(
            session_id=session_id,
            patient_id=config.patient_id,
            exercise=config.specific_exercise,
            start_time=time.time(),
            status=SessionState.IDLE
        )

        self.sessions[session_id] = metrics
        self.current_session = config
        self.current_metrics = metrics

        return session_id

    def start_session(self, session_id: str = None):
        """
        Start a training session.

        Args:
            session_id: Session to start (uses current if None)
        """
        if session_id and session_id in self.sessions:
            self.current_session_id = session_id
            self.current_metrics = self.sessions[session_id]
            self.current_patient_id = self.current_metrics.patient_id
            self.session_state = SessionState.WARMUP

            if self.current_patient_id not in self.patient_history:
                self.patient_history[self.current_patient_id] = []

        elif self.current_session:
            self.session_state = SessionState.WARMUP
            self.get_logger().info(f"Starting session for patient {self.current_patient_id}")
        else:
            self.get_logger().warning("No session to start")
            return

        # Publish start command
        self._send_exercise_command("start")

    def pause_session(self):
        """Pause current session."""
        self.session_state = SessionState.PAUSED
        self._send_exercise_command("pause")
        self.get_logger().info("Session paused")

    def resume_session(self):
        """Resume paused session."""
        if self.session_state == SessionState.PAUSED:
            self.session_state = SessionState.TRAINING
            self._send_exercise_command("resume")
            self.get_logger().info("Session resumed")

    def stop_session(self):
        """Stop current session."""
        self.session_state = SessionState.COMPLETED
        self._send_exercise_command("stop")

        if self.current_metrics:
            self.current_metrics.end_time = time.time()
            self.current_metrics.status = SessionState.COMPLETED

            if self.current_patient_id:
                self.patient_history[self.current_patient_id].append(self.current_metrics)

        self.get_logger().info("Session stopped")

    def _send_exercise_command(self, command: str):
        """Send command to exercise module."""
        msg = String()
        msg.data = command
        self.command_pub.publish(msg)

    def update_metrics(self):
        """Update and publish session metrics."""
        if self.session_state not in [SessionState.TRAINING, SessionState.WARMUP]:
            return

        # Calculate averages
        if self.fatigue_history:
            avg_fatigue = np.mean(self.fatigue_history[-60:])  # Last minute
        else:
            avg_fatigue = 0.0

        if self.comfort_history:
            avg_comfort = np.mean(self.comfort_history[-60:])
        else:
            avg_comfort = 1.0

        # Update current metrics
        if self.current_metrics:
            self.current_metrics.avg_fatigue = avg_fatigue
            self.current_metrics.avg_comfort = avg_comfort

        # Publish metrics
        msg = Float64MultiArray()
        msg.data = [
            avg_fatigue,
            avg_comfort,
            len(self.fatigue_history),
            time.time() - (self.current_metrics.start_time if self.current_metrics else 0)
        ]
        self.metrics_pub.publish(msg)

        # Publish status
        self._publish_status()

    def _publish_status(self):
        """Publish current session status."""
        status = {
            'state': self.session_state.value,
            'patient_id': self.current_patient_id,
            'exercise': self.current_session.specific_exercise if self.current_session else None,
            'sets_completed': self.current_metrics.completed_sets if self.current_metrics else 0,
            'reps_completed': self.current_metrics.completed_reps if self.current_metrics else 0,
            'avg_fatigue': self.current_metrics.avg_fatigue if self.current_metrics else 0.0,
            'avg_comfort': self.current_metrics.avg_comfort if self.current_metrics else 1.0
        }

        msg = String()
        msg.data = json.dumps(status)
        self.status_pub.publish(msg)

    def get_session_report(self, session_id: str) -> Dict:
        """
        Get a detailed report for a session.

        Args:
            session_id: Session ID

        Returns:
            Report dictionary
        """
        if session_id not in self.sessions:
            return {'error': 'Session not found'}

        metrics = self.sessions[session_id]

        report = {
            'session_id': session_id,
            'patient_id': metrics.patient_id,
            'exercise': metrics.exercise,
            'duration': metrics.end_time - metrics.start_time - metrics.pause_duration,
            'sets_completed': metrics.completed_sets,
            'reps_completed': metrics.completed_reps,
            'avg_fatigue': metrics.avg_fatigue,
            'avg_comfort': metrics.avg_comfort,
            'status': metrics.status.value
        }

        return report

    def get_patient_progress(self, patient_id: str) -> Dict:
        """
        Get progress report for a patient.

        Args:
            patient_id: Patient ID

        Returns:
            Progress report
        """
        if patient_id not in self.patient_history:
            return {'sessions': 0}

        sessions = self.patient_history[patient_id]

        total_duration = sum(s.end_time - s.start_time for s in sessions)
        avg_fatigue = np.mean([s.avg_fatigue for s in sessions]) if sessions else 0
        avg_comfort = np.mean([s.avg_comfort for s in sessions]) if sessions else 1

        return {
            'total_sessions': len(sessions),
            'total_duration': total_duration,
            'avg_fatigue': avg_fatigue,
            'avg_comfort': avg_comfort,
            'exercises': list(set(s.exercise for s in sessions))
        }


def main(args=None):
    rclpy.init(args=args)

    manager = TrainingManager()

    try:
        rclpy.spin(manager)
    except KeyboardInterrupt:
        manager.stop_session()
    finally:
        manager.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
