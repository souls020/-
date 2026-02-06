"""
Tests for robot control module
"""

import pytest
import numpy as np
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from kinematics import Kinematics
from trajectory_planner import TrajectoryPlanner, TrajectoryType


class TestKinematics:
    """Tests for kinematics module."""

    @pytest.fixture
    def kinematics(self):
        """Create kinematics instance."""
        return Kinematics("UR5")

    def test_forward_kinematics_home(self, kinematics):
        """Test FK at home position."""
        joints = [0, 0, 0, 0, 0, 0]
        T = kinematics.forward_kinematics(joints)

        # Should return 4x4 matrix
        assert T.shape == (4, 4)
        # Should be homogeneous
        assert np.allclose(T[3, :], [0, 0, 0, 1])

    def test_jacobian_shape(self, kinematics):
        """Test Jacobian matrix shape."""
        joints = [0, 0, 0, 0, 0, 0]
        J = kinematics.get_jacobian(joints)

        # Should be 6x6
        assert J.shape == (6, 6)

    def test_jacobian_symmetric(self, kinematics):
        """Test Jacobian properties."""
        joints = [0.1, 0.2, 0.3, 0.1, 0.2, 0.1]
        J = kinematics.get_jacobian(joints)

        # Jacobian should have correct rank for valid configuration
        rank = np.linalg.matrix_rank(J)
        assert rank >= 5  # At least 5 DOF should be observable

    def test_workspace_computation(self, kinematics):
        """Test workspace computation."""
        ws = kinematics.compute_workspace(resolution=0.1)

        # Should return array
        assert isinstance(ws, np.ndarray)
        assert ws.shape[1] == 3  # x, y, z


class TestTrajectoryPlanner:
    """Tests for trajectory planner."""

    @pytest.fixture
    def planner(self):
        """Create planner instance."""
        return TrajectoryPlanner()

    def test_linear_trajectory(self, planner):
        """Test linear trajectory generation."""
        start = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        end = np.array([0.5, 0.5, 0.5, 0.0, 0.0, 0.0])

        traj = planner.generate_linear_trajectory(
            [start, end],
            duration=5.0,
            num_joints=6
        )

        assert traj.total_duration > 0
        assert len(traj.waypoints) > 0
        assert traj.num_joints == 6

    def test_home_trajectory(self, planner):
        """Test home trajectory generation."""
        traj = planner.generate_home_trajectory(num_joints=6)

        assert traj.num_joints == 6

    def test_repetitive_trajectory(self, planner):
        """Test repetitive trajectory."""
        start = np.zeros(6)
        end = np.array([0.5, 0.5, 0.0, 0.0, 0.0, 0.0])

        traj = planner.generate_repetitive_trajectory(
            start, end,
            num_reps=5,
            num_joints=6
        )

        # Should have waypoints for each rep
        assert len(traj.waypoints) > 5

    def test_trapezoidal_velocity(self, planner):
        """Test trapezoidal velocity profile."""
        start = np.zeros(6)
        end = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])

        traj = planner.generate_trapezoidal_velocity(start, end)

        assert traj.total_duration > 0

    def test_smooth_trajectory(self, planner):
        """Test trajectory smoothing."""
        start = np.zeros(6)
        end = np.array([0.5, 0.5, 0.5, 0.0, 0.0, 0.0])

        traj = planner.generate_linear_trajectory(
            [start, end],
            duration=5.0,
            num_joints=6
        )

        smoothed = planner.smooth_trajectory(traj)

        assert len(smoothed.waypoints) == len(traj.waypoints)


class TestAdaptiveController:
    """Tests for adaptive controller."""

    @pytest.fixture
    def controller(self):
        """Create adaptive controller."""
        from adaptive_controller import AdaptiveController
        return AdaptiveController()

    def test_initial_parameters(self, controller):
        """Test initial parameters."""
        params = controller.get_parameters()

        assert 'rom_percentage' in params
        assert 'speed' in params
        assert 'assistance_level' in params

    def test_update_warmup(self, controller):
        """Test warmup phase update."""
        patient_state = {'fatigue': 0.0, 'effort': 0.5, 'comfort': 1.0}
        performance = {'tracking_error': 0.1}

        params = controller.update(patient_state, performance, 'warmup')

        # Warmup should have high assistance
        assert params['assistance_level'] > 0.8

    def test_update_training(self, controller):
        """Test training phase update."""
        patient_state = {'fatigue': 0.3, 'effort': 0.5, 'comfort': 0.8}
        performance = {'tracking_error': 0.1}

        params = controller.update(patient_state, performance, 'training')

        assert params['rom_percentage'] > 0
        assert params['speed'] > 0

    def test_reset(self, controller):
        """Test controller reset."""
        # Update first
        controller.update(
            {'fatigue': 0.8, 'effort': 0.5, 'comfort': 0.5},
            {'tracking_error': 0.2},
            'training'
        )

        # Reset
        controller.reset()

        params = controller.get_parameters()
        assert params['assistance_level'] == 0.5


class TestPatientAssessment:
    """Tests for patient assessment."""

    @pytest.fixture
    def assessment(self):
        """Create assessment instance."""
        from patient_assessment import PatientAssessment
        return PatientAssessment(num_joints=6)

    def test_assess_from_movement(self, assessment):
        """Test movement-based assessment."""
        joints = np.array([0.1, 0.2, 0.3, 0.1, 0.2, 0.1])
        velocities = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        efforts = np.array([10, 15, 12, 5, 5, 5])
        target = np.array([0.15, 0.25, 0.35, 0.1, 0.2, 0.1])

        state = assessment.assess_from_movement(joints, velocities, efforts, target)

        assert state.fatigue_level >= 0
        assert state.voluntary_effort >= 0

    def test_assess_fatigue(self, assessment):
        """Test fatigue assessment."""
        effort_history = [np.random.rand(6) * 50 + 10 for _ in range(100)]
        velocity_history = [np.random.rand(6) * 0.2 for _ in range(100)]

        result = assessment.assess_fatigue(effort_history, velocity_history)

        assert result.assessment_type.value == "fatigue_level"
        assert 0 <= result.score <= 1

    def test_progress_report(self, assessment):
        """Test progress report generation."""
        # Add some history
        for _ in range(20):
            assessment.strength_history.append(np.random.rand(6) * 0.5 + 0.3)
            assessment.fatigue_history.append(np.random.rand() * 0.5)

        report = assessment.get_progress_report()

        assert 'strength_change' in report
        assert 'recommendations' in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
