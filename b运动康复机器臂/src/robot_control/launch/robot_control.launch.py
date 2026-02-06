"""
Launch file for robot control system
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument


def generate_launch_description():
    """Generate launch description for robot control."""
    return LaunchDescription([
        # Joint Controller
        Node(
            package='rehabilitation_robot',
            executable='joint_controller',
            name='joint_controller',
            parameters=[{
                'config_path': 'src/robot_control/config/controller_params.yaml'
            }],
            output='screen'
        ),

        # Trajectory Planner
        Node(
            package='rehabilitation_robot',
            executable='trajectory_planner',
            name='trajectory_planner',
            parameters=[{
                'config_path': 'src/robot_control/config/controller_params.yaml'
            }],
            output='screen'
        ),

        # Kinematics Service
        Node(
            package='rehabilitation_robot',
            executable='kinematics',
            name='kinematics',
            output='screen'
        ),
    ])
