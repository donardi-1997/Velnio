import pytest
from app.services.experiments import ExperimentAnalysisService


def test_insufficient_data_no_variants():
    service = ExperimentAnalysisService()
    result = service.analyze_experiment([])
    assert result["status"] == "insufficient_data"


def test_insufficient_data_one_variant():
    service = ExperimentAnalysisService()
    result = service.analyze_experiment([{"variant_id": "A", "sessions": 100, "purchases": 5, "conversion_rate": 0.05}])
    assert result["status"] == "insufficient_data"


def test_insufficient_data_low_sessions():
    service = ExperimentAnalysisService()
    result = service.analyze_experiment([
        {"variant_id": "A", "sessions": 50, "purchases": 3, "conversion_rate": 0.06},
        {"variant_id": "B", "sessions": 50, "purchases": 2, "conversion_rate": 0.04},
    ])
    assert result["status"] == "insufficient_data"


def test_leader_detection():
    service = ExperimentAnalysisService()
    result = service.analyze_experiment([
        {"variant_id": "A", "variant_name": "Control", "sessions": 500, "purchases": 18, "conversion_rate": 0.036},
        {"variant_id": "B", "variant_name": "Test", "sessions": 500, "purchases": 40, "conversion_rate": 0.08},
    ])
    assert result["status"] == "leader"
    assert result["variant_id"] == "B"
    assert result["confidence"] > 0.5
    assert result["lift"] > 0


def test_no_false_winner_on_tiny_sample():
    service = ExperimentAnalysisService()
    result = service.analyze_experiment([
        {"variant_id": "A", "variant_name": "Control", "sessions": 20, "purchases": 2, "conversion_rate": 0.10},
        {"variant_id": "B", "variant_name": "Test", "sessions": 20, "purchases": 4, "conversion_rate": 0.20},
    ])
    assert result["status"] == "insufficient_data"


def test_recommend_next_test():
    service = ExperimentAnalysisService()
    result = service.recommend_next_test(
        campaign_data={"status": "PUBLISHED"},
        variant_metrics=[{"variant_id": "A", "sessions": 200, "conversion_rate": 0.02}],
        angle_metrics=[],
    )
    assert "recommendations" in result
    assert len(result["recommendations"]) > 0
    assert result["next_test_type"] in ["HEADLINE_TEST", "ANGLE_TEST", "OFFER_TEST", "PRICE_TEST", "HERO_IMAGE_TEST", "CTA_TEST"]
