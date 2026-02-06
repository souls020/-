#!/usr/bin/env python3
"""
Emergency Handler
Handles emergency situations and graceful shutdown
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import Bool, String
import time
import threading


class EmergencyHandler(Node):
    """
    Emergency handling system.
    Manages emergency stops and recovery procedures.
    """

    def __init__(self):
        super().__init__('emergency_handler')

        # State
        self.e_stop_active = False
        self.recovery_mode = False
        self.emergency_history = []
        self.shutdown_requested = False

        # Recovery state
        self.recovery_start_time = None
        self.auto_recovery_enabled = True
        self.recovery_timeout = 30.0  # seconds

        # Publishers and Subscribers
        self._setup_communications()

        # Start monitoring
        self.timer = self.create_timer(0.1, self.check_recovery)

        self.get_logger().info("Emergency Handler initialized")

    def _setup_communications(self):
        """Setup ROS communications."""
        qos = QoSProfile(depth=10)

        # Subscribers
        self.e_stop_sub = self.create_subscription(
            Bool,
            '/safety/emergency_stop',
            self.e_stop_callback,
            qos
        )

        self.command_sub = self.create_subscription(
            String,
            '/emergency/command',
            self.command_callback,
            qos
        )

        # Publishers
        self.system_stop_pub = self.create_publisher(
            Bool,
            '/system/emergency_stop',
            qos
        )

        self.status_pub = self.create_publisher(
            String,
            '/emergency/status',
            qos
        )

    def e_stop_callback(self, msg: Bool):
        """Handle emergency stop signal."""
        if msg.data and not self.e_stop_active:
            self.activate_emergency_stop("Received E-Stop signal")
        elif not msg.data and self.e_stop_active:
            self.reset_emergency_stop()

    def command_callback(self, msg: String):
        """Handle emergency commands."""
        command = msg.data.lower()

        if command == "emergency_stop":
            self.activate_emergency_stop("Manual emergency stop")
        elif command == "reset":
            self.reset_emergency_stop()
        elif command == "shutdown":
            self.request_shutdown()
        elif command == "recover":
            self.start_recovery()

    def activate_emergency_stop(self, reason: str):
        """
        Activate emergency stop.

        Args:
            reason: Reason for emergency stop
        """
        self.e_stop_active = True
        self.recovery_mode = False

        # Record event
        event = {
            'time': time.time(),
            'reason': reason,
            'type': 'emergency_stop'
        }
        self.emergency_history.append(event)

        # Publish emergency stop
        msg = Bool()
        msg.data = True
        self.system_stop_pub.publish(msg)

        # Publish status
        self._publish_status()

        self.get_logger().error(f"EMERGENCY STOP ACTIVATED: {reason}")

        # If auto-recovery enabled, schedule recovery
        if self.auto_recovery_enabled:
            self.get_logger().info(f"Auto-recovery in {self.recovery_timeout} seconds")
            self.recovery_start_time = time.time()

    def reset_emergency_stop(self):
        """Reset emergency stop (manual intervention required)."""
        if self.e_stop_active:
            self.e_stop_active = False
            self.recovery_mode = False

            # Publish reset
            msg = Bool()
            msg.data = False
            self.system_stop_pub.publish(msg)

            # Publish status
            self._publish_status()

            self.get_logger().info("Emergency stop RESET - system operational")

    def start_recovery(self):
        """Start recovery procedure."""
        self.recovery_mode = True
        self.recovery_start_time = time.time()
        self.get_logger().info("Starting recovery procedure")

    def check_recovery(self):
        """Check recovery status."""
        if not self.recovery_mode or not self.e_stop_active:
            return

        # Check timeout
        if time.time() - self.recovery_start_time > self.recovery_timeout:
            self.get_logger().warning("Recovery timeout - manual intervention required")
            self.recovery_mode = False

    def request_shutdown(self):
        """Request system shutdown."""
        self.shutdown_requested = True
        self.get_logger().info("Shutdown requested")

        # Stop all controllers
        msg = Bool()
        msg.data = True
        self.system_stop_pub.publish(msg)

    def _publish_status(self):
        """Publish current status."""
        msg = String()
        status = {
            'e_stop_active': self.e_stop_active,
            'recovery_mode': self.recovery_mode,
            'shutdown_requested': self.shutdown_requested,
            'auto_recovery': self.auto_recovery_enabled
        }
        msg.data = str(status)
        self.status_pub.publish(msg)

    def get_emergency_history(self) -> list:
        """Get emergency event history."""
        return self.emergency_history

    def clear_history(self):
        """Clear emergency history."""
        self.emergency_history = []


def main(args=None):
    rclpy.init(args=args)

    handler = EmergencyHandler()

    try:
        rclpy.spin(handler)
    except KeyboardInterrupt:
        pass
    finally:
        handler.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
