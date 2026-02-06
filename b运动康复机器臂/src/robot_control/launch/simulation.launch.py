"""
Launch file for simulation mode
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for simulation."""
    return LaunchDescription([
        # Robot Control (simulation mode)
        Node(
            package='rehabilitation_robot',
            executable='joint_controller',
            name='joint_controller',
            parameters=[{
                'simulation_mode': True
            }],
            output='screen'
        ),

        # Trajectory Planner
        Node(
            package='rehabilitation_robot',
            executable='trajectory_planner',
            name='trajectory_planner',
            output='screen'
        ),

        # Upper Limb Trainer
        Node(
            package='rehabilitation_robot',
            executable='upper_limb_trainer',
            name='upper_limb_trainer',
            parameters=[{
                'config_path': 'src/rehabilitation/config/training_protocols.yaml'
            }],
            output='screen'
        ),

        # Lower Limb Trainer
        Node(
            package='rehabilitation_robot',
            executable='lower_limb_trainer',
            name='lower_limb_trainer',
            parameters=[{
                'config_path': 'src/rehabilitation/config/training_protocols.yaml'
            }],
            output='screen'
        ),

        # Safety Monitor
        Node(
            package='rehabilitation_robot',
            executable='safety_monitor',
            name='safety_monitor',
            output='screen'
        ),

        # Training Manager
        Node(
            package='rehabilitation_robot',
            executable='training_manager',
            name='training_manager',
            output='screen'
        ),
    ])
