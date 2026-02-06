#!/usr/bin/env python3
"""
Joint Controller for Rehabilitation Robot
Implements PID control for joint position tracking
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
from geometry_msgs.msg import WrenchStamped
from nav_msgs.msg import Odometry
import numpy as np
from typing import List, Dict, Optional
import yaml
import time


class JointController(Node):
    """
    Joint position controller with PID feedback.
    Designed for safe rehabilitation training.
    """

    def __init__(self, config_path: str = None):
        super().__init__('joint_controller')

        # Load parameters
        self.load_config(config_path)

        # Controller state
        self.joint_positions = np.zeros(self.num_joints)
        self.joint_velocities = np.zeros(self.num_joints)
        self.joint_efforts = np.zeros(self.num_joints)
        self.target_positions = np.zeros(self.num_joints)
        self.current_mode = "position"  # position, velocity, torque, impedance

        # PID state
        self.integral = np.zeros(self.num_joints)
        self.prev_error = np.zeros(self.num_joints)
        self.last_time = time.time()

        # Safety state
        self.e_stop_active = False
        self.collision_detected = False
        self.safety_limits_exceeded = False

        # Publishers and Subscribers
        self._setup_communications()

        # Control timer
        self.control_period = 1.0 / self.control_frequency
        self.timer = self.create_timer(self.control_period, self.control_loop)

        self.get_logger().info("Joint Controller initialized")

    def load_config(self, config_path: str):
        """Load controller parameters from config file."""
        if config_path:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            self.num_joints = config['robot']['num_joints']
            self.joint_names = config['robot']['joint_names']

            limits = config['joint_limits']
            self.joint_limits = {
                'min': np.array(limits['min']),
                'max': np.array(limits['max']),
                'velocity': np.array(limits['velocity']),
                'acceleration': np.array(limits['acceleration'])
            }

            pid = config['pid_gains']
            self.kp = np.array([pid[f'joint_{i}']['p'] for i in range(6)])
            self.ki = np.array([pid[f'joint_{i}']['i'] for i in range(6)])
            self.kd = np.array([pid[f'joint_{i}']['d'] for i in range(6)])

            safety = config['safety']
            self.max_force = safety['max_force']
            self.max_torque = safety['max_torque']
            self.collision_threshold = safety['collision_threshold']

            self.control_frequency = 100.0  # Hz
        else:
            # Default parameters
            self.num_joints = 6
            self.joint_names = [f'joint_{i}' for i in range(6)]
            self.joint_limits = {
                'min': -np.pi * np.ones(6),
                'max': np.pi * np.ones(6),
                'velocity': 2.0 * np.ones(6),
                'acceleration': 1.0 * np.ones(6)
            }
            self.kp = 1000.0 * np.ones(6)
            self.ki = 100.0 * np.ones(6)
            self.kd = 50.0 * np.ones(6)
            self.max_force = 50.0
            self.max_torque = 10.0
            self.collision_threshold = 20.0
            self.control_frequency = 100.0

    def _setup_communications(self):
        """Setup ROS publishers and subscribers."""
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            depth=10
        )

        # Subscribers
        self.joint_state_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            qos
        )

        self.ft_sensor_sub = self.create_subscription(
            WrenchStamped,
            '/ft_sensor/wrench',
            self.ft_sensor_callback,
            qos
        )

        # Publishers
        self.cmd_pub = self.create_publisher(
            Float64MultiArray,
            '/forward_effort_controller/commands',
            qos
        )

        self.status_pub = self.create_publisher(
            Float64MultiArray,
            '/rehabilitation_joint_controller/status',
            qos
        )

        # Service for setting target
        self.target_sub = self.create_subscription(
            Float64MultiArray,
            '/rehabilitation_joint_controller/target',
            self.target_callback,
            qos
        )

    def joint_state_callback(self, msg: JointState):
        """Process joint state measurements."""
        # Handle potentially incomplete joint state messages
        for i, name in enumerate(msg.name):
            if name in self.joint_names:
                idx = self.joint_names.index(name)
                if i < len(msg.position):
                    self.joint_positions[idx] = msg.position[i]
                if i < len(msg.velocity):
                    self.joint_velocities[idx] = msg.velocity[i]
                if i < len(msg.effort):
                    self.joint_efforts[idx] = msg.effort[i]

    def ft_sensor_callback(self, msg: WrenchStamped):
        """Process force/torque sensor data."""
        self.current_force = np.array([
            msg.wrench.force.x,
            msg.wrench.force.y,
            msg.wrench.force.z,
            msg.wrench.torque.x,
            msg.wrench.torque.y,
            msg.wrench.torque.z
        ])

    def target_callback(self, msg: Float64MultiArray):
        """Receive target positions from higher-level controller."""
        if len(msg.data) == self.num_joints:
            self.target_positions = np.array(msg.data)
            self.get_logger().debug(f"New target: {self.target_positions}")

    def control_loop(self):
        """Main control loop - runs at specified frequency."""
        if self.e_stop_active or self.collision_detected:
            self.publish_zero_commands()
            return

        # Compute control command based on mode
        if self.current_mode == "position":
            command = self.position_control()
        elif self.current_mode == "torque":
            command = self.torque_control()
        elif self.current_mode == "impedance":
            command = self.impedance_control()
        else:
            command = np.zeros(self.num_joints)

        # Safety checks
        if self.check_safety_limits():
            self.publish_zero_commands()
            return

        # Publish command
        self.publish_command(command)

        # Publish status
        self.publish_status()

    def position_control(self) -> np.ndarray:
        """Compute PID control effort for position tracking."""
        current_time = time.time()
        dt = current_time - self.last_time

        if dt <= 0:
            return np.zeros(self.num_joints)

        # Compute error
        error = self.target_positions - self.joint_positions

        # Anti-windup: limit integral term
        self.integral = np.clip(
            self.integral + error * dt,
            -self.joint_limits['max'] * 0.5,
            self.joint_limits['max'] * 0.5
        )

        # Derivative term (with filtering)
        derivative = (error - self.prev_error) / dt
        derivative = np.clip(derivative, -10, 10)  # Limit derivative

        # PID output
        effort = (self.kp * error +
                  self.ki * self.integral +
                  self.kd * derivative)

        # Limit output torque
        effort = np.clip(effort, -self.max_torque, self.max_torque)

        # Store for next iteration
        self.prev_error = error
        self.last_time = current_time

        return effort

    def torque_control(self) -> np.ndarray:
        """Direct torque control mode for force-based interactions."""
        # Compute desired torque based on error dynamics
        error = self.target_positions - self.joint_positions

        # Simple P torque controller (would be replaced with full dynamics)
        desired_torque = self.kp * error * 0.1  # Reduced gains for torque mode

        # Clamp to safe limits
        desired_torque = np.clip(desired_torque, -self.max_torque, self.max_torque)

        return desired_torque

    def impedance_control(self) -> np.ndarray:
        """
        Impedance control for compliant interaction.
        Maintains a virtual spring-damper relationship with the environment.
        """
        # Impedance parameters (stiffness, damping)
        K = np.diag([100.0, 100.0, 100.0, 50.0, 50.0, 50.0])  # Stiffness
        D = np.diag([10.0, 10.0, 10.0, 5.0, 5.0, 5.0])  # Damping

        # Compute impedance error (position deviation from desired)
        error = self.joint_positions - self.target_positions

        # Compute velocity error
        velocity_error = self.joint_velocities

        # Impedance equation: F = K*x + D*dx
        desired_effort = K @ error + D @ velocity_error

        # Clamp to safe limits
        desired_effort = np.clip(desired_effort, -self.max_torque * 2, self.max_torque * 2)

        return desired_effort

    def check_safety_limits(self) -> bool:
        """Check if any safety limits are exceeded."""
        # Check joint limits
        for i in range(self.num_joints):
            if (self.joint_positions[i] < self.joint_limits['min'][i] or
                self.joint_positions[i] > self.joint_limits['max'][i]):
                self.get_logger().warning(f"Joint {i} at limit: {self.joint_positions[i]}")
                return True

        # Check velocity limits
        velocities = np.abs(self.joint_velocities)
        if np.any(velocities > self.joint_limits['velocity'] * 1.2):
            self.get_logger().warning("Velocity limit exceeded")
            return True

        # Check force/torque limits
        if hasattr(self, 'current_force'):
            if np.any(np.abs(self.current_force[:3]) > self.max_force):
                self.get_logger().warning("Force limit exceeded")
                return True
            if np.any(np.abs(self.current_force[3:]) > self.max_torque):
                self.get_logger().warning("Torque limit exceeded")
                return True

        return False

    def check_collision(self) -> bool:
        """Detect collision based on force/torque measurements."""
        if not hasattr(self, 'current_force'):
            return False

        # Compare measured forces with expected (from dynamics)
        # Simplified: just check threshold
        if np.any(np.abs(self.current_force[:3]) > self.collision_threshold):
            return True

        return False

    def publish_command(self, command: np.ndarray):
        """Publish effort command to robot."""
        msg = Float64MultiArray()
        msg.data = command.tolist()
        self.cmd_pub.publish(msg)

    def publish_zero_commands(self):
        """Publish zero commands (emergency stop)."""
        self.publish_command(np.zeros(self.num_joints))

    def publish_status(self):
        """Publish controller status."""
        msg = Float64MultiArray()
        status = np.concatenate([
            self.joint_positions,
            self.joint_velocities,
            self.target_positions
        ])
        msg.data = status.tolist()
        self.status_pub.publish(msg)

    def set_target(self, positions: List[float]):
        """Set target joint positions."""
        self.target_positions = np.clip(
            positions,
            self.joint_limits['min'],
            self.joint_limits['max']
        )

    def set_mode(self, mode: str):
        """Set control mode."""
        valid_modes = ["position", "velocity", "torque", "impedance"]
        if mode in valid_modes:
            self.current_mode = mode
            self.get_logger().info(f"Control mode changed to: {mode}")
        else:
            self.get_logger().warning(f"Invalid mode: {mode}")

    def emergency_stop(self):
        """Activate emergency stop."""
        self.e_stop_active = True
        self.publish_zero_commands()
        self.get_logger().error("EMERGENCY STOP ACTIVATED")

    def reset_emergency_stop(self):
        """Reset emergency stop."""
        self.e_stop_active = False
        self.get_logger().info("Emergency stop reset")

    def shutdown(self):
        """Clean shutdown."""
        self.publish_zero_commands()
        self.get_logger().info("Joint Controller shutdown")


def main(args=None):
    rclpy.init(args=args)

    controller = JointController()

    try:
        rclpy.spin(controller)
    except KeyboardInterrupt:
        controller.shutdown()
    finally:
        controller.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
