#!/usr/bin/env python3
"""
Adaptive Controller
Self-adjusting controller for personalized rehabilitation
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
import time


@dataclass
class AdaptationConfig:
    """Configuration for adaptive control."""
    adaptation_rate: float = 0.1
    min_rom_percentage: float = 0.5
    max_rom_percentage: float = 1.0
    min_speed: float = 0.1
    max_speed: float = 0.8
    min_assistance: float = 0.0
    max_assistance: float = 1.0
    fatigue_recovery_factor: float = 0.8
    improvement_threshold: float = 0.1


class AdaptiveController:
    """
    Adaptive controller that adjusts training parameters based on patient state.
    Implements personalized rehabilitation based on real-time assessment.
    """

    def __init__(self, config: AdaptationConfig = None):
        """
        Initialize adaptive controller.

        Args:
            config: Adaptation configuration
        """
        self.config = config if config else AdaptationConfig()

        # Current control parameters
        self.current_rom = 0.8  # Percentage of full ROM
        self.current_speed = 0.3
        self.current_assistance = 0.5
        self.current_resistance = 0.0

        # Patient model (learned over time)
        self.patient_model = {
            'strength_trend': np.zeros(6),
            'fatigue_trend': 0.0,
            'optimal_rom': 0.8,
            'optimal_speed': 0.3,
            'fatigue_threshold': 0.7,
            'learning_rate': 0.01
        }

        # History for adaptation
        self.performance_history: List[Dict] = []
        self.state_history: List[Dict] = []

        # Control limits
        self.limits = {
            'rom': {'min': self.config.min_rom_percentage, 'max': self.config.max_rom_percentage},
            'speed': {'min': self.config.min_speed, 'max': self.config.max_speed},
            'assistance': {'min': self.config.min_assistance, 'max': self.config.max_assistance}
        }

    def update(self,
               patient_state: Dict,
               performance: Dict,
               training_phase: str = 'training') -> Dict:
        """
        Update control parameters based on patient state and performance.

        Args:
            patient_state: Current patient state dict
            performance: Recent performance metrics
            training_phase: Current phase (warmup, training, cooldown)

        Returns:
            Updated control parameters
        """
        # Update patient model
        self._update_patient_model(patient_state, performance)

        # Adjust based on phase
        if training_phase == 'warmup':
            self._adjust_for_warmup()
        elif training_phase == 'training':
            self._adjust_for_training(patient_state, performance)
        elif training_phase == 'cooldown':
            self._adjust_for_cooldown()

        # Apply safety constraints
        self._apply_safety_constraints(patient_state)

        # Store state
        self.state_history.append({
            'timestamp': time.time(),
            'rom': self.current_rom,
            'speed': self.current_speed,
            'assistance': self.current_assistance,
            'patient_state': patient_state
        })

        return self.get_parameters()

    def _update_patient_model(self, patient_state: Dict, performance: Dict):
        """Update internal patient model."""
        # Update strength model
        if 'strength' in patient_state:
            current_strength = np.array(patient_state['strength'])
            self.patient_model['strength_trend'] = (
                self.patient_model['learning_rate'] * current_strength +
                (1 - self.patient_model['learning_rate']) * self.patient_model['strength_trend']
            )

        # Update fatigue model
        if 'fatigue' in patient_state:
            current_fatigue = patient_state['fatigue']
            self.patient_model['fatigue_trend'] = (
                self.patient_model['learning_rate'] * current_fatigue +
                (1 - self.patient_model['learning_rate']) * self.patient_model['fatigue_trend']
            )

        # Update optimal parameters based on performance
        if 'tracking_error' in performance:
            error = performance['tracking_error']
            if error < 0.05:  # Good performance
                # Increase difficulty slightly
                self.patient_model['optimal_rom'] = min(
                    self.patient_model['optimal_rom'] + 0.01, 1.0
                )
                self.patient_model['optimal_speed'] = min(
                    self.patient_model['optimal_speed'] + 0.01, self.limits['speed']['max']
                )
            elif error > 0.2:  # Poor performance
                # Decrease difficulty
                self.patient_model['optimal_rom'] = max(
                    self.patient_model['optimal_rom'] - 0.02, self.limits['rom']['min']
                )
                self.patient_model['optimal_speed'] = max(
                    self.patient_model['optimal_speed'] - 0.02, self.limits['speed']['min']
                )

    def _adjust_for_warmup(self):
        """Adjust parameters for warmup phase."""
        # Warmup: slower speed, full assistance
        self.current_rom = 0.5
        self.current_speed = 0.2
        self.current_assistance = 1.0
        self.current_resistance = 0.0

    def _adjust_for_training(self, patient_state: Dict, performance: Dict):
        """Adjust parameters during training."""
        # Get fatigue level
        fatigue = patient_state.get('fatigue', 0.0)
        effort = patient_state.get('effort', 0.5)
        comfort = patient_state.get('comfort', 1.0)

        # Adjust ROM based on patient state
        if fatigue > self.patient_model['fatigue_threshold']:
            # Reduce ROM when fatigued
            target_rom = self.patient_model['optimal_rom'] * self.config.fatigue_recovery_factor
        else:
            target_rom = self.patient_model['optimal_rom']

        # Adjust speed based on comfort
        if comfort < 0.5:
            target_speed = self.current_speed * 0.8
        elif comfort > 0.8:
            target_speed = min(
                self.current_speed * 1.1,
                self.patient_model['optimal_speed']
            )
        else:
            target_speed = self.patient_model['optimal_speed']

        # Adjust assistance based on effort and performance
        tracking_error = performance.get('tracking_error', 0.1)
        if tracking_error > 0.15:
            # Poor tracking - increase assistance
            target_assistance = min(self.current_assistance + 0.1, 1.0)
        elif tracking_error < 0.05 and effort > 0.7:
            # Good tracking with high effort - reduce assistance
            target_assistance = max(self.current_assistance - 0.05, 0.0)
        else:
            target_assistance = self.current_assistance

        # Smooth transitions
        alpha = self.config.adaptation_rate
        self.current_rom = (1 - alpha) * self.current_rom + alpha * target_rom
        self.current_speed = (1 - alpha) * self.current_speed + alpha * target_speed
        self.current_assistance = (1 - alpha) * self.current_assistance + alpha * target_assistance

        # Clamp to limits
        self.current_rom = np.clip(
            self.current_rom, self.limits['rom']['min'], self.limits['rom']['max']
        )
        self.current_speed = np.clip(
            self.current_speed, self.limits['speed']['min'], self.limits['speed']['max']
        )
        self.current_assistance = np.clip(
            self.current_assistance, self.limits['assistance']['min'], self.limits['assistance']['max']
        )

    def _adjust_for_cooldown(self):
        """Adjust parameters for cooldown phase."""
        self.current_rom = 0.3
        self.current_speed = 0.15
        self.current_assistance = 0.8
        self.current_resistance = 0.0

    def _apply_safety_constraints(self, patient_state: Dict):
        """Apply safety constraints based on patient state."""
        # Check for dangerous states
        pain = patient_state.get('pain', 0.0)
        if pain > 0.8:
            # High pain - reduce all parameters
            self.current_assistance = 1.0
            self.current_rom = 0.3
            self.current_speed = 0.1

        # Check for fatigue emergency
        fatigue = patient_state.get('fatigue', 0.0)
        if fatigue > 0.95:
            self.current_assistance = 1.0
            self.current_speed = 0.05

    def get_parameters(self) -> Dict:
        """Get current control parameters."""
        return {
            'rom_percentage': self.current_rom,
            'speed': self.current_speed,
            'assistance_level': self.current_assistance,
            'resistance': self.current_resistance,
            'limits': self.limits
        }

    def set_limits(self, new_limits: Dict):
        """Update control limits."""
        if 'rom' in new_limits:
            self.limits['rom'].update(new_limits['rom'])
        if 'speed' in new_limits:
            self.limits['speed'].update(new_limits['speed'])
        if 'assistance' in new_limits:
            self.limits['assistance'].update(new_limits['assistance'])

    def get_adaptation_summary(self) -> Dict:
        """Get summary of adaptation behavior."""
        return {
            'current_parameters': self.get_parameters(),
            'patient_model': self.patient_model,
            'adaptation_history_length': len(self.state_history),
            'recommendations': self._get_recommendations()
        }

    def _get_recommendations(self) -> List[str]:
        """Get recommendations based on adaptation history."""
        recommendations = []

        # ROM recommendations
        if self.current_rom > 0.9:
            recommendations.append("Patient handling near-full ROM well")
        elif self.current_rom < 0.5:
            recommendations.append("ROM limited - check for contractures or pain")

        # Speed recommendations
        if self.current_speed > 0.5:
            recommendations.append("Patient tolerating higher speeds")
        elif self.current_speed < 0.2:
            recommendations.append("Speed reduced - consider warmup adequacy")

        # Assistance recommendations
        if self.current_assistance < 0.2:
            recommendations.append("Patient needs minimal assistance - consider active mode")
        elif self.current_assistance > 0.8:
            recommendations.append("High assistance needed - focus on passive range first")

        return recommendations

    def reset(self):
        """Reset controller to initial state."""
        self.current_rom = 0.8
        self.current_speed = 0.3
        self.current_assistance = 0.5
        self.current_resistance = 0.0
        self.patient_model['strength_trend'] = np.zeros(6)
        self.patient_model['fatigue_trend'] = 0.0


def main():
    """Test adaptive controller."""
    controller = AdaptiveController()

    # Simulate training session
    for i in range(100):
        patient_state = {
            'fatigue': min(i / 100 * 0.8, 0.8),
            'effort': 0.5 + 0.1 * np.sin(i / 10),
            'comfort': max(1.0 - i / 150, 0.5),
            'strength': np.random.rand(6) * 0.5 + 0.3
        }

        performance = {
            'tracking_error': 0.1 + 0.05 * np.random.rand()
        }

        params = controller.update(patient_state, performance)
        print(f"Step {i}: ROM={params['rom_percentage']:.2f}, "
              f"Speed={params['speed']:.2f}, "
              f"Assistance={params['assistance_level']:.2f}")


if __name__ == "__main__":
    main()
