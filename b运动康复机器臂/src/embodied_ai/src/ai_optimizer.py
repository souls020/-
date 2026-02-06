#!/usr/bin/env python3
"""
AI Optimizer for Rehabilitation Training
Uses machine learning to optimize training protocols
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import copy


@dataclass
class TrainingData:
    """Training data point."""
    timestamp: float
    patient_id: str
    exercise: str
    parameters: Dict  # ROM, speed, assistance, etc.
    outcomes: Dict  # strength_improvement, fatigue, satisfaction
    patient_characteristics: Dict  # age, condition, history


@dataclass
class OptimizationResult:
    """Result of optimization."""
    recommended_parameters: Dict
    expected_outcome: float
    confidence: float
    reasoning: List[str]


class AIOptimizer:
    """
    AI-powered optimizer for rehabilitation training.
    Uses historical data and patient characteristics to recommend optimal protocols.
    """

    def __init__(self):
        """Initialize AI optimizer."""
        self.training_data: List[TrainingData] = []
        self.patient_outcomes: Dict[str, List[Dict]] = {}
        self.model_weights: Dict = self._initialize_weights()

        # Optimization parameters
        self.min_samples_for_recommendation = 5
        self.exploration_rate = 0.2

    def _initialize_weights(self) -> Dict:
        """Initialize ML model weights."""
        return {
            'rom_weight': 0.3,
            'speed_weight': 0.25,
            'assistance_weight': 0.25,
            'resistance_weight': 0.2,
            'fatigue_penalty': -0.5,
            'improvement_bonus': 1.0
        }

    def add_training_data(self, data: TrainingData):
        """Add training data point."""
        self.training_data.append(data)

        # Track per patient
        if data.patient_id not in self.patient_outcomes:
            self.patient_outcomes[data.patient_id] = []
        self.patient_outcomes[data.patient_id].append({
            'timestamp': data.timestamp,
            'parameters': data.parameters,
            'outcomes': data.outcomes
        })

    def optimize_parameters(self,
                            patient_id: str,
                            exercise: str,
                            patient_characteristics: Dict = None,
                            target_outcome: str = 'strength') -> OptimizationResult:
        """
        Optimize training parameters for a patient.

        Args:
            patient_id: Patient identifier
            exercise: Exercise type
            patient_characteristics: Patient info (age, condition, etc.)
            target_outcome: Target outcome metric

        Returns:
            Optimization result with recommended parameters
        """
        # Get similar historical data
        similar_data = self._get_similar_data(
            patient_id, exercise, patient_characteristics
        )

        # Generate recommendations
        if len(similar_data) >= self.min_samples_for_recommendation:
            return self._ml_based_optimization(
                similar_data, exercise, target_outcome
            )
        else:
            return self._rule_based_optimization(
                exercise, patient_characteristics, target_outcome
            )

    def _get_similar_data(self,
                          patient_id: str,
                          exercise: str,
                          characteristics: Dict = None) -> List[TrainingData]:
        """Get similar training data for recommendation."""
        similar = []

        for data in self.training_data:
            # Check exercise match
            if data.exercise != exercise:
                continue

            # Check patient similarity
            if characteristics:
                if data.patient_characteristics.get('condition') == characteristics.get('condition'):
                    similar.append(data)
            else:
                similar.append(data)

        return similar

    def _ml_based_optimization(self,
                                data: List[TrainingData],
                                exercise: str,
                                target_outcome: str) -> OptimizationResult:
        """
        ML-based parameter optimization using historical data.
        """
        # Extract features and outcomes
        features = []
        outcomes = []

        for d in data:
            feature_vec = [
                d.parameters.get('rom_percentage', 0.8),
                d.parameters.get('speed', 0.3),
                d.parameters.get('assistance', 0.5),
                d.parameters.get('resistance', 0.0)
            ]
            features.append(feature_vec)

            outcome_val = d.outcomes.get(target_outcome, 0.5)
            outcomes.append(outcome_val)

        features = np.array(features)
        outcomes = np.array(outcomes)

        # Simple linear regression (placeholder for more sophisticated ML)
        try:
            # Fit linear model
            X = np.column_stack([np.ones(len(features)), features])
            weights = np.linalg.lstsq(X, outcomes, rcond=None)[0]

            # Predict optimal parameters
            # Constraints: ROM [0.5, 1.0], Speed [0.1, 0.8], Assistance [0, 1]
            best_outcome = -float('inf')
            best_params = None

            # Grid search for optimal parameters
            for rom in np.arange(0.5, 1.01, 0.1):
                for speed in np.arange(0.1, 0.81, 0.1):
                    for assist in np.arange(0.0, 1.01, 0.2):
                        test_feature = np.array([1, rom, speed, assist, 0.0])
                        predicted = np.dot(test_feature, weights)

                        # Add exploration noise
                        predicted += np.random.normal(0, self.exploration_rate * (1 - abs(predicted - 0.5)))

                        if predicted > best_outcome:
                            best_outcome = predicted
                            best_params = {
                                'rom_percentage': rom,
                                'speed': speed,
                                'assistance': assist,
                                'resistance': 0.0
                            }

            confidence = min(len(data) / 50, 0.95)

            return OptimizationResult(
                recommended_parameters=best_params,
                expected_outcome=best_outcome,
                confidence=confidence,
                reasoning=self._generate_reasoning(best_params, data)
            )

        except Exception as e:
            print(f"Optimization error: {e}")
            return self._rule_based_optimization(exercise, {}, target_outcome)

    def _rule_based_optimization(self,
                                 exercise: str,
                                 characteristics: Dict,
                                 target_outcome: str) -> OptimizationResult:
        """
        Rule-based parameter optimization for new patients.
        """
        # Default parameters based on exercise
        params = {
            'shoulder_abduction': {'rom': 0.8, 'speed': 0.3, 'assistance': 0.7},
            'elbow_flexion': {'rom': 0.9, 'speed': 0.4, 'assistance': 0.6},
            'forearm_rotation': {'rom': 0.7, 'speed': 0.3, 'assistance': 0.5},
            'knee_flexion': {'rom': 0.8, 'speed': 0.2, 'assistance': 0.7},
            'hip_flexion': {'rom': 0.7, 'speed': 0.15, 'assistance': 0.8},
            'ankle_dorsiflexion': {'rom': 0.6, 'speed': 0.12, 'assistance': 0.6}
        }

        defaults = params.get(exercise, {'rom': 0.8, 'speed': 0.3, 'assistance': 0.5})

        # Adjust for patient characteristics
        if characteristics:
            if characteristics.get('age', 50) > 65:
                defaults['speed'] *= 0.7
                defaults['rom'] *= 0.9

            if characteristics.get('condition') == 'acute':
                defaults['assistance'] = 0.9
                defaults['rom'] *= 0.7

            if characteristics.get('condition') == 'chronic':
                defaults['assistance'] = 0.4
                defaults['rom'] *= 1.0

        # Adjust for target outcome
        if target_outcome == 'strength':
            defaults['resistance'] = 0.2
            defaults['assistance'] *= 0.8
        elif target_outcome == 'rom':
            defaults['speed'] *= 0.7
            defaults['assistance'] = min(defaults['assistance'] * 1.1, 1.0)

        return OptimizationResult(
            recommended_parameters=defaults,
            expected_outcome=0.6,
            confidence=0.5,  # Lower confidence for new patients
            reasoning=[
                "Using exercise-specific defaults",
                "Parameters adjusted for patient characteristics",
                "Recommendation confidence increases with more data"
            ]
        )

    def _generate_reasoning(self,
                            params: Dict,
                            data: List[TrainingData]) -> List[str]:
        """Generate human-readable reasoning for recommendations."""
        reasoning = []

        # ROM reasoning
        if params['rom_percentage'] > 0.85:
            reasoning.append("High ROM recommended based on patient tolerance")
        elif params['rom_percentage'] < 0.6:
            reasoning.append("Reduced ROM for safety - gradually increase")

        # Speed reasoning
        if params['speed'] > 0.4:
            reasoning.append("Higher speed for active patients")
        elif params['speed'] < 0.2:
            reasoning.append("Reduced speed for better control")

        # Assistance reasoning
        if params['assistance'] > 0.7:
            reasoning.append("High assistance for initial sessions")
        elif params['assistance'] < 0.3:
            reasoning.append("Low assistance indicates good patient progress")

        # Based on data
        if len(data) > 10:
            high_perf = [d for d in data if d.outcomes.get('satisfaction', 0) > 0.8]
            if len(high_perf) > len(data) * 0.5:
                reasoning.append("Similar parameters show high satisfaction rates")

        return reasoning

    def predict_outcome(self,
                        patient_id: str,
                        parameters: Dict,
                        exercise: str) -> Tuple[float, float]:
        """
        Predict outcome for given parameters.

        Args:
            patient_id: Patient identifier
            parameters: Training parameters
            exercise: Exercise type

        Returns:
            Tuple of (predicted outcome, confidence)
        """
        # Find similar cases
        similar = self._get_similar_data(patient_id, exercise, {})

        if len(similar) < 3:
            return 0.5, 0.3  # Default prediction

        # Weighted average of similar outcomes
        total_weight = 0
        weighted_sum = 0

        for data in similar:
            # Calculate similarity
            similarity = self._calculate_similarity(parameters, data.parameters)

            # Weight by similarity and outcome
            weight = similarity * (1 + data.outcomes.get('satisfaction', 0.5))
            weighted_sum += weight * data.outcomes.get('strength_improvement', 0.5)
            total_weight += weight

        if total_weight > 0:
            prediction = weighted_sum / total_weight
        else:
            prediction = 0.5

        confidence = min(len(similar) / 50, 0.9)

        return prediction, confidence

    def _calculate_similarity(self,
                            params1: Dict,
                            params2: Dict) -> float:
        """Calculate similarity between two parameter sets."""
        features = ['rom_percentage', 'speed', 'assistance', 'resistance']

        diff = 0
        for f in features:
            v1 = params1.get(f, 0)
            v2 = params2.get(f, 0)
            diff += abs(v1 - v2)

        # Convert to similarity (0-1)
        return max(0, 1 - diff / 4)

    def get_optimization_report(self) -> Dict:
        """Generate optimization report."""
        return {
            'total_training_sessions': len(self.training_data),
            'unique_patients': len(self.patient_outcomes),
            'model_weights': self.model_weights,
            'recommendations': {
                'needs_more_data': len(self.training_data) < 20,
                'suggested_exploration': self.exploration_rate
            }
        }

    def update_weights(self, new_data: List[TrainingData]):
        """Update model weights based on new data."""
        # Simple incremental learning
        for data in new_data:
            outcome = data.outcomes.get('strength_improvement', 0.5)
            parameters = data.parameters

            # Adjust weights towards parameters that worked
            if outcome > 0.7:
                for key in ['rom_weight', 'speed_weight', 'assistance_weight']:
                    self.model_weights[key] += 0.01
            elif outcome < 0.3:
                for key in ['rom_weight', 'speed_weight', 'assistance_weight']:
                    self.model_weights[key] -= 0.01

        # Normalize weights
        total = sum(self.model_weights.values())
        for key in self.model_weights:
            self.model_weights[key] /= total


def main():
    """Test AI optimizer."""
    optimizer = AIOptimizer()

    # Add some training data
    for i in range(20):
        data = TrainingData(
            timestamp=datetime.now().timestamp(),
            patient_id=f"patient_{i % 5}",
            exercise="elbow_flexion",
            parameters={
                'rom_percentage': 0.7 + np.random.rand() * 0.3,
                'speed': 0.2 + np.random.rand() * 0.3,
                'assistance': 0.3 + np.random.rand() * 0.5,
                'resistance': np.random.rand() * 0.2
            },
            outcomes={
                'strength_improvement': 0.4 + np.random.rand() * 0.5,
                'fatigue': np.random.rand() * 0.5,
                'satisfaction': 0.5 + np.random.rand() * 0.5
            },
            patient_characteristics={'condition': 'subacute', 'age': 55}
        )
        optimizer.add_training_data(data)

    # Get optimization
    result = optimizer.optimize_parameters(
        patient_id="patient_5",
        exercise="elbow_flexion",
        patient_characteristics={'condition': 'subacute', 'age': 60}
    )

    print(f"Recommended parameters: {result.recommended_parameters}")
    print(f"Expected outcome: {result.expected_outcome:.2f}")
    print(f"Confidence: {result.confidence:.2f}")
    print("Reasoning:")
    for r in result.reasoning:
        print(f"  - {r}")


if __name__ == "__main__":
    main()
