from typing import Any, Dict, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class CampaignPublishPrecheckService:
    """Validates a campaign is ready for publishing by checking all prerequisites."""

    def check(self, campaign, product, store, angle, offer, landing, images) -> list:
        checks = []

        def _check(name, passed, message=""):
            checks.append({
                "check": name,
                "status": "passed" if passed else "failed",
                "message": message or (f"{name} OK" if passed else f"{name} missing"),
            })

        _check("store_connected", store is not None, "Store connected" if store else "No store connected")
        _check("product_exists", product is not None, "Product exists" if product else "No product")
        _check("angle_selected", angle is not None, "Angle selected" if angle else "No angle selected")
        _check("offer_exists", offer is not None, "Offer exists" if offer else "No offer")
        _check("landing_ready", landing is not None, "Landing ready" if landing else "Landing not ready")
        _check("has_images", bool(images), f"{len(images)} images" if images else "No images")

        has_vd = getattr(campaign, "visual_direction", None) is not None
        _check("has_visual_direction", has_vd, "Visual direction set" if has_vd else "No visual direction")

        prices_ok = bool(getattr(campaign, "selling_price", None) and getattr(campaign, "supplier_price", None))
        _check("prices_set", prices_ok, "Prices set" if prices_ok else "Prices not set")

        return checks

    def precheck(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        checks = {
            "store_connected": False,
            "product_exists": False,
            "angle_selected": False,
            "offer_exists": False,
            "landing_ready": False,
            "has_images": False,
            "has_visual_direction": False,
            "prices_set": False,
        }
        issues = []
        warnings = []

        if campaign_data.get("store_id"):
            checks["store_connected"] = True
        else:
            issues.append("No store connected to campaign")

        if campaign_data.get("product_id"):
            checks["product_exists"] = True
        else:
            issues.append("No product associated with campaign")

        angles = campaign_data.get("angles", [])
        if angles:
            checks["angle_selected"] = True
            selected = [a for a in angles if a.get("selected")]
            if not selected:
                warnings.append("No angle explicitly selected (first will be used)")
        else:
            issues.append("No selling angles defined")

        if campaign_data.get("offer"):
            checks["offer_exists"] = True
        else:
            issues.append("No offer defined for campaign")

        landing = campaign_data.get("landing_page")
        if landing and landing.get("sections"):
            checks["landing_ready"] = True
        else:
            issues.append("Landing page not ready")

        images = campaign_data.get("images", [])
        if images:
            checks["has_images"] = True
        else:
            warnings.append("No images uploaded or generated")

        if campaign_data.get("visual_direction"):
            checks["has_visual_direction"] = True
        else:
            warnings.append("No visual direction set")

        if campaign_data.get("selling_price") and campaign_data.get("supplier_price"):
            checks["prices_set"] = True
        else:
            warnings.append("Selling or supplier price not set")

        all_passed = all(checks.values())
        critical_missing = [k for k, v in checks.items() if not v and k in {
            "store_connected", "product_exists", "offer_exists", "landing_ready"
        }]

        return {
            "ready": all_passed,
            "checks": checks,
            "issues": issues,
            "warnings": warnings,
            "critical_missing": critical_missing,
        }
