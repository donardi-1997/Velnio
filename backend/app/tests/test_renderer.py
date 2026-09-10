from types import SimpleNamespace
from uuid import uuid4

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

    rendered = renderer.render(FakeLanding())
    assert "<script>" not in rendered
    assert "alert" not in rendered
    assert "Clean" in rendered
    assert "29.99" in rendered


def test_renderer_embeds_variant_assignment_and_private_cart_properties():
    renderer = ShopifyLandingRenderer()

    class FakeSection:
        def __init__(self, st, c, p):
            self.section_type = st
            self.content = c
            self.position = p

    class FakeLanding:
        def __init__(self, headline: str):
            self.title = headline
            self.sections = [
                FakeSection(
                    "HERO",
                    {"headline": headline, "subheadline": "Sub", "cta_text": "Buy now"},
                    0,
                )
            ]

    control_landing = FakeLanding("Control headline")
    challenger_landing = FakeLanding("Challenger headline")
    control = SimpleNamespace(id=uuid4(), variant_key="A", traffic_weight=50)
    challenger = SimpleNamespace(id=uuid4(), variant_key="B", traffic_weight=50)
    control_landing._velnio_tracking = {
        "endpoint": "https://api.example.com/api/tracking/beacon/key",
        "tracking_key": "tracking-key",
        "campaign_id": str(uuid4()),
        "product_handle": "velnio-campaign-product",
    }
    control_landing._velnio_experiment_variants = [
        (control, control_landing),
        (challenger, challenger_landing),
    ]

    rendered = renderer.render(control_landing)

    assert 'id="velnio-landing-root"' in rendered
    assert "Control headline" in rendered
    assert "Challenger headline" in rendered
    assert str(control.id) in rendered
    assert str(challenger.id) in rendered
    assert "velnio:variant:" in rendered
    assert "cart/add.js" in rendered
    assert "_velnio_tracking_key" in rendered
    assert "_velnio_variant_id" in rendered
    assert "_velnio_session_id" in rendered
    assert "_velnio_visitor_id" in rendered
    assert "send('PAGE_VIEW')" in rendered
    assert "send('ADD_TO_CART')" in rendered
    assert "send('BEGIN_CHECKOUT')" in rendered
