import math
from typing import Dict, Any, List, Optional
from uuid import UUID
from app.core.config import settings


class ExperimentAnalysisService:
    """
    Analyzes A/B test results using a two-proportion z-test for conversion rates.

    Method: Two-proportion z-test
    - H0: p1 == p2 (no difference in conversion rates)
    - H1: p1 != p2 (there is a difference)
    - z = (p1 - p2) / sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    - p_pool = (x1 + x2) / (n1 + n2)

    Confidence level: 95% (z_critical = 1.96)

    Limitations:
    - Requires sufficient sample size (MIN_SESSIONS_PER_VARIANT, MIN_PURCHASES)
    - Does not account for multiple comparisons
    - Uses normal approximation which may be less accurate for very small samples
    """

    MIN_SESSIONS_PER_VARIANT = getattr(settings, "EXPERIMENT_MIN_SESSIONS_PER_VARIANT", 100)
    MIN_PURCHASES = getattr(settings, "EXPERIMENT_MIN_PURCHASES", 10)
    Z_CRITICAL = 1.96  # 95% confidence

    def analyze_experiment(
        self,
        variant_metrics: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if len(variant_metrics) < 2:
            return {
                "status": "insufficient_data",
                "reason": "Need at least 2 variants to compare.",
            }

        # Filter to variants with data
        active_variants = [v for v in variant_metrics if v.get("sessions", 0) > 0]
        if len(active_variants) < 2:
            return {
                "status": "insufficient_data",
                "reason": "Need at least 2 variants with traffic.",
            }

        # Check minimum thresholds
        for v in active_variants:
            if v["sessions"] < self.MIN_SESSIONS_PER_VARIANT:
                return {
                    "status": "insufficient_data",
                    "reason": f"Variant {v.get('variant_id', 'unknown')} has {v['sessions']} sessions (need {self.MIN_SESSIONS_PER_VARIANT}).",
                }
            if v.get("purchases", 0) < self.MIN_PURCHASES:
                return {
                    "status": "insufficient_data",
                    "reason": f"Variant {v.get('variant_id', 'unknown')} has {v.get('purchases', 0)} purchases (need {self.MIN_PURCHASES}).",
                }

        # Sort by conversion rate descending
        sorted_variants = sorted(active_variants, key=lambda x: x.get("conversion_rate", 0), reverse=True)
        leader = sorted_variants[0]
        runner = sorted_variants[1]

        # Two-proportion z-test
        n1 = leader["sessions"]
        x1 = leader.get("purchases", 0)
        n2 = runner["sessions"]
        x2 = runner.get("purchases", 0)

        p1 = x1 / n1 if n1 > 0 else 0
        p2 = x2 / n2 if n2 > 0 else 0

        # Pooled proportion
        p_pool = (x1 + x2) / (n1 + n2) if (n1 + n2) > 0 else 0

        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2)) if (n1 > 0 and n2 > 0 and p_pool > 0 and p_pool < 1) else 0

        if se == 0:
            return {
                "status": "insufficient_data",
                "reason": "Cannot compute statistical significance (zero standard error).",
            }

        z_score = (p1 - p2) / se
        confidence = self._z_to_confidence(z_score)

        # Lift calculation
        lift = ((p1 - p2) / p2 * 100) if p2 > 0 else 0

        if abs(z_score) >= self.Z_CRITICAL:
            return {
                "status": "leader",
                "variant_id": leader.get("variant_id"),
                "variant_name": leader.get("variant_name", leader.get("variant_id", "Unknown")),
                "confidence": round(confidence, 4),
                "lift": round(lift, 1),
                "reason": (
                    f"Variant {leader.get('variant_name', leader.get('variant_id', 'A'))} has a "
                    f"{abs(lift):.1f}% {'higher' if lift > 0 else 'lower'} conversion rate "
                    f"({p1:.3f} vs {p2:.3f}) with {confidence*100:.1f}% confidence."
                ),
                "leader_conversion_rate": round(p1, 4),
                "runner_conversion_rate": round(p2, 4),
                "leader_sessions": n1,
                "runner_sessions": n2,
                "leader_purchases": x1,
                "runner_purchases": x2,
                "z_score": round(z_score, 4),
            }
        else:
            return {
                "status": "insufficient_data",
                "reason": (
                    f"Not enough statistical significance yet. "
                    f"Current confidence: {confidence*100:.1f}% (need {self.Z_CRITICAL*100/2:.0f}%). "
                    f"Leader: {leader.get('variant_name', 'A')} ({p1:.3f}), "
                    f"Runner: {runner.get('variant_name', 'B')} ({p2:.3f})."
                ),
                "confidence": round(confidence, 4),
                "z_score": round(z_score, 4),
                "leader_variant_id": leader.get("variant_id"),
                "runner_variant_id": runner.get("variant_id"),
            }

    def _z_to_confidence(self, z: float) -> float:
        """Convert z-score to confidence level using normal CDF approximation."""
        z = abs(z)
        # Using approximation of the normal CDF
        # For z >= 0, CDF(z) ≈ 1 - (1/sqrt(2*pi)) * exp(-z²/2) * (a1*t + a2*t² + a3*t³)
        # where t = 1 / (1 + 0.2316419 * z)
        if z > 8:
            return 1.0
        a1, a2, a3, a4, a5 = 0.319381530, -0.356563782, 1.781477937, -1.821255978, 1.330274429
        t = 1.0 / (1.0 + 0.2316419 * z)
        cdf = 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-z * z / 2) * (
            a1 * t + a2 * t**2 + a3 * t**3 + a4 * t**4 + a5 * t**5
        )
        # Two-tailed confidence
        confidence = 2 * cdf - 1
        return min(max(confidence, 0.0), 1.0)

    def recommend_next_test(
        self,
        campaign_data: Dict[str, Any],
        variant_metrics: List[Dict[str, Any]],
        angle_metrics: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        recommendations = []

        # Check if headline test is needed
        if campaign_data.get("status") == "PUBLISHED":
            recommendations.append({
                "test_type": "HEADLINE_TEST",
                "hypothesis": "Test a different headline angle to improve CTR. Current CTR data suggests room for improvement in initial engagement.",
                "description": "Create a new variant with a different headline hook while keeping all other elements the same.",
            })

        # Check angle performance
        if angle_metrics and len(angle_metrics) >= 2:
            sorted_angles = sorted(angle_metrics, key=lambda x: x.get("conversion_rate", 0), reverse=True)
            if sorted_angles[0]["conversion_rate"] > sorted_angles[-1]["conversion_rate"] * 1.2:
                recommendations.append({
                    "test_type": "ANGLE_TEST",
                    "hypothesis": f"Angle '{sorted_angles[0]['angle_name']}' outperforms '{sorted_angles[-1]['angle_name']}'. Test a new variant using the winning angle against a fresh alternative.",
                    "description": "Clone the winning variant and replace the angle with a new one to validate the pattern.",
                })

        # Check offer performance
        if variant_metrics:
            for v in variant_metrics:
                if v.get("aov", 0) > 0 and v.get("conversion_rate", 0) < 0.02:
                    recommendations.append({
                        "test_type": "OFFER_TEST",
                        "hypothesis": "Low conversion rate with reasonable AOV suggests the offer may need adjustment. Test a stronger discount or bundle.",
                        "description": "Create a variant with a more aggressive offer to see if conversion improves.",
                    })
                    break

        # Check for hero image test
        if variant_metrics:
            leader = max(variant_metrics, key=lambda x: x.get("conversion_rate", 0))
            if leader.get("sessions", 0) > 200 and leader.get("conversion_rate", 0) < 0.03:
                recommendations.append({
                    "test_type": "HERO_IMAGE_TEST",
                    "hypothesis": "The current hero image may not be capturing attention effectively. Test a different product angle or lifestyle shot.",
                    "description": "Create a variant with a different hero image while keeping the same copy and offer.",
                })

        # Check for price test
        if variant_metrics:
            for v in variant_metrics:
                if v.get("revenue", 0) > 0 and v.get("aov", 0) > 0:
                    recommendations.append({
                        "test_type": "PRICE_TEST",
                        "hypothesis": f"Current AOV is ${v.get('aov', 0):.2f}. Test a higher price point to see if revenue per visitor improves despite potential conversion drop.",
                        "description": "Create a variant with a 10-15% higher price to optimize for revenue, not just conversion.",
                    })
                    break

        # CTA test
        if variant_metrics:
            for v in variant_metrics:
                if v.get("sessions", 0) > 100:
                    recommendations.append({
                        "test_type": "CTA_TEST",
                        "hypothesis": "CTA text and placement can significantly impact conversion. Test a more action-oriented or urgency-driven CTA.",
                        "description": "Create a variant with a different CTA button text and/or color.",
                    })
                    break

        if not recommendations:
            recommendations.append({
                "test_type": "ANGLE_TEST",
                "hypothesis": "Generate more selling angles and test the top 2 against each other to find the best messaging.",
                "description": "Create a new angle and run a head-to-head test.",
            })

        return {
            "recommendations": recommendations[:3],
            "next_test_type": recommendations[0]["test_type"] if recommendations else "ANGLE_TEST",
            "next_test_hypothesis": recommendations[0]["hypothesis"] if recommendations else "",
        }
