"""Binary and image processing functions for FDSL."""

import base64
import gzip
import zlib
import bz2
import io
from typing import Any, Dict


def binary_size(data: bytes) -> int:
    """
    Get the size of binary data in bytes.

    Args:
        data: Binary data

    Returns:
        Size in bytes

    Example:
        binary_size(image_data)  # Returns: 51234
    """
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("binary_size requires bytes or bytearray")
    return len(data)


def binary_encode_base64(data: bytes) -> str:
    """
    Encode binary data to base64 string.

    Args:
        data: Binary data to encode

    Returns:
        Base64 encoded string

    Example:
        binary_encode_base64(image_data)  # Returns: "iVBORw0KGgoAAAANS..."
    """
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("binary_encode_base64 requires bytes or bytearray")
    return base64.b64encode(data).decode('utf-8')


def binary_decode_base64(data: str) -> bytes:
    """
    Decode base64 string to binary data.

    Args:
        data: Base64 encoded string

    Returns:
        Decoded binary data

    Example:
        binary_decode_base64("iVBORw0KGgoAAAANS...")  # Returns: b'\x89PNG...'
    """
    if not isinstance(data, str):
        raise ValueError("binary_decode_base64 requires string")
    return base64.b64decode(data)


def image_dimensions(data: bytes) -> Dict[str, int]:
    """
    Get image dimensions (width and height).

    Args:
        data: Image binary data (JPEG, PNG, GIF, etc.)

    Returns:
        Dictionary with 'width' and 'height' keys

    Example:
        image_dimensions(image_data)  # Returns: {"width": 1920, "height": 1080}
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("PIL/Pillow is required for image processing functions. Install with: pip install Pillow")

    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("image_dimensions requires bytes or bytearray")

    try:
        img = Image.open(io.BytesIO(data))
        return {"width": img.width, "height": img.height}
    except Exception as e:
        raise ValueError(f"Failed to read image dimensions: {e}")


def image_invert(data: bytes) -> bytes:
    """
    Invert image colors (negative effect).

    Args:
        data: Image binary data (JPEG, PNG, etc.)

    Returns:
        Processed image as bytes in the same format

    Example:
        image_invert(image_data)  # Returns inverted image bytes
    """
    try:
        from PIL import Image, ImageOps
    except ImportError:
        raise RuntimeError("PIL/Pillow is required for image processing functions. Install with: pip install Pillow")

    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("image_invert requires bytes or bytearray")

    try:
        img = Image.open(io.BytesIO(data))

        # Store original format
        original_format = img.format or 'JPEG'

        # Convert to RGB if necessary (invert doesn't work on some modes)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        # Invert colors
        inverted = ImageOps.invert(img.convert('RGB'))

        # Save to bytes
        output = io.BytesIO()
        inverted.save(output, format=original_format, quality=95)
        return output.getvalue()
    except Exception as e:
        raise ValueError(f"Failed to invert image: {e}")


def image_grayscale(data: bytes) -> bytes:
    """
    Convert image to grayscale.

    Args:
        data: Image binary data (JPEG, PNG, etc.)

    Returns:
        Grayscale image as bytes in the same format

    Example:
        image_grayscale(image_data)  # Returns grayscale image bytes
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("PIL/Pillow is required for image processing functions. Install with: pip install Pillow")

    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("image_grayscale requires bytes or bytearray")

    try:
        img = Image.open(io.BytesIO(data))

        # Store original format
        original_format = img.format or 'JPEG'

        # Convert to grayscale
        grayscale = img.convert('L')

        # Save to bytes
        output = io.BytesIO()
        grayscale.save(output, format=original_format, quality=95)
        return output.getvalue()
    except Exception as e:
        raise ValueError(f"Failed to convert image to grayscale: {e}")


def image_resize(data: bytes, width: int, height: int) -> bytes:
    """
    Resize image to specified dimensions.

    Args:
        data: Image binary data (JPEG, PNG, etc.)
        width: Target width in pixels
        height: Target height in pixels

    Returns:
        Resized image as bytes in the same format

    Example:
        image_resize(image_data, 800, 600)  # Returns resized image
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("PIL/Pillow is required for image processing functions. Install with: pip install Pillow")

    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("image_resize requires bytes or bytearray")
    if not isinstance(width, int) or width <= 0:
        raise ValueError("width must be a positive integer")
    if not isinstance(height, int) or height <= 0:
        raise ValueError("height must be a positive integer")

    try:
        img = Image.open(io.BytesIO(data))

        # Store original format
        original_format = img.format or 'JPEG'

        # Resize using high-quality Lanczos resampling
        resized = img.resize((width, height), Image.Resampling.LANCZOS)

        # Save to bytes
        output = io.BytesIO()
        resized.save(output, format=original_format, quality=95)
        return output.getvalue()
    except Exception as e:
        raise ValueError(f"Failed to resize image: {e}")


def image_rotate(data: bytes, degrees: float) -> bytes:
    """
    Rotate image by specified degrees (counter-clockwise).

    Args:
        data: Image binary data (JPEG, PNG, etc.)
        degrees: Rotation angle in degrees (positive = counter-clockwise)

    Returns:
        Rotated image as bytes in the same format

    Example:
        image_rotate(image_data, 90)   # Rotate 90° counter-clockwise
        image_rotate(image_data, -45)  # Rotate 45° clockwise
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("PIL/Pillow is required for image processing functions. Install with: pip install Pillow")

    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("image_rotate requires bytes or bytearray")
    if not isinstance(degrees, (int, float)):
        raise ValueError("degrees must be a number")

    try:
        img = Image.open(io.BytesIO(data))

        # Store original format
        original_format = img.format or 'JPEG'

        # Rotate image (expand=True to fit entire rotated image)
        rotated = img.rotate(degrees, expand=True, resample=Image.Resampling.BICUBIC)

        # Save to bytes
        output = io.BytesIO()
        rotated.save(output, format=original_format, quality=95)
        return output.getvalue()
    except Exception as e:
        raise ValueError(f"Failed to rotate image: {e}")


# Compression functions
def binary_compress_gzip(data: bytes, level: int = 9) -> bytes:
    """
    Compress binary data using gzip compression.

    Args:
        data: Binary data to compress
        level: Compression level (0-9, where 9 is maximum compression)

    Returns:
        Compressed binary data

    Example:
        compressed = binary_compress_gzip(file_data)
        # Original: 157 bytes -> Compressed: 78 bytes
    """
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("binary_compress_gzip requires bytes or bytearray")
    if not isinstance(level, int) or level < 0 or level > 9:
        raise ValueError("level must be an integer between 0 and 9")

    return gzip.compress(data, compresslevel=level)


def binary_decompress_gzip(data: bytes) -> bytes:
    """
    Decompress gzip-compressed binary data.

    Args:
        data: Gzip-compressed binary data

    Returns:
        Decompressed binary data

    Example:
        original = binary_decompress_gzip(compressed_data)
    """
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("binary_decompress_gzip requires bytes or bytearray")

    try:
        return gzip.decompress(data)
    except Exception as e:
        raise ValueError(f"Failed to decompress gzip data: {e}")


def binary_compress_zlib(data: bytes, level: int = 9) -> bytes:
    """
    Compress binary data using zlib compression (faster than gzip).

    Args:
        data: Binary data to compress
        level: Compression level (0-9, where 9 is maximum compression)

    Returns:
        Compressed binary data

    Example:
        compressed = binary_compress_zlib(file_data)
    """
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("binary_compress_zlib requires bytes or bytearray")
    if not isinstance(level, int) or level < 0 or level > 9:
        raise ValueError("level must be an integer between 0 and 9")

    return zlib.compress(data, level=level)


def binary_decompress_zlib(data: bytes) -> bytes:
    """
    Decompress zlib-compressed binary data.

    Args:
        data: Zlib-compressed binary data

    Returns:
        Decompressed binary data

    Example:
        original = binary_decompress_zlib(compressed_data)
    """
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("binary_decompress_zlib requires bytes or bytearray")

    try:
        return zlib.decompress(data)
    except Exception as e:
        raise ValueError(f"Failed to decompress zlib data: {e}")


def binary_compress_bz2(data: bytes, level: int = 9) -> bytes:
    """
    Compress binary data using bz2 compression (best compression ratio).

    Args:
        data: Binary data to compress
        level: Compression level (1-9, where 9 is maximum compression)

    Returns:
        Compressed binary data

    Example:
        compressed = binary_compress_bz2(file_data)
        # Typically achieves better compression than gzip
    """
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("binary_compress_bz2 requires bytes or bytearray")
    if not isinstance(level, int) or level < 1 or level > 9:
        raise ValueError("level must be an integer between 1 and 9")

    return bz2.compress(data, compresslevel=level)


def binary_decompress_bz2(data: bytes) -> bytes:
    """
    Decompress bz2-compressed binary data.

    Args:
        data: Bz2-compressed binary data

    Returns:
        Decompressed binary data

    Example:
        original = binary_decompress_bz2(compressed_data)
    """
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("binary_decompress_bz2 requires bytes or bytearray")

    try:
        return bz2.decompress(data)
    except Exception as e:
        raise ValueError(f"Failed to decompress bz2 data: {e}")


# Export functions for FDSL registry
# Format: "function_name": (function_reference, (min_args, max_args))
DSL_BINARY_FUNCS = {
    # Binary utilities
    "binary_size":           (binary_size,           (1, 1)),
    "binary_encode_base64":  (binary_encode_base64,  (1, 1)),
    "binary_decode_base64":  (binary_decode_base64,  (1, 1)),

    # Compression (with optional compression level)
    "binary_compress_gzip":    (binary_compress_gzip,    (1, 2)),
    "binary_decompress_gzip":  (binary_decompress_gzip,  (1, 1)),
    "binary_compress_zlib":    (binary_compress_zlib,    (1, 2)),
    "binary_decompress_zlib":  (binary_decompress_zlib,  (1, 1)),
    "binary_compress_bz2":     (binary_compress_bz2,     (1, 2)),
    "binary_decompress_bz2":   (binary_decompress_bz2,   (1, 1)),

    # Image processing
    "image_dimensions":  (image_dimensions,  (1, 1)),
    "image_invert":      (image_invert,      (1, 1)),
    "image_grayscale":   (image_grayscale,   (1, 1)),
    "image_resize":      (image_resize,      (3, 3)),
    "image_rotate":      (image_rotate,      (2, 2)),
}
