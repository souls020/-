#!/usr/bin/env python3
"""
Upper Limb Rehabilitation Trainer
Implements various upper limb rehabilitation exercises
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import String, Float64MultiArray, Int32
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import yaml
import time


class TrainingMode(Enum):
    """Training mode types."""
    PASSIVE = "passive"
    ACTIVE_ASSISTED = "active_assisted"
    ACTIVE_RESISTED = "active_resisted"


@dataclass
class TrainingConfig:
    """Configuration for a training session."""
    exercise_name: str
    mode: TrainingMode
    target_joints: List[int]
    rom_min: float  # Minimum range of motion (radians)
    rom_max: float  # Maximum range of motion (radians)
    speed: float  # Movement speed (rad/s)
    num_sets: int
    num_reps: int
    rest_time: float  # Rest between sets (seconds)
    resistance: float  # Resistance level (0-1)


class UpperLimbTrainer(Node):
    """
    Upper limb rehabilitation training controller.
    Implements various exercises for shoulder, elbow, and forearm.
    """

    def __init__(self, config_path: str = None):
        super().__init__('upper_limb_trainer')

        # Load configuration
        self.load_config(config_path)

        # Training state
        self.current_exercise = None
        self.current_set = 0
        self.current_rep = 0
        self.is_training = False
        self.is_paused = False
        self.session_start_time = None
        self.rep_complete_flag = False
        self.target_joints = []
        self.rom_min = 0.0
        self.rom_max = 1.0
        self.speed = 0.3
        self.current_mode = TrainingMode.PASSIVE

        # Patient state
        self.patient_effort = 0.0  # 0-1 scale
        self.fatigue_level = 0.0
        self.comfort_level = 1.0

        # Exoskeleton interface
        self.joint_positions = np.zeros(6)
        self.joint_velocities = np.zeros(6)

        # Publishers and Subscribers
        self._setup_communications()

        # Training timer
        self.timer = self.create_timer(0.01, self.training_loop)

        self.get_logger().info("Upper Limb Trainer initialized")

    def load_config(self, config_path: str):
        """Load training protocols from config."""
        if config_path:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.protocols = config['upper_limb']
        else:
            # Default protocols
            self.protocols = {
                'shoulder_abduction': {
                    'joints': [0, 1],
                    'range_of_motion': {'min_angle': 0.0, 'max_angle': 1.57},
                    'speed': {'default': 0.3}
                },
                'elbow_flexion': {
                    'joints': [2],
                    'range_of_motion': {'min_angle': 0.0, 'max_angle': 2.44},
                    'speed': {'default': 0.5}
                }
            }

        # Default training parameters
        self.default_config = TrainingConfig(
            exercise_name="default",
            mode=TrainingMode.PASSIVE,
            target_joints=[0, 1, 2],
            rom_min=0.0,
            rom_max=1.0,
            speed=0.3,
            num_sets=3,
            num_reps=10,
            rest_time=30.0,
            resistance=0.0
        )

    def _setup_communications(self):
        """Setup ROS publishers and subscribers."""
        qos = QoSProfile(depth=10)

        # Command publisher (to joint controller)
        self.cmd_pub = self.create_publisher(
            Float64MultiArray,
            '/rehabilitation_joint_controller/target',
            qos
        )

        # Status publishers
        self.status_pub = self.create_publisher(
            String,
            '/rehabilitation/status',
            qos
        )

        self.progress_pub = self.create_publisher(
            Float64MultiArray,
            '/rehabilitation/progress',
            qos
        )

        # Subscribers
        self.exercise_sub = self.create_subscription(
            String,
            '/rehabilitation/exercise_command',
            self.exercise_command_callback,
            qos
        )

        self.patient_sub = self.create_subscription(
            Float64MultiArray,
            '/patient/state',
            self.patient_state_callback,
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
        else:
            self.get_logger().warning(f"Unknown command: {command}")

    def patient_state_callback(self, msg: Float64MultiArray):
        """Receive patient effort and state data."""
        if len(msg.data) >= 3:
            self.patient_effort = msg.data[0]
            self.fatigue_level = msg.data[1]
            self.comfort_level = msg.data[2]

    def start_training(self, exercise: str = "shoulder_abduction",
                      mode: TrainingMode = TrainingMode.PASSIVE):
        """
        Start a training session.

        Args:
            exercise: Exercise name
            mode: Training mode
        """
        if exercise not in self.protocols:
            self.get_logger().error(f"Unknown exercise: {exercise}")
            return

        protocol = self.protocols[exercise]

        self.current_exercise = exercise
        self.current_mode = mode
        self.target_joints = protocol['joints']
        self.rom_min = protocol['range_of_motion']['min_angle']
        self.rom_max = protocol['range_of_motion']['max_angle']
        self.speed = protocol['speed']['default']

        self.current_set = 1
        self.current_rep = 0
        self.is_training = True
        self.is_paused = False
        self.session_start_time = time.time()

        self.get_logger().info(f"Starting {exercise} in {mode.value} mode")

    def stop_training(self):
        """Stop the current training session."""
        self.is_training = False
        self.is_paused = False
        self.publish_command(np.zeros(6))
        self.get_logger().info("Training stopped")

    def pause_training(self):
        """Pause the current training."""
        self.is_paused = True
        self.get_logger().info("Training paused")

    def resume_training(self):
        """Resume paused training."""
        self.is_paused = False
        self.get_logger().info("Training resumed")

    def training_loop(self):
        """Main training loop."""
        if not self.is_training or self.is_paused:
            return

        if self.current_exercise is None:
            return

        # Execute training based on exercise
        if self.current_exercise == "shoulder_abduction":
            self._execute_shoulder_abduction()
        elif self.current_exercise == "elbow_flexion":
            self._execute_elbow_flexion()
        elif self.current_exercise == "forearm_rotation":
            self._execute_forearm_rotation()
        elif self.current_exercise == "shoulder_rotation":
            self._execute_shoulder_rotation()
        else:
            self.get_logger().warning(f"Exercise not implemented: {self.current_exercise}")
            self.stop_training()

    def _execute_shoulder_abduction(self):
        """Execute shoulder abduction/adduction exercise."""
        # Pattern: 0 -> max -> 0
        exercise_protocol = self.protocols['shoulder_abduction']
        max_angle = exercise_protocol['range_of_motion']['max_angle']
        speed = self.speed

        t = time.time()
        phase = (t * speed) % (2 * np.pi)

        # Calculate target position
        if phase < np.pi:
            # Abduction phase
            target_angle = (phase / np.pi) * max_angle
        else:
            # Adduction phase
            target_angle = max_angle - ((phase - np.pi) / np.pi) * max_angle

        # Apply to shoulder joints
        target = self.joint_positions.copy()
        target[0] = target_angle * 0.5  # Shoulder pan
        target[1] = target_angle  # Shoulder lift

        self.publish_command(target)
        self._check_rep_completion(target_angle, max_angle)

    def _execute_elbow_flexion(self):
        """Execute elbow flexion/extension exercise."""
        exercise_protocol = self.protocols['elbow_flexion']
        max_angle = exercise_protocol['range_of_motion']['max_angle']
        speed = self.speed

        t = time.time()
        phase = (t * speed) % (2 * np.pi)

        if phase < np.pi:
            # Flexion
            target_angle = (phase / np.pi) * max_angle
        else:
            # Extension
            target_angle = max_angle - ((phase - np.pi) / np.pi) * max_angle

        target = self.joint_positions.copy()
        target[2] = target_angle  # Elbow joint

        self.publish_command(target)
        self._check_rep_completion(target_angle, max_angle)

    def _execute_forearm_rotation(self):
        """Execute forearm pronation/supination exercise."""
        max_angle = np.pi
        speed = self.speed * 0.8

        t = time.time()
        phase = (t * speed) % (2 * np.pi)

        target = self.joint_positions.copy()
        target[5] = phase - np.pi  # Wrist 3 joint

        self.publish_command(target)

    def _execute_shoulder_rotation(self):
        """Execute shoulder internal/external rotation."""
        exercise_protocol = self.protocols['shoulder_rotation']
        max_angle = exercise_protocol['range_of_motion']['max_angle']
        speed = self.speed * 0.8

        t = time.time()
        phase = (t * speed) % (2 * np.pi)

        target = self.joint_positions.copy()
        target[0] = (phase / np.pi - 1) * max_angle

        self.publish_command(target)

    def _check_rep_completion(self, current_angle: float, max_angle: float):
        """Check if a repetition is complete."""
        threshold = max_angle * 0.95

        if current_angle >= threshold and not self.rep_complete_flag:
            self.rep_complete_flag = True
            self.current_rep += 1
            self.get_logger().info(f"Rep {self.current_rep} completed")

            # Check set completion
            exercise_protocol = self.protocols.get(self.current_exercise, {})
            num_reps = exercise_protocol.get('default_reps', 10)

            if self.current_rep >= num_reps:
                self._complete_set()

    def _complete_set(self):
        """Handle set completion."""
        self.current_set += 1
        self.current_rep = 0
        self.rep_complete_flag = False

        exercise_protocol = self.protocols.get(self.current_exercise, {})
        num_sets = exercise_protocol.get('default_sets', 3)

        if self.current_set > num_sets:
            self.get_logger().info("Training session complete!")
            self.stop_training()
        else:
            self.get_logger().info(f"Set {self.current_set} complete. Resting...")
            # Could implement rest period here

    def publish_command(self, target: np.ndarray):
        """Publish target command to joint controller."""
        msg = Float64MultiArray()
        msg.data = target.tolist()
        self.cmd_pub.publish(msg)

    def publish_status(self):
        """Publish current training status."""
        msg = String()
        status = {
            'exercise': self.current_exercise,
            'mode': self.current_mode.value if self.current_mode else None,
            'set': self.current_set,
            'rep': self.current_rep,
            'fatigue': self.fatigue_level,
            'effort': self.patient_effort
        }
        msg.data = str(status)
        self.status_pub.publish(msg)

    def get_exercise_list(self) -> List[str]:
        """Get list of available exercises."""
        return list(self.protocols.keys())


def main(args=None):
    rclpy.init(args=args)

    trainer = UpperLimbTrainer()

    try:
        rclpy.spin(trainer)
    except KeyboardInterrupt:
        trainer.stop_training()
    finally:
        trainer.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
