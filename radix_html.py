# radix_html.py - Consolidated HTML Generation
# All HTML generation utilities to eliminate duplication

import html as pyhtml
from typing import Optional


# ==================== CSS UTILITIES ====================

def build_gradient(start_color: str, end_color: str, angle: int = 135) -> str:
    """
    Build CSS linear gradient.
    Consolidates repeated gradient pattern.
    """
    return f"linear-gradient({angle}deg, {start_color} 0%, {end_color} 100%)"


def build_box_shadow(offset: str = "0 4px 12px", color: str = "rgba(0,0,0,0.06)") -> str:
    """Build consistent box shadow."""
    return f"{offset} {color}"


# ==================== BASE COMPONENTS ====================

def wrap_with_tooltip(content: str, tooltip_text: str, width: str = "240px") -> str:
    """
    Wrap content with tooltip.
    Consolidates repeated tooltip pattern.
    """
    return f"""<div class='radix-tooltip'>{content}<span class='radix-tooltiptext' style='width:{width};'>{tooltip_text}</span></div>"""


def build_badge(
    label: str,
    color: str,
    tooltip: Optional[str] = None,
    minimal: bool = False,
    badge_class: str = "meta-tag"
) -> str:
    """
    Build badge with optional tooltip.
    Consolidates frequency, usage, and other badge builders.
    
    Args:
        label: Badge text
        color: Primary color (hex)
        tooltip: Optional tooltip text
        minimal: If True, use minimal styling
        badge_class: CSS class name
    """
    # Build gradient background
    gradient = build_gradient(f"{color}15", f"{color}25")
    
    # Build style
    style = f"background: {gradient}; color: {color}; border: 1px solid {color}40; font-weight: 700;"
    if not minimal:
        style += " cursor: help;"
    
    # Build badge HTML
    badge_html = f"<span class='{badge_class}' style='{style}'>{pyhtml.escape(label)}</span>"
    
    # Wrap with tooltip if provided
    if tooltip and not minimal:
        return wrap_with_tooltip(badge_html, tooltip)
    
    return badge_html


def build_card(content: str, card_class: str = "char-card") -> str:
    """Build card container."""
    return f"<div class='{card_class}'>{content}</div>"


# ==================== SPECIALIZED BADGES ====================

def build_frequency_badge(freq: float, minimal: bool = False) -> str:
    """
    Build frequency badge with automatic color/label selection.
    Consolidates duplicate frequency badge logic.
    """
    from radix_utils import get_color_by_frequency, format_number
    
    if freq > 0:
        color, label = get_color_by_frequency(freq)
        badge_text = f"Frequency: {label} ({format_number(freq, short=True)}/M)"
        
        tooltip = """<strong>📊 Frequency Guide</strong><br><br>
<strong>Top 5%:</strong> Core survival vocabulary<br>
<strong>Top 25%:</strong> Standard for news & business<br>
<strong>Above Average:</strong> Topic-specific<br>
<strong>Below Average:</strong> Literary words<br>
<strong>Bottom 25%:</strong> Rare or archaic"""
        
        return build_badge(badge_text, color, tooltip if not minimal else None, minimal)
    else:
        tooltip = "No frequency data available in SUBTLEX-CH for this character."
        return build_badge("Freq: No Data", "#999", tooltip if not minimal else None, minimal)


def build_usage_badge(count: int, char: str, is_static: bool = False, minimal: bool = False) -> str:
    """
    Build usage badge showing derivative count.
    Consolidates duplicate usage badge logic.
    """
    from radix_utils import get_color_by_usage
    
    if count <= 0:
        return build_badge("Usage: None", "#999", "Not used in other characters", minimal)
    
    color, level = get_color_by_usage(count)
    badge_text = f"Usage: {level} ({count})"
    
    tooltip = f"<strong>Component Usage</strong><br><br>'{pyhtml.escape(char)}' appears in <strong>{count} derivative characters</strong>.<br><br>Higher usage often indicates a productive radical or phonetic component."
    
    return build_badge(badge_text, color, tooltip if not minimal and not is_static else None, minimal)


def build_script_badge(char: str, script_type: str) -> str:
    """
    Build script type badge (Simplified/Traditional).
    
    Args:
        char: Character to display
        script_type: 'simplified' or 'traditional'
    """
    if script_type == "traditional":
        return "<span class='meta-tag meta-tag-trad'>繁體 Traditional</span>"
    elif script_type == "simplified":
        return "<span class='meta-tag meta-tag-simp'>简体 Simplified</span>"
    return ""


# ==================== COMPLEX COMPONENTS ====================

def build_character_header(char: str, pinyin: str) -> str:
    """Build character display header with pinyin."""
    return f"""<div style='text-align: center; margin-bottom: 20px;'>
    <div style='font-size: 4em; font-weight: 700; color: #2c3e50;'>{pyhtml.escape(char)}</div>
    <div class='meta-pinyin' style='margin-top: 10px;'>{pyhtml.escape(pinyin)}</div>
</div>"""


def build_metadata_row(items: list[str]) -> str:
    """
    Build metadata row with tags.
    
    Args:
        items: List of HTML badge/tag strings
    """
    return f"<div class='meta-row'>{''.join(items)}</div>"


def build_definition_row(definition: str) -> str:
    """Build definition display row."""
    return f"<div class='def-row'>{pyhtml.escape(definition)}</div>"


def build_etymology_row(etymology: str) -> str:
    """Build etymology display row."""
    if not etymology:
        return ""
    return f"<div class='ety-row'>{pyhtml.escape(etymology)}</div>"


# ==================== PHRASE COMPONENTS ====================

def build_phrase_item(word: str, pinyin: str, meaning: str) -> str:
    """
    Build single phrase item HTML.
    
    Args:
        word: Chinese word/phrase
        pinyin: Pinyin pronunciation
        meaning: English meaning
    """
    from radix_utils import safe_text
    
    safe_meaning = safe_text(meaning, max_len=130)
    
    return f"""<div class='compound-item'>
    <span class='cp-word'>{pyhtml.escape(word)}</span>
    <span class='cp-pinyin'>{pyhtml.escape(pinyin)}</span>
    <span class='cp-mean'>{safe_meaning}</span>
</div>"""


def build_phrase_list(phrases: list[dict], title: str = "Phrases") -> str:
    """
    Build complete phrase list HTML.
    Consolidates duplicate phrase rendering logic.
    
    Args:
        phrases: List of dicts with 'word', 'pinyin', 'meanings' keys
        title: Section title
    """
    if not phrases:
        return ""
    
    items_html = []
    for phrase in phrases:
        word = phrase.get('word', '')
        pinyin = phrase.get('pinyin', '')
        meanings = phrase.get('meanings', '')
        
        if word:
            items_html.append(build_phrase_item(word, pinyin, meanings))
    
    if not items_html:
        return ""
    
    return f"""<div style='padding: 15px; background: #f1f8e9; border-radius: 8px; 
margin: 10px auto; border: 1px solid #dcedc8; max-width: 800px; 
max-height: 400px; overflow-y: auto;'>
<div style='font-weight: bold; margin-bottom: 10px; color: #2e7d32; 
border-bottom: 2px solid #a5d6a7; padding-bottom: 5px; text-align: center;'>{pyhtml.escape(title)}</div>
{''.join(items_html)}
</div>"""


# ==================== BUTTON COMPONENTS ====================

def build_button(
    text: str,
    style: str = "primary",
    icon: Optional[str] = None,
    extra_style: str = ""
) -> str:
    """
    Build styled button HTML.
    
    Args:
        text: Button text
        style: 'primary', 'secondary', or 'danger'
        icon: Optional emoji/icon
        extra_style: Additional CSS
    """
    color_map = {
        'primary': ('linear-gradient(135deg, #4caf50 0%, #45a049 100%)', '#fff', '#2e7d32'),
        'secondary': ('linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)', '#555', '#dee2e6'),
        'danger': ('linear-gradient(135deg, #f44336 0%, #d32f2f 100%)', '#fff', '#b71c1c'),
    }
    
    bg, text_color, border = color_map.get(style, color_map['secondary'])
    
    icon_html = f"<span style='font-size: 1.2em; margin-right: 8px;'>{icon}</span>" if icon else ""
    
    return f"""<button style='
display: inline-flex; align-items: center; justify-content: center;
padding: 12px 24px; border-radius: 8px; background: {bg};
color: {text_color}; border: 2px solid {border}; font-weight: 700;
font-size: 1em; cursor: pointer; transition: all 0.2s ease;
{extra_style}
' onmouseover="this.style.transform='translateY(-2px)'"
   onmouseout="this.style.transform='translateY(0)'">
{icon_html}{pyhtml.escape(text)}
</button>"""


# ==================== LAYOUT COMPONENTS ====================

def build_header(text: str, level: int = 1, style: str = "") -> str:
    """Build styled header."""
    tag = f"h{min(level, 6)}"
    return f"<{tag} class='lineage-header' style='{style}'>{pyhtml.escape(text)}</{tag}>"


def build_section(content: str, title: Optional[str] = None, expanded: bool = True) -> str:
    """Build collapsible section."""
    if not title:
        return content
    
    display = "block" if expanded else "none"
    
    return f"""<div style='margin: 20px 0;'>
<div style='cursor: pointer; font-weight: 700; padding: 10px; background: #f8f9fa; 
border-radius: 8px; margin-bottom: 10px;' onclick='this.nextElementSibling.style.display = 
this.nextElementSibling.style.display === "none" ? "block" : "none"'>
{pyhtml.escape(title)} <span style='float: right;'>▼</span>
</div>
<div style='display: {display};'>{content}</div>
</div>"""


def build_grid(items: list[str], columns: int = 10) -> str:
    """Build responsive grid layout."""
    return f"""<div style='display: grid; grid-template-columns: repeat({columns}, 1fr); 
gap: 10px; margin: 20px 0;'>{''.join(items)}</div>"""


# ==================== STATUS COMPONENTS ====================

def build_status_line(text: str, status: str = "success") -> str:
    """
    Build status line banner.
    
    Args:
        text: Status message
        status: 'success', 'info', 'warning', or 'error'
    """
    color_map = {
        'success': ('#0f5132', '#d1e7dd', '#95d5b2'),
        'info': ('#084298', '#cfe2ff', '#9ec5fe'),
        'warning': ('#664d03', '#fff3cd', '#ffecb5'),
        'error': ('#842029', '#f8d7da', '#f5c2c7'),
    }
    
    text_color, bg_start, border = color_map.get(status, color_map['info'])
    bg_end = bg_start  # Simplified - no gradient needed
    
    return f"""<div class='status-line' style='color: {text_color}; 
background: {bg_start}; border-color: {border};'>{pyhtml.escape(text)}</div>"""


# ==================== EXPORT ====================

__all__ = [
    # CSS utilities
    'build_gradient',
    'build_box_shadow',
    
    # Base components
    'wrap_with_tooltip',
    'build_badge',
    'build_card',
    
    # Specialized badges
    'build_frequency_badge',
    'build_usage_badge',
    'build_script_badge',
    
    # Complex components
    'build_character_header',
    'build_metadata_row',
    'build_definition_row',
    'build_etymology_row',
    
    # Phrase components
    'build_phrase_item',
    'build_phrase_list',
    
    # Button components
    'build_button',
    
    # Layout components
    'build_header',
    'build_section',
    'build_grid',
    
    # Status components
    'build_status_line',
]
