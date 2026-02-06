#!/usr/bin/env python3
"""
Trajectory Planner for Rehabilitation Robot
Generates smooth trajectories for rehabilitation exercises
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import yaml


class TrajectoryType(Enum):
    """Types of trajectory interpolation."""
    LINEAR = "linear"
    CUBIC = "cubic"
    QUINTIC = "quintic"
    B_SPLINE = "b_spline"
    TRAPEZOIDAL = "trapezoidal"


@dataclass
class Waypoint:
    """A single waypoint in joint space."""
    positions: np.ndarray
    velocities: np.ndarray = None
    accelerations: np.ndarray = None
    time_from_start: float = 0.0


@dataclass
class Trajectory:
    """A complete trajectory."""
    waypoints: List[Waypoint]
    total_duration: float
    num_joints: int


class TrajectoryPlanner:
    """
    Trajectory planning for rehabilitation movements.
    Generates smooth, safe trajectories for patient exercises.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize trajectory planner.

        Args:
            config_path: Path to controller_params.yaml
        """
        self.load_config(config_path)

    def load_config(self, config_path: str):
        """Load trajectory parameters."""
        if config_path:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            traj = config['trajectory']
            self.interpolation_frequency = traj['interpolation_frequency']
            self.max_velocity = traj['max_velocity']
            self.max_acceleration = traj['max_acceleration']
            self.smoothing_factor = traj['smoothing_factor']
            self.waypoint_tolerance = traj['waypoint_tolerance']
        else:
            # Default parameters
            self.interpolation_frequency = 100.0
            self.max_velocity = 0.5
            self.max_acceleration = 0.3
            self.smoothing_factor = 0.1
            self.waypoint_tolerance = 0.01

    def generate_home_trajectory(self, num_joints: int = 6) -> Trajectory:
        """
        Generate trajectory to home position.

        Args:
            num_joints: Number of robot joints

        Returns:
            Trajectory to home position
        """
        home = np.zeros(num_joints)
        return self.generate_linear_trajectory([home], duration=3.0)

    def generate_linear_trajectory(self,
                                   positions: List[np.ndarray],
                                   velocities: List[np.ndarray] = None,
                                   duration: float = None,
                                   num_joints: int = 6) -> Trajectory:
        """
        Generate linear interpolation trajectory.

        Args:
            positions: List of joint position arrays
            velocities: Optional list of velocity arrays
            duration: Total trajectory duration
            num_joints: Number of joints

        Returns:
            Trajectory with interpolated points
        """
        if not positions:
            raise ValueError("At least one position required")

        if len(positions) < 2:
            # Single point - return as waypoint
            waypoint = Waypoint(
                positions=positions[0],
                time_from_start=0.0
            )
            return Trajectory(
                waypoints=[waypoint],
                total_duration=0.0,
                num_joints=num_joints
            )

        # Calculate duration based on maximum velocity
        if duration is None:
            max_dist = 0.0
            for i in range(1, len(positions)):
                dist = np.max(np.abs(positions[i] - positions[i-1]))
                max_dist = max(max_dist, dist)
            duration = max_dist / (self.max_velocity * 0.5) + 1.0

        # Create waypoints
        waypoints = []
        for i, pos in enumerate(positions):
            t = duration * i / (len(positions) - 1)
            vel = velocities[i] if velocities else np.zeros(num_joints)
            waypoints.append(Waypoint(
                positions=pos,
                velocities=vel,
                time_from_start=t
            ))

        # Interpolate
        return self._interpolate_cubic(waypoints, num_joints)

    def generate_circular_trajectory(self,
                                     center: np.ndarray,
                                     radius: float,
                                     plane: str = "xy",
                                     num_points: int = 50,
                                     num_joints: int = 6) -> Trajectory:
        """
        Generate circular trajectory in task space.

        Args:
            center: Center point of circle [x, y, z]
            radius: Circle radius
            plane: Plane of motion ("xy", "xz", "yz")
            num_points: Number of points in trajectory
            num_joints: Number of joints

        Returns:
            Trajectory as list of joint positions
        """
        angles = np.linspace(0, 2*np.pi, num_points)

        # Generate task space points
        task_points = []
        for angle in angles:
            if plane == "xy":
                point = center + np.array([
                    radius * np.cos(angle),
                    radius * np.sin(angle),
                    0
                ])
            elif plane == "xz":
                point = center + np.array([
                    radius * np.cos(angle),
                    0,
                    radius * np.sin(angle)
                ])
            else:  # yz
                point = center + np.array([
                    0,
                    radius * np.cos(angle),
                    radius * np.sin(angle)
                ])
            task_points.append(point)

        # Convert task space points to joint space using inverse kinematics
        from .kinematics import Kinematics
        kin = Kinematics()

        joint_trajectory = []
        for point in task_points:
            # Create a pose matrix with identity rotation
            # User should specify desired orientation for proper IK
            pose = np.eye(4)
            pose[:3, 3] = point

            # Solve IK - use a neutral orientation for now
            # A full implementation would take orientation as parameter
            neutral_R = np.eye(3)
            pose[:3, :3] = neutral_R

            solution = kin.inverse_kinematics_analytical(pose)
            if solution is not None:
                joint_trajectory.append(np.array(solution))
            else:
                # Fallback: use zeros if IK fails
                joint_trajectory.append(np.zeros(num_joints))

        return self.generate_linear_trajectory(
            joint_trajectory,
            duration=10.0,
            num_joints=num_joints
        )

    def generate_repetitive_trajectory(self,
                                      start_pos: np.ndarray,
                                      end_pos: np.ndarray,
                                      num_reps: int,
                                      hold_time: float = 0.5,
                                      num_joints: int = 6) -> Trajectory:
        """
        Generate repetitive back-and-forth trajectory.

        Args:
            start_pos: Starting joint position
            end_pos: Ending joint position
            num_reps: Number of repetitions
            hold_time: Hold time at each endpoint (seconds)
            num_joints: Number of joints

        Returns:
            Trajectory with repetitive motion
        """
        positions = []
        for rep in range(num_reps):
            if rep % 2 == 0:
                positions.append(start_pos)
                if hold_time > 0:
                    # Add intermediate waypoints for hold
                    positions.append(start_pos.copy())
            else:
                positions.append(end_pos)
                if hold_time > 0:
                    positions.append(end_pos.copy())

        # Add final position
        positions.append(start_pos.copy())

        # Calculate duration
        move_distance = np.max(np.abs(end_pos - start_pos))
        move_time = move_distance / self.max_velocity
        total_duration = num_reps * move_time * 2 + num_reps * hold_time

        return self.generate_linear_trajectory(
            positions,
            duration=total_duration,
            num_joints=num_joints
        )

    def generate_trapezoidal_velocity(self,
                                      start_pos: np.ndarray,
                                      end_pos: np.ndarray,
                                      max_velocity: float = None,
                                      max_acceleration: float = None,
                                      num_joints: int = 6) -> Trajectory:
        """
        Generate trajectory with trapezoidal velocity profile.

        Args:
            start_pos: Starting position
            end_pos: Ending position
            max_velocity: Maximum velocity (use default if None)
            max_acceleration: Maximum acceleration (use default if None)
            num_joints: Number of joints

        Returns:
            Trajectory with trapezoidal velocity profile
        """
        if max_velocity is None:
            max_velocity = self.max_velocity
        if max_acceleration is None:
            max_acceleration = self.max_acceleration

        # Calculate for each joint
        total_duration = 0
        waypoints_list = []

        for j in range(num_joints):
            dist = abs(end_pos[j] - start_pos[j])
            if dist == 0:
                continue

            # Time to accelerate to max velocity
            t_accel = max_velocity / max_acceleration
            dist_accel = 0.5 * max_acceleration * t_accel**2

            # Time to decelerate
            dist_decel = dist_accel
            t_decel = t_accel

            # Distance at constant velocity
            dist_const = dist - dist_accel - dist_decel

            if dist_const < 0:
                # Triangle profile - reduce max velocity
                t_accel = np.sqrt(dist / max_acceleration)
                t_decel = t_accel
                dist_const = 0
                max_velocity_actual = max_acceleration * t_accel
            else:
                max_velocity_actual = max_velocity

            t_const = dist_const / max_velocity_actual if max_velocity_actual > 0 else 0
            total_duration = max(total_duration, 2*t_accel + t_const)

        # Generate waypoints
        waypoints = []

        # Initial point
        waypoints.append(Waypoint(
            positions=start_pos,
            velocities=np.zeros(num_joints),
            time_from_start=0.0
        ))

        # Midpoint (if applicable)
        mid_pos = (start_pos + end_pos) / 2
        waypoints.append(Waypoint(
            positions=mid_pos,
            velocities=np.zeros(num_joints),
            time_from_start=total_duration / 2
        ))

        # Final point
        waypoints.append(Waypoint(
            positions=end_pos,
            velocities=np.zeros(num_joints),
            time_from_start=total_duration
        ))

        return self._interpolate_cubic(waypoints, num_joints)

    def _interpolate_cubic(self,
                           waypoints: List[Waypoint],
                           num_joints: int) -> Trajectory:
        """
        Cubic spline interpolation between waypoints.

        Args:
            waypoints: List of waypoints with constraints
            num_joints: Number of joints

        Returns:
            Smooth interpolated trajectory
        """
        if len(waypoints) < 2:
            return Trajectory(
                waypoints=waypoints,
                total_duration=waypoints[0].time_from_start if waypoints else 0.0,
                num_joints=num_joints
            )

        # Create time array for sampling
        total_duration = waypoints[-1].time_from_start
        n_samples = int(total_duration * self.interpolation_frequency) + 1
        t = np.linspace(0, total_duration, n_samples)

        # Interpolate each joint separately
        interpolated_positions = np.zeros((n_samples, num_joints))
        interpolated_velocities = np.zeros((n_samples, num_joints))
        interpolated_accelerations = np.zeros((n_samples, num_joints))

        waypoint_times = [w.time_from_start for w in waypoints]

        for j in range(num_joints):
            # Extract joint trajectory
            q = np.array([w.positions[j] for w in waypoints])
            v = np.array([w.velocities[j] if w.velocities is not None else 0
                         for w in waypoints]) if waypoints[0].velocities is not None else None

            # Cubic interpolation
            if v is not None:
                coeff = self._cubic_coefficients(waypoint_times, q, v)
            else:
                coeff = self._natural_cubic(waypoint_times, q)

            # Evaluate at sample times
            for i, ti in enumerate(t):
                q_i, v_i, a_i = self._evaluate_cubic(ti, waypoint_times, coeff, j)
                interpolated_positions[i, j] = q_i
                interpolated_velocities[i, j] = v_i
                interpolated_accelerations[i, j] = a_i

        # Convert to waypoint format
        result_waypoints = []
        for i in range(n_samples):
            result_waypoints.append(Waypoint(
                positions=interpolated_positions[i],
                velocities=interpolated_velocities[i],
                accelerations=interpolated_accelerations[i],
                time_from_start=t[i]
            ))

        return Trajectory(
            waypoints=result_waypoints,
            total_duration=total_duration,
            num_joints=num_joints
        )

    def _cubic_coefficients(self,
                            t: List[float],
                            q: np.ndarray,
                            v: np.ndarray) -> np.ndarray:
        """
        Compute cubic spline coefficients.

        Args:
            t: Waypoint times
            q: Position values
            v: Velocity values

        Returns:
            Coefficient matrix
        """
        n = len(t) - 1
        coeff = np.zeros((n, 4))

        for i in range(n):
            dt = t[i+1] - t[i]
            coeff[i, 0] = q[i]
            coeff[i, 1] = v[i]
            coeff[i, 2] = (3*(q[i+1] - q[i])/dt**2 - 2*v[i]/dt - v[i+1]/dt)
            coeff[i, 3] = (-2*(q[i+1] - q[i])/dt**3 + (v[i] + v[i+1])/dt**2)

        return coeff

    def _natural_cubic(self,
                       t: List[float],
                       q: np.ndarray) -> np.ndarray:
        """
        Compute natural cubic spline (velocity-free).

        Args:
            t: Waypoint times
            q: Position values

        Returns:
            Coefficient matrix
        """
        n = len(t) - 1
        h = np.diff(t)

        # Build tridiagonal system
        A = np.zeros((n+1, n+1))
        b = np.zeros(n+1)

        A[0, 0] = 1
        A[n, n] = 1

        for i in range(1, n):
            A[i, i-1] = h[i-1]
            A[i, i] = 2 * (h[i-1] + h[i])
            A[i, i+1] = h[i]

            b[i] = 3 * (q[i+1] - q[i]) / h[i] - 3 * (q[i] - q[i-1]) / h[i-1]

        # Solve for second derivatives
        z = np.linalg.solve(A, b)

        # Compute coefficients
        coeff = np.zeros((n, 4))
        for i in range(n):
            dt = t[i+1] - t[i]
            coeff[i, 0] = q[i]
            coeff[i, 1] = z[i]
            coeff[i, 2] = (3*(q[i+1] - q[i])/dt**2 - 2*z[i]/dt - z[i+1]/dt)
            coeff[i, 3] = (-2*(q[i+1] - q[i])/dt**3 + (z[i] + z[i+1])/dt**2)

        return coeff

    def _evaluate_cubic(self,
                        t: float,
                        waypoint_times: List[float],
                        coeff: np.ndarray,
                        joint_idx: int) -> Tuple[float, float, float]:
        """
        Evaluate cubic spline at given time.

        Args:
            t: Query time
            waypoint_times: List of waypoint times
            coeff: Coefficient matrix
            joint_idx: Joint index

        Returns:
            Position, velocity, acceleration at time t
        """
        # Find segment
        n = len(waypoint_times) - 1
        for i in range(n):
            if t >= waypoint_times[i] and t <= waypoint_times[i+1]:
                dt = t - waypoint_times[i]
                c = coeff[i]

                pos = c[0] + c[1]*dt + c[2]*dt**2 + c[3]*dt**3
                vel = c[1] + 2*c[2]*dt + 3*c[3]*dt**2
                acc = 2*c[2] + 6*c[3]*dt

                return pos, vel, acc

        # Out of range - return last point
        last_coeff = coeff[-1]
        dt = waypoint_times[-1] - waypoint_times[-2]
        c = last_coeff

        pos = c[0] + c[1]*dt + c[2]*dt**2 + c[3]*dt**3
        vel = c[1] + 2*c[2]*dt + 3*c[3]*dt**2
        acc = 2*c[2] + 6*c[3]*dt

        return pos, vel, acc

    def smooth_trajectory(self,
                         trajectory: Trajectory,
                         smoothing_factor: float = None) -> Trajectory:
        """
        Apply smoothing to trajectory.

        Args:
            trajectory: Input trajectory
            smoothing_factor: Smoothing strength (0-1, lower is smoother)

        Returns:
            Smoothed trajectory
        """
        if smoothing_factor is None:
            smoothing_factor = self.smoothing_factor

        positions = np.array([w.positions for w in trajectory.waypoints])
        n = len(positions)

        if n < 3:
            return trajectory

        # Simple moving average smoothing
        smoothed = positions.copy()
        for i in range(1, n-1):
            smoothed[i] = (1 - smoothing_factor) * positions[i] + \
                          smoothing_factor * 0.5 * (positions[i-1] + positions[i+1])

        # Create new waypoints
        new_waypoints = []
        for i, w in enumerate(trajectory.waypoints):
            new_waypoints.append(Waypoint(
                positions=smoothed[i],
                velocities=w.velocities,
                accelerations=w.accelerations,
                time_from_start=w.time_from_start
            ))

        return Trajectory(
            waypoints=new_waypoints,
            total_duration=trajectory.total_duration,
            num_joints=trajectory.num_joints
        )


def main():
    """Test trajectory planner."""
    planner = TrajectoryPlanner()

    # Test linear trajectory
    start = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    end = np.array([0.5, 0.5, 0.5, 0.0, 0.0, 0.0])

    traj = planner.generate_linear_trajectory(
        [start, end],
        duration=5.0,
        num_joints=6
    )

    print(f"Trajectory generated: {len(traj.waypoints)} waypoints")
    print(f"Duration: {traj.total_duration:.2f}s")
    print(f"First waypoint: {traj.waypoints[0].positions}")
    print(f"Last waypoint: {traj.waypoints[-1].positions}")


if __name__ == "__main__":
    main()
