import json
from typing import Any, Dict, List
from app.services.ai.base import AIProvider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIProvider(AIProvider):
    def __init__(self):
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        except ImportError:
            logger.warning("openai package not installed, falling back to mock")
            from app.services.ai.mock_provider import MockAIProvider
            self._fallback = MockAIProvider()

    async def analyze_product(self, product) -> Dict[str, Any]:
        if hasattr(self, '_fallback'):
            return await self._fallback.analyze_product(product)
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
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    async def generate_selling_angles(self, product) -> List[Dict[str, Any]]:
        if hasattr(self, '_fallback'):
            return await self._fallback.generate_selling_angles(product)
        prompt = f"""Generate 3 selling angles for this product. Return JSON array.
Product: {product.name}
Description: {product.description or 'N/A'}
Price: ${product.selling_price or 'N/A'}
Country: {product.target_country}

Each angle needs: name, target_audience, pain_point, main_promise, hook, description, score (0-100)"""
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        return data.get("angles", data) if isinstance(data, dict) else data

    async def generate_selling_angles_for_campaign(self, product, campaign) -> List[Dict[str, Any]]:
        if hasattr(self, '_fallback'):
            return await self._fallback.generate_selling_angles_for_campaign(product, campaign)
        prompt = f"""Generate 3 selling angles for this campaign. Return JSON array.
Product: {product.name}
Description: {product.description or 'N/A'}
Campaign Target Country: {campaign.target_country}
Campaign Target Language: {campaign.target_language}
Campaign Price: ${campaign.selling_price or product.selling_price or 'N/A'}
Campaign Currency: {campaign.currency}
Campaign Target Audience: {campaign.target_audience or 'General'}
Campaign Payment: {campaign.payment_strategy or 'Standard'}
Campaign Shipping: {campaign.shipping_strategy or 'Standard'}

Each angle needs: name, target_audience, pain_point, main_promise, hook, description, score (0-100).
Tailor angles specifically for the campaign target country and audience."""
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        return data.get("angles", data) if isinstance(data, dict) else data

    async def generate_offer(self, product, campaign, analysis, angle) -> Dict[str, Any]:
        if hasattr(self, '_fallback'):
            return await self._fallback.generate_offer(product, campaign, analysis, angle)
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
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    async def generate_landing(self, product, angle, analysis) -> Dict[str, Any]:
        if hasattr(self, '_fallback'):
            return await self._fallback.generate_landing(product, angle, analysis)
        prompt = f"""Generate a landing page in JSON for this product.
Product: {product.name}
Angle: {angle.name} - {angle.hook}
Promise: {angle.main_promise}
Price: ${product.selling_price or 29.99}

Return JSON with title, slug, sections (array of section_type + content objects)."""
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    async def generate_landing_for_campaign(self, product, campaign, angle, analysis, offer) -> Dict[str, Any]:
        if hasattr(self, '_fallback'):
            return await self._fallback.generate_landing_for_campaign(product, campaign, angle, analysis, offer)
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
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    async def regenerate_landing_section(self, section_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if hasattr(self, '_fallback'):
            return await self._fallback.regenerate_landing_section(section_type, context)
        return context

    async def analyze_campaign_performance(
        self,
        campaign,
        metrics: Dict[str, Any],
        variants: List[Dict[str, Any]],
        angles: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if hasattr(self, '_fallback'):
            return await self._fallback.analyze_campaign_performance(campaign, metrics, variants, angles)
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
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
