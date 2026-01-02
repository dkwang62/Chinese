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

def build_profile_payload() -> dict:
    return build_profile_dict()

def export_profile_str() -> str:
    return json.dumps(build_profile_dict(), ensure_ascii=False, indent=2)

def import_profile_dict(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Uploaded JSON must be an object.")
    if data.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise ValueError("Unsupported schema_version.")
    st.session_state.favourites_list = data.get("favourites_list", [])
    st.session_state.fav_cursor = 0
    st.session_state.prompt_config = data.get("prompt_config", {})
    st.session_state.prompt_ui = data.get("prompt_ui", {}) if isinstance(data.get("prompt_ui", {}), dict) else {}

st.set_page_config(layout="wide", page_title="Radix", page_icon="🈑")

# --- Dynamic CSS ---
def apply_dynamic_css():
    css = """
    <style>
    .main .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    
    /* Card Styling */
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
    
    /* Meta Row & Tags */
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
        margin-bottom: 6px;
        display: inline-block;
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

    /* Definition & Etymology (The Distinction You Requested) */
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

    /* Sidebar Specific Fixes */
    section[data-testid="stSidebar"] .meta-pinyin { font-size: 2.0em !important; }
    section[data-testid="stSidebar"] .char-card { padding: 16px !important; }
    
    /* Interactive Elements */
    .comp-grid .stButton > button {
        width: 100% !important; font-size: 2.2em !important; height: 85px !important;
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
        border: 2px solid #dee2e6 !important; border-radius: 14px !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.08) !important; padding: 0 !important;
        line-height: 85px !important; font-weight: 600 !important; transition: all 0.2s ease !important;
    }
    .comp-grid .stButton > button:hover {
        background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%) !important;
        border-color: #f2c6c6 !important; color: #c0392b !important;
        transform: translateY(-3px) !important; box-shadow: 0 6px 16px rgba(192, 57, 43, 0.15) !important;
    }
    .char-btn-wrap .stButton > button {
        width: 100% !important; font-size: 3.8em !important; font-weight: 700 !important;
        background: linear-gradient(135deg, #ffffff 0%, #f0f4f8 100%) !important;
        border: 3px solid #dee2e6 !important; padding: 10px !important; min-height: 90px !important;
        border-radius: 16px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        transition: all 0.25s ease !important;
    }
    .char-btn-wrap .stButton > button:hover {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%) !important;
        border-color: #3b82f6 !important; transform: scale(1.02) !important;
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.2) !important;
    }
    .pen-btn-wrap .stButton > button {
        width: 100% !important; font-size: 1.6em !important; border: 2px solid #dee2e6 !important;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%) !important;
        margin-top: 8px !important; height: 45px !important; line-height: 1 !important;
        color: #555 !important; font-weight: 600 !important; border-radius: 12px !important;
        transition: all 0.2s ease !important;
    }
    .pen-btn-wrap .stButton > button:hover {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%) !important;
        border-color: #64b5f6 !important; color: #1565c0 !important;
        transform: translateY(-2px) !important; box-shadow: 0 4px 12px rgba(100, 181, 246, 0.2) !important;
    }
    .char-static-box {
        font-size: 3.8em; font-weight: 700; background: linear-gradient(135deg, #fafafa 0%, #f0f0f0 100%);
        color: #bbb; border: 2px solid #e0e0e0; border-radius: 16px; padding: 10px;
        min-height: 90px; display: flex; align-items: center; justify-content: center;
        width: 100%; cursor: default; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .status-line {
        font-size: 1.1em; font-weight: 600; color: #0f5132;
        background: linear-gradient(135deg, #d1e7dd 0%, #c3e6cb 100%);
        border: 2px solid #95d5b2; padding: 18px; border-radius: 12px;
        margin: 20px 0 30px 0; box-shadow: 0 3px 10px rgba(15, 81, 50, 0.08);
    }
    .status-tag {
        background: linear-gradient(135deg, #ffffff 0%, #f1f3f5 100%);
        color: #2c3e50; padding: 6px 14px; border-radius: 8px; font-weight: 700;
        font-size: 0.9em; border: 2px solid #dee2e6; display: inline-flex; align-items: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .lineage-header {
        font-size: 1.4em; font-weight: 800; color: #2c3e50; margin: 30px 0 20px 0;
        padding: 12px 20px; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-left: 5px solid #1976d2; border-radius: 8px;
        box-shadow: 0 2px 8px rgba(25, 118, 210, 0.1);
    }
    .compound-item {
        display: flex; align-items: baseline; margin-bottom: 10px; padding: 12px;
        border-bottom: 2px solid #e9ecef; border-radius: 8px; background: #ffffff;
        transition: all 0.2s ease;
    }
    .compound-item:hover { background: #f8f9fa; transform: translateX(4px); }
    .cp-word { font-weight: 700; font-size: 1.2em; color: #2c3e50; min-width: 85px; margin-right: 15px; }
    .cp-pinyin { color: #d35400; font-family: 'Monaco', 'Menlo', monospace; margin-right: 15px; font-weight: 600; font-size: 1.5em; }
    .cp-mean { color: #495057; font-size: 1em; flex: 1; line-height: 1.5; }
    .char-btn-hint { margin-top: 6px; text-align: center; font-size: 0.86em; color: #6c757d; font-weight: 700; }
    .char-btn-hint.previewing { color: #c0392b; }
    .status-line span { color: #0f5132; }
    .splash-wrap { max-width: 850px; margin: 0 auto; padding: 60px 20px 20px 20px; }
    .splash-card { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 40px; padding: 60px; box-shadow: 0 15px 50px rgba(0,0,0,0.05); text-align: center; }
    .splash-title { font-size: 3.0em; font-weight: 800; color: #1a1a1a; margin-bottom: 10px; }
    .splash-sub { font-size: 1.3em; color: #666; }
    .palace-entrance-container { text-align: center; margin: 60px 0; }
    .grand-torii { font-size: 250px !important; line-height: 1; filter: drop-shadow(0 10px 20px rgba(0,0,0,0.1)); }
    .entrance-text { color: #2c3e50; font-size: 24px; font-weight: 700; margin-top: 20px; margin-bottom: 30px; letter-spacing: 2px; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def render_copy_to_clipboard(prompt_text: str, widget_id: str):
    safe_text = json.dumps(prompt_text, ensure_ascii=False)
    st_html(
        f"""
        <div style="display:flex; justify-content:center; margin:10px 0 0 0;">
          <button id="copy-btn-{widget_id}" style="padding:10px 14px; border-radius:10px; border:1px solid #ddd; background:#fff; cursor:pointer; font-weight:700;">
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
              try {{ await navigator.clipboard.writeText(text); msg.textContent = "Copied. Paste into ChatGPT."; }} 
              catch (e) {{ msg.textContent = "Copy failed."; }}
              setTimeout(() => {{ msg.textContent = ""; }}, 2500);
            }}
            btn.addEventListener("click", copy);
          }})();
        </script>
        """,
        height=90,
    )

# --- Session State Defaults ---
DEFAULTS = {
    "startup_file_choice_made": False,
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
    "favourites_list": [],
    "fav_cursor": 0,
    "prompt_config": None,
    "prompt_ui": {"default_selected_task_ids": []},
    "prompt_selected_task_ids": [],
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

# Auto-load server-side user data
if "server_data_loaded" not in st.session_state:
    st.session_state.server_data_loaded = True
    st.session_state.server_data_available = False
    if not st.session_state.get("_manual_config_active", False):
        try:
            with open("radix_user_data.json", "r", encoding="utf-8") as f:
                obj = json.load(f)
            if (isinstance(obj, dict) and obj.get("schema_version") == 1):
                st.session_state.server_data = obj
                st.session_state.server_data_available = True
        except FileNotFoundError: pass
        except Exception as e: st.error(f"Error loading server radix_user_data.json: {e}")

st.session_state.prompt_config = normalize_prompt_config(st.session_state.get("prompt_config"))
if st.session_state.prompt_config is None:
    st.session_state.prompt_config = get_default_prompt_config()
else:
    st.session_state.prompt_config = normalize_prompt_config(st.session_state.prompt_config)

_task_ids = [t.get('id') for t in st.session_state.prompt_config.get('tasks', []) if t.get('id')]
if not st.session_state.prompt_ui.get('default_selected_task_ids'):
    st.session_state.prompt_ui['default_selected_task_ids'] = _task_ids
if not st.session_state.prompt_selected_task_ids:
    st.session_state.prompt_selected_task_ids = list(st.session_state.prompt_ui.get('default_selected_task_ids', _task_ids))

# --- Callbacks & Helpers ---

def normalize_prompt_state() -> None:
    """Ensure prompt_config/tasks and prompt selection UI state are internally consistent."""
    cfg = st.session_state.get("prompt_config") or {}
    tasks = cfg.get("tasks", []) or []
    cleaned_tasks = []
    seen_ids = set()
    for t in tasks:
        if isinstance(t, dict) and t.get("id"):
            if t["id"] not in seen_ids:
                seen_ids.add(t["id"])
                cleaned_tasks.append(t)
    cfg["tasks"] = cleaned_tasks
    st.session_state.prompt_config = cfg
    
    all_task_ids = [t["id"] for t in cleaned_tasks]
    pui = st.session_state.get("prompt_ui") or {}
    default_ids = pui.get("default_selected_task_ids", [])
    pui["default_selected_task_ids"] = [t for t in default_ids if t in all_task_ids] or list(all_task_ids)
    st.session_state.prompt_ui = pui
    
    cur_sel = st.session_state.get("prompt_selected_task_ids") or []
    st.session_state.prompt_selected_task_ids = [t for t in cur_sel if t in all_task_ids] or list(pui["default_selected_task_ids"])
    
    for tid in all_task_ids:
        key = f"prompt_task_cb_{tid}"
        if key not in st.session_state:
            st.session_state[key] = (tid in st.session_state.prompt_selected_task_ids)

def _clear_derived_widget_state():
    """Nuclear clear of ALL derived keys to prevent zombie state from old configs."""
    keys_to_clear = []
    for k in list(st.session_state.keys()):
        if (k == "fav_bulk_editor" or k.startswith("pt_title_") or k.startswith("pt_tpl_") or 
            k.startswith("prompt_task_cb_") or k == "prompt_selected_task_ids" or 
            k == "prompt_default_sel_editor" or k.startswith("fav_chk_")):
            keys_to_clear.append(k)
    for k in keys_to_clear:
        st.session_state.pop(k, None)

def _enter_character_view(char: str):
    """Centralized logic to enter the main character view."""
    st.session_state.update({
        "script_filter": "Any",
        "history": [],
        "selected_comp": char,
        "last_valid_selected_comp": char,
        "text_input_comp": char,
        "text_input_warning": None,
        "show_inputs": False,
        "preview_comp": None,
        "stroke_view_active": False,
        "stroke_view_char": "",
        "display_mode": "2-Characters",
        "definition_search_mode": False,
        "definition_search_results": None
    })

def _validate_and_search(raw: str, error_callback=None):
    """Refactored shared search logic."""
    v = normalize_single_hanzi(raw)
    if not v:
        if error_callback: error_callback("One character only")
        return
    resolved = resolve_to_known_variant(v)
    if not resolved:
        if error_callback: error_callback("Not found")
        return
    _enter_character_view(resolved)

def sync_text():
    def cb(msg): st.session_state.text_input_warning = msg
    _validate_and_search(st.session_state.get("w_text", ""), cb)

def sync_sidebar_text():
    _validate_and_search(st.session_state.get("sb_search", ""), st.toast)

def sync_splash_text():
    raw = st.session_state.get("splash_search", "")
    if normalize_single_hanzi(raw) and resolve_to_known_variant(normalize_single_hanzi(raw)):
        st.session_state.onboarding_done = True
    st.session_state.sb_search = raw
    sync_sidebar_text()

def sync_stroke_range(): st.session_state.stroke_range = st.session_state.w_stroke_range; st.session_state.page = 1
def sync_radical(): st.session_state.radical = st.session_state.w_radical; st.session_state.page = 1
def sync_idc(): st.session_state.component_idc = st.session_state.w_idc; st.session_state.page = 1
def sync_script_filter(): st.session_state.script_filter = st.session_state.w_script_filter

def tile_click(c):
    if st.session_state.show_inputs and st.session_state.preview_comp == c: _enter_character_view(c)
    else: st.session_state.preview_comp = c

def list_tile_click(c):
    if st.session_state.preview_comp == c:
        if not st.session_state.get("has_drilled_down", False):
            st.toast("Feature Discovered: You have entered the Character Lineage view!", icon="🌳")
            st.session_state.has_drilled_down = True
        if st.session_state.selected_comp: st.session_state.history.append(st.session_state.selected_comp)
        st.session_state.selected_comp = c
        st.session_state.show_inputs = False
        st.session_state.preview_comp = None
    else: st.session_state.preview_comp = c

def go_back():
    st.session_state.update({"preview_comp": None, "stroke_view_active": False, "stroke_view_char": "", 
                           "definition_search_mode": False, "definition_search_results": None, "text_input_warning": None})
    if st.session_state.history:
        prev = st.session_state.history.pop()
        st.session_state.update({"selected_comp": prev, "last_valid_selected_comp": prev, "script_filter": "Any", "show_inputs": False})
    else: st.session_state.show_inputs = True

def go_to_root():
    st.session_state.update({"history": [], "preview_comp": None, "stroke_view_active": False, "stroke_view_char": "", 
                           "text_input_comp": "", "text_input_warning": None, "selected_comp": "", "show_inputs": True, 
                           "script_filter": "Any", "display_mode": "2-Characters", "definition_search_mode": False, 
                           "definition_search_results": None})

def end_stroke_view():
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""

def toggle_favourite(char):
    if st.session_state.get(f"fav_chk_{char}", False):
        if char not in st.session_state.favourites_list:
            if len(st.session_state.favourites_list) < 20: st.session_state.favourites_list.append(char)
            else:
                idx = st.session_state.fav_cursor
                st.session_state.favourites_list[idx] = char
                st.session_state.fav_cursor = (idx + 1) % 20
    elif char in st.session_state.favourites_list: st.session_state.favourites_list.remove(char)

def _apply_uploaded_profile_bytes(file_bytes: bytes) -> None:
    try:
        obj = json.loads(file_bytes.decode("utf-8"))
        _clear_derived_widget_state()
        import_profile_dict(obj)
        st.session_state.update({"_upload_applied": True, "_manual_config_active": True, "_post_apply_rerun": True})
        st.session_state.pop("_upload_error", None)
        normalize_prompt_state()
    except Exception as e:
        st.session_state["_upload_error"] = f"Invalid JSON: {e}"
        st.session_state["_upload_applied"] = False

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
    
    st.session_state.update({"definition_search_mode": True, "definition_search_query": query, 
                           "definition_search_results": {"characters": char_results[:120], "phrases": phrase_results[:200]},
                           "show_inputs": False, "selected_comp": "", "preview_comp": None})

def render_definition_search_ui(key_prefix: str):
    """Consolidated UI for definition search."""
    st.markdown("**English Definition Search**")
    key = f"{key_prefix}_def_search"
    st.text_input("Search definitions", key=key, placeholder="e.g., water, fire, mountain", label_visibility="collapsed")
    if st.button("Search Definitions", use_container_width=True, type="primary", key=f"{key_prefix}_def_btn"):
        st.session_state.w_def_search = st.session_state.get(key, "")
        search_by_definition()
        if key_prefix == "splash": st.session_state.onboarding_done = True
        st.rerun()
    st.caption("Search across character definitions and phrase meanings")

def render_startup_file_choice():
    st.markdown("""<div class="splash-wrap"><div class="splash-card"><div class="splash-title">Radix 🈑 - Data Setup</div>
                   <div class="splash-sub" style="margin-top: 20px;">Do you have a local Radix user data file you'd like to use?</div></div></div>""", unsafe_allow_html=True)
    st.markdown("<div style='max-width: 600px; margin: 40px auto;'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("📱 Yes, upload my local file", use_container_width=True, type="primary"):
        st.session_state.startup_choice = "upload"; st.rerun()
    if c2.button("☁️ No, use server defaults", use_container_width=True):
        st.session_state.startup_choice = "server"
        if st.session_state.get("server_data_available"):
            obj = st.session_state.server_data
            st.session_state.update({"favourites_list": obj["favourites_list"], "prompt_config": obj["prompt_config"], "prompt_ui": obj["prompt_ui"]})
        st.session_state.startup_file_choice_made = True; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.session_state.get("startup_choice") == "upload":
        st.markdown("<div style='max-width: 600px; margin: 40px auto;'><h3>📤 Upload Your Local File</h3>", unsafe_allow_html=True)
        if f := st.file_uploader("Choose your radix_user_data.json file", type=["json"], key="startup_uploader"):
            _apply_uploaded_profile_bytes(f.getvalue())
            if st.session_state.get("_upload_applied"):
                 st.success("✅ File loaded successfully!"); 
                 if st.button("Continue to Radix", type="primary", use_container_width=True):
                    st.session_state.startup_file_choice_made = True; st.rerun()
            elif st.session_state.get("_upload_error"): st.error(st.session_state["_upload_error"])
            elif st.button("← Back to choice", use_container_width=True): st.session_state.startup_choice = None; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def render_splash():
    st.markdown("""<div class="splash-wrap"><div class="splash-card"><div class="splash-title">Radix 🈑 Components</div></div></div>""", unsafe_allow_html=True)
    st.markdown("""<div class="palace-entrance-container"><div class="grand-torii">⛩️</div><div class="entrance-text">Grand Hall of Radix 🈑 Components</div></div>""", unsafe_allow_html=True)
    _, c, _ = st.columns([1,1,1])
    if c.button("🚪 Enter", key="entrance_btn", use_container_width=True, type="primary"): st.session_state.onboarding_done = True; st.rerun()

    st.markdown("<div style='max-width: 600px; margin: 40px auto;'>", unsafe_allow_html=True)
    with st.expander("🔍 Search", expanded=False):
        st.markdown("**Character Search**")
        st.text_input("Paste or type a character to explore", key="splash_search", on_change=sync_splash_text, placeholder="e.g., 水", label_visibility="collapsed")
        st.caption("Enter one Chinese character to jump directly to its details")
        st.markdown("---")
        render_definition_search_ui("splash")
    st.markdown("</div>", unsafe_allow_html=True)

    if demos := st.session_state.favourites_list:
        st.markdown("<h4 style='text-align:center; color:#666; margin-top:20px;'>Quick Access Favourites</h4>", unsafe_allow_html=True)
        lc1, lc2, lc3 = st.columns([1, 2, 1])
        with lc2:
            with st.expander("📂 User Data (Save/Load/Review & Edit)", expanded=False):
                st.caption("Single JSON file for **Favourites** + **AI Prompt Tasks (Tasks)**. Upload applies immediately in-app; download is your backup/export.")
                if st.session_state.get("_manual_config_active"): st.info("🔒 Using uploaded configuration (overrides server defaults)")
                elif st.session_state.get("server_data_available"): st.info("☁️ Using server default configuration")
                else: st.info("🆕 Using app default configuration")

                c_dl, c_ul = st.columns(2)
                with c_dl: st.markdown(render_ipad_safe_download_html(export_profile_str(), PROFILE_FILENAME, "💾 Download user data"), unsafe_allow_html=True)
                with c_ul: 
                    if uf := st.file_uploader("Upload user data (JSON)", type=["json"], key="profile_uploader_persistent", label_visibility="collapsed"):
                        hash_val = hashlib.sha256(uf.getvalue()).hexdigest()
                        if hash_val != st.session_state.get('_last_upload_hash', ''):
                            st.warning("⚠️ New file detected - click Apply to use it")
                            if st.button("✅ Apply uploaded file now", use_container_width=True, type="primary", key="apply_upload_btn"):
                                st.session_state["_last_upload_hash"] = hash_val; _apply_uploaded_profile_bytes(uf.getvalue()); st.rerun()
                        else: st.success("✓ Current file is active")
                        if st.button("♻️ Upload different file", use_container_width=True, key="reset_uploader_btn"):
                            st.session_state.pop("_last_upload_hash", None); st.session_state.pop("_upload_error", None)
                            st.session_state.pop("_upload_applied", None); st.session_state.pop("profile_uploader_persistent", None); st.rerun()
                
                if st.session_state.get("_upload_error"): st.error(st.session_state["_upload_error"])
                elif st.session_state.get("_upload_applied"):
                    st.success("✅ Upload applied successfully! Download to save changes.")
                    if st.button("Dismiss", key="dismiss_success"): st.session_state["_upload_applied"] = False; st.rerun()
                if st.session_state.get("_post_apply_rerun"): st.session_state["_post_apply_rerun"] = False; st.rerun()

                with st.expander("🔎 Review current data snapshot (what will be downloaded)", expanded=False): st.json(build_profile_payload())

                st.markdown("---"); st.subheader("Favourites")
                fav_txt = st.text_area("Favourites (space or newline separated)", value=" ".join(st.session_state.get("favourites_list", [])), height=90, key="fav_bulk_editor", label_visibility="collapsed")
                c1, c2, c3 = st.columns([1, 1, 2])
                with c1:
                    if st.button("Apply favourites", use_container_width=True, key="fav_apply"):
                        tokens = [t for t in re.split(r"\s+", (fav_txt or "").strip()) if t]
                        cleaned = []
                        seen = set()
                        for c in [t for t in tokens if len(t)==1]:
                            if c not in seen: cleaned.append(c); seen.add(c)
                        st.session_state.favourites_list = cleaned; st.session_state.fav_cursor = 0
                        st.toast("Favourites updated.", icon="✅"); st.rerun()
                with c2: 
                    if st.button("Clear favourites", use_container_width=True, key="fav_clear"): st.session_state.favourites_list = []; st.session_state.fav_cursor = 0; st.toast("Cleared favourites.", icon="✅"); st.rerun()
                with c3:
                    add_char = st.text_input("Add a character", value="", key="fav_add_one", placeholder="e.g., 我", label_visibility="collapsed")
                    if st.button("Add", use_container_width=True, key="fav_add_btn"):
                        c = (add_char or "").strip()
                        if len(c) != 1: st.toast("Please enter exactly 1 character.", icon="⚠️")
                        else:
                            if c not in st.session_state.favourites_list: st.session_state.favourites_list.append(c); st.toast("Added.", icon="✅"); st.rerun()

                favs = st.session_state.get("favourites_list", [])
                if favs:
                    st.markdown("**Current favourites**")
                    for i, c in enumerate(favs):
                        cc1, cc2 = st.columns([6, 1])
                        with cc1: st.write(c)
                        with cc2:
                            if st.button("✕", key=f"fav_rm_{i}", help="Remove"): st.session_state.favourites_list.pop(i); st.toast("Removed.", icon="✅"); st.rerun()

                st.markdown("---"); st.subheader("AI Prompt Tasks (Task 1–10)")
                normalize_prompt_state()
                cfg = st.session_state.get("prompt_config") or {}
                tasks = cfg.get("tasks", []) or []
                all_task_ids = [t.get("id") for t in tasks if t.get("id")]
                
                default_sel = st.multiselect("Default selected tasks", options=all_task_ids, default=list(st.session_state.prompt_ui.get("default_selected_task_ids", all_task_ids)), key="prompt_default_sel_editor")
                if st.button("Save default selection", key="save_default_task_sel"):
                    st.session_state.prompt_ui["default_selected_task_ids"] = list(default_sel)
                    normalize_prompt_state(); st.toast("Default task selection updated.", icon="✅"); st.rerun()

                st.caption("Edit titles/templates below. Changes persist in-session and will be included in the next download.")
                edited_tasks = []
                for idx, t in enumerate(tasks):
                    tid = t.get("id")
                    if not tid: continue
                    with st.expander(f"✏️ {t.get('title','(untitled)')}  —  {tid}", expanded=False):
                        title = st.text_input("Title", value=t.get("title", ""), key=f"pt_title_{tid}")
                        template = st.text_area("Template", value=t.get("template", ""), height=160, key=f"pt_tpl_{tid}")
                        cA, cB = st.columns([1, 3])
                        with cA:
                            if st.button("Delete task", key=f"pt_del_{tid}"):
                                st.session_state.prompt_config["tasks"] = [tt for tt in tasks if tt.get("id") != tid]
                                st.session_state.pop(f"pt_title_{tid}", None); st.session_state.pop(f"pt_tpl_{tid}", None); st.session_state.pop(f"prompt_task_cb_{tid}", None)
                                normalize_prompt_state(); st.toast("Task deleted.", icon="✅"); st.rerun()
                        with cB: st.caption("Tip: Keep the template as plain instructions. The character and definition are inserted separately.")
                    edited_tasks.append({"id": tid, "title": title, "template": template})
                
                c_add, c_apply = st.columns([1, 1])
                with c_add:
                    if st.button("Add new task", key="pt_add_new_home", use_container_width=True):
                        new_id = f"task_{uuid.uuid4().hex[:8]}"
                        tasks.append({"id": new_id, "title": "New task", "template": "Write your task instructions here.\n"})
                        st.session_state.prompt_config["tasks"] = tasks
                        normalize_prompt_state(); st.toast("Task added. Edit it below.", icon="✅")
                with c_apply:
                    if st.button("Apply task edits", key="pt_apply_home", use_container_width=True):
                        st.session_state.prompt_config["tasks"] = edited_tasks; normalize_prompt_state(); st.toast("Tasks updated.", icon="✅"); st.rerun()

        st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
        unique_demos = []
        seen = set()
        for d in demos:
            if d not in seen: unique_demos.append(d); seen.add(d)
        
        COLS = 5
        for r in range((len(unique_demos) + COLS - 1) // COLS):
            cols = st.columns(COLS)
            for j in range(COLS):
                idx = r * COLS + j
                if idx < len(unique_demos):
                    ch = unique_demos[idx]
                    with cols[j]:
                        if st.button(f"Explore {ch}", key=f"v4_splash_btn_{idx}_{ord(ch)}", use_container_width=True, type="primary"):
                            st.session_state.onboarding_done = True; _enter_character_view(ch); st.rerun()
                        st.caption(f"used in {component_usage_count(ch)} characters")
        st.markdown("</div>", unsafe_allow_html=True)

def _render_phrase_html(c: str) -> str:
    """Consolidated logic to render the phrase table HTML for any character."""
    n_map = {"Single Character": 1, "2-Characters": 2, "3-Characters": 3, "4-Characters": 4}
    n = n_map.get(st.session_state.display_mode, 2)
    compounds = [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w) == n]
    
    if compounds and (db := get_db_connection()):
        phrases = batch_get_phrase_details(sorted(compounds), db)
        items_html_list = []
        for word in sorted(compounds):
            entry = phrases.get(word)
            if entry:
                p_mean = pyhtml.escape(entry.get('meanings', '')[:130] + ('...' if len(entry.get('meanings', '')) > 130 else ''))
                items_html_list.append(f"<div style='display:flex; align-items:baseline; padding:5px 8px; border-bottom:1px solid #eee;'><span style='font-weight:700; font-size:1.0rem; min-width:65px;'>{word}</span><span style='color:#d35400; font-size:0.85rem; font-family:monospace; margin-right:12px; font-weight:600;'>{entry.get('pinyin', '')}</span><span style='color:#444; font-size:0.85rem; flex:1; line-height:1.2;'>{p_mean}</span></div>")
        
        if items_html_list:
            return f"""
            <div style='padding:12px; background:#f1f8e9; border-radius:8px; margin-top:10px; border:1px solid #dcedc8; max-height:400px; overflow-y:auto;'>
                <div style='font-weight:bold; font-size:0.8rem; margin-bottom:8px; color:#2e7d32; text-transform:uppercase;'>
                    {st.session_state.display_mode} containing {c}
                </div>
                {''.join(items_html_list)}
            </div>
            """
    return ""

def render_radix_row(c, context="detail", is_static=False):
    col_char, col_details = st.columns([2, 10])
    is_preview = st.session_state.preview_comp == c
    is_active_focus = is_preview or (st.session_state.preview_comp is None and c == st.session_state.selected_comp)

    with col_char:
        if is_static: st.markdown(f"<div class='char-static-box'>{c}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='char-btn-wrap'>", unsafe_allow_html=True)
            uid = str(uuid.uuid4())[:8]
            st.button(c, key=f"explore_char_{context}_{c}_{ord(c)}_{uid}", type="primary" if is_preview else "secondary",
                      help="Previewing..." if is_preview else "Click to preview", on_click=list_tile_click, args=(c,), use_container_width=True)
            st.markdown(f"<div class='char-btn-hint {'previewing' if is_preview else ''}'>{'Click again to drill down' if is_preview else 'Click once to preview'}</div>", unsafe_allow_html=True)
            st.markdown("<div class='pen-btn-wrap'>", unsafe_allow_html=True)
            def activate_stroke_view(char):
                st.session_state.stroke_view_char = char; st.session_state.stroke_view_active = True; st.session_state.show_inputs = False
                if not st.session_state.selected_comp: st.session_state.selected_comp = char; st.session_state.last_valid_selected_comp = char
            if st.button("🧠 link", key=f"stroke_btn_{c}_{ord(c)}_{uid}", help="Write AI prompt", use_container_width=True, on_click=activate_stroke_view, args=(c,)): pass
            st.markdown("</div></div>", unsafe_allow_html=True)
        
    with col_details:
        st.markdown(generate_clean_card_html(c, usage_count=component_usage_count(c), is_static=is_static), unsafe_allow_html=True)
        if not is_static and is_active_focus and st.session_state.display_mode != "Single Character":
            if html := _render_phrase_html(c):
                st.markdown(html, unsafe_allow_html=True)
    st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

def main():
    if not component_map: st.error("Component dataset not loaded."); st.stop()
    apply_dynamic_css()
    if st.session_state.get("_post_apply_rerun"): st.session_state["_post_apply_rerun"] = False

    if not st.session_state.get("startup_file_choice_made", False): render_startup_file_choice(); st.stop()
    if not st.session_state.get("onboarding_done", False): render_splash(); st.stop()

    with st.sidebar:
        current_main_char = st.session_state.stroke_view_char if st.session_state.stroke_view_active else st.session_state.selected_comp
        if current_main_char:
            path_items = ["🏠 Root"] + st.session_state.history + ([f"<i>{current_main_char}</i> (🧠)"] if st.session_state.stroke_view_active else [f"<b>{current_main_char}</b>"])
            st.markdown(f"<div style='font-size:0.85em; margin:0 0 12px 0; padding:10px; color:#fff; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius:8px; text-align:center; font-weight:600; box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);'>{' → '.join(path_items)}</div>", unsafe_allow_html=True)
        
        if not st.session_state.show_inputs:
            nav_col1, nav_col2 = st.columns(2)
            with nav_col1:
                if st.session_state.stroke_view_active: st.button("← Back", on_click=end_stroke_view, use_container_width=True, type="primary")
                else: st.button("← Back", on_click=go_back, use_container_width=True, type="primary")
            with nav_col2: st.button("🏠 Root", on_click=go_to_root, use_container_width=True)
            st.markdown("---")

        current_char_for_sidebar = st.session_state.stroke_view_char if st.session_state.stroke_view_active else (st.session_state.preview_comp or st.session_state.selected_comp)
        if current_char_for_sidebar:
            sidebar_html, sidebar_height = get_stroke_order_sidebar_html(current_char_for_sidebar, size=140)
            if sidebar_html: st_html(sidebar_html, height=sidebar_height)
            
            related = component_map.get(current_char_for_sidebar, {}).get("related_characters", [])
            chars_filtered = apply_script_filter([c for c in related if c in component_map], st.session_state.script_filter)
            if len(chars_filtered) > 0: st.markdown(f"<div style='font-size:0.75em; line-height:1.1; margin:0.15rem 0 0.35rem 0; opacity:0.8;'>{len(chars_filtered)} characters contain <span class='char'>{current_char_for_sidebar}</span></div>", unsafe_allow_html=True)
            
            st.checkbox("Show in Favourites", value=(current_char_for_sidebar in st.session_state.favourites_list), key=f"fav_chk_{current_char_for_sidebar}", on_change=toggle_favourite, args=(current_char_for_sidebar,))
            if st.button("Show Favourites", use_container_width=True): go_to_root(); st.session_state.onboarding_done = False; st.rerun()

            if st.session_state.stroke_view_active:
                st.markdown("### Character Info")
                # Updated: Use 'char-card' div wrapper + generate_clean_card_html with is_static=True 
                # This ensures the card looks exactly like the "wide card" screenshot (Screenshot 2)
                # with usage count, definition/etymology separation, and tip box.
                st.markdown(f"<div class='char-card'>{generate_clean_card_html(current_char_for_sidebar, usage_count=component_usage_count(current_char_for_sidebar), is_static=True)}</div>", unsafe_allow_html=True)

        if not st.session_state.show_inputs:
            with st.expander("Display Phrases", expanded=False):
                modes = ["Single Character", "2-Characters", "3-Characters", "4-Characters"]
                idx = modes.index(st.session_state.display_mode) if st.session_state.display_mode in modes else 1
                if (nm := st.radio("Select mode", options=modes, index=idx, key="sidebar_display_mode", label_visibility="collapsed")) != st.session_state.display_mode:
                    st.session_state.display_mode = nm; st.rerun()

        with st.expander("🔍 Search", expanded=False):
            st.markdown("**Character Search**")
            st.text_input("Paste or type a character", key="sb_search", on_change=sync_sidebar_text, placeholder="e.g., 水", label_visibility="collapsed")
            st.markdown("---")
            render_definition_search_ui("sb")

        if not st.session_state.stroke_view_active:
            with st.expander("🔎 Filters", expanded=False):
                if not st.session_state.show_inputs:
                    st.radio("Filter Results", options=SCRIPT_FILTERS, index=SCRIPT_FILTERS.index(st.session_state.get("script_filter", "Any")), key="w_script_filter", on_change=sync_script_filter)
                if st.session_state.show_inputs:
                    st.slider("Stroke count", 1, 30, value=st.session_state.stroke_range, key="w_stroke_range", on_change=sync_stroke_range)
                    rads = sorted(list(set(i.get("meta", {}).get("radical") for i in component_map.values() if i.get("meta", {}).get("radical"))))
                    st.selectbox("Radical", options=["none"] + rads, index=(["none"] + rads).index(st.session_state.radical) if st.session_state.radical in rads else 0, key="w_radical", on_change=sync_radical)
                    idcs = sorted(stats_cache.get("idc_counts", {}).keys())
                    st.selectbox("Structure (IDC)", options=["none"] + idcs, index=(["none"] + idcs).index(st.session_state.component_idc) if st.session_state.component_idc in idcs else 0, key="w_idc", on_change=sync_idc)
                    
                    st.markdown("### Sort Grid By")
                    def update_grid_sort_mode():
                        st.session_state.grid_sort_mode = "usage" if st.session_state.grid_sort_mode_radio == "Component frequency" else "frequency"
                        st.session_state.page = 1
                    st.radio("Sort key", options=["Component frequency", "Character frequency"], index=0 if st.session_state.get("grid_sort_mode", "usage") == "usage" else 1, key="grid_sort_mode_radio", on_change=update_grid_sort_mode, help="Component frequency: how often this component appears inside other characters.\nCharacter frequency: how often this character appears in common use.")
                    
                    if st.session_state.grid_sort_mode == "frequency":
                        st.markdown("#### Script Preference")
                        st.radio("Show characters in:", options=["Simplified", "Traditional", "Any"], index=["Simplified", "Traditional", "Any"].index(st.session_state.grid_script_filter), key="grid_script_radio", on_change=lambda: st.session_state.update({"grid_script_filter": st.session_state.grid_script_radio, "page": 1}), horizontal=True)
    
    if st.session_state.stroke_view_active:
        st.markdown("### Stroke Order Animation")
        main_html, _ = get_stroke_order_view_html(st.session_state.stroke_view_char, st.session_state.display_mode)
        st_html(main_html, height=450)
        
        # Explicitly render the phrase table using our reliable helper
        if st.session_state.display_mode != "Single Character":
            if phrase_html := _render_phrase_html(st.session_state.stroke_view_char):
                st.markdown(phrase_html, unsafe_allow_html=True)

        char = (st.session_state.stroke_view_char or "").strip()
        if not char: st.info("Select a character to generate the ChatGPT prompt."); st.stop()

        st.markdown("### ChatGPT Prompt")
        normalize_prompt_state()
        cfg = st.session_state.prompt_config
        tasks = cfg.get("tasks", []) or []
        all_task_ids = [t.get("id") for t in tasks if t.get("id")]
        cur_sel = [tid for tid in (st.session_state.prompt_selected_task_ids or []) if tid in all_task_ids]
        if not cur_sel: cur_sel = list(st.session_state.prompt_ui.get("default_selected_task_ids", all_task_ids)) or list(all_task_ids)
        st.session_state.prompt_selected_task_ids = cur_sel

        with st.expander("Prompt tasks (choose what to include)", expanded=True):
            if st.button("Select all tasks", key="select_all_prompt_tasks"):
                st.session_state.prompt_selected_task_ids = list(all_task_ids)
                for tid in all_task_ids: st.session_state[f"prompt_task_cb_{tid}"] = True
                st.rerun()
            sel = []
            for t in tasks:
                tid = t.get("id", "")
                if tid and st.checkbox(t.get("title", tid), key=f"prompt_task_cb_{tid}"): sel.append(tid)
            st.session_state.prompt_selected_task_ids = sel

        prompt_text = render_combined_prompt(char=char, prompt_config=st.session_state.prompt_config, selected_task_ids=st.session_state.prompt_selected_task_ids, definition_en=get_char_definition_en(char))
        st.text_area("Copy this prompt into ChatGPT", value=prompt_text, height=320)
        render_copy_to_clipboard(prompt_text, str(hash(st.session_state.stroke_view_char)))
        st.stop()

    if st.session_state.show_inputs:
        cur_min, cur_max = st.session_state.stroke_range
        filter_parts = [f"<span class='status-tag'>Sort: {'Component' if st.session_state.grid_sort_mode == 'usage' else 'Character'} frequency</span>"]
        max_s_val = max((get_stroke_count(c) for c in component_map if get_stroke_count(c) is not None), default=30)
        if not (cur_min == 1 and cur_max == max_s_val):
            if cur_min == cur_max: filter_parts.append(f"<span class='status-tag'>{cur_min} strokes</span>")
            elif cur_min == 1: filter_parts.append(f"<span class='status-tag'>≤ {cur_max} strokes</span>")
            elif cur_max == max_s_val: filter_parts.append(f"<span class='status-tag'>≥ {cur_min} strokes</span>")
            else: filter_parts.append(f"<span class='status-tag'>{cur_min}–{cur_max} strokes</span>")
        if st.session_state.radical != "none": filter_parts.append(f"<span class='status-tag'>Rad. {st.session_state.radical}</span>")
        if st.session_state.component_idc != "none": filter_parts.append(f"<span class='status-tag'>{st.session_state.component_idc}</span>")
        if st.session_state.grid_sort_mode == "usage": filter_parts.append("<span class='status-tag'>View: Components only</span>")
        if st.session_state.grid_sort_mode == "frequency": filter_parts.append(f"<span class='status-tag'>Script: {st.session_state.grid_script_filter}</span>")
        
        st.markdown(f"<div class='status-line' style='display: flex; flex-direction: column; gap: 8px;'><div style='display: flex; justify-content: space-between; align-items: center;'><div style='display: flex; flex-wrap: wrap; gap: 8px;'><span style='font-weight: 800; margin-right: 5px;'>🔍 Filters:</span> {''.join(filter_parts)}</div><div style='font-size: 0.8em; color: rgba(15, 81, 50, 0.7); font-weight: 700;'>Click once to preview in the sidebar; click the same button again to drill down. </div></div></div>", unsafe_allow_html=True)

        filtered = [c for c in component_map if (s := get_stroke_count(c)) is not None and cur_min <= s <= cur_max and (st.session_state.radical == "none" or component_map[c]["meta"].get("radical") == st.session_state.radical) and (st.session_state.component_idc == "none" or component_map[c]["meta"].get("decomposition", "").startswith(st.session_state.component_idc)) and (st.session_state.grid_sort_mode != "usage" or c in stats_cache["used_components"])]
        if st.session_state.grid_sort_mode == "frequency": filtered = apply_script_filter(filtered, st.session_state.grid_script_filter)
        
        sorted_comps = sorted(filtered, key=sort_key_frequency_primary if st.session_state.grid_sort_mode == "frequency" else sort_key_usage_primary)

        if not sorted_comps: st.info("No components match current filters.")
        else:
            PAGE_SIZE = 120
            total = len(sorted_comps)
            max_page = max(1, math.ceil(total / PAGE_SIZE))
            st.session_state.page = max(1, min(st.session_state.page, max_page))
            p1, p2, p3 = st.columns([1, 3, 1])
            with p1:
                if st.button("◀ Prev", disabled=st.session_state.page <= 1, use_container_width=True): st.session_state.page -= 1; st.rerun()
            with p2: st.markdown(f"<div style='text-align:center; padding:10px 0; color:#555;'><div style='font-size:1.1em; font-weight:bold;'>{(st.session_state.page - 1) * PAGE_SIZE + 1}–{min(st.session_state.page * PAGE_SIZE, total)} of {total}</div></div>", unsafe_allow_html=True)
            with p3:
                if st.button("Next ▶", disabled=st.session_state.page >= max_page, use_container_width=True): st.session_state.page += 1; st.rerun()

            st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
            cols = st.columns(10)
            for i, ch in enumerate(sorted_comps[(st.session_state.page - 1) * PAGE_SIZE : st.session_state.page * PAGE_SIZE]):
                with cols[i % 10]:
                    st.button(ch, key=f"b_{ch}_{st.session_state.page}", type="primary" if st.session_state.preview_comp == ch else "secondary", on_click=tile_click, args=(ch,), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("🔍 Search", expanded=False):
                st.markdown("**Character Search**")
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.session_state.text_input_warning: st.warning(st.session_state.text_input_warning)
                    st.text_input("Go to component/character", value=st.session_state.text_input_comp, key="w_text", on_change=sync_text, placeholder="Type one Hanzi, e.g. 水", label_visibility="collapsed")
                    st.caption("Enter one Chinese character to jump directly to its details")
                st.markdown("---")
                col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
                with col_s2: render_definition_search_ui("w")

    else:
        if st.session_state.definition_search_mode and st.session_state.definition_search_results:
            results = st.session_state.definition_search_results
            st.markdown(f"<div class='status-line'><div style='font-size:1.2em; font-weight:700;'>Search Results for \"{pyhtml.escape(st.session_state.definition_search_query)}\"</div><div class='status-text' style='font-size:0.85em; color:#666; margin-top:8px;'>Found {len(results['characters'])} characters and {len(results['phrases'])} phrases</div></div>", unsafe_allow_html=True)
            if results['characters']:
                st.markdown("<div class='lineage-header'>📖 Characters</div>", unsafe_allow_html=True)
                for char in results['characters'][:30]: render_radix_row(char)
            if results['phrases']:
                st.markdown("<div class='lineage-header'>💬 Phrases</div>", unsafe_allow_html=True)
                st.markdown("<div style='max-width:900px; margin:0 auto;'>", unsafe_allow_html=True)
                for phrase_data in results['phrases']:
                    st.markdown(f"<div class='compound-item' style='margin-bottom:15px;'><span class='cp-word' style='font-size:1.4em;'>{phrase_data['word']}</span><span class='cp-pinyin'>{phrase_data['pinyin']}</span><span class='cp-mean'>{pyhtml.escape(phrase_data['meanings'][:200] + ('...' if len(phrase_data['meanings']) > 200 else ''))}</span></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            if not results['characters'] and not results['phrases']: st.info(f"No results found for '{st.session_state.definition_search_query}'. Try different search terms.")
        else:
            sel = st.session_state.selected_comp
            info = component_map.get(sel, {})
            decomp = info.get("meta", {}).get("decomposition", "")
            parents = [p for p in decomp if p in component_map and p not in IDC_CHARS and p not in ["?", "—"] and p != sel]
            parents = apply_script_filter(parents, st.session_state.script_filter)
            p_html = "".join([f"<span class='status-tag' style='margin-right:5px; padding: 2px 8px;'>{p}</span>" for p in parents])
            
            rel = info.get("related_characters", [])
            children = [c for c in rel if isinstance(c, str) and len(c) == 1 and c in component_map and c != sel]
            children_preview = apply_script_filter(children, st.session_state.script_filter)[:50]
            c_html = "".join([f"<span class='status-tag' style='margin-right:5px; padding: 2px 8px; opacity: 0.8;'>{c}</span>" for c in children_preview])

            st.markdown(f"<div class='status-line'><div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;'><div><div style='font-weight: 800; font-size: 1.2em;'> {sel}</div><div style='margin-top:4px; font-size:0.85em;'><b>Components</b> {p_html if parents else 'Basic Root'}</div></div><div style='text-align: left; font-size: 1.0em; opacity: 0.7;'><b>Derivatives</b><br/>{c_html}{'...' if len(children) > 50 else ''}</div></div></div>", unsafe_allow_html=True)

            if parents:
                st.markdown("<div class='lineage-header'>🧱 Components (How it's built)</div>", unsafe_allow_html=True)
                for p in parents: render_radix_row(p)

            st.markdown("<div class='lineage-header'>🎯 Current Selection</div>", unsafe_allow_html=True)
            focus_group = [sel]
            if cc_t2s and cc_s2t:
                s_cand = cc_t2s.convert(sel); t_cand = cc_s2t.convert(sel)
                variant = s_cand if s_cand != sel else t_cand
                if variant != sel and variant in component_map: focus_group.append(variant)
            
            for f in apply_script_filter(focus_group, st.session_state.script_filter): render_radix_row(f)

            if children:
                children_sorted = sorted(children, key=sort_key_usage_primary)
                visible_children = apply_script_filter(children_sorted, st.session_state.script_filter)    
                unique_visible = []
                seen = set()
                for child in visible_children:
                    if child not in seen: unique_visible.append(child); seen.add(child)
                
                st.markdown(f"<div class='lineage-header'>🌲 Derivatives (Used in {len(unique_visible)} characters)</div>", unsafe_allow_html=True)
                for child in unique_visible[:120]: render_radix_row(child)
                if len(unique_visible) > 120:
                    remaining = len(unique_visible) - 120
                    st.markdown("---\n" + f"<div style='text-align:center; color:#888; font-weight:bold; margin-bottom:20px;'>⬇️ {remaining} More Derivatives ⬇️</div>", unsafe_allow_html=True)
                    for c in unique_visible[120:]: render_radix_row(c, context="static_derivative", is_static=True)

if __name__ == "__main__":
    main()
