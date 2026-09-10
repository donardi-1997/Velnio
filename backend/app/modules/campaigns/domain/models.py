"""Campaign domain exports.

During the modular-monolith migration the SQLAlchemy entity remains in the
legacy model package so Alembic metadata and existing imports stay stable.
New campaign code should import the entity through this module boundary.
"""

from app.models.campaign import Campaign, CampaignStatus

__all__ = ["Campaign", "CampaignStatus"]
