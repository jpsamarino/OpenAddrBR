"""Text normalization utilities."""

from unicodedata import normalize


def text_to_ascii(text: str) -> str:
    """
    Convert text to ASCII by removing accents/diacritics.

    Args:
        text: Input string which may contain accented characters.

    Returns:
        ASCII representation of the input string with accents removed.
    """
    return normalize('NFKD', text or "").encode('ASCII', 'ignore').decode('ASCII')


def normalize_text(text: str) -> str:
    """
    Normalize text to uppercase ASCII.

    Args:
        text: Input string to normalize.

    Returns:
        Uppercase ASCII representation of the input string.
    """
    return text_to_ascii(text).upper()