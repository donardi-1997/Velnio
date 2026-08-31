from typing import Any, Dict, List, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class LandingValidationService:
    """Validates that a landing page has all required sections and elements."""

    REQUIRED_SECTIONS = {"hero", "features", "benefits", "social_proof", "cta"}
    RECOMMENDED_SECTIONS = {"offer", "pricing", "faq", "guarantee"}

    def validate(self, landing_data: Dict[str, Any]) -> Dict[str, Any]:
        sections = landing_data.get("sections", [])
        section_types = {s.get("type") for s in sections if s.get("type")}

        missing_required = self.REQUIRED_SECTIONS - section_types
        missing_recommended = self.RECOMMENDED_SECTIONS - section_types

        issues = []
        warnings = []

        if missing_required:
            issues.append(f"Missing required sections: {', '.join(missing_required)}")
        if missing_recommended:
            warnings.append(f"Missing recommended sections: {', '.join(missing_recommended)}")

        hero = next((s for s in sections if s.get("type") == "hero"), None)
        if hero:
            content = hero.get("content", {})
            if not content.get("headline"):
                issues.append("Hero section is missing a headline")
            if not content.get("subheadline"):
                warnings.append("Hero section is missing a subheadline")

        cta = next((s for s in sections if s.get("type") == "cta"), None)
        if cta:
            content = cta.get("content", {})
            if not content.get("button_text"):
                issues.append("CTA section is missing button text")

        offer_section = next((s for s in sections if s.get("type") == "offer"), None)
        if offer_section:
            content = offer_section.get("content", {})
            if not content.get("headline"):
                warnings.append("Offer section is missing a headline")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "section_types_found": list(section_types),
            "missing_required": list(missing_required),
            "missing_recommended": list(missing_recommended),
        }
