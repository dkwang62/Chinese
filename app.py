# app.py
# Main Streamlit app for Radix - with definition search and commonality ranking

import streamlit as st
from streamlit.components.v1 import html as st_html
import json
import hashlib
import html as pyhtml
import math
import uuid
import re
import copy

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
    get_default_prompt_config,
    normalize_prompt_config,
    render_combined_prompt,
    get_char_definition_en,
    generate_clean_card_html,
    render_ipad_safe_download_html,
    get_stroke_order_sidebar_html,
    get_stroke_order_view_html,
    SCRIPT_FILTERS,
    IDC_CHARS,
    sort_key_usage_primary,
    sort_key_frequency_primary,
)

# -----------------------------
# Profile (single-file) storage
# -----------------------------
PROFILE_SCHEMA_VERSION = 1
PROFILE_FILENAME = "radix_user_data.json"

def build_profile_dict() -> dict:
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "favourites_list": st.session_state.get("favourites_list", []),
        "prompt_config": st.session_state.get("prompt_config", {}),
        "prompt_ui": st.session_state.get("prompt_ui", {}),
    }

def export_profile_str() -> str:
    return json.dumps(build_profile_dict(), ensure_ascii=False, indent=2)

def import_profile_dict(data: dict) -> None:
    """
    Imports data into session state and marks it as an 'upload' 
    so the initialization logic treats it as the source of truth.
    """
    if not isinstance(data, dict):
        raise ValueError("Uploaded JSON must be an object.")
    if data.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise ValueError("Unsupported schema_version.")
    
    # 1. Extract and Deep Copy
    favs = data.get("favourites_list", [])
    prompts = data.get("prompt_config", {})
    prompt_ui = data.get("prompt_ui", {})
    
    st.session_state.favourites_list = list(favs)
    st.session_state.fav_cursor = 0
    st.session_state.prompt_config = copy.deepcopy(prompts)
    st.session_state.prompt_ui = copy.deepcopy(prompt_ui)

    # 2. Force Normalization Immediately (Sanity Check)
    normalized = normalize_prompt_config(st.session_state.prompt_config)
    if normalized:
        st.session_state.prompt_config = normalized
    else:
        st.session_state.prompt_config = get_default_prompt_config()

    # 3. Set Lock Flag
    # This prevents the disk-loader from overwriting this data on the next run.
    st.session_state["_upload_applied"] = True

    # 4. Clean Slate for UI
    # We remove derived UI keys so they get rebuilt fresh from the new config.
    keys_to_kill = ["prompt_selected_task_ids", "fav_bulk_editor"]
    for k in list(st.session_state.keys()):
        if k.startswith("prompt_task_cb_") or k.startswith("pt_"):
            keys_to_kill.append(k)
            
    for k in keys_to_kill:
        st.session_state.pop(k, None)

# -----------------------------
# Initialization Logic
# -----------------------------
def init_app_state():
    """
    The Single Source of Truth for State Initialization.
    Runs at the top of every script execution.
    """
    # 1. Define Static Defaults (Scalars)
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
        "fav_cursor": 0,
        "history": [],
        "definition_search_mode": False,
        "definition_search_query": "",
        "definition_search_results": None,
        "grid_sort_mode": "usage",
        "grid_script_filter": "Any",
        # Complex objects defaulting to None/Empty
        "favourites_list": [],
        "prompt_config": None, 
        "prompt_ui": {},
        "prompt_selected_task_ids": []
    }

    # Initialize missing keys
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # 2. Disk Load Logic
    # Only load from disk if:
    #   a) prompt_config is missing/None 
    #   b) We are NOT in the middle of applying a manual upload ("_upload_applied")
    if not st.session_state.get("_upload_applied"):
        if st.session_state.prompt_config is None:
            loaded = False
            try:
                with open("radix_user_data.json", "r", encoding="utf-8") as f:
                    obj = json.load(f)
                    if isinstance(obj, dict) and obj.get("schema_version") == 1:
                        st.session_state.favourites_list = obj.get("favourites_list", [])
                        st.session_state.prompt_config = obj.get("prompt_config")
                        st.session_state.prompt_ui = obj.get("prompt_ui", {})
                        loaded = True
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            
            if not loaded:
                # Apply hardcoded defaults if disk load failed
                st.session_state.prompt_config = get_default_prompt_config()
                st.session_state.prompt_ui = {"default_selected_task_ids": []}

    # 3. Ensure Config Validity (Normalization)
    if st.session_state.prompt_config:
        normalized = normalize_prompt_config(st.session_state.prompt_config)
        if normalized:
            st.session_state.prompt_config = normalized

    # 4. Sync Derived UI State
    cfg = st.session_state.get("prompt_config", {})
    tasks = cfg.get("tasks", []) if isinstance(cfg, dict) else []
    _task_ids = [t.get('id') for t in tasks if isinstance(t, dict) and t.get('id')]
    
    # Init prompt_ui if empty
    if not st.session_state.get('prompt_ui'):
        st.session_state.prompt_ui = {'default_selected_task_ids': _task_ids}
        
    # Init prompt_selected_task_ids if empty or missing
    current_sel = st.session_state.get("prompt_selected_task_ids")
    if current_sel is None or not isinstance(current_sel, list) or not current_sel:
        defaults = st.session_state.prompt_ui.get('default_selected_task_ids', [])
        valid_defaults = [t for t in defaults if t in _task_ids]
        st.session_state.prompt_selected_task_ids = valid_defaults if valid_defaults else list(_task_ids)


st.set_page_config(layout="wide", page_title="Radix", page_icon=" 🈑 ")

# --- STARTUP ---
init_app_state()
# ---------------

def normalize_prompt_state() -> None:
    """Helper to refresh UI keys after a config change."""
    init_app_state() 
    cfg = st.session_state.get("prompt_config", {})
    tasks = cfg.get("tasks", [])
    cur_sel = st.session_state.get("prompt_selected_task_ids", [])
    for t in tasks:
        tid = t.get("id")
        if tid:
            st.session_state[f"prompt_task_cb_{tid}"] = (tid in cur_sel)

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
        font-size: 250px !important;
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
        color: #0f5132;
    }
    /* Button override for the entrance to look nicer */
    .entrance-btn button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #2c3e50 !important;
    }
    .entrance-btn button:hover {
        background: transparent !important;
        transform: scale(1.05);
        color: #e67e22 !important;
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
        if not st.session_state.get("has_drilled_down", False):
            st.toast("Feature Discovered: You have entered the Character Lineage view!", icon="🌳")
            st.session_state.has_drilled_down = True
        if st.session_state.selected_comp:
            st.session_state.history.append(st.session_state.selected_comp)
        st.session_state.selected_comp = c
        st.session_state.show_inputs = False
        st.session_state.preview_comp = None
        st.session_state.display_mode = "2-Characters"
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

def _apply_uploaded_profile_bytes(file_bytes: bytes) -> None:
    """Cleans the widget cache and applies the takeover."""
    try:
        obj = json.loads(file_bytes.decode("utf-8"))
        import_profile_dict(obj)
        
        # EXHAUSTIVE WIDGET PURGE: Forces UI text boxes to refresh
        keys_to_purge = [
            k for k in st.session_state.keys()
            if k.startswith("pt_title_")
            or k.startswith("pt_tpl_")
            or k.startswith("prompt_task_cb_")
            or k == "fav_bulk_editor"
        ]
        
        for k in keys_to_purge:
            st.session_state.pop(k, None)
        
        # Purge the selection list so it regenerates from defaults
        st.session_state.pop("prompt_selected_task_ids", None)
        
        # Re-run normalization to populate prompt_selected_task_ids from the new defaults
        normalize_prompt_state()
        
        st.session_state["_upload_applied"] = True
        st.session_state.pop("_upload_error", None)
        st.session_state["_post_apply_rerun"] = True
        st.rerun()
        
    except Exception as e:
        st.session_state["_upload_error"] = f"Takeover failed: {e}"

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
    st.markdown(
        """
        <div class="splash-wrap">
          <div class="splash-card">
            <div class="splash-title">Radix 🈑 Components</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # REPLACED HTML LINK WITH NATIVE BUTTON TO FIX STATE RESET
    st.markdown(
        """
        <div class="palace-entrance-container">
            <div class="grand-torii">⛩️</div>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Use columns to center the button nicely
    col_c = st.columns([1, 1.2, 1])[1]
    with col_c:
        if st.button("Enter the Grand Hall of Radix 🈑", use_container_width=True, type="primary"):
            st.session_state.onboarding_done = True
            st.rerun()

    demos = st.session_state.favourites_list
    if demos:
        st.markdown("<h4 style='text-align:center; color:#666; margin-top:20px;'>Quick Access Favourites</h4>", unsafe_allow_html=True)
        lc1, lc2, lc3 = st.columns([1, 2, 1])
        with lc2:
            with st.expander("📂 User Data (Save/Load/Review & Edit)", expanded=False):
                st.caption("Single JSON file for **Favourites** + **AI Prompt Tasks**. Upload applies immediately; download is your backup.")
                c_dl, c_ul = st.columns(2)
                with c_dl:
                    st.download_button(
                        label="💾 Download user data (JSON)",
                        data=export_profile_str(),
                        file_name=PROFILE_FILENAME,
                        mime="application/json",
                        use_container_width=True,
                    )
                with c_ul:
                    # Separate logic for widget vs state
                    uploaded_file = st.file_uploader(
                        "Upload user data (JSON)",
                        type=["json"],
                        key="profile_uploader_persistent",
                        label_visibility="collapsed",
                    )
                    
                    if uploaded_file is not None:
                        file_bytes = uploaded_file.getvalue()
                        file_hash = hashlib.sha256(file_bytes).hexdigest()
                        last_hash = st.session_state.get('_last_upload_hash', '')
                        
                        # Only show "Apply" if it's a new or un-applied file
                        if file_hash != last_hash:
                            st.warning("⚠️ New file detected - click Apply to use it")
                            if st.button("✅ Apply uploaded file now", use_container_width=True, type="primary", key="apply_upload_btn"):
                                st.session_state["_last_upload_hash"] = file_hash
                                _apply_uploaded_profile_bytes(file_bytes)
                        else:
                            st.success("✓ Current file is active")
                        
                        if st.button("♻️ Upload different file", use_container_width=True, key="reset_uploader_btn"):
                            st.session_state.pop("_last_upload_hash", None)
                            st.session_state.pop("_upload_error", None)
                            st.session_state.pop("_upload_applied", None)
                            st.session_state.pop("profile_uploader_persistent", None)
                            st.rerun()

                if st.session_state.get("_upload_error"):
                    st.error(st.session_state["_upload_error"])
                elif st.session_state.get("_upload_applied"):
                    st.success("✅ Upload applied! Download to save.")
                    if st.button("Dismiss", key="dismiss_success"):
                        st.session_state["_upload_applied"] = False
                        st.rerun()

                with st.expander("🔎 Review current data snapshot", expanded=False):
                    st.json(build_profile_dict()) # Match the defined function name

                st.markdown("---")
                st.subheader("Favourites")
                fav_text_default = " ".join(st.session_state.get("favourites_list", []))
                fav_text = st.text_area("Favourites", value=fav_text_default, height=90, key="fav_bulk_editor", label_visibility="collapsed")
                tokens = [t for t in re.split(r"\s+", (fav_text or "").strip()) if t]
                valid = [t for t in tokens if isinstance(t, str) and len(t) == 1]
                seen = set()
                cleaned = []
                for c in valid:
                    if c not in seen:
                        cleaned.append(c)
                        seen.add(c)
                st.caption(f"Preview: {len(cleaned)} favourites ready.")

                c1, c2, c3 = st.columns([1, 1, 2])
                with c1:
                    if st.button("Apply favourites", use_container_width=True, key="fav_apply"):
                        st.session_state.favourites_list = cleaned
                        st.session_state.fav_cursor = 0
                        st.toast("Updated.", icon="✅")
                        st.rerun()
                with c2:
                    if st.button("Clear favourites", use_container_width=True, key="fav_clear"):
                        st.session_state.favourites_list = []
                        st.session_state.fav_cursor = 0
                        st.rerun()

                st.markdown("---")
                st.subheader("AI Prompt Tasks")
                normalize_prompt_state()
                cfg = st.session_state.get("prompt_config") or {}
                tasks = cfg.get("tasks", []) or []
                all_task_ids = [t.get("id") for t in tasks if t.get("id")]
                default_sel = st.multiselect("Default tasks", options=all_task_ids, default=list(st.session_state.prompt_ui.get("default_selected_task_ids", all_task_ids)), key="prompt_default_sel_editor")
                if st.button("Save defaults", key="save_default_task_sel"):
                    st.session_state.prompt_ui["default_selected_task_ids"] = list(default_sel)
                    st.rerun()

                edited_tasks = []
                for t in tasks:
                    tid = t.get("id")
                    if not tid: continue
                    with st.expander(f"✏️ {t.get('title','(untitled)')}", expanded=False):
                        title = st.text_input("Title", value=t.get("title", ""), key=f"pt_title_{tid}")
                        template = st.text_area("Template", value=t.get("template", ""), height=160, key=f"pt_tpl_{tid}")
                        if st.button("Delete task", key=f"pt_del_{tid}"):
                            cur = (st.session_state.get("prompt_config") or {}).get("tasks", []) or []
                            st.session_state.prompt_config["tasks"] = [tt for tt in cur if tt.get("id") != tid]
                            st.rerun()
                    edited_tasks.append({"id": tid, "title": title, "template": template})
                
                c_add, c_apply = st.columns([1, 1])
                with c_add:
                    if st.button("Add new task", key="pt_add_new_home", use_container_width=True):
                        cfg = st.session_state.get("prompt_config") or {}
                        tasks_cur = list(cfg.get("tasks", []) or [])
                        existing_ids = [t.get("id") for t in tasks_cur]
                        nums = [int(re.match(r"^task(\d+)$", tid).group(1)) for tid in existing_ids if re.match(r"^task(\d+)$", tid)]
                        next_num = (max(nums) + 1) if nums else 1
                        tasks_cur.append({"id": f"task{next_num}", "title": "New task", "template": "Prompt template...\n"})
                        st.session_state.prompt_config["tasks"] = tasks_cur
                        st.rerun()
                with c_apply:
                    if st.button("Apply task edits", key="pt_apply_home", use_container_width=True):
                        st.session_state.prompt_config["tasks"] = edited_tasks
                        st.rerun()

        st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
        COLS = 5
        rows = (len(demos) + COLS - 1) // COLS
        for r in range(rows):
            cols = st.columns(COLS)
            for j in range(COLS):
                idx = r * COLS + j
                if idx < len(demos):
                    ch = demos[idx]
                    count = component_usage_count(ch)
                    with cols[j]:
                        if st.button(f"Explore {ch}", key=f"v4_splash_{idx}_{ord(ch)}", use_container_width=True, type="primary"):
                            st.session_state.onboarding_done = True
                            enter_component(ch)
                            st.rerun()
                        st.caption(f"in {count} chars")
        st.markdown("</div>", unsafe_allow_html=True)

def render_radix_row(c, context="detail", is_static=False):
    col_char, col_details = st.columns([2, 10])
    is_preview = st.session_state.preview_comp == c
    is_active_focus = is_preview or (st.session_state.preview_comp is None and c == st.session_state.selected_comp)
    with col_char:
        if is_static:
            st.markdown(f"<div class='char-static-box'>{c}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='char-btn-wrap'>", unsafe_allow_html=True)
            st.button(c, key=f"explore_{context}_{c}_{ord(c)}_{uuid.uuid4().hex[:8]}", type="primary" if is_preview else "secondary", on_click=list_tile_click, args=(c,), use_container_width=True)
            st.markdown(f"<div class='char-btn-hint {'previewing' if is_preview else ''}'>{'Drill down' if is_preview else 'Preview'}</div>", unsafe_allow_html=True)
            st.markdown("<div class='pen-btn-wrap'>", unsafe_allow_html=True)
            def activate_stroke_view(char):
                st.session_state.stroke_view_char = char
                st.session_state.stroke_view_active = True
                st.session_state.show_inputs = False
                if not st.session_state.selected_comp:
                    st.session_state.selected_comp = char
            if st.button("🧠 link", key=f"strk_{c}_{ord(c)}_{uuid.uuid4().hex[:8]}", use_container_width=True, on_click=activate_stroke_view, args=(c,)): pass
            st.markdown("</div></div>", unsafe_allow_html=True)
    with col_details:
        st.markdown(generate_clean_card_html(c, usage_count=component_usage_count(c), is_static=is_static), unsafe_allow_html=True)
        if not is_static and is_active_focus and st.session_state.display_mode != "Single Character":
            n = {"2-Characters": 2, "3-Characters": 3, "4-Characters": 4}.get(st.session_state.display_mode, 0)
            meta_compounds = component_map.get(c, {}).get("meta", {}).get("compounds", [])
            relevant = [w for w in meta_compounds if len(w) == n]
            if relevant:
                db_conn = get_db_connection()
                if db_conn:
                    phrases_map = batch_get_phrase_details(sorted(relevant), db_conn)
                    items = [f"<div style='display:flex; align-items:baseline; padding:5px 8px; border-bottom:1px solid #eee;'><span style='font-weight:700; font-size:1.0rem; min-width:65px;'>{word}</span><span style='color:#d35400; font-size:0.85rem; font-family:monospace; margin-right:12px; font-weight:600;'>{phrases_map.get(word,{}).get('pinyin','')}</span><span style='color:#444; font-size:0.85rem; flex:1; line-height:1.2;'>{pyhtml.escape(phrases_map.get(word,{}).get('meanings','')[:130])}</span></div>" for word in sorted(relevant)]
                    st.markdown(f"<div style='padding:12px; background:#f1f8e9; border-radius:8px; margin-top:10px; border:1px solid #dcedc8; max-height:400px; overflow-y:auto;'><div style='font-weight:bold; font-size:0.8rem; margin-bottom:8px; color:#2e7d32; text-transform:uppercase;'>{st.session_state.display_mode} containing {c}</div>{''.join(items)}</div>", unsafe_allow_html=True)

def main():
    if not component_map: st.stop()
    apply_dynamic_css()
    if not st.session_state.get("onboarding_done", False):
        render_splash()
        st.stop()
    with st.sidebar:
        cur = st.session_state.stroke_view_char if st.session_state.stroke_view_active else (st.session_state.preview_comp or st.session_state.selected_comp)
        if cur:
            sidebar_html, sidebar_height = get_stroke_order_sidebar_html(cur, size=140)
            if sidebar_html: st_html(sidebar_html, height=sidebar_height)
            count = len(apply_script_filter([c for c in component_map.get(cur, {}).get("related_characters", []) if len(c) == 1], st.session_state.script_filter))
            if count > 0: st.markdown(f"<div style='font-size:0.75em; line-height:1.1; margin:0.15rem 0 0.35rem 0; opacity:0.8;'>{count} chars contain <span class='char'>{cur}</span></div>", unsafe_allow_html=True)
            st.checkbox("Favourite", value=(cur in st.session_state.favourites_list), key=f"fav_chk_{cur}", on_change=toggle_favourite, args=(cur,))
            if st.button("Show Favourites", use_container_width=True): go_to_root(); st.session_state.onboarding_done = False; st.rerun()
        if not st.session_state.show_inputs:
            c1, c2 = st.columns(2)
            with c1: st.button("← Back", on_click=(end_stroke_view if st.session_state.stroke_view_active else go_back), use_container_width=True)
            with c2: st.button("🏠 Root", on_click=go_to_root, use_container_width=True)
            with st.expander("Display Phrases", expanded=False):
                modes = ["Single Character", "2-Characters", "3-Characters", "4-Characters"]
                new_mode = st.radio("Select mode", options=modes, index=modes.index(st.session_state.display_mode), label_visibility="collapsed")
                if new_mode != st.session_state.display_mode: st.session_state.display_mode = new_mode; st.rerun()
        st.text_input("Shortcut search", key="sb_search", on_change=sync_sidebar_text)
        with st.expander("🔎 Filters", expanded=False):
            if not st.session_state.show_inputs: st.radio("Filter", options=SCRIPT_FILTERS, index=SCRIPT_FILTERS.index(st.session_state.script_filter), key="w_script_filter", on_change=sync_script_filter)
            else:
                st.slider("Stroke count", min_value=1, max_value=30, value=st.session_state.stroke_range, key="w_stroke_range", on_change=sync_stroke_range)
                st.selectbox("Radical", options=["none"] + sorted(list(set(info.get("meta", {}).get("radical") for info in component_map.values() if info.get("meta", {}).get("radical")))), key="w_radical", on_change=sync_radical)
                st.selectbox("IDC", options=["none"] + sorted(stats_cache.get("idc_counts", {}).keys()), key="w_idc", on_change=sync_idc)
                st.radio("Sort", options=["Most Useful", "Most Common"], index=(0 if st.session_state.grid_sort_mode == "usage" else 1), key="grid_sort_mode_radio", on_change=lambda: st.session_state.update({"grid_sort_mode": "usage" if st.session_state.grid_sort_mode_radio == "Most Useful" else "frequency", "page": 1}))

    if st.session_state.stroke_view_active:
        main_html, phrases_html = get_stroke_order_view_html(st.session_state.stroke_view_char, st.session_state.display_mode)
        st_html(main_html, height=450)
        if phrases_html: st.markdown(phrases_html, unsafe_allow_html=True)
        st.markdown("### ChatGPT Prompt")
        cfg = st.session_state.prompt_config
        tasks = cfg.get("tasks", [])
        all_ids = [t.get("id") for t in tasks]
        with st.expander("Prompt tasks", expanded=True):
            # FALLBACK: Use .get() here to prevent crashes if prompt_selected_task_ids is momentarily missing
            sel_ids = st.session_state.get("prompt_selected_task_ids", [])
            sel = [tid for tid in all_ids if st.checkbox(next(t["title"] for t in tasks if t["id"] == tid), value=(tid in sel_ids), key=f"prompt_task_cb_{tid}")]
            st.session_state.prompt_selected_task_ids = sel
        if st.button("Select all"): st.session_state.prompt_selected_task_ids = all_ids; st.rerun()
        prompt_text = render_combined_prompt(char=st.session_state.stroke_view_char, prompt_config=st.session_state.prompt_config, selected_task_ids=st.session_state.prompt_selected_task_ids, definition_en=get_char_definition_en(st.session_state.stroke_view_char))
        st.text_area("Prompt", value=prompt_text, height=320)
        render_copy_to_clipboard(prompt_text, str(hash(st.session_state.stroke_view_char)))
        st.stop()

    if st.session_state.show_inputs:
        f_sum = "".join([f"<span class='status-tag'>{st.session_state.stroke_range} strokes</span>", f"<span class='status-tag'>Rad. {st.session_state.radical}</span>" if st.session_state.radical != "none" else ""])
        st.markdown(f"<div class='status-line'><div style='display: flex; justify-content: space-between;'><div><b>🔍 Filters:</b> {f_sum or 'All'}</div><div style='font-size: 0.8em;'>Preview then drill down.</div></div></div>", unsafe_allow_html=True)
        filtered = [c for c in component_map if st.session_state.stroke_range[0] <= (get_stroke_count(c) or 0) <= st.session_state.stroke_range[1] and (st.session_state.radical == "none" or component_map[c]["meta"].get("radical") == st.session_state.radical) and (st.session_state.component_idc == "none" or component_map[c]["meta"].get("decomposition", "").startswith(st.session_state.component_idc)) and (st.session_state.grid_sort_mode != "usage" or c in stats_cache["used_components"])]
        sorted_comps = sorted(filtered, key=(sort_key_frequency_primary if st.session_state.grid_sort_mode == "frequency" else sort_key_usage_primary))
        if not sorted_comps: st.info("No match.")
        else:
            P_SIZE = 120
            max_p = max(1, math.ceil(len(sorted_comps) / P_SIZE))
            st.session_state.page = max(1, min(st.session_state.page, max_p))
            p1, p2, p3 = st.columns([1, 3, 1])
            with p1: st.button("◀ Prev", disabled=(st.session_state.page <= 1), on_click=lambda: st.session_state.update({"page": st.session_state.page - 1}), use_container_width=True)
            with p2: st.markdown(f"<div style='text-align:center;'><b>{(st.session_state.page-1)*P_SIZE+1}–{min(st.session_state.page*P_SIZE, len(sorted_comps))} of {len(sorted_comps)}</b></div>", unsafe_allow_html=True)
            with p3: st.button("Next ▶", disabled=(st.session_state.page >= max_p), on_click=lambda: st.session_state.update({"page": st.session_state.page + 1}), use_container_width=True)
            page = sorted_comps[(st.session_state.page - 1) * P_SIZE : st.session_state.page * P_SIZE]
            st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
            cols = st.columns(10)
            for i, ch in enumerate(page):
                with cols[i % 10]: st.button(ch, key=f"b_{ch}_{st.session_state.page}", type="primary" if st.session_state.preview_comp == ch else "secondary", on_click=tile_click, args=(ch,), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            col2 = st.columns([1, 2, 1])[1]
            with col2: st.text_input("Jump", key="w_text", on_change=sync_text, placeholder="Hanzi...", label_visibility="collapsed")
            st.markdown("<div class='jump-footer'><h4>🔍 Definition Search</h4>", unsafe_allow_html=True)
            with st.columns([1, 2, 1])[1]:
                st.text_input("Search", key="w_def_search", placeholder="e.g., water", label_visibility="collapsed")
                if st.button("Search", use_container_width=True, type="primary"): search_by_definition(); st.rerun()
    else:
        if st.session_state.definition_search_mode and st.session_state.definition_search_results:
            res = st.session_state.definition_search_results
            st.markdown(f"<div class='status-line'><b>Search for \"{pyhtml.escape(st.session_state.definition_search_query)}\"</b></div>", unsafe_allow_html=True)
            for char in res['characters'][:30]: render_radix_row(char)
            for p in res['phrases']: st.markdown(f"<div class='compound-item'><span class='cp-word'>{p['word']}</span><span class='cp-pinyin'>{p['pinyin']}</span><span class='cp-mean'>{pyhtml.escape(p['meanings'][:200])}</span></div>", unsafe_allow_html=True)
        else:
            sel = st.session_state.selected_comp
            info = component_map.get(sel, {})
            p_html = "".join([f"<span class='status-tag'>{p}</span>" for p in apply_script_filter([p for p in info.get("meta", {}).get("decomposition", "") if p in component_map and p not in IDC_CHARS], st.session_state.script_filter)])
            c_html = "".join([f"<span class='status-tag' style='opacity: 0.8;'>{c}</span>" for c in apply_script_filter([c for c in info.get("related_characters", []) if len(c) == 1], st.session_state.script_filter)[:50]])
            st.markdown(f"<div class='status-line'><div style='display: flex; justify-content: space-between;'><div><b>{sel}</b><br/>Built from: {p_html or 'Root'}</div><div style='text-align: left;'><b>Derivatives</b><br/>{c_html}</div></div></div>", unsafe_allow_html=True)
            parents = apply_script_filter([p for p in info.get("meta", {}).get("decomposition", "") if p in component_map and p not in IDC_CHARS and p != sel], st.session_state.script_filter)
            if parents: 
                st.markdown("<div class='lineage-header'>🧱 Components</div>", unsafe_allow_html=True)
                for p in parents: render_radix_row(p)
            st.markdown("<div class='lineage-header'>🎯 Selection</div>", unsafe_allow_html=True)
            render_radix_row(sel)
            children = apply_script_filter(sorted([c for c in info.get("related_characters", []) if len(c) == 1 and c != sel], key=sort_key_usage_primary), st.session_state.script_filter)
            if children:
                st.markdown(f"<div class='lineage-header'>🌲 Derivatives ({len(children)})</div>", unsafe_allow_html=True)
                for child in children[:120]: render_radix_row(child)
                if len(children) > 120:
                    st.markdown(f"<div style='text-align:center;'>⬇️ {len(children)-120} More ⬇️</div>", unsafe_allow_html=True)
                    for c in children[120:]: render_radix_row(c, is_static=True)

if __name__ == "__main__": main()
