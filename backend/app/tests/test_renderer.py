import pytest
from app.services.shopify.renderer import ShopifyLandingRenderer


def test_renderer_sanitizes_html():
    renderer = ShopifyLandingRenderer()

    class FakeSection:
        def __init__(self, st, c, p):
            self.section_type = st
            self.content = c
            self.position = p

    class FakeLanding:
        def __init__(self):
            self.title = "Test <script>alert('xss')</script>"
            self.sections = [
                FakeSection("HERO", {"headline": "Clean <b>head</b>", "subheadline": "sub"}, 0),
                FakeSection("PROBLEM", {"title": "Problem", "description": "desc"}, 1),
                FakeSection("OFFER", {"title": "Offer", "original_price": "29.99", "discount_price": "19.99"}, 2),
                FakeSection("FAQ", {"title": "FAQ", "items": [{"question": "Q1", "answer": "A1"}]}, 3),
                FakeSection("FINAL_CTA", {"headline": "CTA", "subheadline": "sub"}, 4),
            ]

    html = renderer.render(FakeLanding())
    assert "<script>" not in html
    assert "alert" not in html
    assert "Clean" in html
    assert "29.99" in html
