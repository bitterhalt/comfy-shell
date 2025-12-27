"""
Screenshot preview cache management
"""

import hashlib
import time
from pathlib import Path

from PIL import Image

CACHE_DIR = Path("~/.cache/ignis/screenshot_previews").expanduser()
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MAX_CACHE_SIZE_MB = 50
MAX_CACHE_AGE_DAYS = 7


def _cleanup_old_cache():
    """Remove old or excessive cache files (LRU)"""
    try:
        cache_files = list(CACHE_DIR.glob("*.png"))

        files_info = []
        total_size = 0

        for f in cache_files:
            try:
                stat = f.stat()
                files_info.append((f, stat.st_size, stat.st_mtime))
                total_size += stat.st_size
            except:
                pass

        files_info.sort(key=lambda x: x[2])

        now = time.time()
        cutoff = now - (MAX_CACHE_AGE_DAYS * 86400)

        for path, size, mtime in files_info[:]:
            if mtime < cutoff:
                try:
                    path.unlink()
                    total_size -= size
                    files_info.remove((path, size, mtime))
                except:
                    pass

        max_bytes = MAX_CACHE_SIZE_MB * 1024 * 1024

        while total_size > max_bytes and files_info:
            path, size, _ = files_info.pop(0)
            try:
                path.unlink()
                total_size -= size
            except:
                pass

    except Exception as e:
        print(f"Cache cleanup failed: {e}")


def get_cached_preview(
    image_path: str,
    size: tuple[int, int],
    crop: bool = False,
) -> str:
    """
    Get or generate a cached preview of an image.

    NOTE: This is a BLOCKING operation. Call from executor in async context.

    Args:
        image_path: Path to source image
        size: Target size (width, height)
        crop: Whether to crop to square first

    Returns:
        Path to cached preview (or original if generation fails)
    """
    src = Path(image_path)

    key = f"{src}:{size}:{crop}"
    digest = hashlib.sha1(key.encode()).hexdigest()
    cached = CACHE_DIR / f"{digest}.png"

    if cached.exists():
        try:
            cached.touch()
        except:
            pass
        return str(cached)

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
        img.save(cached, "PNG", optimize=True)

        import random

        if random.randint(1, 10) == 1:
            _cleanup_old_cache()

        return str(cached)

    except Exception as e:
        print(f"Preview generation failed: {e}")
        return image_path


def delete_cached_preview(image_path: str):
    """
    Delete cached previews for a specific image.

    Args:
        image_path: Path to source image
    """
    try:
        src = Path(image_path)
        if not src.exists():
            return

        src_str = str(src)

        for cached_file in CACHE_DIR.glob("*.png"):
            try:
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
