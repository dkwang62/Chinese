# app.py
# Main Streamlit app for Radix - with definition search and commonality ranking

import streamlit as st
from streamlit.components.v1 import html as st_html
import json
import html as pyhtml
import math
import uuid

from radix_core import (
    component_map,
    stats_cache,
    cc_t2s,
    cc_s2t,
    get_db_connection,
    batch_get_phrase_details,
    search_phrases_by_definition,
    get_stroke_count,
    component_usage_count,
    apply_script_filter,
    normalize_single_hanzi,
    resolve_to_known_variant,
    build_chatgpt_prompt,
    generate_clean_card_html,
    render_ipad_safe_download_html,
    get_stroke_order_sidebar_html,
    get_stroke_order_view_html,
    SCRIPT_FILTERS,
    IDC_CHARS,
    sort_key_usage_primary,
    sort_key_frequency_primary,
)

st.set_page_config(layout="wide", page_title="Radix", page_icon="🈑")


# --- Dynamic CSS ---
def apply_dynamic_css():
    css = """
    <style>
    .main .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    .char-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 24px;
        border-radius: 16px;
        margin-bottom: 0px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        border: 1px solid #e9ecef;
        transition: all 0.3s ease;
    }
    .char-card:hover {
        box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    .meta-row {
        font-size: 0.95em;
        color: #555;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }
    .meta-pinyin {
        font-weight: 700;
        font-size: 2.4em;
        color: #d35400;
        text-shadow: 0 2px 4px rgba(211, 84, 0, 0.1);
    }
    .meta-tag {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 0.85em;
        color: #495057;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .meta-tag-trad {
        background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
        color: #856404;
        border: 1px solid #ffd54f;
    }
    .meta-tag-simp {
        background: linear-gradient(135deg, #d1e7dd 0%, #a3cfbb 100%);
        color: #0f5132;
        border: 1px solid #81c784;
    }
    .def-row {
        font-size: 1.15em;
        line-height: 1.6;
        color: #2c3e50;
        margin-bottom: 10px;
        font-weight: 500;
    }
    .ety-row {
        font-size: 0.92em;
        color: #666;
        font-style: italic;
        border-top: 2px solid #e9ecef;
        padding-top: 12px;
        margin-top: 8px;
        line-height: 1.5;
    }
    .comp-grid .stButton > button {
        width: 100% !important;
        font-size: 2.2em !important;
        height: 85px !important;
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
        border: 2px solid #dee2e6 !important;
        border-radius: 14px !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.08) !important;
        padding: 0 !important;
        line-height: 85px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .comp-grid .stButton > button:hover {
        background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%) !important;
        border-color: #f2c6c6 !important;
        color: #c0392b !important;
        transform: translateY(-3px) !important;
        box-shadow: 0 6px 16px rgba(192, 57, 43, 0.15) !important;
    }
    .char-btn-wrap .stButton > button {
        width: 100% !important;
        font-size: 3.8em !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #ffffff 0%, #f0f4f8 100%) !important;
        border: 3px solid #dee2e6 !important;
        padding: 10px !important;
        min-height: 90px !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        transition: all 0.25s ease !important;
    }
    .char-btn-wrap .stButton > button:hover {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%) !important;
        border-color: #3b82f6 !important;
        transform: scale(1.02) !important;
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.2) !important;
    }
    .pen-btn-wrap .stButton > button {
        width: 100% !important;
        font-size: 1.6em !important;
        border: 2px solid #dee2e6 !important;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%) !important;
        margin-top: 8px !important;
        height: 45px !important;
        line-height: 1 !important;
        color: #555 !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        transition: all 0.2s ease !important;
    }
    .pen-btn-wrap .stButton > button:hover {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%) !important;
        border-color: #64b5f6 !important;
        color: #1565c0 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(100, 181, 246, 0.2) !important;
    }
    .char-static-box {
        font-size: 3.8em;
        font-weight: 700;
        background: linear-gradient(135deg, #fafafa 0%, #f0f0f0 100%);
        color: #bbb;
        border: 2px solid #e0e0e0;
        border-radius: 16px;
        padding: 10px;
        min-height: 90px;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        cursor: default;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .status-line {
        font-size: 1.1em;
        font-weight: 600;
        color: #0f5132;
        background: linear-gradient(135deg, #d1e7dd 0%, #c3e6cb 100%);
        border: 2px solid #95d5b2;
        padding: 18px;
        border-radius: 12px;
        margin: 20px 0 30px 0;
        box-shadow: 0 3px 10px rgba(15, 81, 50, 0.08);
    }
    .status-tag {
        background: linear-gradient(135deg, #ffffff 0%, #f1f3f5 100%);
        color: #2c3e50;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.9em;
        border: 2px solid #dee2e6;
        display: inline-flex;
        align-items: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .preview-count-line {
        font-size: 1.4em;
        text-align: center;
        color: #2c3e50;
        margin: 25px 0 30px 0;
        font-weight: 600;
    }
    .preview-count-line .char {
        font-size: 1.5em;
        font-weight: 800;
        color: #e74c3c;
        text-shadow: 0 2px 4px rgba(231, 76, 60, 0.1);
    }
    .jump-footer {
        margin-top: 50px;
        padding: 25px;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-top: 3px solid #dee2e6;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 -3px 10px rgba(0,0,0,0.04);
    }
    .lineage-header {
        font-size: 1.4em;
        font-weight: 800;
        color: #2c3e50;
        margin: 30px 0 20px 0;
        padding: 12px 20px;
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-left: 5px solid #1976d2;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(25, 118, 210, 0.1);
    }
    .compound-item {
        display: flex;
        align-items: baseline;
        margin-bottom: 10px;
        padding: 12px;
        border-bottom: 2px solid #e9ecef;
        border-radius: 8px;
        background: #ffffff;
        transition: all 0.2s ease;
    }
    .compound-item:hover {
        background: #f8f9fa;
        transform: translateX(4px);
    }
    .cp-word {
        font-weight: 700;
        font-size: 1.2em;
        color: #2c3e50;
        min-width: 85px;
        margin-right: 15px;
    }
    .cp-pinyin {
        color: #d35400;
        font-family: 'Monaco', 'Menlo', monospace;
        margin-right: 15px;
        font-weight: 600;
        font-size: 1.5em;
    }
    .cp-mean {
        color: #495057;
        font-size: 1em;
        flex: 1;
        line-height: 1.5;
    }

/* PALACE ENTRANCE STYLING */
    .splash-wrap {
        max-width: 850px;
        margin: 0 auto;
        padding: 60px 20px 20px 20px;
    }
    .splash-card {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 40px;
        padding: 60px;
        box-shadow: 0 15px 50px rgba(0,0,0,0.05);
        text-align: center;
    }
    .splash-title {
        font-size: 3.0em;
        font-weight: 800;
        color: #1a1a1a;
        margin-bottom: 10px;
    }
    .splash-sub {
        font-size: 1.3em;
        color: #666;
    }
    .palace-entrance-container {
        text-align: center;
        margin: 60px 0;
    }
    .grand-torii {
        font-size: 250px !important; /* Palace Scale */
        cursor: pointer;
        line-height: 1;
        transition: transform 0.4s ease;
        filter: drop-shadow(0 10px 20px rgba(0,0,0,0.1));
    }
    .grand-torii:hover {
        transform: scale(1.1);
    }
    .entrance-text {
        color: #2c3e50;
        font-size: 24px;
        font-weight: 700;
        margin-top: 20px;
        letter-spacing: 2px;
    }
    
    
    /* --- List View Interaction Banner + Button Hints --- */
    .interaction-banner {
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid #e9ecef;
        background: #f8f9fa;
        margin: 10px 0 18px 0;
        color: #2c3e50;
        font-weight: 600;
        line-height: 1.25;
    }
    .interaction-banner .k {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        border: 1px solid #dee2e6;
        background: #ffffff;
        font-weight: 800;
        margin: 0 6px 0 0;
        font-size: 0.92em;
    }
    .interaction-banner .muted { color: #6c757d; font-weight: 600; }
    .char-btn-hint {
        margin-top: 6px;
        text-align: center;
        font-size: 0.86em;
        color: #6c757d;
        font-weight: 700;
    }
    .char-btn-hint.previewing {
        color: #c0392b;
    }
    .status-line {
        line-height: 1.4;
    }
    .status-line span {
        color: #0f5132; /* Ensure the text inside remains the dark green */
    }

</style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_copy_to_clipboard(prompt_text: str, widget_id: str):
    safe_text = json.dumps(prompt_text, ensure_ascii=False)
    st_html(
        f"""
        <div style="display:flex; justify-content:center; margin:10px 0 0 0;">
          <button id="copy-btn-{widget_id}" style="
              padding:10px 14px; border-radius:10px; border:1px solid #ddd;
              background:#fff; cursor:pointer; font-weight:700;">
            Copy Prompt to Clipboard
          </button>
        </div>
        <div id="copy-msg-{widget_id}" style="text-align:center; margin-top:8px; color:#2e7d32; font-weight:600;"></div>
        <script>
          (function() {{
            const text = {safe_text};
            const btn = document.getElementById("copy-btn-{widget_id}");
            const msg = document.getElementById("copy-msg-{widget_id}");
            if (!btn) return;

            async function copy() {{
              try {{
                await navigator.clipboard.writeText(text);
                msg.textContent = "Copied. Paste into ChatGPT.";
              }} catch (e) {{
                msg.textContent = "Copy failed. Please manually select and copy from the textbox above.";
              }}
              setTimeout(() => {{ msg.textContent = ""; }}, 2500);
            }}

            btn.addEventListener("click", copy);
          }})();
        </script>
        """,
        height=90,
    )


# --- Session State Defaults (initialized at top) ---
DEFAULTS = {
    "onboarding_done": False,
    "selected_comp": "",
    "stroke_range": (3, 8),
    "radical": "none",
    "component_idc": "none",
    "display_mode": "2-Characters",
    "text_input_comp": "",
    "page": 1,
    "text_input_warning": None,
    "show_inputs": True,
    "last_valid_selected_comp": "",
    "preview_comp": None,
    "stroke_view_active": False,
    "stroke_view_char": "",
    "script_filter": "Any",
#   "component_only": True,
    "favourites_list": [],
    "fav_cursor": 0,
    "history": [],
    "definition_search_mode": False,
    "definition_search_query": "",
    "definition_search_results": None,
    "grid_sort_mode": "usage",
    "grid_script_filter": "Any",
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# Load favourites
if not st.session_state.favourites_list:
    try:
        with open("favourites.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                valid = [c for c in data if isinstance(c, str) and len(c) == 1]
                st.session_state.favourites_list = valid[:20]
    except FileNotFoundError:
        pass
    except Exception as e:
        st.error(f"Error loading favourites.json: {e}")


# --- Callbacks ---
def sync_stroke_range():
    st.session_state.stroke_range = st.session_state.w_stroke_range
    st.session_state.page = 1

def sync_radical():
    st.session_state.radical = st.session_state.w_radical
    st.session_state.page = 1

def sync_idc():
    st.session_state.component_idc = st.session_state.w_idc
    st.session_state.page = 1

def sync_script_filter():
    st.session_state.script_filter = st.session_state.w_script_filter

def sync_text():
    raw = st.session_state.get("w_text", "")
    v = normalize_single_hanzi(raw)
    if not v:
        st.session_state.text_input_warning = "One character only"
        return
    resolved = resolve_to_known_variant(v)
    if not resolved:
        st.session_state.text_input_warning = "Not found"
        return
    st.session_state.script_filter = "Any"
    st.session_state.history = []
    st.session_state.selected_comp = resolved
    st.session_state.last_valid_selected_comp = resolved
    st.session_state.text_input_comp = resolved
    st.session_state.text_input_warning = None
    st.session_state.show_inputs = False
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.display_mode = "2-Characters"
    st.session_state.definition_search_mode = False
    st.session_state.definition_search_results = None

def sync_sidebar_text():
    raw = st.session_state.get("sb_search", "")
    v = normalize_single_hanzi(raw)
    if not v:
        st.toast("Please enter exactly one character.")
        return
    resolved = resolve_to_known_variant(v)
    if not resolved:
        st.toast("Character not found.")
        return
    st.session_state.script_filter = "Any"
    st.session_state.history = []
    st.session_state.selected_comp = resolved
    st.session_state.last_valid_selected_comp = resolved
    st.session_state.text_input_comp = resolved
    st.session_state.show_inputs = False
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""
    st.session_state.display_mode = "2-Characters"
    st.session_state.definition_search_mode = False
    st.session_state.definition_search_results = None

def tile_click(c):
    if st.session_state.show_inputs:
        if st.session_state.preview_comp == c:
            st.session_state.script_filter = "Any"
            st.session_state.history = []
            st.session_state.selected_comp = c
            st.session_state.last_valid_selected_comp = c
            st.session_state.show_inputs = False
            st.session_state.preview_comp = None
            st.session_state.text_input_comp = c
            st.session_state.stroke_view_active = False
            st.session_state.display_mode = "2-Characters"
            st.session_state.definition_search_mode = False
            st.session_state.definition_search_results = None
        else:
            st.session_state.preview_comp = c

def list_tile_click(c):
    if st.session_state.preview_comp == c:
        # Trigger the feature alert toast
        if not st.session_state.get("has_drilled_down", False):
            st.toast("Feature Discovered: You have entered the Character Lineage view!", icon="🌳")
            st.session_state.has_drilled_down = True
            
        # Standard navigation logic
        if st.session_state.selected_comp:
            st.session_state.history.append(st.session_state.selected_comp)
        st.session_state.selected_comp = c
        st.session_state.show_inputs = False
        st.session_state.preview_comp = None
        st.session_state.display_mode = "2-Characters" # Ensure default
    else:
        st.session_state.preview_comp = c

def go_back():
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""
    st.session_state.text_input_comp = ""
    st.session_state.text_input_warning = None
    st.session_state.definition_search_mode = False
    st.session_state.definition_search_results = None
    if st.session_state.history:
        prev = st.session_state.history.pop()
        st.session_state.script_filter = "Any"
        st.session_state.selected_comp = prev
        st.session_state.last_valid_selected_comp = prev
        st.session_state.show_inputs = False
        st.session_state.display_mode = "2-Characters"
    else:
        st.session_state.show_inputs = True

def go_to_root():
    st.session_state.history = []
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""
    st.session_state.text_input_comp = ""
    st.session_state.text_input_warning = None
    st.session_state.selected_comp = ""
    st.session_state.show_inputs = True
    st.session_state.script_filter = "Any"
    st.session_state.display_mode = "2-Characters"
    st.session_state.definition_search_mode = False
    st.session_state.definition_search_results = None

def end_stroke_view():
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""

def toggle_favourite(char):
    is_now_checked = st.session_state.get(f"fav_chk_{char}", False)
    if is_now_checked:
        if char not in st.session_state.favourites_list:
            if len(st.session_state.favourites_list) < 20:
                st.session_state.favourites_list.append(char)
            else:
                idx = st.session_state.fav_cursor
                st.session_state.favourites_list[idx] = char
                st.session_state.fav_cursor = (idx + 1) % 20
    else:
        if char in st.session_state.favourites_list:
            st.session_state.favourites_list.remove(char)

def handle_file_upload():
    uploaded_file = st.session_state.get("fav_uploader")
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            if isinstance(data, list):
                valid_chars = [c for c in data if isinstance(c, str) and len(c) == 1]
                st.session_state.favourites_list = valid_chars[:20]
                st.session_state.fav_cursor = 0
                st.toast("Favourites loaded successfully!", icon="✅")
        except Exception as e:
            st.error(f"Error loading file: {e}")

def search_by_definition():
    query = st.session_state.get("w_def_search", "").strip()
    if not query or len(query) < 2:
        st.toast("Please enter at least 2 characters to search.")
        return
    
    char_results = []
    query_lower = query.lower()
    for char, info in component_map.items():
        definition = info.get("meta", {}).get("definition", "")
        if isinstance(definition, str) and query_lower in definition.lower():
            char_results.append(char)
    
    db_conn = get_db_connection()
    phrase_results = []
    if db_conn:
        phrase_results = search_phrases_by_definition(query, db_conn, limit=200)
    
    st.session_state.definition_search_mode = True
    st.session_state.definition_search_query = query
    st.session_state.definition_search_results = {
        "characters": char_results[:120],
        "phrases": phrase_results[:200]
    }
    st.session_state.show_inputs = False
    st.session_state.selected_comp = ""
    st.session_state.preview_comp = None

def enter_component(comp: str):
    st.session_state.script_filter = "Any"
    st.session_state.history = []
    st.session_state.selected_comp = comp
    st.session_state.last_valid_selected_comp = comp
    st.session_state.show_inputs = False
    st.session_state.preview_comp = None
    st.session_state.text_input_comp = comp
    st.session_state.text_input_warning = None
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""
    st.session_state.display_mode = "2-Characters"
    st.session_state.definition_search_mode = False
    st.session_state.definition_search_results = None

def render_splash():
    """Renders the entry screen with a grand palace-style entrance."""
    # 1. Main Title Card - Styled for a premium, palace feel
    st.markdown(
        """
        <div class="splash-wrap">
          <div class="splash-card">
            <div class="splash-title">Radix 🈑 Chinese Characters</div>
            <div class="splash-sub">
              Spot the COMPONENTS (字部件). Read and write HANZI (汉字 / 漢字).
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. ENLARGED ENTRANCE: The Torii gate scaled to palace proportions
    st.markdown(
        """
        <div class="palace-entrance-container">
            <a href="/?onboarding=done" target="_self" style="text-decoration:none;">
                <div class="grand-torii">⛩️</div>
                <div class="entrance-text">Enter the Grand Hall of Radix 🈑</div>
            </a>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # Handling the entrance logic via query parameters
    if st.query_params.get("onboarding") == "done":
        st.session_state.onboarding_done = True
        st.query_params.clear() 
        st.rerun()
    

    demos = st.session_state.favourites_list
    if demos:
        st.markdown("<h4 style='text-align:center; color:#666; margin-top:20px;'>Quick Access Favourites</h4>", unsafe_allow_html=True)
        lc1, lc2, lc3 = st.columns([1, 2, 1])
        with lc2:
            with st.expander("📂 Manage Favourites (Save/Load)", expanded=False):
                c_dl, c_ul = st.columns(2)
                with c_dl:
                    json_data = json.dumps(st.session_state.favourites_list, ensure_ascii=False, indent=2)
                    st.markdown(render_ipad_safe_download_html(json_data, "favourites.json", "💾 Save Favourites"), unsafe_allow_html=True)
                with c_ul:
                    st.file_uploader("Load", type=["json"], key="fav_uploader", on_change=handle_file_upload, label_visibility="collapsed")
        
        st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
        
        unique_demos = []
        seen = set()
        for d in demos:
            if d not in seen:
                unique_demos.append(d)
                seen.add(d)

        COLS = 5
        rows = (len(unique_demos) + COLS - 1) // COLS
        for r in range(rows):
            cols = st.columns(COLS)
            for j in range(COLS):
                idx = r * COLS + j
                if idx < len(unique_demos):
                    ch = unique_demos[idx]
                    count = component_usage_count(ch)
                    with cols[j]:
                        if st.button(f"Explore {ch}", key=f"v4_splash_btn_{idx}_{ord(ch)}", use_container_width=True, type="primary"):
                            st.session_state.onboarding_done = True
                            enter_component(ch)
                            st.rerun()
                        st.caption(f"used in {count} characters")
        st.markdown("</div>", unsafe_allow_html=True)

def render_radix_row(c, context="detail", is_static=False):
    col_char, col_details = st.columns([2, 10])
    is_preview = st.session_state.preview_comp == c
    is_active_focus = is_preview or (st.session_state.preview_comp is None and c == st.session_state.selected_comp)

    with col_char:
        if is_static:
            # Static display for non-interactive cards
            st.markdown(f"<div class='char-static-box'>{c}</div>", unsafe_allow_html=True)
        else:
            # Interactive button with preview/drill-down functionality
            st.markdown("<div class='char-btn-wrap'>", unsafe_allow_html=True)
            unique_id = str(uuid.uuid4())[:8]

            btn_help = (
                "Previewing in the sidebar. Click again to drill down into this character family."
                if is_preview
                else "Click once to preview in the sidebar; click the same button again to drill down."
            )

            st.button(
                c,
                key=f"explore_char_{context}_{c}_{ord(c)}_{unique_id}",
                type="primary" if is_preview else "secondary",
                help=btn_help,
                on_click=list_tile_click,
                args=(c,),
                use_container_width=True,
            )

            hint_text = "Click again to drill down" if is_preview else "Click once to preview"
            hint_class = "char-btn-hint previewing" if is_preview else "char-btn-hint"
            st.markdown(f"<div class='{hint_class}'>{hint_text}</div>", unsafe_allow_html=True)

            st.markdown("<div class='pen-btn-wrap'>", unsafe_allow_html=True)
            
            def activate_stroke_view(char):
                st.session_state.stroke_view_char = char
                st.session_state.stroke_view_active = True
                st.session_state.show_inputs = False
                if not st.session_state.selected_comp:
                    st.session_state.selected_comp = char
                    st.session_state.last_valid_selected_comp = char
            
            if st.button("🧠 link", key=f"stroke_btn_{c}_{ord(c)}_{unique_id}", 
                         help="Write AI prompt", use_container_width=True,
                         on_click=activate_stroke_view, args=(c,)):
                pass
            
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
    with col_details:
        usage_count = component_usage_count(c)
        # Pass the is_static flag to control the tip text
        st.markdown(
            generate_clean_card_html(c, usage_count=usage_count, is_static=is_static), 
            unsafe_allow_html=True
        )
        
        if not is_static and is_active_focus and st.session_state.display_mode != "Single Character":
            n = {"2-Characters": 2, "3-Characters": 3, "4-Characters": 4}.get(st.session_state.display_mode, 0)
            meta_compounds = component_map.get(c, {}).get("meta", {}).get("compounds", [])
            relevant = [w for w in meta_compounds if isinstance(w, str) and len(w) == n]
            
            if relevant:
                db_conn = get_db_connection()
                if db_conn:
                    phrases_map = batch_get_phrase_details(sorted(relevant), db_conn)
                    items_html_list = []
                    for word in sorted(relevant):
                        entry = phrases_map.get(word)
                        if entry:
                            raw_mean = entry.get('meanings', '')
                            p_mean = pyhtml.escape(raw_mean[:130] + ('...' if len(raw_mean) > 130 else ''))
                            items_html_list.append(
                                f"<div style='display:flex; align-items:baseline; padding:5px 8px; border-bottom:1px solid #eee;'>"
                                f"<span style='font-weight:700; font-size:1.0rem; min-width:65px;'>{word}</span>"
                                f"<span style='color:#d35400; font-size:0.85rem; font-family:monospace; margin-right:12px; font-weight:600;'>{entry.get('pinyin', '')}</span>"
                                f"<span style='color:#444; font-size:0.85rem; flex:1; line-height:1.2;'>{p_mean}</span>"
                                f"</div>"
                            )
                    
                    all_rows = "".join(items_html_list)
                    st.markdown(f"""
                        <div style='padding:12px; background:#f1f8e9; border-radius:8px; margin-top:10px; border:1px solid #dcedc8; max-height:400px; overflow-y:auto;'>
                          <div style='font-weight:bold; font-size:0.8rem; margin-bottom:8px; color:#2e7d32; text-transform:uppercase;'>
                            {st.session_state.display_mode} containing {c}
                          </div>
                          {all_rows}
                        </div>
                        """, unsafe_allow_html=True)
    st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

def main():
    if not component_map:
        st.error("Component dataset not loaded. Ensure enhanced_component_map_with_etymology.json exists.")
        st.stop()

    apply_dynamic_css()

    if not st.session_state.get("onboarding_done", False):
        render_splash()
        st.stop()

    with st.sidebar:
        st.markdown("<h1 style='text-align:center; margin-bottom:30px;'>🈑 Radix</h1>", unsafe_allow_html=True)

        current_char_for_sidebar = (
            st.session_state.stroke_view_char if st.session_state.stroke_view_active
            else (st.session_state.preview_comp or st.session_state.selected_comp)
        )

        if current_char_for_sidebar:
            sidebar_html, sidebar_height = get_stroke_order_sidebar_html(current_char_for_sidebar, size=140)
            if sidebar_html:
                st_html(sidebar_html, height=sidebar_height)

            related = component_map.get(current_char_for_sidebar, {}).get("related_characters", [])
            chars_all = [c for c in related if isinstance(c, str) and len(c) == 1 and c in component_map]
            chars_filtered = apply_script_filter(chars_all, st.session_state.script_filter)
            count = len(chars_filtered)
            if count > 0:
                st.markdown(
                    f"<div class='preview-count-line'>{count} characters contain <span class='char'>{current_char_for_sidebar}</span></div>",
                    unsafe_allow_html=True,
                )

            is_fav = current_char_for_sidebar in st.session_state.favourites_list
            st.checkbox("Show in Favourites", value=is_fav, key=f"fav_chk_{current_char_for_sidebar}",
                        on_change=toggle_favourite, args=(current_char_for_sidebar,))


        
        if st.button("Show Favourites", use_container_width=True):
            go_to_root()
            st.session_state.onboarding_done = False
            st.rerun()

        st.text_input("Shortcut: Paste/Type characters", key="sb_search", on_change=sync_sidebar_text)

        if st.session_state.show_inputs:
            st.markdown("---")
            max_s_val = max((get_stroke_count(c) for c in component_map if get_stroke_count(c) is not None), default=30)
            with st.expander("🔎 Filters", expanded=False):
                st.slider("Stroke count", min_value=1, max_value=max_s_val, value=st.session_state.stroke_range,
                          key="w_stroke_range", on_change=sync_stroke_range)

                all_radicals = sorted(set(info.get("meta", {}).get("radical")
                                          for info in component_map.values() if info.get("meta", {}).get("radical")))
                radical_options = ["none"] + all_radicals
                st.selectbox("Radical", options=radical_options,
                             index=radical_options.index(st.session_state.radical) if st.session_state.radical in radical_options else 0,
                             key="w_radical", on_change=sync_radical)

                idc_options = ["none"] + sorted(stats_cache.get("idc_counts", {}).keys())
                st.selectbox("Structure (IDC)", options=idc_options,
                             index=idc_options.index(st.session_state.component_idc) if st.session_state.component_idc in idc_options else 0,
                             key="w_idc", on_change=sync_idc)

            st.markdown("---")

            st.markdown("### Sort Grid By")

            def update_grid_sort_mode():
                selected = st.session_state.grid_sort_mode_radio
                if selected == "Most Useful Components First":
                    st.session_state.grid_sort_mode = "usage"
                else:
                    st.session_state.grid_sort_mode = "frequency"
                st.session_state.page = 1

            st.radio(
                "Choose sorting priority",
                options=["Most Useful Components First", "Most Common in Language First"],
                index=0 if st.session_state.get("grid_sort_mode", "usage") == "usage" else 1,
                key="grid_sort_mode_radio",
                on_change=update_grid_sort_mode,
                help="• Useful Components: Shows building-block characters first (auto-filters to components only)\n"
                     "• Common in Language: Shows everyday characters first (asks script preference)"
            )

            if st.session_state.grid_sort_mode == "frequency":
                def update_grid_script():
                    st.session_state.grid_script_filter = st.session_state.grid_script_radio
                    st.session_state.page = 1

                st.markdown("#### Script Preference (affects all views)")
                st.radio(
                    "Show characters in:",
                    options=["Simplified", "Traditional", "Any"],
                    index=["Simplified", "Traditional", "Any"].index(st.session_state.grid_script_filter),
                    key="grid_script_radio",
                    on_change=update_grid_script,
                    horizontal=True
                )
            st.markdown("---")

        current_main_char = st.session_state.stroke_view_char if st.session_state.stroke_view_active else st.session_state.selected_comp

        if current_main_char:
            path_items = ["🏠 Root"] + st.session_state.history
            if st.session_state.stroke_view_active:
                path_items += [f"<i>{current_main_char}</i> (🧠)"]
            else:
                path_items += [f"<b>{current_main_char}</b>"]
            path_str = " → ".join(path_items)
            st.markdown(f"<div style='font-size:0.95em; margin:18px 0; color:#444; text-align:center; font-weight:500;'>{path_str}</div>", unsafe_allow_html=True)

        nav_col1, nav_col2 = st.columns(2)
        with nav_col1:
            if st.session_state.stroke_view_active:
                st.button("← Back", on_click=end_stroke_view, use_container_width=True)
            else:
                st.button("← Back", on_click=go_back, use_container_width=True)
        with nav_col2:
            st.button("🏠 Root", on_click=go_to_root, use_container_width=True)

        st.markdown("---")



            if not st.session_state.show_inputs:
                st.markdown("---")
                st.markdown("### Display Phrases")
                modes = ["Single Character", "2-Characters", "3-Characters", "4-Characters"]
                current_idx = modes.index(st.session_state.display_mode) if st.session_state.display_mode in modes else 1
                new_mode = st.radio("Select mode", options=modes, index=current_idx, key="sidebar_display_mode", label_visibility="collapsed")
                if new_mode != st.session_state.display_mode:
                    st.session_state.display_mode = new_mode
                    st.rerun()

            if not st.session_state.stroke_view_active and not st.session_state.show_inputs:
                st.markdown("---")
                current_script = st.session_state.get("script_filter", st.session_state.grid_script_filter)
                st.radio("Filter Results", options=SCRIPT_FILTERS, index=SCRIPT_FILTERS.index(current_script),
                         key="w_script_filter", on_change=sync_script_filter)

            if st.session_state.stroke_view_active:
                st.markdown("---")
                st.markdown("### Character Info")
                st.markdown(f"<div style='font-size:2em; font-weight:bold; text-align:center; margin-bottom:10px;'>{current_char_for_sidebar}</div>", unsafe_allow_html=True)
                st.markdown(generate_clean_card_html(current_char_for_sidebar), unsafe_allow_html=True)

    if st.session_state.stroke_view_active:
        st.markdown("### Stroke Order Animation")
        main_html, phrases_html = get_stroke_order_view_html(st.session_state.stroke_view_char, st.session_state.display_mode)
        st_html(main_html, height=450)
        if phrases_html:
            st.markdown(phrases_html, unsafe_allow_html=True)

        st.markdown("### ChatGPT Prompt")
        prompt_text = build_chatgpt_prompt(st.session_state.stroke_view_char)
        st.text_area("Copy this prompt into ChatGPT", value=prompt_text, height=320)
        render_copy_to_clipboard(prompt_text, str(hash(st.session_state.stroke_view_char)))

        st.stop()

    if st.session_state.show_inputs:
        cur_min, cur_max = st.session_state.stroke_range

        filter_parts = []
        max_s_val = max((get_stroke_count(c) for c in component_map if get_stroke_count(c) is not None), default=30)

        if not (cur_min == 1 and cur_max == max_s_val):
            if cur_min == cur_max:
                filter_parts.append(f"<span class='status-tag'>{cur_min} strokes</span>")
            elif cur_min == 1:
                filter_parts.append(f"<span class='status-tag'>≤ {cur_max} strokes</span>")
            elif cur_max == max_s_val:
                filter_parts.append(f"<span class='status-tag'>≥ {cur_min} strokes</span>")
            else:
                filter_parts.append(f"<span class='status-tag'>{cur_min}–{cur_max} strokes</span>")

        if st.session_state.radical != "none":
            filter_parts.append(f"<span class='status-tag'>Rad. {st.session_state.radical}</span>")
        if st.session_state.component_idc != "none":
            filter_parts.append(f"<span class='status-tag'>{st.session_state.component_idc}</span>")

        force_components_only = (st.session_state.grid_sort_mode == "usage")
        if force_components_only:
            filter_parts.append("<span class='status-tag'>Components Only</span>")

        if st.session_state.grid_sort_mode == "frequency":
            filter_parts.append(f"<span class='status-tag'>Script: {st.session_state.grid_script_filter}</span>")

        filter_summary = "".join(filter_parts) if filter_parts else "<span class='status-tag'>All characters</span>"


        st.markdown(
            f"""
            <div class='status-line' style='display: flex; flex-direction: column; gap: 8px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div style='display: flex; flex-wrap: wrap; gap: 8px;'>
                        <span style='font-weight: 800; margin-right: 5px;'>🔍 Filters:</span> {filter_summary}
                    </div>
                    <div style='font-size: 0.8em; color: rgba(15, 81, 50, 0.7); font-weight: 700;'>Click once to preview in the sidebar; click the same button again to drill down. </div>
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )

        use_component_only = force_components_only

        filtered = [
            c for c in component_map
            if (s := get_stroke_count(c)) is not None and cur_min <= s <= cur_max
            and (st.session_state.radical == "none" or component_map[c]["meta"].get("radical") == st.session_state.radical)
            and (st.session_state.component_idc == "none" or component_map[c]["meta"].get("decomposition", "").startswith(st.session_state.component_idc))
            and (not use_component_only or c in stats_cache["used_components"])
        ]

        if st.session_state.grid_sort_mode == "frequency":
            filtered = apply_script_filter(filtered, st.session_state.grid_script_filter)

        if st.session_state.grid_sort_mode == "frequency":
            sorted_comps = sorted(filtered, key=sort_key_frequency_primary)
        else:
            sorted_comps = sorted(filtered, key=sort_key_usage_primary)

        if not sorted_comps:
            st.info("No components match current filters.")
        else:
            PAGE_SIZE = 120
            GRID_COLS = 10
            total = len(sorted_comps)
            max_page = max(1, math.ceil(total / PAGE_SIZE))
            st.session_state.page = max(1, min(st.session_state.page, max_page))

            p1, p2, p3 = st.columns([1, 3, 1])
            with p1:
                if st.button("◀ Prev", disabled=st.session_state.page <= 1, use_container_width=True):
                    st.session_state.page -= 1
                    st.rerun()
            with p2:
                start = (st.session_state.page - 1) * PAGE_SIZE + 1
                end = min(st.session_state.page * PAGE_SIZE, total)
                st.markdown(f"<div style='text-align:center; padding:10px 0; color:#555;'><div style='font-size:1.1em; font-weight:bold;'>{start}–{end} of {total}</div></div>", unsafe_allow_html=True)
            with p3:
                if st.button("Next ▶", disabled=st.session_state.page >= max_page, use_container_width=True):
                    st.session_state.page += 1
                    st.rerun()

            page = sorted_comps[(st.session_state.page - 1) * PAGE_SIZE : st.session_state.page * PAGE_SIZE]
            st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
            cols = st.columns(GRID_COLS)
            for i, ch in enumerate(page):
                with cols[i % GRID_COLS]:
                    is_preview = st.session_state.preview_comp == ch
                    st.button(ch, key=f"b_{ch}_{st.session_state.page}", type="primary" if is_preview else "secondary",
                              on_click=tile_click, args=(ch,), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='jump-footer'>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.session_state.text_input_warning:
                    st.warning(st.session_state.text_input_warning)
                st.text_input("Go to component/character", value=st.session_state.text_input_comp, key="w_text",
                              on_change=sync_text, placeholder="Type one Hanzi, e.g. 水", label_visibility="collapsed")
                st.caption("Enter one Chinese character to jump directly to its details")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='jump-footer' style='margin-top:20px;'>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align:center; color:#2c3e50; margin-bottom:15px;'>🔍 Search by English Definition</h4>", unsafe_allow_html=True)
            col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
            with col_s2:
                st.text_input("Search definitions", key="w_def_search", placeholder="e.g., water, fire, mountain", label_visibility="collapsed")
                if st.button("Search Definitions", use_container_width=True, type="primary"):
                    search_by_definition()
                    st.rerun()
                st.caption("Search across character definitions and phrase meanings")
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        if st.session_state.definition_search_mode and st.session_state.definition_search_results:
            results = st.session_state.definition_search_results
            query = st.session_state.definition_search_query
            
            st.markdown(f"""
                <div class='status-line'>
                    <div style='font-size:1.2em; font-weight:700;'>
                        Search Results for "{pyhtml.escape(query)}"
                    </div>
                    <div class='status-text' style='font-size:0.85em; color:#666; margin-top:8px;'>
                        Found {len(results['characters'])} characters and {len(results['phrases'])} phrases
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            if results['characters']:
                st.markdown("<div class='lineage-header'>📝 Characters</div>", unsafe_allow_html=True)
                for char in results['characters'][:30]:
                    render_radix_row(char)
            
            if results['phrases']:
                st.markdown("<div class='lineage-header'>💬 Phrases</div>", unsafe_allow_html=True)
                st.markdown("<div style='max-width:900px; margin:0 auto;'>", unsafe_allow_html=True)
                for phrase_data in results['phrases']:
                    word = phrase_data['word']
                    pinyin = phrase_data['pinyin']
                    meanings = pyhtml.escape(phrase_data['meanings'][:200] + ('...' if len(phrase_data['meanings']) > 200 else ''))
                    st.markdown(f"""
                        <div class='compound-item' style='margin-bottom:15px;'>
                            <span class='cp-word' style='font-size:1.4em;'>{word}</span>
                            <span class='cp-pinyin'>{pinyin}</span>
                            <span class='cp-mean'>{meanings}</span>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            if not results['characters'] and not results['phrases']:
                st.info(f"No results found for '{query}'. Try different search terms.")
        else:

            # --- NEW DYNAMIC LINEAGE BANNER ---
            sel = st.session_state.selected_comp
            info = component_map.get(sel, {})
            
            # 1. Get Parents (for the banner only)
            decomp = info.get("meta", {}).get("decomposition", "")
            parents = [p for p in decomp if p in component_map and p not in IDC_CHARS and p not in ["?", "—"] and p != sel]
            parents = apply_script_filter(parents, st.session_state.script_filter)
            p_html = "".join([f"<span class='status-tag' style='margin-right:5px; padding: 2px 8px;'>{p}</span>" for p in parents])
            
            # 2. Get Derivatives
            rel = info.get("related_characters", [])
            children = [c for c in rel if isinstance(c, str) and len(c) == 1 and c in component_map and c != sel]
            children_preview = apply_script_filter(children, st.session_state.script_filter)[:50]
            c_html = "".join([f"<span class='status-tag' style='margin-right:5px; padding: 2px 8px; opacity: 0.8;'>{c}</span>" for c in children_preview])

            st.markdown(f"""
                <div class='status-line'>
                    <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;'>
                        <div>
                            <div style='font-weight: 800; font-size: 1.2em;'> {sel}</div>
                            <div style='margin-top:4px; font-size:0.85em;'>
                                <b>Components</b> {p_html if parents else "Basic Root"}
                            </div>
                        </div>
                        <div style='text-align: left; font-size: 1.0em; opacity: 0.7;'>
                            <b>Derivatives</b><br/>{c_html}{"..." if len(children) > 50 else ""}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            # --- END DYNAMIC BANNER ---

            selected = st.session_state.selected_comp

            # 1. PARENTS (Ingredients) - exclude self if present
            decomp_raw = component_map.get(selected, {}).get("meta", {}).get("decomposition", "")
            parents = [p for p in decomp_raw if p in component_map and p not in IDC_CHARS and p not in ["?", "—"] and p != selected]
            
            if parents:
                st.markdown("<div class='lineage-header'>🧱 Components (How it's built)</div>", unsafe_allow_html=True)
                for p in apply_script_filter(parents, st.session_state.script_filter):
                    render_radix_row(p)

                    

            st.markdown("<div class='lineage-header'>🎯 Current Selection</div>", unsafe_allow_html=True)
            focus_group = [selected]
            if cc_t2s and cc_s2t:
                s_cand = cc_t2s.convert(selected)
                t_cand = cc_s2t.convert(selected)
                variant = s_cand if s_cand != selected else t_cand
                if variant != selected and variant in component_map:
                    focus_group.append(variant)
            
            for f in apply_script_filter(focus_group, st.session_state.script_filter):
                render_radix_row(f)

            related_raw = component_map.get(selected, {}).get("related_characters", [])
            children = [c for c in related_raw if isinstance(c, str) and len(c) == 1 and c in component_map and c != selected]
            
            if children:
                children_sorted = sorted(children, key=sort_key_usage_primary)
                visible_children = apply_script_filter(children_sorted, st.session_state.script_filter)    
                
                # Remove duplicates while preserving order
                seen = set()
                unique_visible = []
                for child in visible_children:
                    if child not in seen:
                        unique_visible.append(child)
                        seen.add(child)
                visible_children = unique_visible

                # Now use the deduplicated count in the header
                st.markdown(f"<div class='lineage-header'>🌲 Derivatives (Used in {len(visible_children)} characters)</div>", unsafe_allow_html=True)
                
                # First 120: Fully interactive
                for child in visible_children[:120]:
                    render_radix_row(child)
                
                # Remaining: Static cards (unlimited)
                if len(visible_children) > 120:
                    remaining = len(visible_children) - 120
                    st.markdown("---")
                    st.markdown(
                        f"<div style='text-align:center; color:#888; font-weight:bold; margin-bottom:20px;'>"
                        f"⬇️ {remaining} More Derivatives ⬇️</div>",
                        unsafe_allow_html=True
                    )
                    for c in visible_children[120:]:
                        # Render with is_static=True to show appropriate tip
                        render_radix_row(c, context="static_derivative", is_static=True)


if __name__ == "__main__":
    main()
