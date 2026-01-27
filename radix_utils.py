# radix_utils.py - Consolidated Utilities
# All cross-cutting utility functions to eliminate code duplication

import unicodedata
from typing import Any, Optional

# Import core dependencies (assume these exist in radix_core)
try:
    from radix_core import component_map, cc_t2s, cc_s2t
except ImportError:
    component_map = {}
    cc_t2s = cc_s2t = None


# ==================== TEXT PROCESSING ====================

def normalize_pinyin(pinyin_str: str) -> str:
    """
    Remove tone marks from pinyin for fuzzy search (e.g., 'nǐ' -> 'ni').
    Consolidated from duplicate implementations.
    """
    if not isinstance(pinyin_str, str):
        return ""
    # Decompose unicode and strip diacritical marks
    normalized = unicodedata.normalize('NFD', pinyin_str)
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn').lower()


def safe_text(text: str, max_len: Optional[int] = None) -> str:
    """
    Safely escape HTML and optionally truncate text.
    Consolidates repeated pyhtml.escape() + truncation pattern.
    """
    import html as pyhtml
    
    if not isinstance(text, str):
        text = str(text) if text else ""
    
    escaped = pyhtml.escape(text)
    
    if max_len and len(escaped) > max_len:
        return escaped[:max_len] + "..."
    
    return escaped


def normalize_stroke_count(value: Any) -> Optional[int]:
    """
    Extract integer stroke count from various input types.
    Consolidates repeated validation pattern.
    """
    try:
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
        elif isinstance(value, str) and value.isdigit():
            return int(value)
        return None
    except (ValueError, TypeError):
        return None


# ==================== CHARACTER OPERATIONS ====================

def get_char_field(char: str, *path, default: Any = "") -> Any:
    """
    Safely navigate nested dictionary structure for character data.
    Replaces: component_map.get(c, {}).get("meta", {}).get("field", "")
    
    Usage:
        get_char_field(char, "meta", "definition")
        get_char_field(char, "meta", "decomposition", default="None")
    """
    if not char or char not in component_map:
        return default
    
    result = component_map[char]
    for key in path:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    
    return result if result is not None else default


def get_variant_char(char: str, prefer: str = "simplified") -> str:
    """
    Get character variant (simplified/traditional).
    Consolidates repeated cc_t2s/cc_s2t checks.
    
    Args:
        char: Input character
        prefer: 'simplified' or 'traditional'
    
    Returns:
        Variant character, or original if no conversion available
    """
    if not char:
        return char
    
    if prefer == "simplified" and cc_t2s:
        variant = cc_t2s.convert(char)
        return variant if variant != char else char
    elif prefer == "traditional" and cc_s2t:
        variant = cc_s2t.convert(char)
        return variant if variant != char else char
    
    return char


def get_both_variants(char: str) -> list[str]:
    """
    Get both simplified and traditional variants, removing duplicates.
    Returns list with original first, then variant if different.
    """
    if not char:
        return []
    
    variants = [char]
    
    if cc_t2s:
        s_variant = cc_t2s.convert(char)
        if s_variant != char and s_variant not in variants:
            variants.append(s_variant)
    
    if cc_s2t:
        t_variant = cc_s2t.convert(char)
        if t_variant != char and t_variant not in variants:
            variants.append(t_variant)
    
    return variants


def clean_field(value: Any, default: str = "") -> str:
    """
    Clean and normalize field value.
    Consolidates repeated cleaning pattern.
    """
    if value is None:
        return default
    
    if not isinstance(value, str):
        value = str(value)
    
    return value.strip() or default


# ==================== VALIDATION ====================

def validate_character(char: str) -> tuple[bool, Optional[str]]:
    """
    Validate if character exists in component map.
    Returns: (is_valid, error_message)
    """
    if not char or not isinstance(char, str):
        return False, "Invalid input"
    
    if len(char) != 1:
        return False, "One character only"
    
    # Check if character exists directly or via variant
    if char in component_map:
        return True, None
    
    # Try variants
    variants = get_both_variants(char)
    for variant in variants:
        if variant in component_map:
            return True, None
    
    return False, "Character not found"


# ==================== LIST OPERATIONS ====================

def deduplicate_list(items: list) -> list:
    """
    Remove duplicates while preserving order.
    More efficient than repeated list(dict.fromkeys()) pattern.
    """
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def batch_process(items: list, batch_size: int = 25):
    """
    Generate batches from list.
    Consolidates pagination logic.
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


# ==================== DISPLAY HELPERS ====================

def format_number(num: int | float, short: bool = False) -> str:
    """
    Format numbers consistently across app.
    
    Args:
        num: Number to format
        short: If True, use abbreviations (1K, 1M)
    """
    if short:
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
    
    return f"{num:,.0f}"


def truncate_with_ellipsis(text: str, max_len: int, at_word: bool = False) -> str:
    """
    Truncate text intelligently.
    
    Args:
        text: Text to truncate
        max_len: Maximum length
        at_word: If True, break at word boundary
    """
    if len(text) <= max_len:
        return text
    
    if at_word:
        # Find last space before max_len
        truncated = text[:max_len]
        last_space = truncated.rfind(' ')
        if last_space > max_len * 0.8:  # Don't cut too early
            return truncated[:last_space] + "..."
    
    return text[:max_len] + "..."


# ==================== COLOR HELPERS ====================

def get_color_by_frequency(freq: float) -> tuple[str, str]:
    """
    Get color and label for frequency value.
    Consolidates frequency badge logic.
    
    Returns: (color_hex, label_text)
    """
    FREQ_PERCENTILES = {
        'p95': 8500,  # Top 5%
        'p75': 3200,  # Top 25%
        'p50': 800,   # Top 50%
        'p25': 150    # Bottom 25%
    }
    
    if freq >= FREQ_PERCENTILES['p95']:
        return "#2e7d32", "Top 5%"
    elif freq >= FREQ_PERCENTILES['p75']:
        return "#558b2f", "Top 25%"
    elif freq >= FREQ_PERCENTILES['p50']:
        return "#ff8f00", "Above Average"
    elif freq >= FREQ_PERCENTILES['p25']:
        return "#f57c00", "Below Average"
    else:
        return "#c62828", "Bottom 25%"


def get_color_by_usage(count: int) -> tuple[str, str]:
    """
    Get color and label for usage count.
    
    Returns: (color_hex, label_text)
    """
    if count >= 100:
        return "#2e7d32", "Very High"
    elif count >= 50:
        return "#558b2f", "High"
    elif count >= 20:
        return "#ff8f00", "Medium"
    elif count >= 5:
        return "#f57c00", "Low"
    else:
        return "#c62828", "Very Low"


# ==================== EXPORT ====================

__all__ = [
    # Text processing
    'normalize_pinyin',
    'safe_text',
    'normalize_stroke_count',
    'clean_field',
    'truncate_with_ellipsis',
    
    # Character operations
    'get_char_field',
    'get_variant_char',
    'get_both_variants',
    'validate_character',
    
    # List operations
    'deduplicate_list',
    'batch_process',
    
    # Display helpers
    'format_number',
    'get_color_by_frequency',
    'get_color_by_usage',
]
