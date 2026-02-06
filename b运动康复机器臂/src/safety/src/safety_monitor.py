#!/usr/bin/env python3
"""
Safety Monitor
Real-time safety monitoring for rehabilitation robot
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import String, Bool, Float64MultiArray
from geometry_msgs.msg import WrenchStamped, TwistStamped
from sensor_msgs.msg import JointState, Imu
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time
import json


class SafetyLevel(Enum):
    """Safety level enumeration."""
    NORMAL = "normal"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class SafetyLimits:
    """Safety limits configuration."""
    # Force limits (N)
    max_linear_force: float = 50.0
    max_rotational_force: float = 10.0

    # Velocity limits (m/s, rad/s)
    max_linear_velocity: float = 0.5
    max_angular_velocity: float = 1.0

    # Joint limits (radians)
    max_joint_position_error: float = 0.1

    # Interaction limits
    max_pressure: float = 100.0  # N/cm^2
    max_skin_stretch: float = 0.3  # fraction

    # Time thresholds (seconds)
    force_limit_duration: float = 0.1
    velocity_limit_duration: float = 0.5


class SafetyMonitor(Node):
    """
    Comprehensive safety monitoring system.
    Monitors forces, velocities, joint positions, and patient state.
    """

    def __init__(self):
        super().__init__('safety_monitor')

        # Safety state
        self.current_level = SafetyLevel.NORMAL
        self.safety_limits = SafetyLimits()
        self.last_safety_event = None
        self.safety_violations = []

        # Joint limits (loaded from config or use defaults)
        self.joint_limits = {
            'min': np.array([-np.pi, -np.pi, -np.pi, -np.pi, -np.pi, -np.pi]),
            'max': np.array([np.pi, np.pi, np.pi, np.pi, np.pi, np.pi])
        }

        # Monitored states
        self.current_wrench = np.zeros(6)
        self.current_twist = np.zeros(6)
        self.joint_positions = np.zeros(6)
        self.joint_velocities = np.zeros(6)
        self.target_positions = np.zeros(6)

        # Violation tracking
        self.force_violation_time = 0.0
        self.velocity_violation_time = 0.0
        self.position_error = np.zeros(6)

        # Emergency state
        self.e_stop_active = False
        self.collision_detected = False

        # Subscribers and Publishers
        self._setup_communications()

        # Monitor timer
        self.monitor_timer = self.create_timer(0.01, self.monitor_loop)

        self.get_logger().info("Safety Monitor initialized")

    def _setup_communications(self):
        """Setup ROS publishers and subscribers."""
        qos = QoSProfile(depth=10)

        # Subscribers
        self.ft_sub = self.create_subscription(
            WrenchStamped,
            '/ft_sensor/wrench',
            self.ft_callback,
            qos
        )

        self.velocity_sub = self.create_subscription(
            TwistStamped,
            '/tool_velocity',
            self.velocity_callback,
            qos
        )

        self.joint_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_callback,
            qos
        )

        self.target_sub = self.create_subscription(
            Float64MultiArray,
            '/rehabilitation_joint_controller/target',
            self.target_callback,
            qos
        )

        # Publishers
        self.status_pub = self.create_publisher(
            String,
            '/safety/status',
            qos
        )

        self.warning_pub = self.create_publisher(
            String,
            '/safety/warning',
            qos
        )

        self.e_stop_pub = self.create_publisher(
            Bool,
            '/safety/emergency_stop',
            qos
        )

    def ft_callback(self, msg: WrenchStamped):
        """Process force/torque data."""
        self.current_wrench = np.array([
            msg.wrench.force.x,
            msg.wrench.force.y,
            msg.wrench.force.z,
            msg.wrench.torque.x,
            msg.wrench.torque.y,
            msg.wrench.torque.z
        ])

    def velocity_callback(self, msg: TwistStamped):
        """Process velocity data."""
        self.current_twist = np.array([
            msg.twist.linear.x,
            msg.twist.linear.y,
            msg.twist.linear.z,
            msg.twist.angular.x,
            msg.twist.angular.y,
            msg.twist.angular.z
        ])

    def joint_callback(self, msg: JointState):
        """Process joint state data."""
        for i, name in enumerate(msg.name):
            if i < len(msg.position):
                self.joint_positions[i] = msg.position[i]
            if i < len(msg.velocity):
                self.joint_velocities[i] = msg.velocity[i]

    def target_callback(self, msg: Float64MultiArray):
        """Process target positions."""
        if len(msg.data) >= 6:
            self.target_positions = np.array(msg.data[:6])

    def monitor_loop(self):
        """Main safety monitoring loop."""
        if self.e_stop_active:
            return

        # Check all safety conditions
        force_safe = self._check_force_limits()
        velocity_safe = self._check_velocity_limits()
        position_safe = self._check_position_limits()
        joint_safe = self._check_joint_limits()

        # Determine overall safety level
        if not force_safe:
            self._handle_force_violation()
        elif not velocity_safe:
            self._handle_velocity_violation()
        elif not position_safe:
            self._handle_position_violation()
        else:
            self._reset_violation_timers()
            self.current_level = SafetyLevel.NORMAL

        # Publish status
        self._publish_status()

        # Check for emergency conditions
        self._check_emergency_conditions()

    def _check_force_limits(self) -> bool:
        """Check if forces are within limits."""
        linear_force = np.linalg.norm(self.current_wrench[:3])
        rotational_force = np.linalg.norm(self.current_wrench[3:])

        return (linear_force < self.safety_limits.max_linear_force and
                rotational_force < self.safety_limits.max_rotational_force)

    def _check_velocity_limits(self) -> bool:
        """Check if velocities are within limits."""
        linear_vel = np.linalg.norm(self.current_twist[:3])
        angular_vel = np.linalg.norm(self.current_twist[3:])

        return (linear_vel < self.safety_limits.max_linear_velocity and
                angular_vel < self.safety_limits.max_angular_velocity)

    def _check_position_limits(self) -> bool:
        """Check if position tracking is within limits."""
        self.position_error = np.abs(self.joint_positions - self.target_positions)
        return np.all(self.position_error < self.safety_limits.max_joint_position_error)

    def _check_joint_limits(self) -> bool:
        """Check if joints are within hard limits."""
        return (np.all(self.joint_positions > self.joint_limits['min'] + 0.1) and
                np.all(self.joint_positions < self.joint_limits['max'] - 0.1))

    def _handle_force_violation(self):
        """Handle force limit violation."""
        current_time = time.time()

        if self.force_violation_time == 0:
            self.force_violation_time = current_time
        elif current_time - self.force_violation_time > self.safety_limits.force_limit_duration:
            # Duration exceeded - upgrade to warning
            self.current_level = SafetyLevel.WARNING
            self._log_violation('force', self.current_wrench)
            self._publish_warning('Force limit exceeded')

    def _handle_velocity_violation(self):
        """Handle velocity limit violation."""
        current_time = time.time()

        if self.velocity_violation_time == 0:
            self.velocity_violation_time = current_time
        elif current_time - self.velocity_violation_time > self.safety_limits.velocity_limit_duration:
            self.current_level = SafetyLevel.CAUTION
            self._log_violation('velocity', self.current_twist)

    def _handle_position_violation(self):
        """Handle position tracking violation."""
        self.current_level = SafetyLevel.CAUTION
        max_error_joint = np.argmax(self.position_error)
        self.get_logger().warning(
            f"Position error on joint {max_error_joint}: "
            f"{self.position_error[max_error_joint]:.4f}"
        )

    def _reset_violation_timers(self):
        """Reset violation timers when all conditions are safe."""
        self.force_violation_time = 0
        self.velocity_violation_time = 0

    def _check_emergency_conditions(self):
        """Check for emergency conditions."""
        # Check for collision
        if np.any(np.abs(self.current_wrench[:3]) > self.safety_limits.max_linear_force * 1.5):
            self.collision_detected = True
            self._trigger_emergency_stop("Collision detected")
            return

        # Check for runaway condition
        if np.any(np.abs(self.joint_velocities) > self.safety_limits.max_angular_velocity * 2):
            self._trigger_emergency_stop("Runaway condition detected")
            return

    def _trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop."""
        self.e_stop_active = True
        self.current_level = SafetyLevel.EMERGENCY
        self.last_safety_event = {
            'time': time.time(),
            'reason': reason,
            'wrench': self.current_wrench.tolist(),
            'velocity': self.current_twist.tolist()
        }

        # Publish emergency stop
        msg = Bool()
        msg.data = True
        self.e_stop_pub.publish(msg)

        # Log
        self.get_logger().error(f"EMERGENCY STOP: {reason}")
        self._log_violation('emergency', self.last_safety_event)

    def reset_emergency_stop(self):
        """Reset emergency stop (manual intervention required)."""
        self.e_stop_active = False
        self.collision_detected = False
        self.current_level = SafetyLevel.NORMAL
        self.get_logger().info("Emergency stop reset - system ready")

    def _log_violation(self, violation_type: str, data):
        """Log safety violation."""
        violation = {
            'timestamp': time.time(),
            'type': violation_type,
            'data': data.tolist() if hasattr(data, 'tolist') else data,
            'safety_level': self.current_level.value
        }
        self.safety_violations.append(violation)

        # Keep only recent violations
        if len(self.safety_violations) > 1000:
            self.safety_violations = self.safety_violations[-500:]

    def _publish_status(self):
        """Publish safety status."""
        msg = String()
        status = {
            'level': self.current_level.value,
            'e_stop': self.e_stop_active,
            'force_linear': float(np.linalg.norm(self.current_wrench[:3])),
            'force_rotational': float(np.linalg.norm(self.current_wrench[3:])),
            'velocity_linear': float(np.linalg.norm(self.current_twist[:3])),
            'velocity_angular': float(np.linalg.norm(self.current_twist[3:])),
            'max_position_error': float(np.max(self.position_error))
        }
        msg.data = json.dumps(status)
        self.status_pub.publish(msg)

    def _publish_warning(self, message: str):
        """Publish safety warning."""
        msg = String()
        msg.data = message
        self.warning_pub.publish(msg)

    def get_safety_report(self) -> Dict:
        """Generate safety report."""
        return {
            'current_level': self.current_level.value,
            'e_stop_active': self.e_stop_active,
            'violation_count': len(self.safety_violations),
            'recent_violations': self.safety_violations[-10:],
            'last_event': self.last_safety_event
        }

    def update_limits(self, new_limits: Dict):
        """Update safety limits at runtime."""
        for key, value in new_limits.items():
            if hasattr(self.safety_limits, key):
                setattr(self.safety_limits, key, value)
                self.get_logger().info(f"Updated limit {key} to {value}")


def main(args=None):
    rclpy.init(args=args)

    monitor = SafetyMonitor()

    try:
        rclpy.spin(monitor)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
