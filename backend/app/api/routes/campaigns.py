"""Compatibility shim for the modular Campaigns API.

New code should import from ``app.modules.campaigns.api``.  This module keeps
legacy imports stable while the rest of the backend migrates module-by-module.
"""

from app.modules.campaigns.api.angles import (
    generate_campaign_angles,
    list_campaign_angles,
    select_campaign_angle,
)
from app.modules.campaigns.api.briefs import generate_campaign_brief
from app.modules.campaigns.api.campaigns import (
    create_campaign,
    create_campaign_for_product,
    delete_campaign,
    get_campaign,
    list_campaigns,
    list_campaigns_for_product,
    update_campaign,
)
from app.modules.campaigns.api.landings import (
    generate_campaign_landing,
    get_campaign_landing,
)
from app.modules.campaigns.api.offers import (
    generate_campaign_offer,
    get_campaign_offer,
    update_offer,
)
from app.modules.campaigns.api.publishing import publish_campaign
from app.modules.campaigns.api.router import router

__all__ = [
    "router",
    "list_campaigns",
    "create_campaign",
    "get_campaign",
    "update_campaign",
    "delete_campaign",
    "list_campaigns_for_product",
    "create_campaign_for_product",
    "list_campaign_angles",
    "generate_campaign_angles",
    "select_campaign_angle",
    "get_campaign_offer",
    "generate_campaign_offer",
    "update_offer",
    "get_campaign_landing",
    "generate_campaign_landing",
    "publish_campaign",
    "generate_campaign_brief",
]
