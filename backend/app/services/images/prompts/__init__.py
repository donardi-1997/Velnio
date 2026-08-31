from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class VisualDirection:
    visual_style: str = "modern, clean"
    tone: str = "professional, trustworthy"
    color_notes: Optional[str] = None
    background_style: Optional[str] = None
    photography_style: Optional[str] = None
    audience_context: Optional[str] = None
    additional_instructions: Optional[str] = None

    def to_prompt_suffix(self) -> str:
        parts = [f"Style: {self.visual_style}.", f"Tone: {self.tone}."]
        if self.color_notes:
            parts.append(f"Colors: {self.color_notes}.")
        if self.background_style:
            parts.append(f"Background: {self.background_style}.")
        if self.photography_style:
            parts.append(f"Photography: {self.photography_style}.")
        if self.audience_context:
            parts.append(f"Audience: {self.audience_context}.")
        if self.additional_instructions:
            parts.append(self.additional_instructions)
        return " ".join(parts)


def build_product_image_prompt(
    product_name: str,
    purpose: str,
    description: Optional[str] = None,
    visual_direction: Optional[VisualDirection] = None,
    angle: Optional[str] = None,
) -> str:
    base = f"Product image of {product_name}"
    if description:
        base += f" - {description}"

    purpose_instructions = {
        "HERO": "Hero shot, main marketing image, eye-catching, centered product.",
        "LIFESTYLE": "Lifestyle photography, product in real-life context, natural setting.",
        "PROBLEM": "Problem illustration, showing the pain point the product solves.",
        "SOLUTION": "Solution showcase, product solving a problem effectively.",
        "BENEFIT": "Benefit highlight, visually demonstrating the product's key benefit.",
        "BEFORE": "Before state, showing the situation without the product.",
        "AFTER": "After state, showing the improvement with the product.",
        "COMPARISON": "Side-by-side comparison, before and after or vs competitor.",
        "SOCIAL": "Social media optimized image, square format, bold and scroll-stopping.",
    }

    if purpose in purpose_instructions:
        base += f". {purpose_instructions[purpose]}"
    elif purpose != "ORIGINAL":
        base += f". Purpose: {purpose}"

    if angle:
        base += f" Selling angle: {angle}"

    if visual_direction:
        suffix = visual_direction.to_prompt_suffix()
        if suffix:
            base += f". {suffix}"

    base += ". Professional quality, high resolution."
    return base


def build_lifestyle_prompt(
    product_name: str,
    angle: str,
    audience: Optional[str] = None,
    visual_direction: Optional[VisualDirection] = None,
) -> str:
    prompt = f"Lifestyle photograph of {product_name} being used naturally."
    prompt += f" Context: {angle}"
    if audience:
        prompt += f". Target audience: {audience}"
    if visual_direction:
        suffix = visual_direction.to_prompt_suffix()
        if suffix:
            prompt += f". {suffix}"
    prompt += ". Authentic, warm, professional product photography."
    return prompt


def build_problem_solution_prompt(
    product_name: str,
    problem: str,
    solution_benefit: str,
    visual_direction: Optional[VisualDirection] = None,
) -> str:
    prompt = f"Split comparison image. Left side: {problem}. Right side: {product_name} providing {solution_benefit}."
    if visual_direction:
        suffix = visual_direction.to_prompt_suffix()
        if suffix:
            prompt += f" {suffix}"
    prompt += ". Clean visual contrast, professional marketing image."
    return prompt


def generate_visual_direction_prompt(product, campaign) -> dict:
    product_name = getattr(product, "name", "product")
    description = getattr(product, "description", "") or ""
    audience = getattr(campaign, "target_audience", "") or "general consumers"
    country = getattr(campaign, "target_country", "US")

    return {
        "visual_style": f"Modern, clean, conversion-optimized for {country} market",
        "tone": "Professional yet approachable, trust-building",
        "color_notes": "Clean whites, product accent colors, high contrast for mobile",
        "background_style": "Clean studio or lifestyle context",
        "photography_style": "High-quality product photography with natural lighting",
        "audience_context": f"Tailored for {audience}",
        "additional_instructions": f"Focus on {product_name} key benefits. {description[:200] if description else ''}",
    }
