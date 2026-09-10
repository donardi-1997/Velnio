import html
import json
from typing import Any, Dict


class ShopifyLandingRenderer:
    def render(self, landing) -> str:
        rendered = self._render_content(landing)
        tracking = getattr(landing, "_velnio_tracking", None)
        variants = getattr(landing, "_velnio_experiment_variants", None)
        if not tracking or not variants:
            return rendered

        definitions = []
        contents = {}
        for variant, variant_landing in variants:
            variant_id = str(variant.id)
            definitions.append(
                {
                    "id": variant_id,
                    "key": str(variant.variant_key),
                    "weight": float(variant.traffic_weight or 0),
                }
            )
            contents[variant_id] = self._render_content(variant_landing or landing)

        config = {
            "endpoint": str(tracking["endpoint"]),
            "trackingKey": str(tracking["tracking_key"]),
            "campaignId": str(tracking["campaign_id"]),
            "productHandle": str(tracking["product_handle"]),
            "variants": definitions,
            "contents": contents,
        }
        config_json = json.dumps(config, separators=(",", ":")).replace("</", "<\\/")
        return f'''<div id="velnio-landing-root">{rendered}</div>
<script>
(function() {{
  const cfg = {config_json};
  const root = document.getElementById('velnio-landing-root');
  if (!root || !cfg.variants.length) return;

  const uuid = () => {{
    if (window.crypto && typeof window.crypto.randomUUID === 'function') return window.crypto.randomUUID();
    return 'v-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
  }};
  const safeGet = (storage, key) => {{ try {{ return storage.getItem(key); }} catch (_) {{ return null; }} }};
  const safeSet = (storage, key, value) => {{ try {{ storage.setItem(key, value); }} catch (_) {{}} }};

  const visitorKey = 'velnio:visitor';
  const sessionKey = 'velnio:session:' + cfg.campaignId;
  const assignmentKey = 'velnio:variant:' + cfg.campaignId;
  let visitorId = safeGet(localStorage, visitorKey);
  if (!visitorId) {{ visitorId = uuid(); safeSet(localStorage, visitorKey, visitorId); }}
  let sessionId = safeGet(sessionStorage, sessionKey);
  if (!sessionId) {{ sessionId = uuid(); safeSet(sessionStorage, sessionKey, sessionId); }}

  const eligible = cfg.variants.filter(v => Number(v.weight) > 0);
  const candidates = eligible.length ? eligible : cfg.variants;
  let selected = candidates.find(v => v.id === safeGet(localStorage, assignmentKey));
  if (!selected) {{
    const total = candidates.reduce((sum, v) => sum + Math.max(0, Number(v.weight) || 0), 0);
    if (total > 0) {{
      let unit;
      if (window.crypto && typeof window.crypto.getRandomValues === 'function') {{
        const values = new Uint32Array(1);
        window.crypto.getRandomValues(values);
        unit = values[0] / 4294967296;
      }} else {{
        unit = Math.random();
      }}
      let cursor = unit * total;
      selected = candidates[candidates.length - 1];
      for (const candidate of candidates) {{
        cursor -= Math.max(0, Number(candidate.weight) || 0);
        if (cursor <= 0) {{ selected = candidate; break; }}
      }}
    }} else {{
      selected = candidates[0];
    }}
    safeSet(localStorage, assignmentKey, selected.id);
  }}

  if (cfg.contents[selected.id]) root.innerHTML = cfg.contents[selected.id];

  const query = new URLSearchParams(window.location.search);
  const device = window.matchMedia && window.matchMedia('(max-width: 767px)').matches ? 'mobile' : 'desktop';
  const send = (eventType) => {{
    const payload = new URLSearchParams();
    payload.set('event_type', eventType);
    payload.set('session_id', sessionId);
    payload.set('visitor_id', visitorId);
    payload.set('landing_variant_id', selected.id);
    payload.set('occurred_at', new Date().toISOString());
    payload.set('device_type', device);
    if (document.referrer) payload.set('referrer', document.referrer.slice(0, 2048));
    if (query.get('utm_source')) payload.set('source', query.get('utm_source').slice(0, 50));
    if (query.get('utm_medium')) payload.set('medium', query.get('utm_medium').slice(0, 50));
    if (query.get('utm_campaign')) payload.set('campaign_source', query.get('utm_campaign').slice(0, 100));
    fetch(cfg.endpoint, {{ method: 'POST', mode: 'no-cors', keepalive: true, body: payload }}).catch(() => {{}});
  }};

  send('PAGE_VIEW');

  const shopRoot = window.Shopify && window.Shopify.routes && window.Shopify.routes.root
    ? window.Shopify.routes.root
    : '/';
  const productUrl = shopRoot + 'products/' + encodeURIComponent(cfg.productHandle);

  root.querySelectorAll('[data-velnio-buy]').forEach(button => {{
    button.addEventListener('click', async (event) => {{
      event.preventDefault();
      if (button.dataset.velnioBusy === '1') return;
      button.dataset.velnioBusy = '1';
      send('CTA_CLICK');
      try {{
        const productResponse = await fetch(productUrl + '.js', {{ credentials: 'same-origin' }});
        if (!productResponse.ok) throw new Error('product lookup failed');
        const product = await productResponse.json();
        const variant = (product.variants || []).find(item => item.available) || (product.variants || [])[0];
        if (!variant || !variant.id) throw new Error('no purchasable variant');

        const addResponse = await fetch(shopRoot + 'cart/add.js', {{
          method: 'POST',
          credentials: 'same-origin',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            items: [{{
              id: variant.id,
              quantity: 1,
              properties: {{
                _velnio_tracking_key: cfg.trackingKey,
                _velnio_variant_id: selected.id,
                _velnio_session_id: sessionId,
                _velnio_visitor_id: visitorId
              }}
            }}]
          }})
        }});
        if (!addResponse.ok) throw new Error('add to cart failed');
        send('ADD_TO_CART');
        send('BEGIN_CHECKOUT');
        window.location.assign(shopRoot + 'checkout');
      }} catch (_) {{
        window.location.assign(productUrl + '?ref=velnio');
      }}
    }});
  }});
}})();
</script>'''

    def _render_content(self, landing) -> str:
        if not landing.sections:
            return f"<h1>{html.escape(landing.title or '')}</h1>"

        sorted_sections = sorted(landing.sections, key=lambda s: s.position)
        parts = []
        for section in sorted_sections:
            content = section.content or {}
            rendered = self._render_section(section.section_type, content)
            if rendered:
                parts.append(rendered)
        return "\n".join(parts)

    def _render_section(self, section_type: str, content: Dict[str, Any]) -> str:
        renderer = getattr(self, f"_render_{section_type.lower()}", None)
        if renderer:
            return renderer(content)
        return ""

    def _esc(self, text: Any) -> str:
        if text is None:
            return ""
        return html.escape(str(text))

    def _render_hero(self, c: Dict) -> str:
        headline = self._esc(c.get("headline", ""))
        subheadline = self._esc(c.get("subheadline", ""))
        cta = self._esc(c.get("cta_text", "Shop Now"))
        img_url = c.get("image_url", "")
        img_tag = f'<img src="{self._esc(img_url)}" alt="{headline}" style="max-width:100%;border-radius:8px;">' if img_url else ""
        return f'<section class="hero" style="text-align:center;padding:40px 20px;"><h1 style="font-size:2em;">{headline}</h1><p style="font-size:1.2em;color:#666;">{subheadline}</p>{img_tag}<a href="#offer" data-velnio-buy="1" style="display:inline-block;margin-top:20px;padding:14px 32px;background:#2563eb;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold;">{cta}</a></section>'

    def _render_problem(self, c: Dict) -> str:
        title = self._esc(c.get("title", "The Problem"))
        desc = self._esc(c.get("description", ""))
        items = c.get("items", [])
        items_html = "".join(f"<li>{self._esc(i)}</li>" for i in items)
        return f'<section class="problem" style="padding:40px 20px;"><h2>{title}</h2><p>{desc}</p><ul>{items_html}</ul></section>'

    def _render_benefits(self, c: Dict) -> str:
        title = self._esc(c.get("title", "Benefits"))
        items = c.get("items", [])
        cards = []
        for item in items:
            if isinstance(item, dict):
                cards.append(f'<div style="flex:1;min-width:200px;padding:16px;"><h3>{self._esc(item.get("title", ""))}</h3><p>{self._esc(item.get("description", ""))}</p></div>')
            else:
                cards.append(f'<div style="flex:1;min-width:200px;padding:16px;"><p>{self._esc(item)}</p></div>')
        return f'<section class="benefits" style="padding:40px 20px;"><h2>{title}</h2><div style="display:flex;flex-wrap:wrap;gap:16px;">{"".join(cards)}</div></section>'

    def _render_product_showcase(self, c: Dict) -> str:
        title = self._esc(c.get("title", ""))
        desc = self._esc(c.get("description", ""))
        features = c.get("features", [])
        features_html = "".join(f"<li>{self._esc(f)}</li>" for f in features)
        return f'<section class="showcase" style="padding:40px 20px;"><h2>{title}</h2><p>{desc}</p><ul>{features_html}</ul></section>'

    def _render_how_it_works(self, c: Dict) -> str:
        title = self._esc(c.get("title", "How it Works"))
        steps = c.get("steps", [])
        steps_html = "".join(
            f'<div style="flex:1;min-width:150px;padding:16px;text-align:center;"><h3>{self._esc(s.get("title", ""))}</h3><p>{self._esc(s.get("description", ""))}</p></div>'
            for s in steps
        )
        return f'<section class="how-it-works" style="padding:40px 20px;"><h2>{title}</h2><div style="display:flex;flex-wrap:wrap;gap:16px;">{steps_html}</div></section>'

    def _render_before_after(self, c: Dict) -> str:
        title = self._esc(c.get("title", "Before & After"))
        before = self._esc(c.get("before", ""))
        after = self._esc(c.get("after", ""))
        return f'<section class="before-after" style="padding:40px 20px;"><h2>{title}</h2><div style="display:flex;gap:20px;"><div style="flex:1;padding:16px;background:#fee2e2;border-radius:8px;"><h3>Before</h3><p>{before}</p></div><div style="flex:1;padding:16px;background:#dcfce7;border-radius:8px;"><h3>After</h3><p>{after}</p></div></div></section>'

    def _render_social_proof(self, c: Dict) -> str:
        title = self._esc(c.get("title", "What Our Customers Say"))
        testimonials = c.get("testimonials", [])
        cards = []
        for t in testimonials:
            stars = "★" * t.get("rating", 5)
            cards.append(f'<div style="flex:1;min-width:200px;padding:16px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;"><p style="font-style:italic;">"{self._esc(t.get("text", ""))}"</p><p><strong>{self._esc(t.get("name", ""))}</strong> <span style="color:#f59e0b;">{stars}</span></p></div>')
        return f'<section class="social-proof" style="padding:40px 20px;"><h2>{title}</h2><div style="display:flex;flex-wrap:wrap;gap:16px;">{"".join(cards)}</div></section>'

    def _render_offer(self, c: Dict) -> str:
        title = self._esc(c.get("title", "Special Offer"))
        orig = self._esc(c.get("original_price", ""))
        disc = self._esc(c.get("discount_price", ""))
        savings = self._esc(c.get("savings", ""))
        bonus = self._esc(c.get("bonus", ""))
        urgency = self._esc(c.get("urgency", ""))
        scarcity = self._esc(c.get("scarcity", ""))
        return f'<section class="offer" id="offer" style="padding:40px 20px;text-align:center;background:#eff6ff;border-radius:12px;"><h2>{title}</h2><p style="font-size:1.5em;"><s style="color:#94a3b8;">${orig}</s> <strong style="color:#dc2626;">${disc}</strong></p><p style="color:#16a34a;font-weight:bold;">You save ${savings}</p><p>{bonus}</p><p style="color:#dc2626;font-weight:bold;">{urgency}</p><p style="color:#9333ea;">{scarcity}</p></section>'

    def _render_guarantee(self, c: Dict) -> str:
        title = self._esc(c.get("title", "Money-Back Guarantee"))
        desc = self._esc(c.get("description", ""))
        badge = self._esc(c.get("badge", "100% Satisfaction Guaranteed"))
        return f'<section class="guarantee" style="padding:40px 20px;text-align:center;"><h2>{title}</h2><p>{desc}</p><p style="font-size:1.2em;font-weight:bold;color:#16a34a;">{badge}</p></section>'

    def _render_faq(self, c: Dict) -> str:
        title = self._esc(c.get("title", "Frequently Asked Questions"))
        items = c.get("items", [])
        faq_html = ""
        for item in items:
            q = self._esc(item.get("question", ""))
            a = self._esc(item.get("answer", ""))
            faq_html += f'<details style="margin-bottom:8px;padding:12px;background:#f8fafc;border-radius:8px;"><summary style="font-weight:bold;cursor:pointer;">{q}</summary><p style="margin-top:8px;color:#64748b;">{a}</p></details>'
        return f'<section class="faq" style="padding:40px 20px;"><h2>{title}</h2>{faq_html}</section>'

    def _render_final_cta(self, c: Dict) -> str:
        headline = self._esc(c.get("headline", "Ready to Order?"))
        subheadline = self._esc(c.get("subheadline", ""))
        cta = self._esc(c.get("cta_text", "Order Now"))
        guarantee = self._esc(c.get("guarantee_text", ""))
        return f'<section class="final-cta" style="padding:40px 20px;text-align:center;background:#1e293b;color:#fff;border-radius:12px;"><h2 style="color:#fff;">{headline}</h2><p style="color:#94a3b8;">{subheadline}</p><a href="#offer" data-velnio-buy="1" style="display:inline-block;margin-top:16px;padding:14px 32px;background:#2563eb;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold;">{cta}</a><p style="margin-top:12px;color:#94a3b8;font-size:0.9em;">{guarantee}</p></section>'
