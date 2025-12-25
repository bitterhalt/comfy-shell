"""
Screenshot preview cache management
"""

import hashlib
from pathlib import Path

from PIL import Image

CACHE_DIR = Path("~/.cache/ignis/screenshot_previews").expanduser()
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cached_preview(
    image_path: str,
    size: tuple[int, int],
    crop: bool = False,
) -> str:
    """
    Get or generate a cached preview of an image.
    Args:image_path: Path to source image size: Target size (width, height) crop: Whether to crop to square first
    Returns: Path to cached preview (or original if generation fails)
    """
    src = Path(image_path)

    # Generate cache key
    key = f"{src}:{size}:{crop}"
    digest = hashlib.sha1(key.encode()).hexdigest()
    cached = CACHE_DIR / f"{digest}.png"

    # Return cached if exists
    if cached.exists():
        return str(cached)

    # Cannot generate without source
    if not src.exists():
        return image_path

    try:
        img = Image.open(src)

        if crop:
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))

        img = img.resize(size, Image.LANCZOS)
        img.save(cached, "PNG")
        return str(cached)

    except Exception:
        return image_path


def delete_cached_preview(image_path: str):
    """
    Delete cached previews for a specific image.
    Args: image_path: Path to source image
    """
    try:
        src = Path(image_path)
        if not src.exists():
            return

        # Generate base key for this image
        src_str = str(src)

        # Delete all cached versions of this image
        for cached_file in CACHE_DIR.glob("*.png"):
            try:
                # Check if this cache file is for our image
                # by attempting to reconstruct possible cache keys
                for crop in (False, True):
                    for size in [(340, 191), (320, 180), (400, 225)]:
                        key = f"{src_str}:{size}:{crop}"
                        digest = hashlib.sha1(key.encode()).hexdigest()
                        if cached_file.name == f"{digest}.png":
                            cached_file.unlink()
                            break
            except Exception:
                pass

    except Exception:
        pass


def clear_cache():
    """Clear all cached previews (maintenance function)"""
    try:
        for cached_file in CACHE_DIR.glob("*.png"):
            try:
                cached_file.unlink()
            except Exception:
                pass
    except Exception:
        pass
