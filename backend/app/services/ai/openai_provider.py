import json
import math
from typing import Any, Dict, List, Literal

import openai

from app.core.config import settings
from app.core.exceptions import BadGatewayException
from app.core.logging import get_logger
from app.services.ai.base import AIProvider

logger = get_logger(__name__)


class OpenAIProvider(AIProvider):
    def __init__(self):
        api_key = settings.OPENAI_API_KEY.strip()
        if not api_key:
            raise BadGatewayException("AI provider is not configured")
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
            max_retries=1,
        )

    async def _request_json(
        self,
        prompt: str,
        *,
        expected: Literal["object", "object_or_array"] = "object",
    ) -> Any:
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
        except openai.APITimeoutError as exc:
            logger.warning("OpenAI request timed out")
            raise BadGatewayException("AI request timed out; try again") from exc
        except openai.RateLimitError as exc:
            logger.warning("OpenAI rate limit reached")
            raise BadGatewayException("AI provider is busy; try again") from exc
        except openai.AuthenticationError as exc:
            logger.error("OpenAI authentication failed")
            raise BadGatewayException("AI provider authentication failed") from exc
        except openai.APIConnectionError as exc:
            logger.warning("OpenAI connection failed")
            raise BadGatewayException("AI provider is unavailable; try again") from exc
        except openai.APIStatusError as exc:
            logger.warning(
                "OpenAI status error status=%s request_id=%s",
                exc.status_code,
                getattr(exc, "request_id", None),
            )
            raise BadGatewayException("AI provider request failed; try again") from exc
        except openai.APIError as exc:
            logger.warning("OpenAI API error type=%s", type(exc).__name__)
            raise BadGatewayException("AI provider request failed; try again") from exc

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise BadGatewayException("AI provider returned an invalid response") from exc

        if not isinstance(content, str) or not content.strip():
            raise BadGatewayException("AI provider returned an invalid response")

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise BadGatewayException("AI provider returned invalid JSON") from exc

        if expected == "object" and not isinstance(data, dict):
            raise BadGatewayException("AI provider returned an invalid response")
        if expected == "object_or_array" and not isinstance(data, (dict, list)):
            raise BadGatewayException("AI provider returned an invalid response")
        return data

    @staticmethod
    def _require_fields(data: Dict[str, Any], fields: tuple[str, ...]) -> None:
        if any(field not in data for field in fields):
            raise BadGatewayException("AI provider returned an incomplete response")

    @staticmethod
    def _require_string(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise BadGatewayException(f"AI provider returned an invalid {field}")
        return value

    @staticmethod
    def _require_number(value: Any, field: str, minimum: float, maximum: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise BadGatewayException(f"AI provider returned an invalid {field}")
        number = float(value)
        if not math.isfinite(number) or number < minimum or number > maximum:
            raise BadGatewayException(f"AI provider returned an invalid {field}")
        return number

    @staticmethod
    def _require_string_list(value: Any, field: str) -> List[str]:
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise BadGatewayException(f"AI provider returned an invalid {field}")
        return value

    def _validate_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        score_fields = (
            "demand_score",
            "visual_score",
            "problem_score",
            "margin_score",
            "saturation_score",
            "ad_potential_score",
            "impulse_score",
            "return_risk_score",
        )
        self._require_fields(
            data,
            ("overall_score", *score_fields, "summary", "strengths", "risks"),
        )
        self._require_number(data["overall_score"], "overall_score", 0, 100)
        for field in score_fields:
            self._require_number(data[field], field, 0, 10)
        self._require_string(data["summary"], "summary")
        self._require_string_list(data["strengths"], "strengths")
        self._require_string_list(data["risks"], "risks")
        for field in ("recommended_price_min", "recommended_price_max"):
            if data.get(field) is not None:
                self._require_number(data[field], field, 0, 1_000_000_000)
        return data

    def _validate_angles(self, data: Any) -> List[Dict[str, Any]]:
        angles = data.get("angles") if isinstance(data, dict) else data
        if not isinstance(angles, list) or not angles:
            raise BadGatewayException("AI provider returned invalid selling angles")
        required = (
            "name",
            "target_audience",
            "pain_point",
            "main_promise",
            "hook",
            "description",
            "score",
        )
        for angle in angles:
            if not isinstance(angle, dict):
                raise BadGatewayException("AI provider returned invalid selling angles")
            self._require_fields(angle, required)
            for field in required[:-1]:
                self._require_string(angle[field], field)
            self._require_number(angle["score"], "score", 0, 100)
        return angles

    def _validate_offer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_fields(data, ("headline", "offer_type", "primary_price"))
        self._require_string(data["headline"], "headline")
        self._require_string(data["offer_type"], "offer_type")
        if data["offer_type"] not in {
            "STANDARD",
            "DISCOUNT",
            "BUNDLE",
            "BOGO",
            "FREE_SHIPPING",
            "COD",
            "CUSTOM",
        }:
            raise BadGatewayException("AI provider returned an invalid offer_type")
        self._require_number(data["primary_price"], "primary_price", 0, 1_000_000_000)
        return data

    def _validate_landing(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_fields(data, ("title", "slug", "sections"))
        self._require_string(data["title"], "title")
        self._require_string(data["slug"], "slug")
        sections = data["sections"]
        if not isinstance(sections, list) or not sections:
            raise BadGatewayException("AI provider returned invalid landing sections")
        for section in sections:
            if not isinstance(section, dict):
                raise BadGatewayException("AI provider returned invalid landing sections")
            self._require_fields(section, ("section_type", "content"))
            self._require_string(section["section_type"], "section_type")
            if not isinstance(section["content"], dict):
                raise BadGatewayException("AI provider returned invalid landing content")
        return data

    def _validate_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self._require_fields(
            data,
            (
                "summary",
                "weak_points",
                "recommended_actions",
                "next_test_type",
                "next_test_hypothesis",
                "confidence",
            ),
        )
        self._require_string(data["summary"], "summary")
        self._require_string_list(data["weak_points"], "weak_points")
        self._require_string_list(data["recommended_actions"], "recommended_actions")
        self._require_string(data["next_test_type"], "next_test_type")
        self._require_string(data["next_test_hypothesis"], "next_test_hypothesis")
        self._require_number(data["confidence"], "confidence", 0, 1)
        return data

    def _validate_brief(self, data: Dict[str, Any]) -> Dict[str, Any]:
        fields = (
            "product_summary",
            "target_audience",
            "key_benefits",
            "tone_of_voice",
            "pricing_strategy",
            "positioning",
        )
        self._require_fields(data, fields)
        for field in fields:
            self._require_string(data[field], field)
        return data

    async def analyze_product(self, product) -> Dict[str, Any]:
        prompt = f"""Analyze this product for dropshipping potential and return JSON:
Product: {product.name}
Description: {product.description or 'N/A'}
Price: ${product.selling_price or 'N/A'}
Country: {product.target_country}

Return JSON with:
overall_score (0-100), demand_score (0-10), visual_score (0-10), problem_score (0-10),
margin_score (0-10), saturation_score (0-10), ad_potential_score (0-10), impulse_score (0-10),
return_risk_score (0-10), summary (string), strengths (list of strings), risks (list of strings),
recommended_price_min (number), recommended_price_max (number)"""
        return self._validate_analysis(await self._request_json(prompt))

    async def generate_selling_angles(self, product) -> List[Dict[str, Any]]:
        prompt = f"""Generate 3 selling angles for this product.
Product: {product.name}
Description: {product.description or 'N/A'}
Price: ${product.selling_price or 'N/A'}
Country: {product.target_country}

Return a JSON object with an `angles` array. Each angle needs: name, target_audience,
pain_point, main_promise, hook, description, score (0-100)."""
        return self._validate_angles(await self._request_json(prompt, expected="object_or_array"))

    async def generate_selling_angles_for_campaign(
        self,
        product,
        campaign,
        knowledge_context: str = "",
    ) -> List[Dict[str, Any]]:
        prompt = f"""Generate 3 selling angles for this campaign.
Product: {product.name}
Description: {product.description or 'N/A'}
Campaign Target Country: {campaign.target_country}
Campaign Target Language: {campaign.target_language}
Campaign Price: ${campaign.selling_price or product.selling_price or 'N/A'}
Campaign Currency: {campaign.currency}
Campaign Target Audience: {campaign.target_audience or 'General'}
Campaign Payment: {campaign.payment_strategy or 'Standard'}
Campaign Shipping: {campaign.shipping_strategy or 'Standard'}

Knowledge Context:
{knowledge_context[:2000] if knowledge_context else 'No knowledge sources available.'}

Return a JSON object with an `angles` array. Each angle needs: name, target_audience,
pain_point, main_promise, hook, description, score (0-100). Tailor the angles to the
campaign target country and audience."""
        return self._validate_angles(await self._request_json(prompt, expected="object_or_array"))

    async def generate_offer(self, product, campaign, analysis, angle) -> Dict[str, Any]:
        prompt = f"""Generate an offer for this product campaign. Return JSON.
Product: {product.name}
Selling Price: ${campaign.selling_price or product.selling_price}
Supplier Price: ${campaign.supplier_price or product.supplier_price}
Target Country: {campaign.target_country}
Currency: {campaign.currency}
Angle Hook: {angle.hook}
Analysis Summary: {analysis.summary if analysis else 'N/A'}
Analysis Strengths: {', '.join(analysis.strengths) if analysis else 'N/A'}
Analysis Risks: {', '.join(analysis.risks) if analysis else 'N/A'}

Return JSON with:
headline (string), offer_type (STANDARD/DISCOUNT/BUNDLE/BOGO/FREE_SHIPPING/COD/CUSTOM),
primary_price (number), compare_at_price (number), discount_percentage (number),
bundle_quantity (number or null), free_shipping (boolean), cash_on_delivery (boolean),
guarantee_days (number), urgency_text (string), scarcity_text (string), bonus_text (string)"""
        return self._validate_offer(await self._request_json(prompt))

    async def generate_landing(self, product, angle, analysis) -> Dict[str, Any]:
        prompt = f"""Generate a landing page in JSON for this product.
Product: {product.name}
Angle: {angle.name} - {angle.hook}
Promise: {angle.main_promise}
Price: ${product.selling_price or 29.99}

Return JSON with title, slug, sections (array of section_type + content objects)."""
        return self._validate_landing(await self._request_json(prompt))

    async def generate_landing_for_campaign(
        self,
        product,
        campaign,
        angle,
        analysis,
        offer,
    ) -> Dict[str, Any]:
        prompt = f"""Generate a landing page in JSON for this campaign.
Product: {product.name}
Campaign: {campaign.name}
Target Country: {campaign.target_country}
Price: ${campaign.selling_price or product.selling_price or 29.99}
Angle: {angle.name} - {angle.hook}
Promise: {angle.main_promise}
Offer: {offer.headline if offer else 'N/A'}
Discount Price: ${offer.primary_price if offer else 'N/A'}
Offer Type: {offer.offer_type if offer else 'STANDARD'}
Free Shipping: {offer.free_shipping if offer else True}
Guarantee: {offer.guarantee_days if offer else 30} days

Return JSON with title, slug, sections (array of section_type + content objects).
Include offer details in the OFFER and FINAL_CTA sections."""
        return self._validate_landing(await self._request_json(prompt))

    async def regenerate_landing_section(
        self,
        section_type: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        return context

    async def analyze_campaign_performance(
        self,
        campaign,
        metrics: Dict[str, Any],
        variants: List[Dict[str, Any]],
        angles: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = f"""Analyze this campaign's performance and provide insights. Return JSON.

Campaign: {campaign.name}
Target Country: {campaign.target_country}
Currency: {campaign.currency}

Performance Metrics:
- Sessions: {metrics.get('sessions', 0)}
- Page Views: {metrics.get('page_views', 0)}
- CTA Clicks: {metrics.get('cta_clicks', 0)}
- Add to Carts: {metrics.get('add_to_carts', 0)}
- Checkouts: {metrics.get('checkouts', 0)}
- Purchases: {metrics.get('purchases', 0)}
- Revenue: ${metrics.get('revenue', 0):.2f}
- CTR: {metrics.get('ctr', 0):.2%}
- ATC Rate: {metrics.get('atc_rate', 0):.2%}
- Conversion Rate: {metrics.get('conversion_rate', 0):.2%}
- AOV: ${metrics.get('aov', 0):.2f}

Variant Performance:
{json.dumps(variants, indent=2) if variants else 'No variant data'}

Angle Performance:
{json.dumps(angles, indent=2) if angles else 'No angle data'}

IMPORTANT: Never fabricate performance data. Only analyze the data provided above.

Return JSON with:
- summary (string): Overall performance summary
- winning_pattern (string or null): What's working well
- weak_points (list of strings): Areas for improvement
- recommended_actions (list of strings): Specific next steps
- next_test_type (string): HEADLINE_TEST, ANGLE_TEST, OFFER_TEST, PRICE_TEST, HERO_IMAGE_TEST, or CTA_TEST
- next_test_hypothesis (string): Why this test should be run
- confidence (number): 0-1 confidence in the analysis"""
        return self._validate_performance(await self._request_json(prompt))

    async def generate_campaign_brief(
        self,
        product,
        campaign,
        knowledge_context: str,
    ) -> Dict[str, Any]:
        product_name = getattr(product, "name", "Product")
        description = getattr(product, "description", "") or ""
        campaign_name = getattr(campaign, "name", "Campaign") if campaign else ""
        target_country = getattr(campaign, "target_country", "US") if campaign else "US"

        prompt = f"""Generate a campaign brief for this product. Return JSON.

Product: {product_name}
Description: {description[:500]}
Campaign: {campaign_name}
Target Country: {target_country}

Knowledge Context:
{knowledge_context[:2000] if knowledge_context else 'No knowledge sources available.'}

Return JSON with:
- product_summary (string): 1-2 sentence product summary
- target_audience (string): Detailed target audience description
- key_benefits (string): Top 3-5 key benefits for this product
- tone_of_voice (string): Recommended tone for marketing
- pricing_strategy (string): Recommended pricing approach
- positioning (string): How to position this product in the market"""
        return self._validate_brief(await self._request_json(prompt))
