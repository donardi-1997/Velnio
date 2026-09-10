from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.campaign import Campaign
from app.models.google_drive import DocumentImportStatus, ProductSourceDocument
from app.models.product import Product, ProductImage
from app.schemas.google_drive import (
    GoogleDriveImportAssetRequest,
    GoogleDriveImportDocumentRequest,
    GoogleDriveImportImageRequest,
    GoogleDriveImportResponse,
    ProductSourceDocumentResponse,
)
from app.services.google_drive import get_google_drive_provider
from app.services.knowledge.extraction import DocumentExtractionService
from app.services.storage import get_storage_provider
from app.modules.integrations.application.google_drive_connection import GoogleDriveConnectionService

IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp", "image/tiff"}
DOCUMENT_MIMETYPES = {"application/pdf", "text/plain", "text/html", "text/csv"}
EXPORT_MIMETYPES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
}
MAX_FILE_SIZE = settings.GOOGLE_DRIVE_MAX_FILE_MB * 1024 * 1024


class GoogleDriveImportService:
    def __init__(self, db: AsyncSession, connection_service: GoogleDriveConnectionService) -> None:
        self.db = db
        self.connection_service = connection_service

    async def import_image(
        self,
        data: GoogleDriveImportImageRequest,
        workspace_id: UUID,
    ) -> GoogleDriveImportResponse:
        product = await self._require_product(data.product_id, workspace_id)
        provider = get_google_drive_provider()
        access_token = await self.connection_service.get_valid_token(workspace_id)
        file_data = await provider.get_file(access_token, data.file_id)
        mime_type = file_data.get("mimeType", "")
        if mime_type not in IMAGE_MIMETYPES:
            raise BadRequestException("File is not an image")

        existing_result = await self.db.execute(
            select(ProductImage).where(
                ProductImage.product_id == product.id,
                ProductImage.external_source == "GOOGLE_DRIVE",
                ProductImage.external_file_id == data.file_id,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            return GoogleDriveImportResponse(
                id=existing.id,
                file_name=file_data.get("name"),
                file_type=mime_type,
                status="IMPORTED",
                storage_key=existing.storage_key,
                image_url=existing.image_url,
                created_at=existing.created_at,
            )

        content = await provider.download_file(access_token, data.file_id)
        self._check_size(content)
        storage = get_storage_provider()
        storage_key = await storage.save_bytes(content, mime_type or "image/jpeg", f"products/{product.id}/images")
        image_url = storage.get_public_url(storage_key)

        image = ProductImage(
            product_id=product.id,
            image_url=image_url,
            image_type=data.purpose,
            position=data.position,
            generated_by_ai="false",
            source_type="SOURCE",
            purpose=data.purpose,
            storage_key=storage_key,
            external_source="GOOGLE_DRIVE",
            external_file_id=data.file_id,
            external_file_name=file_data.get("name"),
        )
        self.db.add(image)
        await self.db.flush()
        await self.db.refresh(image)
        return GoogleDriveImportResponse(
            id=image.id,
            file_name=file_data.get("name"),
            file_type=mime_type,
            status="IMPORTED",
            storage_key=storage_key,
            image_url=image_url,
            created_at=image.created_at,
        )

    async def import_document(
        self,
        data: GoogleDriveImportDocumentRequest,
        workspace_id: UUID,
        user_id: UUID,
    ) -> ProductSourceDocument:
        product = await self._require_product(data.product_id, workspace_id)
        if data.campaign_id is not None:
            await self._require_campaign(data.campaign_id, workspace_id)

        provider = get_google_drive_provider()
        access_token = await self.connection_service.get_valid_token(workspace_id)
        file_data = await provider.get_file(access_token, data.file_id)
        mime_type = file_data.get("mimeType", "")
        if mime_type in IMAGE_MIMETYPES:
            raise BadRequestException("Use /import-image for image files")

        content_text = None
        storage_key = None
        file_size = int(file_data.get("size", 0) or 0)

        if mime_type in EXPORT_MIMETYPES:
            content = await provider.export_file(access_token, data.file_id, EXPORT_MIMETYPES[mime_type])
            self._check_size(content)
            content_text = content.decode("utf-8", errors="replace")
            file_size = len(content)
        elif mime_type in DOCUMENT_MIMETYPES:
            if mime_type == "application/pdf":
                content = await provider.download_file(access_token, data.file_id)
                self._check_size(content)
                file_size = len(content)
                storage = get_storage_provider()
                storage_key = await storage.save_bytes(content, "application/pdf", f"products/{product.id}/documents")
            elif mime_type in {"text/plain", "text/html", "text/csv"}:
                content = await provider.download_file(access_token, data.file_id)
                self._check_size(content)
                content_text = content.decode("utf-8", errors="replace")
                file_size = len(content)
        else:
            raise BadRequestException(f"Unsupported file type: {mime_type}")

        doc = ProductSourceDocument(
            product_id=product.id,
            workspace_id=workspace_id,
            campaign_id=data.campaign_id,
            external_file_id=data.file_id,
            external_file_name=file_data.get("name"),
            file_type=mime_type,
            file_size=file_size,
            status=DocumentImportStatus.PROCESSING,
            storage_key=storage_key,
            content_text=content_text,
            imported_by_user_id=user_id,
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)

        extraction = await DocumentExtractionService().extract(doc, get_storage_provider())
        doc.extracted_text = extraction.text
        doc.character_count = extraction.character_count
        doc.page_count = extraction.page_count
        doc.extraction_error = extraction.error
        doc.processed_at = datetime.now(timezone.utc)
        if extraction.status == "NEEDS_OCR":
            doc.status = DocumentImportStatus.NEEDS_OCR
        elif extraction.status == "FAILED":
            doc.status = DocumentImportStatus.FAILED
        else:
            doc.status = DocumentImportStatus.READY

        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def import_asset(
        self,
        data: GoogleDriveImportAssetRequest,
        workspace_id: UUID,
    ) -> GoogleDriveImportResponse:
        campaign = await self._require_campaign(data.campaign_id, workspace_id)
        provider = get_google_drive_provider()
        access_token = await self.connection_service.get_valid_token(workspace_id)
        file_data = await provider.get_file(access_token, data.file_id)
        mime_type = file_data.get("mimeType", "")
        if mime_type not in IMAGE_MIMETYPES:
            raise BadRequestException("Campaign assets must be images")

        content = await provider.download_file(access_token, data.file_id)
        self._check_size(content)
        storage = get_storage_provider()
        storage_key = await storage.save_bytes(content, mime_type or "image/jpeg", f"campaigns/{campaign.id}/assets")
        image_url = storage.get_public_url(storage_key)

        product_result = await self.db.execute(select(Product).where(Product.id == campaign.product_id))
        product = product_result.scalar_one_or_none()
        image = ProductImage(
            product_id=product.id if product else None,
            campaign_id=campaign.id,
            image_url=image_url,
            image_type=data.purpose,
            position=0,
            generated_by_ai="false",
            source_type="SOURCE",
            purpose=data.purpose,
            storage_key=storage_key,
            external_source="GOOGLE_DRIVE",
            external_file_id=data.file_id,
            external_file_name=file_data.get("name"),
        )
        self.db.add(image)
        await self.db.flush()
        await self.db.refresh(image)
        return GoogleDriveImportResponse(
            id=image.id,
            file_name=file_data.get("name"),
            file_type=mime_type,
            status="IMPORTED",
            storage_key=storage_key,
            image_url=image_url,
            created_at=image.created_at,
        )

    async def list_product_documents(self, product_id: UUID, workspace_id: UUID):
        await self._require_product(product_id, workspace_id)
        result = await self.db.execute(
            select(ProductSourceDocument)
            .where(
                ProductSourceDocument.product_id == product_id,
                ProductSourceDocument.workspace_id == workspace_id,
            )
            .order_by(ProductSourceDocument.created_at.desc())
        )
        return result.scalars().all()

    async def _require_product(self, product_id: UUID, workspace_id: UUID) -> Product:
        result = await self.db.execute(
            select(Product).where(Product.id == product_id, Product.workspace_id == workspace_id)
        )
        product = result.scalar_one_or_none()
        if product is None:
            raise NotFoundException("Product")
        return product

    async def _require_campaign(self, campaign_id: UUID, workspace_id: UUID) -> Campaign:
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace_id)
        )
        campaign = result.scalar_one_or_none()
        if campaign is None:
            raise NotFoundException("Campaign")
        return campaign

    @staticmethod
    def _check_size(content: bytes) -> None:
        if len(content) > MAX_FILE_SIZE:
            raise BadRequestException(f"File exceeds {settings.GOOGLE_DRIVE_MAX_FILE_MB}MB limit")
