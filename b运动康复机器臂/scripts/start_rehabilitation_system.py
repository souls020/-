#!/usr/bin/env python3
"""
Start script for rehabilitation robot system
Launches all required nodes
"""

import subprocess
import sys
import os
import argparse


def run_command(cmd: list, background: bool = False):
    """Run a command."""
    if background:
        return subprocess.Popen(cmd)
    else:
        return subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(description='Start rehabilitation robot system')
    parser.add_argument('--simulation', action='store_true', default=True,
                        help='Run in simulation mode')
    parser.add_argument('--hardware', action='store_true',
                        help='Run with hardware connection')
    parser.add_argument('--gui', action='store_true',
                        help='Launch GUI')
    parser.add_argument('--voice', action='store_true',
                        help='Launch voice controller')
    args = parser.parse_args()

    # Setup environment
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Source ROS environment (if not already sourced)
    if 'ROS_DISTRO' not in os.environ:
        print("Warning: ROS environment not sourced")
        print("Please run: source /opt/ros/humble/setup.bash")

    processes = []

    try:
        # Launch safety monitor first
        print("Starting safety monitor...")
        safety_proc = run_command([
            'ros2', 'run', 'rehabilitation_robot', 'safety_monitor'
        ], background=True)
        processes.append(safety_proc)

        # Launch training manager
        print("Starting training manager...")
        manager_proc = run_command([
            'ros2', 'run', 'rehabilitation_robot', 'training_manager'
        ], background=True)
        processes.append(manager_proc)

        if args.simulation:
            # Launch upper limb trainer
            print("Starting upper limb trainer...")
            upper_proc = run_command([
                'ros2', 'run', 'rehabilitation_robot', 'upper_limb_trainer'
            ], background=True)
            processes.append(upper_proc)

            # Launch lower limb trainer
            print("Starting lower limb trainer...")
            lower_proc = run_command([
                'ros2', 'run', 'rehabilitation_robot', 'lower_limb_trainer'
            ], background=True)
            processes.append(lower_proc)

        if args.hardware:
            # Launch joint controller for hardware
            print("Starting joint controller (hardware mode)...")
            controller_proc = run_command([
                'ros2', 'run', 'rehabilitation_robot', 'joint_controller'
            ], background=True)
            processes.append(controller_proc)

        if args.gui:
            # Launch GUI
            print("Starting GUI...")
            gui_proc = run_command([
                'ros2', 'run', 'rehabilitation_robot', 'gui_main'
            ], background=True)
            processes.append(gui_proc)

        if args.voice:
            # Launch voice controller
            print("Starting voice controller...")
            voice_proc = run_command([
                'ros2', 'run', 'rehabilitation_robot', 'voice_controller'
            ], background=True)
            processes.append(voice_proc)

        print("\nAll systems started. Press Ctrl+C to stop.\n")

        # Wait for processes
        for proc in processes:
            proc.wait()

    except KeyboardInterrupt:
        print("\nShutting down...")
        for proc in processes:
            proc.terminate()
            proc.wait()
        print("Done.")


if __name__ == "__main__":
    main()
