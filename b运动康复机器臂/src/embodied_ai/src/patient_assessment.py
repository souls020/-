#!/usr/bin/env python3
"""
Patient Assessment Module
AI-powered patient state assessment for rehabilitation
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
import time


class AssessmentType(Enum):
    """Types of patient assessments."""
    MUSCLE_STRENGTH = "muscle_strength"
    RANGE_OF_MOTION = "range_of_motion"
    FATIGUE_LEVEL = "fatigue_level"
    PAIN_LEVEL = "pain_level"
    SPASTICITY = "spasticity"
    COORDINATION = "coordination"
    OVERALL_STATE = "overall_state"


@dataclass
class PatientState:
    """Complete patient state assessment."""
    timestamp: float
    muscle_strength: np.ndarray  # Per joint/muscle group
    range_of_motion: np.ndarray  # Per joint
    fatigue_level: float  # 0-1 scale
    pain_level: float  # 0-1 scale
    spasticity: np.ndarray  # Per joint
    coordination_score: float  # 0-1 scale
    comfort_level: float  # 0-1 scale
    voluntary_effort: float  # 0-1 scale


@dataclass
class AssessmentResult:
    """Result of a single assessment."""
    assessment_type: AssessmentType
    score: float  # 0-1 normalized
    confidence: float  # 0-1 confidence level
    details: Dict
    recommendations: List[str]


class PatientAssessment:
    """
    AI-powered patient assessment system.
    Evaluates patient state during rehabilitation sessions.
    """

    def __init__(self, num_joints: int = 6):
        """
        Initialize patient assessment.

        Args:
            num_joints: Number of robot/joint interfaces
        """
        self.num_joints = num_joints

        # Baseline measurements (updated over time)
        self.baseline_strength = np.ones(num_joints) * 0.5
        self.baseline_rom = np.ones(num_joints) * np.pi  # Full ROM

        # Historical data
        self.assessment_history: List[PatientState] = []
        self.strength_history: List[np.ndarray] = []
        self.rom_history: List[np.ndarray] = []
        self.fatigue_history: List[float] = []

        # Assessment thresholds
        self.fatigue_threshold = 0.7
        self.pain_threshold = 0.5
        self.strength_improvement_threshold = 0.1

        # Model weights (could be loaded from trained model)
        self.fatigue_weights = np.array([0.2, 0.3, 0.2, 0.1, 0.1, 0.1])

    def assess_from_movement(self,
                            joint_positions: np.ndarray,
                            joint_velocities: np.ndarray,
                            joint_efforts: np.ndarray,
                            target_positions: np.ndarray) -> PatientState:
        """
        Assess patient state from movement data.

        Args:
            joint_positions: Current joint positions
            joint_velocities: Current joint velocities
            joint_efforts: Current joint efforts/torques
            target_positions: Target positions

        Returns:
            Complete patient state
        """
        # Calculate tracking error
        tracking_error = np.abs(joint_positions - target_positions)

        # Estimate strength (higher effort for same movement = lower strength)
        effort_normalized = np.clip(joint_efforts / 100.0, 0, 1)
        velocity_normalized = np.clip(np.abs(joint_velocities) / 2.0, 0, 1)

        # Strength estimate: can move at good speed with moderate effort
        strength_estimate = np.where(
            velocity_normalized > 0.1,
            np.clip(effort_normalized / (velocity_normalized + 0.1), 0, 1),
            0.5
        )

        # ROM assessment
        rom_estimate = np.zeros(self.num_joints)
        if len(self.rom_history) >= 10:
            # 获取最近10次记录
            recent_roms = np.array(self.rom_history[-10:])
            for i in range(self.num_joints):
                # 对每个关节计算ROM范围
                min_pos = np.min(recent_roms[:, i])
                max_pos = np.max(recent_roms[:, i])
                rom_range = max_pos - min_pos
                # 与基线ROM比较，避免除以零
                if self.baseline_rom[i] > 1e-6:
                    rom_estimate[i] = np.clip(rom_range / self.baseline_rom[i], 0, 1)
                else:
                    rom_estimate[i] = 0.5
        else:
            # 数据不足时使用默认值
            rom_estimate = np.ones(self.num_joints) * 0.5

        # Fatigue assessment
        recent_fatigue = self.fatigue_history[-60:] if len(self.fatigue_history) >= 60 else self.fatigue_history
        fatigue_estimate = np.mean(recent_fatigue) if recent_fatigue else 0.0

        # Effort assessment (voluntary vs assisted)
        voluntary_effort = np.mean(1.0 - effort_normalized)

        # Create state
        state = PatientState(
            timestamp=time.time(),
            muscle_strength=strength_estimate,
            range_of_motion=rom_estimate,
            fatigue_level=fatigue_estimate,
            pain_level=0.0,  # Would need patient input
            spasticity=np.zeros(self.num_joints),
            coordination_score=self._assess_coordination(joint_velocities),
            comfort_level=1.0 - fatigue_estimate,
            voluntary_effort=voluntary_effort
        )

        # Store for history
        self.assessment_history.append(state)
        self.strength_history.append(strength_estimate)
        self.rom_history.append(joint_positions.copy())
        self.fatigue_history.append(fatigue_estimate)

        return state

    def assess_strength(self,
                        patient_effort: np.ndarray,
                        robot_assistance: np.ndarray,
                        movement_quality: np.ndarray) -> AssessmentResult:
        """
        Assess muscle strength.

        Args:
            patient_effort: Patient effort level (0-1)
            robot_assistance: Robot assistance level (0-1)
            movement_quality: Quality of movement (0-1)

        Returns:
            Assessment result
        """
        # Strength = patient effort * movement quality / (1 - assistance)
        assistance_factor = np.clip(1.0 - robot_assistance + 0.1, 0.1, 1.0)
        strength = np.mean(patient_effort * movement_quality / assistance_factor)

        confidence = np.std(patient_effort) * 0.5 + 0.5

        recommendations = []
        if strength < 0.3:
            recommendations.append("Increase passive assistance")
            recommendations.append("Reduce range of motion")
        elif strength < 0.6:
            recommendations.append("Maintain active-assisted mode")
            recommendations.append("Consider resistance training")
        else:
            recommendations.append("Progress to active-resisted training")

        return AssessmentResult(
            assessment_type=AssessmentType.MUSCLE_STRENGTH,
            score=strength,
            confidence=confidence,
            details={
                'per_joint': patient_effort.tolist(),
                'assistance_used': robot_assistance.tolist()
            },
            recommendations=recommendations
        )

    def assess_rom(self,
                   achieved_positions: np.ndarray,
                   target_positions: np.ndarray,
                   joint_limits: Dict) -> AssessmentResult:
        """
        Assess range of motion.

        Args:
            achieved_positions: Positions actually achieved
            target_positions: Target positions
            joint_limits: Joint limits

        Returns:
            Assessment result
        """
        # ROM percentage = achieved / target * 100
        rom_percentage = np.zeros(self.num_joints)
        for i in range(self.num_joints):
            target_val = abs(target_positions[i])
            achieved_val = abs(achieved_positions[i])
            # Avoid division by zero with a small epsilon
            if target_val > 1e-6:
                rom_percentage[i] = np.clip(achieved_val / target_val, 0, 1)
            else:
                # If target is near zero, check if achieved is also near zero
                rom_percentage[i] = 1.0 if achieved_val < 1e-3 else 0.0

        avg_rom = np.mean(rom_percentage)
        confidence = 0.9  # High confidence from direct measurement

        recommendations = []
        if avg_rom < 0.5:
            recommendations.append("Start with smaller ROM")
            recommendations.append("Focus on flexibility exercises")
        elif avg_rom < 0.8:
            recommendations.append("Gradually increase ROM")
            recommendations.append("Monitor patient tolerance")
        else:
            recommendations.append("ROM within normal limits")
            recommendations.append("Consider increasing difficulty")

        return AssessmentResult(
            assessment_type=AssessmentType.RANGE_OF_MOTION,
            score=avg_rom,
            confidence=confidence,
            details={
                'per_joint': rom_percentage.tolist(),
                'target': target_positions.tolist()
            },
            recommendations=recommendations
        )

    def assess_fatigue(self,
                       effort_history: List[np.ndarray],
                       velocity_history: List[np.ndarray],
                       time_threshold: float = 300.0) -> AssessmentResult:
        """
        Assess patient fatigue level.

        Args:
            effort_history: Historical effort measurements
            velocity_history: Historical velocity measurements
            time_threshold: Time window in seconds

        Returns:
            Assessment result
        """
        if len(effort_history) < 10:
            return AssessmentResult(
                assessment_type=AssessmentType.FATIGUE_LEVEL,
                score=0.0,
                confidence=0.0,
                details={'message': 'Insufficient data'},
                recommendations=[]
            )

        # Calculate fatigue trend
        recent_effort = np.mean(effort_history[-60:], axis=0)
        earlier_effort = np.mean(effort_history[-120:-60], axis=0) if len(effort_history) >= 120 else recent_effort

        # Increasing effort with same velocity = fatigue
        effort_increase = recent_effort - earlier_effort
        fatigue_score = np.clip(np.mean(recent_effort) + effort_increase * 0.5, 0, 1)

        # Trend analysis
        if len(effort_history) >= 180:
            trend = np.polyfit(range(180), [np.mean(e) for e in effort_history[-180:]], 1)[0]
            fatigue_score += trend * 0.3

        confidence = min(0.5 + len(effort_history) / 1000, 0.95)

        recommendations = []
        if fatigue_score > 0.7:
            recommendations.append("REST REQUIRED: High fatigue detected")
            recommendations.append("Reduce training intensity")
            recommendations.append("Consider ending session")
        elif fatigue_score > 0.5:
            recommendations.append("Monitor fatigue closely")
            recommendations.append("Reduce speed or ROM")
            recommendations.append("Increase rest periods")
        elif fatigue_score > 0.3:
            recommendations.append("Fatigue at moderate level")
            recommendations.append("Continue with current parameters")
        else:
            recommendations.append("Low fatigue - good performance")

        return AssessmentResult(
            assessment_type=AssessmentType.FATIGUE_LEVEL,
            score=min(fatigue_score, 1.0),
            confidence=confidence,
            details={
                'current_effort': np.mean(recent_effort),
                'effort_trend': float(np.mean(effort_increase))
            },
            recommendations=recommendations
        )

    def _assess_coordination(self, velocities: np.ndarray) -> float:
        """
        Assess movement coordination from velocity profile.

        Args:
            velocities: Joint velocities

        Returns:
            Coordination score (0-1)
        """
        # Smooth velocities = better coordination
        vel_magnitude = np.linalg.norm(velocities)
        if vel_magnitude < 0.01:
            return 0.5

        # Variance across joints (lower = more coordinated)
        variance = np.var(velocities / (vel_magnitude + 0.001))
        coordination = np.exp(-variance * 10)

        return coordination

    def update_baseline(self, new_state: PatientState):
        """Update baseline measurements from new assessment."""
        # Moving average for baseline
        alpha = 0.1
        self.baseline_strength = alpha * new_state.muscle_strength + (1 - alpha) * self.baseline_strength
        self.baseline_rom = alpha * new_state.range_of_motion + (1 - alpha) * self.baseline_rom

    def get_progress_report(self) -> Dict:
        """
        Generate progress report from history.

        Returns:
            Progress report dictionary
        """
        if len(self.strength_history) < 2:
            return {'message': 'Insufficient data for progress report'}

        # Strength trend
        strength_start = np.mean(self.strength_history[:10], axis=0) if len(self.strength_history) >= 10 else self.strength_history[0]
        strength_end = np.mean(self.strength_history[-10:], axis=0)
        strength_change = strength_end - strength_start

        # Fatigue trend
        fatigue_start = np.mean(self.fatigue_history[:60]) if len(self.fatigue_history) >= 60 else self.fatigue_history[0]
        fatigue_end = np.mean(self.fatigue_history[-60:])
        fatigue_change = fatigue_end - fatigue_start

        return {
            'strength_change': strength_change.tolist(),
            'overall_strength_improvement': float(np.mean(strength_change)),
            'fatigue_trend': float(fatigue_change),
            'assessments_count': len(self.assessment_history),
            'recommendations': self._generate_recommendations(strength_change, fatigue_change)
        }

    def _generate_recommendations(self,
                                   strength_change: np.ndarray,
                                   fatigue_change: float) -> List[str]:
        """Generate recommendations based on progress."""
        recommendations = []

        avg_improvement = np.mean(strength_change)

        if avg_improvement > 0.1:
            recommendations.append("Excellent progress in strength!")
            recommendations.append("Consider advancing to next difficulty level")
        elif avg_improvement > 0.05:
            recommendations.append("Good progress - continue current protocol")
        elif avg_improvement < -0.05:
            recommendations.append("Strength decreased - review training parameters")
            recommendations.append("Ensure adequate rest between sessions")

        if fatigue_change > 0.2:
            recommendations.append("Fatigue increasing - reduce intensity")
        elif fatigue_change < -0.1:
            recommendations.append("Fatigue decreasing - patient adapting well")

        return recommendations
