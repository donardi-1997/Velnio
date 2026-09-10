from typing import List

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_current_workspace,
    get_current_workspace_member,
)
from app.core.exceptions import ForbiddenException
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import MemberRole, Workspace, WorkspaceMember
from app.modules.billing.application.entitlements import EntitlementService
from app.modules.billing.application.subscriptions import SubscriptionService
from app.modules.billing.infrastructure.repository import BillingRepository
from app.schemas.billing import (
    BillingSessionResponse,
    BillingWebhookResponse,
    CheckoutSessionRequest,
    EntitlementsResponse,
    PlanResponse,
    SubscriptionResponse,
)

router = APIRouter()


def get_subscription_service(db: AsyncSession = Depends(get_db)) -> SubscriptionService:
    return SubscriptionService(BillingRepository(db))


def get_entitlement_service(db: AsyncSession = Depends(get_db)) -> EntitlementService:
    return EntitlementService(BillingRepository(db))


def require_billing_admin(member: WorkspaceMember = Depends(get_current_workspace_member)) -> WorkspaceMember:
    if member.role not in {MemberRole.OWNER, MemberRole.ADMIN}:
        raise ForbiddenException("Only workspace owners and admins can manage billing")
    return member


@router.get("/plans", response_model=List[PlanResponse])
async def list_plans(
    service: SubscriptionService = Depends(get_subscription_service),
):
    return await service.list_plans()


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    workspace: Workspace = Depends(get_current_workspace),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return await service.get_subscription(workspace.id)


@router.get("/entitlements", response_model=EntitlementsResponse)
async def get_entitlements(
    workspace: Workspace = Depends(get_current_workspace),
    service: EntitlementService = Depends(get_entitlement_service),
):
    return await service.snapshot(workspace.id)


@router.post("/checkout", response_model=BillingSessionResponse)
async def create_checkout_session(
    data: CheckoutSessionRequest,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    _: WorkspaceMember = Depends(require_billing_admin),
    service: SubscriptionService = Depends(get_subscription_service),
):
    session = await service.create_checkout_session(
        workspace_id=workspace.id,
        user_id=user.id,
        email=user.email,
        plan_code=data.plan_code,
    )
    return BillingSessionResponse(url=session.url, session_id=session.session_id)


@router.post("/portal", response_model=BillingSessionResponse)
async def create_portal_session(
    workspace: Workspace = Depends(get_current_workspace),
    _: WorkspaceMember = Depends(require_billing_admin),
    service: SubscriptionService = Depends(get_subscription_service),
):
    session = await service.create_portal_session(workspace.id)
    return BillingSessionResponse(url=session.url, session_id=session.session_id)


@router.post("/webhook", response_model=BillingWebhookResponse)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    service: SubscriptionService = Depends(get_subscription_service),
):
    payload = await request.body()
    duplicate = await service.handle_webhook(payload, stripe_signature)
    return BillingWebhookResponse(received=True, duplicate=duplicate)
