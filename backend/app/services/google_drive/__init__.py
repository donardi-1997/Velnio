from app.core.config import settings


def get_google_drive_provider():
    if settings.GOOGLE_DRIVE_MODE == "real":
        from app.services.google_drive.real_provider import RealGoogleDriveProvider
        return RealGoogleDriveProvider()
    from app.services.google_drive.mock_provider import MockGoogleDriveProvider
    return MockGoogleDriveProvider()
