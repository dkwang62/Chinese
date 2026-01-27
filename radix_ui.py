# radix_ui.py - CLEANED VERSION
# UI components - delegates HTML generation to radix_html

import streamlit as st
from streamlit.components.v1 import html as st_html
import html as pyhtml

# Import from our consolidated modules
from radix_utils import get_char_field, get_both_variants, clean_field
from radix_html import (
    build_frequency_badge, build_usage_badge, build_script_badge,
    build_metadata_row, build_definition_row, build_etymology_row,
    wrap_with_tooltip
)
from radix_core import (
    component_map, get_char_definition_en, component_usage_count,
    analyze_component_structure, get_pronunciation_family, get_semantic_family,
    cc_t2s, cc_s2t
)


# ==================== STYLES ====================

def apply_styles():
    """Apply all CSS styles."""
    st.markdown("""
    <style>
    .main .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    .char-card {background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); padding: 24px; border-radius: 16px; margin-bottom: 0px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e9ecef; transition: all 0.3s ease;}
    .char-card:hover {box-shadow: 0 6px 20px rgba(0,0,0,0.1); transform: translateY(-2px);}
    .meta-row {font-size: 0.95em; color: #555; margin-bottom: 12px; display: flex; align-items: center; flex-wrap: wrap; gap: 12px;}
    .meta-pinyin {font-weight: 700; font-size: 2.4em; color: #d35400; text-shadow: 0 2px 4px rgba(211, 84, 0, 0.1);}
    .meta-tag {background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 4px 12px; border-radius: 8px; font-size: 0.85em; color: #495057; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.04); margin-bottom: 6px; display: inline-block;}
    .meta-tag-trad {background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%); color: #856404; border: 1px solid #ffd54f;}
    .meta-tag-simp {background: linear-gradient(135deg, #d1e7dd 0%, #a3cfbb 100%); color: #0f5132; border: 1px solid #81c784;}
    .def-row {font-size: 1.15em; line-height: 1.6; color: #2c3e50; margin-bottom: 10px; font-weight: 500;}
    .ety-row {font-size: 0.92em; color: #666; font-style: italic; border-top: 2px solid #e9ecef; padding-top: 12px; margin-top: 8px; line-height: 1.5;}
    section[data-testid="stSidebar"] .meta-pinyin {font-size: 2.0em !important;}
    section[data-testid="stSidebar"] .char-card {padding: 16px !important;}
    section[data-testid="stSidebar"] .def-row {font-size: 1.05em !important;}
    .comp-grid .stButton > button {width: 100% !important; font-size: 2.2em !important; height: 85px !important; background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important; border: 2px solid #dee2e6 !important; border-radius: 14px !important; box-shadow: 0 3px 8px rgba(0,0,0,0.08) !important; padding: 0 !important; line-height: 85px !important; font-weight: 600 !important; transition: all 0.2s ease !important;}
    .comp-grid .stButton > button:hover {background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%) !important; border-color: #f2c6c6 !important; color: #c0392b !important; transform: translateY(-3px) !important; box-shadow: 0 6px 16px rgba(192, 57, 43, 0.15) !important;}
    .char-btn-wrap .stButton > button {width: 100% !important; font-size: 3.8em !important; font-weight: 700 !important; background: linear-gradient(135deg, #ffffff 0%, #f0f4f8 100%) !important; border: 3px solid #dee2e6 !important; padding: 10px !important; min-height: 90px !important; border-radius: 16px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important; transition: all 0.25s ease !important;}
    .char-btn-wrap .stButton > button:hover {background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%) !important; border-color: #3b82f6 !important; transform: scale(1.02) !important; box-shadow: 0 6px 20px rgba(59, 130, 246, 0.2) !important;}
    .pen-btn-wrap .stButton > button {width: 100% !important; font-size: 1.6em !important; border: 2px solid #dee2e6 !important; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%) !important; margin-top: 8px !important; height: 45px !important; line-height: 1 !important; color: #555 !important; font-weight: 600 !important; border-radius: 12px !important; transition: all 0.2s ease !important;}
    .pen-btn-wrap .stButton > button:hover {background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%) !important; border-color: #64b5f6 !important; color: #1565c0 !important; transform: translateY(-2px) !important; box-shadow: 0 4px 12px rgba(100, 181, 246, 0.2) !important;}
    .char-static-box {font-size: 3.8em; font-weight: 700; background: linear-gradient(135deg, #fafafa 0%, #f0f0f0 100%); color: #bbb; border: 2px solid #e0e0e0; border-radius: 16px; padding: 10px; min-height: 90px; display: flex; align-items: center; justify-content: center; width: 100%; cursor: default; box-shadow: 0 2px 8px rgba(0,0,0,0.04);}
    .status-line {font-size: 1.1em; font-weight: 600; color: #0f5132; background: linear-gradient(135deg, #d1e7dd 0%, #c3e6cb 100%); border: 2px solid #95d5b2; padding: 18px; border-radius: 12px; margin: 20px 0 30px 0; box-shadow: 0 3px 10px rgba(15, 81, 50, 0.08);}
    .status-tag {background: linear-gradient(135deg, #ffffff 0%, #f1f3f5 100%); color: #2c3e50; padding: 6px 14px; border-radius: 8px; font-weight: 700; font-size: 0.9em; border: 2px solid #dee2e6; display: inline-flex; align-items: center; box-shadow: 0 2px 6px rgba(0,0,0,0.06);}
    .lineage-header {font-size: 1.4em; font-weight: 800; color: #2c3e50; margin: 30px 0 20px 0; padding: 12px 20px; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-left: 5px solid #1976d2; border-radius: 8px; box-shadow: 0 2px 8px rgba(25, 118, 210, 0.1);}
    .compound-item {display: flex; align-items: baseline; margin-bottom: 10px; padding: 12px; border-bottom: 2px solid #e9ecef; border-radius: 8px; background: #ffffff; transition: all 0.2s ease;}
    .compound-item:hover {background: #f8f9fa; transform: translateX(4px);}
    .cp-word {font-weight: 700; font-size: 1.2em; color: #2c3e50; min-width: 85px; margin-right: 15px;}
    .cp-pinyin {color: #d35400; font-family: 'Monaco', 'Menlo', monospace; margin-right: 15px; font-weight: 600; font-size: 1.5em;}
    .cp-mean {color: #495057; font-size: 1em; flex: 1; line-height: 1.5;}
    .char-btn-hint {margin-top: 6px; text-align: center; font-size: 0.86em; color: #6c757d; font-weight: 700;}
    .char-btn-hint.previewing {color: #c0392b;}
    .splash-wrap {max-width: 850px; margin: 0 auto; padding: 60px 20px 20px 20px;}
    .splash-card {background: #ffffff; border: 1px solid #e0e0e0; border-radius: 40px; padding: 60px; box-shadow: 0 15px 50px rgba(0,0,0,0.05); text-align: center;}
    .splash-title {font-size: 3.0em; font-weight: 800; color: #1a1a1a; margin-bottom: 10px;}
    .splash-sub {font-size: 1.3em; color: #666;}
    .palace-entrance-container {text-align: center; margin: 60px 0;}
    .grand-torii {font-size: 250px !important; line-height: 1; filter: drop-shadow(0 10px 20px rgba(0,0,0,0.1));}
    .entrance-text {color: #2c3e50; font-size: 24px; font-weight: 700; margin-top: 20px; margin-bottom: 30px; letter-spacing: 2px;}
    .radix-tooltip {position: relative; display: inline-block; cursor: help;}
    .radix-tooltip .radix-tooltiptext {visibility: hidden; width: 240px; background-color: #262626; color: #fff; text-align: left; border-radius: 6px; padding: 12px; position: absolute; z-index: 1000; bottom: 125%; left: 50%; margin-left: -120px; opacity: 0; transition: opacity 0.3s; font-size: 0.8rem; font-weight: normal; line-height: 1.4; box-shadow: 0 4px 12px rgba(0,0,0,0.3); pointer-events: none;}
    .radix-tooltip .radix-tooltiptext::after {content: ""; position: absolute; top: 100%; left: 50%; margin-left: -5px; border-width: 5px; border-style: solid; border-color: #262626 transparent transparent transparent;}
    .radix-tooltip:hover .radix-tooltiptext {visibility: visible; opacity: 1;}
    .radix-tooltiptext strong {color: #ffb74d;}
    .insight-box {background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; margin-top: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);}
    .insight-title {font-weight: 800; color: #37474f; font-size: 1.1em; margin-bottom: 15px; display: flex; align-items: center; gap: 8px;}
    .role-badge {display: inline-flex; align-items: center; padding: 6px 12px; border-radius: 8px; font-size: 0.9em; font-weight: 600; margin-right: 10px; margin-bottom: 8px;}
    .role-semantic {background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9;}
    .role-phonetic {background: #e3f2fd; color: #1565c0; border: 1px solid #bbdefb;}
    .family-list {display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px;}
    .family-char {font-size: 1.4em; color: #333; cursor: pointer; padding: 2px 8px; background: #f5f5f5; border-radius: 6px; border: 1px solid #eee;}
    </style>
    """, unsafe_allow_html=True)


# ==================== CARD GENERATION ====================

def generate_clean_card_html(char: str, usage_count: int = 0, is_static: bool = False, minimal: bool = False) -> str:
    """
    Generate character card HTML using consolidated HTML builders.
    """
    # Get all character data using utilities
    pinyin = clean_field(get_char_field(char, "meta", "pinyin", default=""))
    definition = get_char_definition_en(char)
    
    # Build metadata badges using consolidated builders
    badges = []
    
    # Frequency badge
    freq = component_map.get(char, {}).get('freq_per_million', 0.0)
    badges.append(build_frequency_badge(freq, minimal))
    
    # Usage badge
    badges.append(build_usage_badge(usage_count, char, is_static, minimal))
    
    # Script badge if variants exist
    variants = get_both_variants(char)
    if len(variants) > 1:
        if cc_t2s and cc_t2s.convert(char) == char:
            badges.append(build_script_badge(char, "simplified"))
        elif cc_s2t and cc_s2t.convert(char) == char:
            badges.append(build_script_badge(char, "traditional"))
    
    # Build card HTML
    card_html = f"<div class='char-card'>"
    card_html += f"<div class='meta-pinyin'>{pyhtml.escape(pinyin)}</div>"
    card_html += build_metadata_row(badges)
    card_html += build_definition_row(definition)
    
    # Etymology if not minimal
    if not minimal:
        meta = get_char_field(char, "meta", default={})
        from radix_core import get_etymology_text
        etymology = get_etymology_text(meta)
        if etymology:
            card_html += build_etymology_row(etymology)
    
    card_html += "</div>"
    return card_html


# ==================== LEARNING INSIGHTS ====================

def render_learning_insights_html(char: str) -> tuple:
    """
    Generate learning insights HTML with character analysis.
    Returns (html, height, prompt_text)
    """
    analysis = analyze_component_structure(char)
    sem = analysis.get("semantic")
    pho = analysis.get("phonetic")
    pho_pinyin = analysis.get("phonetic_pinyin")
    is_match = analysis.get("is_sound_match")
    
    def_en = get_char_definition_en(char)
    decomposition = get_char_field(char, "meta", "decomposition", default="None")
    
    p_fam = get_pronunciation_family(char)
    s_fam = get_semantic_family(char)
    
    # Build HTML using our utilities
    html_parts = ['<div class="insight-box"><div class="insight-title">🧠 Character Logic & Patterns</div>']
    
    # Component roles
    if sem or pho:
        html_parts.append('<div style="margin-bottom:15px;">')
        if sem:
            html_parts.append(f'<span class="role-badge role-semantic">Meaning (Radical): {pyhtml.escape(sem)}</span>')
        if pho:
            match_label = "Sound Match ✓" if is_match else "Sound Component"
            html_parts.append(f'<span class="role-badge role-phonetic">{match_label}: {pyhtml.escape(pho)} ({pyhtml.escape(pho_pinyin)})</span>')
        html_parts.append('</div>')
    
    # Pronunciation family
    if p_fam:
        html_parts.append(f'<div style="margin-bottom:15px;"><strong>🔊 Pronunciation Family:</strong> Characters sharing {pyhtml.escape(pho or "component")}</div>')
        html_parts.append('<div class="family-list">')
        for c in p_fam:
            html_parts.append(f'<span class="family-char">{pyhtml.escape(c)}</span>')
        html_parts.append('</div>')
    
    # Semantic family
    if s_fam:
        html_parts.append(f'<div style="margin-top:15px; margin-bottom:15px;"><strong>📚 Meaning Family:</strong> Characters sharing {pyhtml.escape(sem or "radical")}</div>')
        html_parts.append('<div class="family-list">')
        for c in s_fam:
            html_parts.append(f'<span class="family-char">{pyhtml.escape(c)}</span>')
        html_parts.append('</div>')
    
    html_parts.append('</div>')
    
    # Build prompt text
    prompt_lines = [
        "Task 4 — Logic & Pattern Tutor",
        "",
        f"INPUT: char={char}, def_en={def_en}, decomposition={decomposition}, semantic={sem or 'None'}, phonetic={pho or 'None'}, phonetic_pinyin={pho_pinyin or 'None'}, is_sound_match={is_match}, pronunciation_family={', '.join(p_fam) if p_fam else 'None'}, semantic_family={', '.join(s_fam) if s_fam else 'None'}",
        "",
        "TASK: Explain component roles and families conservatively.",
    ]
    prompt_text = "\n".join(prompt_lines)
    
    content = ''.join(html_parts)
    base_height = 200
    if p_fam:
        base_height += 80
    if s_fam:
        base_height += 80
    
    return content, base_height, prompt_text


# ==================== DOWNLOAD & CLIPBOARD ====================

def render_ipad_safe_download_html(content: str, filename: str, button_text: str = "Download"):
    """Render download button HTML."""
    import base64
    b64 = base64.b64encode(content.encode()).decode()
    return f"""<a href='data:text/plain;base64,{b64}' download='{filename}' style='display:inline-block; padding:10px 20px; background:#4caf50; color:white; text-decoration:none; border-radius:5px; font-weight:700;'>{button_text}</a>"""


def render_copy_to_clipboard(text: str, unique_id: str):
    """Render copy-to-clipboard button."""
    st_html(f"""
<button onclick="navigator.clipboard.writeText(document.getElementById('text_{unique_id}').value)" 
style='padding:10px 20px; background:#2196f3; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:700;'>
📋 Copy to Clipboard
</button>
<textarea id='text_{unique_id}' style='position:absolute; left:-9999px;'>{pyhtml.escape(text)}</textarea>
""", height=50)


def get_stroke_order_sidebar_html(char: str) -> str:
    """Get stroke order sidebar HTML."""
    return f"<div style='text-align:center; padding:20px; background:#f8f9fa; border-radius:10px; margin:10px 0;'><div style='font-size:3em; font-weight:700; color:#2c3e50;'>{pyhtml.escape(char)}</div><div style='font-size:0.9em; color:#666; margin-top:10px;'>Stroke order view</div></div>"


# ==================== UI COMPONENTS ====================

def render_definition_search_ui(key_prefix: str):
    """Render definition search interface."""
    st.markdown("**English Definition Search**")
    key = f"{key_prefix}_def_search"
    st.text_input("Search definitions", key=key, placeholder="e.g., water, fire, mountain", label_visibility="collapsed")
    return key
