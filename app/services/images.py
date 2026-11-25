import re

from fastapi import HTTPException, status

IMAGE_DATA_URL_PATTERN = re.compile(
    r"^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$"
)
MAX_IMAGE_LENGTH = 1_500_000


def validate_image_data_url(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) > MAX_IMAGE_LENGTH or not IMAGE_DATA_URL_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen debe ser una data URL JPEG, PNG o WEBP válida",
        )
    return value
