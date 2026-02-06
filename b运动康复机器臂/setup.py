from setuptools import find_packages, setup
import os

package_name = 'rehabilitation_robot'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', [
            'src/robot_control/config/controller_params.yaml',
            'src/rehabilitation/config/training_protocols.yaml'
        ]),
        ('share/' + package_name + '/launch', [
            'src/robot_control/launch/robot_control.launch.py',
            'src/robot_control/launch/simulation.launch.py'
        ]),
    ],
    install_requires=[
        'numpy>=1.24.0',
        'scipy>=1.11.0',
        'torch>=2.0.0',
        'scikit-learn>=1.3.0',
        'pyyaml>=6.0',
        'matplotlib>=3.7.0',
    ],
    zip_safe=True,
    maintainer='Development Team',
    maintainer_email='developer@rehabrobot.org',
    description='Embodied AI Rehabilitation Robot System',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'joint_controller = robot_control.src.joint_controller:main',
            'trajectory_planner = robot_control.src.trajectory_planner:main',
            'kinematics = robot_control.src.kinematics:main',
            'upper_limb_trainer = rehabilitation.src.upper_limb_trainer:main',
            'lower_limb_trainer = rehabilitation.src.lower_limb_trainer:main',
            'training_manager = rehabilitation.src.training_manager:main',
            'patient_assessment = embodied_ai.src.patient_assessment:main',
            'adaptive_controller = embodied_ai.src.adaptive_controller:main',
            'safety_monitor = safety.src.safety_monitor:main',
            'gui_main = human_interaction.gui.main_window:main',
            'voice_controller = human_interaction.voice.voice_controller:main',
        ],
    },
)
