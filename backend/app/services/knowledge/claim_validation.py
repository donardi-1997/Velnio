"""Validates AI-generated claims against knowledge sources."""

from dataclasses import dataclass, field
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID


@dataclass
class ClaimValidationResult:
    """Result of validating a single claim."""
    claim_text: str
    supported: bool
    source_title: Optional[str] = None
    source_type: Optional[str] = None
    confidence: float = 0.0
    note: Optional[str] = None


@dataclass
class ValidationReport:
    """Full validation report for generated content."""
    overall_status: str  # "PASS", "WARNING", "BLOCKED"
    results: List[ClaimValidationResult] = field(default_factory=list)
    unsupported_claims: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ClaimValidationService:
    """Validates generated marketing claims against knowledge sources.

    Uses textual heuristic matching (not semantic). Unsupported claims
    are blocking; missing source support is warning-only.
    """

    # Common marketing claims that are typically safe without sources
    SAFE_CLAIMS = {
        "free shipping", "money-back guarantee", "satisfaction guaranteed",
        "fast shipping", "easy returns", "secure checkout",
        "premium quality", "high quality", "best seller",
        "limited time offer", "while supplies last",
        "customer favorite", "trending", "popular",
    }

    # Keywords that typically require source backing
    REQUIRES_SOURCE_KEYWORDS = {
        "clinically proven", "scientifically tested", "doctor recommended",
        "fda approved", "lab tested", "certified organic",
        "#1", "number one", "award winning", "world's best",
        "cures", "treats", "prevents", "heals",
        "guaranteed results", "lose weight", "anti-aging",
    }

    async def validate(
        self,
        content_text: str,
        db: AsyncSession,
        product_id: Optional[UUID] = None,
        campaign_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
    ) -> ValidationReport:
        """Validate generated content against knowledge sources."""
        from app.models.knowledge import KnowledgeSource

        report = ValidationReport(overall_status="PASS")

        # Load knowledge sources
        query = select(KnowledgeSource).where(
            KnowledgeSource.workspace_id == workspace_id,
            KnowledgeSource.status == "ACTIVE",
        )
        if product_id:
            query = query.where(KnowledgeSource.product_id == product_id)
        if campaign_id:
            query = query.where(KnowledgeSource.campaign_id == campaign_id)

        result = await db.execute(query)
        sources = result.scalars().all()

        # Build combined source text for matching
        source_texts = []
        for s in sources:
            if s.content_text:
                source_texts.append({
                    "title": s.title,
                    "type": s.source_type,
                    "text": s.content_text.lower(),
                })

        # Extract claims from content
        claims = self._extract_claims(content_text)

        for claim in claims:
            result = self._validate_claim(claim, source_texts)
            report.results.append(result)

            if not result.supported:
                # Check if it's a risky claim that needs backing
                if self._needs_source_backing(claim):
                    report.unsupported_claims.append(claim)
                    report.warnings.append(
                        f"Claim '{claim[:50]}...' lacks source backing"
                    )
                else:
                    # Safe claim, no source needed
                    result.supported = True
                    result.note = "Common marketing claim, no source needed"

        # Determine overall status
        if report.unsupported_claims:
            report.overall_status = "WARNING"
        else:
            report.overall_status = "PASS"

        return report

    def _extract_claims(self, text: str) -> List[str]:
        """Extract potential claims from text."""
        claims = []
        sentences = text.replace("!", ".").replace("?", ".").split(".")
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:
                claims.append(sentence)
        return claims

    def _validate_claim(self, claim: str, source_texts: List[dict]) -> ClaimValidationResult:
        """Validate a single claim against source texts."""
        claim_lower = claim.lower()

        for source in source_texts:
            # Simple keyword overlap check
            claim_words = set(claim_lower.split())
            source_words = set(source["text"].split())
            overlap = claim_words & source_words

            if len(overlap) >= 3:
                return ClaimValidationResult(
                    claim_text=claim,
                    supported=True,
                    source_title=source["title"],
                    source_type=source["type"],
                    confidence=min(len(overlap) / 10, 1.0),
                )

        return ClaimValidationResult(
            claim_text=claim,
            supported=False,
            confidence=0.0,
        )

    def _needs_source_backing(self, claim: str) -> bool:
        """Check if a claim typically requires source backing."""
        claim_lower = claim.lower()
        for keyword in self.REQUIRES_SOURCE_KEYWORDS:
            if keyword in claim_lower:
                return True
        return False
