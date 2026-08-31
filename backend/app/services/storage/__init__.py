from app.core.config import settings


def get_storage_provider():
    if settings.STORAGE_PROVIDER == "s3":
        from app.services.storage.s3_provider import S3StorageProvider
        return S3StorageProvider()
    from app.services.storage.local_provider import LocalStorageProvider
    return LocalStorageProvider()
