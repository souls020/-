#!/usr/bin/env python3
"""
Robot calibration script
Performs calibration procedures for rehabilitation robot
"""

import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from robot_control.src.kinematics import Kinematics


class RobotCalibrator:
    """Robot calibration utility."""

    def __init__(self, robot_type: str = "UR5"):
        """Initialize calibrator."""
        self.kinematics = Kinematics(robot_type)
        self.calibration_points = []

    def collect_calibration_point(self, name: str, joint_positions: list):
        """Collect a calibration point."""
        point = {
            'name': name,
            'joints': joint_positions,
            'timestamp': time.time()
        }
        self.calibration_points.append(point)
        print(f"Collected calibration point: {name}")
        return point

    def run_home_calibration(self):
        """Run home position calibration."""
        print("Home Position Calibration")
        print("-" * 30)
        print("Move robot to home position...")
        input("Press Enter when ready: ")

        self.collect_calibration_point('home', [0, 0, 0, 0, 0, 0])
        print("Home calibration complete.\n")

    def run_joint_limit_calibration(self):
        """Run joint limit calibration."""
        print("Joint Limit Calibration")
        print("-" * 30)

        limits = {'min': [], 'max': []}

        for i in range(6):
            print(f"Joint {i}: Move to minimum position...")
            input("Press Enter when ready: ")
            # Record position
            limits['min'].append(input(f"Enter min position for joint {i} (or press Enter to use current): "))

            print(f"Joint {i}: Move to maximum position...")
            input("Press Enter when ready: ")
            limits['max'].append(input(f"Enter max position for joint {i} (or press Enter to use current): "))

        print("Joint limit calibration complete.\n")
        return limits

    def run_tcp_calibration(self):
        """Run TCP (Tool Center Point) calibration."""
        print("TCP Calibration")
        print("-" * 30)
        print("This procedure calibrates the tool center point.")
        print("Move the TCP to the same physical point from 4 different orientations.\n")

        tcp_points = []

        for i in range(4):
            print(f"Position {i + 1}/4: Move robot so TCP is at calibration point.")
            input("Press Enter when ready: ")
            tcp_points.append({'timestamp': time.time()})

        print("TCP calibration complete.\n")
        return tcp_points

    def save_calibration(self, filepath: str = "calibration_data.yaml"):
        """Save calibration data."""
        import yaml

        data = {
            'calibration_time': time.time(),
            'calibration_points': self.calibration_points
        }

        with open(filepath, 'w') as f:
            yaml.dump(data, f)

        print(f"Calibration saved to {filepath}")

    def print_summary(self):
        """Print calibration summary."""
        print("\nCalibration Summary")
        print("=" * 40)
        print(f"Calibration points collected: {len(self.calibration_points)}")
        for point in self.calibration_points:
            print(f"  - {point['name']}")


def main():
    """Main calibration routine."""
    print("Rehabilitation Robot Calibration")
    print("=" * 40)
    print()

    calibrator = RobotCalibrator()

    # Run calibrations
    calibrator.run_home_calibration()
    limits = calibrator.run_joint_limit_calibration()
    tcp_points = calibrator.run_tcp_calibration()

    # Save calibration
    calibrator.save_calibration()

    # Print summary
    calibrator.print_summary()


if __name__ == "__main__":
    main()
