#!/usr/bin/env python3
"""
Lower Limb Rehabilitation Trainer
Implements various lower limb rehabilitation exercises
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import String, Float64MultiArray
import numpy as np
from typing import Dict, List, Optional
from enum import Enum
import yaml
import time


class LowerLimbTrainer(Node):
    """
    Lower limb rehabilitation training controller.
    Implements exercises for hip, knee, and ankle rehabilitation.
    """

    def __init__(self, config_path: str = None):
        super().__init__('lower_limb_trainer')

        # Load configuration
        self.load_config(config_path)

        # Training state
        self.current_exercise = None
        self.current_set = 0
        self.current_rep = 0
        self.is_training = False
        self.is_paused = False

        # Joint states (using robot joints for control)
        self.joint_positions = np.zeros(6)
        self.target_positions = np.zeros(6)

        # Exercise state
        self.phase = 0.0
        self.rep_complete_flag = False

        # Publishers and Subscribers
        self._setup_communications()

        # Training timer
        self.timer = self.create_timer(0.01, self.training_loop)

        self.get_logger().info("Lower Limb Trainer initialized")

    def load_config(self, config_path: str):
        """Load training protocols."""
        if config_path:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.protocols = config['lower_limb']
        else:
            # Default protocols
            self.protocols = {
                'hip_flexion': {
                    'joints': [0, 1],
                    'range_of_motion': {'min_angle': 0.0, 'max_angle': 1.22},
                    'speed': {'default': 0.15}
                },
                'knee_flexion': {
                    'joints': [2],
                    'range_of_motion': {'min_angle': 0.0, 'max_angle': 2.09},
                    'speed': {'default': 0.2}
                },
                'ankle_dorsiflexion': {
                    'joints': [3],
                    'range_of_motion': {'min_angle': -0.52, 'max_angle': 0.35},
                    'speed': {'default': 0.12}
                }
            }

    def _setup_communications(self):
        """Setup ROS publishers and subscribers."""
        qos = QoSProfile(depth=10)

        # Command publisher
        self.cmd_pub = self.create_publisher(
            Float64MultiArray,
            '/rehabilitation_joint_controller/target',
            qos
        )

        # Status publisher
        self.status_pub = self.create_publisher(
            String,
            '/rehabilitation/status',
            qos
        )

        # Subscribers
        self.exercise_sub = self.create_subscription(
            String,
            '/rehabilitation/exercise_command',
            self.exercise_command_callback,
            qos
        )

    def exercise_command_callback(self, msg: String):
        """Handle exercise commands."""
        command = msg.data.lower()

        if command == "start":
            self.start_training()
        elif command == "stop":
            self.stop_training()
        elif command == "pause":
            self.pause_training()
        elif command == "resume":
            self.resume_training()

    def start_training(self, exercise: str = "knee_flexion"):
        """
        Start a training session.

        Args:
            exercise: Exercise name
        """
        if exercise not in self.protocols:
            self.get_logger().error(f"Unknown exercise: {exercise}")
            return

        protocol = self.protocols[exercise]

        self.current_exercise = exercise
        self.target_joints = protocol['joints']
        self.rom_min = protocol['range_of_motion']['min_angle']
        self.rom_max = protocol['range_of_motion']['max_angle']
        self.speed = protocol['speed']['default']

        self.current_set = 1
        self.current_rep = 0
        self.is_training = True
        self.is_paused = False
        self.phase = 0.0
        self.rep_complete_flag = False

        self.get_logger().info(f"Starting lower limb exercise: {exercise}")

    def stop_training(self):
        """Stop the current training."""
        self.is_training = False
        self.is_paused = False
        self.publish_command(np.zeros(6))
        self.get_logger().info("Training stopped")

    def pause_training(self):
        """Pause training."""
        self.is_paused = True
        self.get_logger().info("Training paused")

    def resume_training(self):
        """Resume training."""
        self.is_paused = False
        self.get_logger().info("Training resumed")

    def training_loop(self):
        """Main training loop."""
        if not self.is_training or self.is_paused:
            return

        if self.current_exercise == "hip_flexion":
            self._execute_hip_flexion()
        elif self.current_exercise == "knee_flexion":
            self._execute_knee_flexion()
        elif self.current_exercise == "ankle_dorsiflexion":
            self._execute_ankle_dorsiflexion()
        else:
            self.get_logger().warning(f"Exercise not implemented: {self.current_exercise}")

    def _execute_hip_flexion(self):
        """Execute hip flexion/extension exercise."""
        protocol = self.protocols['hip_flexion']
        max_angle = protocol['range_of_motion']['max_angle']
        speed = self.speed

        t = time.time()
        phase = (t * speed) % (2 * np.pi)

        if phase < np.pi:
            target_angle = (phase / np.pi) * max_angle
        else:
            target_angle = max_angle - ((phase - np.pi) / np.pi) * max_angle

        target = self.joint_positions.copy()
        target[0] = target_angle * 0.3
        target[1] = target_angle * 0.7

        self.publish_command(target)
        self._check_rep_completion(target_angle, max_angle)

    def _execute_knee_flexion(self):
        """Execute knee flexion/extension exercise."""
        protocol = self.protocols['knee_flexion']
        max_angle = protocol['range_of_motion']['max_angle']
        speed = self.speed

        t = time.time()
        phase = (t * speed) % (2 * np.pi)

        if phase < np.pi:
            target_angle = (phase / np.pi) * max_angle
        else:
            target_angle = max_angle - ((phase - np.pi) / np.pi) * max_angle

        target = self.joint_positions.copy()
        target[2] = target_angle

        self.publish_command(target)
        self._check_rep_completion(target_angle, max_angle)

    def _execute_ankle_dorsiflexion(self):
        """Execute ankle dorsiflexion/plantarflexion exercise."""
        protocol = self.protocols['ankle_dorsiflexion']
        min_angle = protocol['range_of_motion']['min_angle']
        max_angle = protocol['range_of_motion']['max_angle']
        speed = self.speed

        t = time.time()
        phase = (t * speed) % (2 * np.pi)

        # Full range: plantar -> dorsi -> plantar
        if phase < np.pi:
            target_angle = min_angle + (phase / np.pi) * (max_angle - min_angle)
        else:
            target_angle = max_angle - ((phase - np.pi) / np.pi) * (max_angle - min_angle)

        target = self.joint_positions.copy()
        target[3] = target_angle

        self.publish_command(target)

    def _check_rep_completion(self, current_angle: float, max_angle: float):
        """Check if a repetition is complete."""
        threshold = max_angle * 0.95

        if current_angle >= threshold and not self.rep_complete_flag:
            self.rep_complete_flag = True
            self.current_rep += 1
            self.get_logger().info(f"Rep {self.current_rep}")

            if self.current_rep >= 10:
                self._complete_set()

    def _complete_set(self):
        """Handle set completion."""
        self.current_set += 1
        self.current_rep = 0
        self.rep_complete_flag = False

        if self.current_set > 3:
            self.get_logger().info("Session complete!")
            self.stop_training()
        else:
            self.get_logger().info(f"Set {self.current_set} complete")

    def publish_command(self, target: np.ndarray):
        """Publish target command."""
        msg = Float64MultiArray()
        msg.data = target.tolist()
        self.cmd_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    trainer = LowerLimbTrainer()

    try:
        rclpy.spin(trainer)
    except KeyboardInterrupt:
        trainer.stop_training()
    finally:
        trainer.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
