#!/usr/bin/env python3
"""
Kinematics Module for Rehabilitation Robot
Provides forward and inverse kinematics for UR5/UR10 robots
"""

import numpy as np
from typing import Tuple, List, Optional
import yaml


class Kinematics:
    """
    Kinematics solver for UR series robots.
    Supports both forward kinematics and analytical inverse kinematics.
    """

    def __init__(self, robot_type: str = "UR5", config_path: str = None):
        """
        Initialize kinematics solver.

        Args:
            robot_type: "UR5" or "UR10"
            config_path: Path to controller_params.yaml
        """
        self.robot_type = robot_type

        # Load DH parameters
        if config_path:
            self._load_config(config_path)
        else:
            self._default_dh_params()

        # Precompute transformation matrices
        self._precompute_matrices()

    def _load_config(self, config_path: str):
        """Load DH parameters from config file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        dh = config['dh_parameters']
        self.a = np.array(dh['a'])
        self.d = np.array(dh['d'])
        self.alpha = np.array(dh['alpha'])

    def _default_dh_params(self):
        """Set default DH parameters for UR5."""
        if self.robot_type == "UR5":
            self.a = np.array([0.0, -0.425, -0.39225, 0.0, 0.0, 0.0])
            self.d = np.array([0.089159, 0.0, 0.0, 0.10915, 0.09456, 0.0823])
            self.alpha = np.array([np.pi/2, 0, 0, np.pi/2, -np.pi/2, 0])
        else:  # UR10
            self.a = np.array([0.0, -0.612, -0.5723, 0.0, 0.0, 0.0])
            self.d = np.array([0.1273, 0.0, 0.0, 0.163941, 0.1157, 0.0922])
            self.alpha = np.array([np.pi/2, 0, 0, np.pi/2, -np.pi/2, 0])

    def _precompute_matrices(self):
        """Precompute constant transformation matrices."""
        self.T_base = np.eye(4)

    def dh_transform(self, theta: float, a: float, d: float, alpha: float) -> np.ndarray:
        """
        Compute DH transformation matrix.

        Args:
            theta: Joint angle (radians)
            a: Link length
            d: Link offset
            alpha: Link twist

        Returns:
            4x4 transformation matrix
        """
        ct = np.cos(theta)
        st = np.sin(theta)
        ca = np.cos(alpha)
        sa = np.sin(alpha)

        T = np.array([
            [ct, -st * ca, st * sa, a * ct],
            [st, ct * ca, -ct * sa, a * st],
            [0, sa, ca, d],
            [0, 0, 0, 1]
        ])
        return T

    def forward_kinematics(self, joint_positions: List[float]) -> np.ndarray:
        """
        Compute forward kinematics (joint angles -> end effector pose).

        Args:
            joint_positions: List of 6 joint angles in radians

        Returns:
            4x4 homogeneous transformation matrix (base to end effector)
        """
        # Validate input
        if len(joint_positions) != 6:
            raise ValueError(f"Expected 6 joint positions, got {len(joint_positions)}")

        T = np.eye(4)
        for i in range(6):
            T_i = self.dh_transform(
                joint_positions[i],
                self.a[i],
                self.d[i],
                self.alpha[i]
            )
            T = T @ T_i

        return T

    def forward_kinematics_partial(self, joint_positions: List[float],
                                   joint_index: int) -> np.ndarray:
        """
        Compute forward kinematics up to specified joint.

        Args:
            joint_positions: List of 6 joint angles
            joint_index: Compute up to this joint (0-5)

        Returns:
            4x4 homogeneous transformation matrix
        """
        T = np.eye(4)
        for i in range(joint_index + 1):
            T_i = self.dh_transform(
                joint_positions[i],
                self.a[i],
                self.d[i],
                self.alpha[i]
            )
            T = T @ T_i

        return T

    def get_jacobian(self, joint_positions: List[float]) -> np.ndarray:
        """
        Compute Jacobian matrix.

        Args:
            joint_positions: List of 6 joint angles

        Returns:
            6x6 Jacobian matrix (first 3 rows linear, last 3 angular)
        """
        n_joints = len(joint_positions)
        J = np.zeros((6, n_joints))

        # Position of end effector
        T_total = self.forward_kinematics(joint_positions)
        p_ee = T_total[:3, 3]

        # Compute Jacobian column by column
        for i in range(n_joints):
            # Position of joint i
            T_i = self.forward_kinematics_partial(joint_positions, i)
            p_i = T_i[:3, 3]

            # Axis of rotation (z-axis of joint frame)
            z_i = T_i[:3, 2]

            # Linear velocity component
            J[:3, i] = np.cross(z_i, p_ee - p_i)

            # Angular velocity component
            J[3:, i] = z_i

        return J

    def inverse_kinematics_analytical(self, target_pose: np.ndarray,
                                      seed: List[float] = None,
                                      joint_limits: dict = None) -> Optional[List[float]]:
        """
        Compute inverse kinematics using analytical method for UR robots.

        Args:
            target_pose: 4x4 target transformation matrix
            seed: Initial seed for iterative methods
            joint_limits: Dictionary with 'min' and 'max' arrays

        Returns:
            List of 6 joint angles or None if no solution
        """
        # UR robots have analytical IK solutions
        # This is a simplified implementation

        # Extract position and orientation
        px, py, pz = target_pose[:3, 3]
        R = target_pose[:3, :3]

        # Wrist position (offset from end effector)
        d_6 = self.d[5]  # Distance from wrist center to end effector
        wrist_offset = d_6

        # Compute wrist center position
        z_axis = R[:, 2]
        wrist_center = np.array([px, py, pz]) - wrist_offset * z_axis

        # Solve for first three joints (position)
        try:
            q1, q2, q3 = self._solve_wrist_position(wrist_center)

            # Solve for last three joints (orientation)
            q4, q5, q6 = self._solve_wrist_orientation(R, q1, q2, q3)

            solution = [q1, q2, q3, q4, q5, q6]

            # Check joint limits if provided
            if joint_limits:
                if not self._check_limits(solution, joint_limits):
                    return None

            return solution

        except Exception as e:
            print(f"IK solution failed: {e}")
            return None

    def _solve_wrist_position(self, wrist_center: np.ndarray) -> Tuple[float, float, float]:
        """
        Solve for first three joints to reach wrist center position.
        Simplified implementation - returns primary solution.
        """
        x, y, z = wrist_center

        # Q1: Shoulder pan angle
        q1 = np.arctan2(y, x)

        # Distance from shoulder to wrist (projected)
        r = np.sqrt(x**2 + y**2) - self.d[3]
        w = z - self.d[0]

        # Distance between shoulder and elbow
        d_12 = self.a[1]
        d_23 = -self.a[2]  # a[2] is negative in UR convention

        # Cosine rule for elbow angle
        D = (r**2 + w**2 - d_12**2 - d_23**2) / (2 * d_12 * d_23)

        # Check for valid solution
        if D < -1 or D > 1:
            raise ValueError("Target position out of reach")

        # Elbow angle (q3) - two solutions possible
        q3 = np.arctan2(-np.sqrt(1 - D**2), D)

        # Shoulder angle (q2)
        gamma = np.arctan2(w, r)
        delta = np.arctan2(d_23 * np.sin(q3), d_12 + d_23 * np.cos(q3))
        q2 = gamma - delta

        return q1, q2, q3

    def _solve_wrist_orientation(self, R: np.ndarray,
                                  q1: float, q2: float, q3: float) -> Tuple[float, float, float]:
        """
        Solve for last three joints to achieve desired orientation.
        Uses analytical solution for UR-series robots.
        """
        # Compute wrist frame orientation based on first three joint angles
        # This is needed to determine wrist pitch, roll, and yaw

        # Q5: Wrist pitch (rotation around Y-axis of wrist frame)
        # Extract from rotation matrix components
        # R[0,2] and R[2,2] relate to pitch angle
        q5 = np.arcsin(np.clip(R[0, 2], -1.0, 1.0))

        # Q4: Wrist roll (rotation around X-axis/tool axis)
        # Depends on q5 to avoid singularity
        if np.abs(np.cos(q5)) > 0.1:
            q4 = np.arctan2(-R[1, 2], R[2, 2])
        else:
            q4 = np.arctan2(R[1, 0], R[0, 0])

        # Q6: Wrist roll 2 (rotation around Z-axis of tool frame)
        q6 = np.arctan2(-R[0, 1], R[0, 0]) if np.abs(np.cos(q5)) > 0.1 else 0.0

        return q4, q5, q6

    def _check_limits(self, solution: List[float], limits: dict) -> bool:
        """Check if solution satisfies joint limits."""
        for i, (val, min_val, max_val) in enumerate(zip(
                solution, limits['min'], limits['max'])):
            if val < min_val[i] or val > max_val[i]:
                return False
        return True

    def compute_workspace(self, resolution: float = 0.05) -> np.ndarray:
        """
        Compute robot workspace points.

        Args:
            resolution: Grid resolution in meters

        Returns:
            Nx3 array of reachable points
        """
        # Simplified workspace computation
        # Full implementation would sample joint space

        max_reach = sum(abs(a) for a in self.a) + sum(abs(d) for d in self.d)

        # Generate points in a sphere
        points = []
        x = np.arange(-max_reach, max_reach, resolution)
        y = np.arange(-max_reach, max_reach, resolution)
        z = np.arange(0, max_reach * 2, resolution)

        for xi in x:
            for yi in y:
                for zi in z:
                    r = np.sqrt(xi**2 + yi**2 + zi**2)
                    if r <= max_reach and r >= min(abs(self.a[1] + self.a[2]), 0.1):
                        points.append([xi, yi, zi])

        return np.array(points)


def main():
    """Test kinematics module."""
    kin = Kinematics("UR5")

    # Test forward kinematics
    home_joints = [0, 0, 0, 0, 0, 0]
    T = kin.forward_kinematics(home_joints)
    print("Home position FK:")
    print(T)

    # Test Jacobian
    J = kin.get_jacobian(home_joints)
    print("\nJacobian at home:")
    print(J)

    # Test workspace
    ws = kin.compute_workspace(0.1)
    print(f"\nWorkspace points: {len(ws)}")


if __name__ == "__main__":
    main()
