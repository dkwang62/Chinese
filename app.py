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
    component_map, stats_cache, cc_t2s, cc_s2t, get_db_connection,
    batch_get_phrase_details, search_phrases_by_definition, get_stroke_count,
    component_usage_count, apply_script_filter, normalize_single_hanzi,
    resolve_to_known_variant, get_default_prompt_config,
    normalize_prompt_config, render_combined_prompt, get_char_definition_en,
    generate_clean_card_html, render_ipad_safe_download_html,
    get_stroke_order_sidebar_html, get_stroke_order_view_html,
    SCRIPT_FILTERS, IDC_CHARS, sort_key_usage_primary,
    sort_key_frequency_primary,
)

# -----------------------------
# Configuration & Constants
# -----------------------------
PROFILE_SCHEMA_VERSION = 1
PROFILE_FILENAME = "radix_user_data.json"
st.set_page_config(layout="wide", page_title="Radix", page_icon="🈑")

# -----------------------------
# State Management Helpers
# -----------------------------
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
    if not isinstance(data, dict) or data.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise ValueError("Invalid schema or JSON object.")
    st.session_state.favourites_list = data.get("favourites_list", [])
    st.session_state.fav_cursor = 0
    st.session_state.prompt_config = data.get("prompt_config", {})
    st.session_state.prompt_ui = data.get("prompt_ui", {})

def normalize_prompt_state() -> None:
    """Ensure prompt_config/tasks and prompt selection UI state are internally consistent."""
    cfg = st.session_state.get("prompt_config", {})
    if not isinstance(cfg, dict): cfg = {}
    
    tasks = [t for t in cfg.get("tasks", []) if isinstance(t, dict) and t.get("id")]
    
    unique_tasks = []
    seen = set()
    for t in tasks:
        if t["id"] not in seen:
            unique_tasks.append(t)
            seen.add(t["id"])
    cfg["tasks"] = unique_tasks
    st.session_state.prompt_config = cfg

    all_ids = [t["id"] for t in unique_tasks]
    pui = st.session_state.get("prompt_ui", {})
    
    def_ids = [i for i in pui.get("default_selected_task_ids", []) if i in all_ids]
    pui["default_selected_task_ids"] = def_ids or list(all_ids)
    st.session_state.prompt_ui = pui

    cur_sel = [i for i in st.session_state.get("prompt_selected_task_ids", []) if i in all_ids]
    st.session_state.prompt_selected_task_ids = cur_sel or list(pui["default_selected_task_ids"])

    # Sync widgets
    for tid in all_ids:
        key = f"prompt_task_cb_{tid}"
        if key not in st.session_state:
            st.session_state[key] = (tid in st.session_state.prompt_selected_task_ids)

def _clear_derived_widget_state():
    """Nuclear clear of ALL derived keys to prevent zombie state from old configs."""
    for k in list(st.session_state.keys()):
        if (k.startswith(("pt_title_", "pt_tpl_", "prompt_task_cb_", "fav_chk_", "fav_bulk")) or 
            k in ["prompt_selected_task_ids", "prompt_default_sel_editor"]):
            st.session_state.pop(k, None)

def _apply_uploaded_profile_bytes(file_bytes: bytes) -> None:
    try:
        obj = json.loads(file_bytes.decode("utf-8"))
        _clear_derived_widget_state()
        import_profile_dict(obj)
        st.session_state.update({
            "_upload_applied": True,
            "_manual_config_active": True,
            "_post_apply_rerun": True
        })
        st.session_state.pop("_upload_error", None)
        normalize_prompt_state()
    except Exception as e:
        st.session_state["_upload_error"] = f"Error: {e}"
        st.session_state["_upload_applied"] = False

# -----------------------------
# Callbacks & Logic
# -----------------------------
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

def enter_component(comp: str):
    st.session_state.update({
        "script_filter": "Any",
        "history": [],
        "selected_comp": comp,
        "last_valid_selected_comp": comp,
        "text_input_comp": comp,
        "text_input_warning": None,
        "show_inputs": False,
        "preview_comp": None,
        "stroke_view_active": False,
        "display_mode": "2-Characters",
        "definition_search_mode": False,
        "definition_search_results": None
    })

def _validate_and_enter(raw_text: str, error_callback):
    v = normalize_single_hanzi(raw_text)
    if not v:
        error_callback("One character only")
        return
    resolved = resolve_to_known_variant(v)
    if not resolved:
        error_callback("Character not found")
        return
    enter_component(resolved)

def sync_text():
    def err(msg): st.session_state.text_input_warning = msg
    _validate_and_enter(st.session_state.get("w_text", ""), err)

def sync_sidebar_text():
    _validate_and_enter(st.session_state.get("sb_search", ""), lambda m: st.toast(m))

def sync_splash_text():
    st.session_state.sb_search = st.session_state.get("splash_search", "")
    st.session_state.onboarding_done = True
    sync_sidebar_text()

def tile_click(c):
    if st.session_state.show_inputs and st.session_state.preview_comp == c:
        enter_component(c)
    else:
        st.session_state.preview_comp = c

def list_tile_click(c):
    if st.session_state.preview_comp == c:
        if not st.session_state.get("has_drilled_down"):
            st.toast("Feature Discovered: Character Lineage view!", icon="🌳")
            st.session_state.has_drilled_down = True
        if st.session_state.selected_comp:
            st.session_state.history.append(st.session_state.selected_comp)
        st.session_state.selected_comp = c
        st.session_state.update({"show_inputs": False, "preview_comp": None})
    else:
        st.session_state.preview_comp = c

def search_by_definition():
    query = st.session_state.get("w_def_search", "").strip()
    if not query or len(query) < 2:
        st.toast("Please enter at least 2 characters.")
        return
    
    char_results = [c for c, i in component_map.items() 
                   if query.lower() in i.get("meta", {}).get("definition", "").lower()]
    
    db_conn = get_db_connection()
    phrase_results = search_phrases_by_definition(query, db_conn, limit=200) if db_conn else []
    
    st.session_state.update({
        "definition_search_mode": True,
        "definition_search_query": query,
        "definition_search_results": {"characters": char_results[:120], "phrases": phrase_results},
        "show_inputs": False,
        "selected_comp": "",
        "preview_comp": None
    })

def toggle_favourite(char):
    chk = st.session_state.get(f"fav_chk_{char}", False)
    lst = st.session_state.favourites_list
    if chk and char not in lst:
        if len(lst) < 20: lst.append(char)
        else:
            lst[st.session_state.fav_cursor] = char
            st.session_state.fav_cursor = (st.session_state.fav_cursor + 1) % 20
    elif not chk and char in lst:
        lst.remove(char)

# -----------------------------
# UI Component Helpers
# -----------------------------
def apply_dynamic_css():
    st.markdown("""
    <style>
    .main .block-container {padding-top: 2rem;}
    .char-card {background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%); padding: 24px; border-radius: 16px; border: 1px solid #e9ecef; box-shadow: 0 4px 12px rgba(0,0,0,0.06);}
    .char-card:hover {transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.1);}
    .meta-pinyin {font-weight: 700; font-size: 2.4em; color: #d35400;}
    .status-tag {background: #fff; padding: 6px 14px; border-radius: 8px; border: 2px solid #dee2e6; display: inline-flex; align-items: center; font-weight: 700; font-size: 0.9em; color: #2c3e50;}
    .lineage-header {font-size: 1.4em; font-weight: 800; margin: 30px 0 20px 0; padding: 12px 20px; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-left: 5px solid #1976d2; border-radius: 8px;}
    .char-btn-wrap .stButton > button {width: 100% !important; font-size: 3.8em !important; font-weight: 700 !important; min-height: 90px !important; border-radius: 16px !important;}
    .comp-grid .stButton > button {width: 100% !important; font-size: 2.2em !important; height: 85px !important;}
    .splash-card {background: #ffffff; border-radius: 40px; padding: 60px; box-shadow: 0 15px 50px rgba(0,0,0,0.05); text-align: center;}
    .grand-torii {font-size: 250px !important; line-height: 1; filter: drop-shadow(0 10px 20px rgba(0,0,0,0.1));}
    </style>
    """, unsafe_allow_html=True)

def render_definition_search_ui(key_prefix: str):
    st.markdown("**English Definition Search**")
    key = f"{key_prefix}_def_search"
    st.text_input("Search definitions", key=key, placeholder="e.g., water, fire", label_visibility="collapsed")
    if st.button("Search Definitions", use_container_width=True, type="primary", key=f"{key_prefix}_def_btn"):
        st.session_state.w_def_search = st.session_state.get(key, "")
        search_by_definition()
        if key_prefix == "splash": st.session_state.onboarding_done = True
        st.rerun()

def _render_phrase_html(c: str) -> str:
    """Consolidated logic to render the phrase table HTML for any character."""
    n_map = {"Single Character": 1, "2-Characters": 2, "3-Characters": 3, "4-Characters": 4}
    n = n_map.get(st.session_state.display_mode, 2)
    compounds = [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w) == n]
    
    if compounds and (db := get_db_connection()):
        phrases = batch_get_phrase_details(sorted(compounds), db)
        rows = []
        for w in sorted(compounds):
            if p := phrases.get(w):
                rows.append(f"<div style='display:flex; padding:5px; border-bottom:1px solid #eee;'>"
                            f"<span style='font-weight:700; min-width:65px;'>{w}</span>"
                            f"<span style='color:#d35400; font-family:monospace; margin-right:10px;'>{p.get('pinyin')}</span>"
                            f"<span style='color:#444;'>{pyhtml.escape(p.get('meanings','')[:100])}</span></div>")
        return f"""
        <div style='background:#f1f8e9; padding:10px; border-radius:8px; margin-top:10px; max-height:400px; overflow-y:auto; border:1px solid #dcedc8;'>
            <div style='font-weight:bold; font-size:0.8rem; margin-bottom:8px; color:#2e7d32; text-transform:uppercase;'>
                {st.session_state.display_mode} containing {c}
            </div>
            {''.join(rows)}
        </div>
        """
    return ""

def render_radix_row(c, is_static=False):
    col_char, col_details = st.columns([2, 10])
    is_preview = st.session_state.preview_comp == c
    is_selected = (not st.session_state.preview_comp and c == st.session_state.selected_comp)
    
    with col_char:
        if is_static:
            st.markdown(f"<div class='char-static-box'>{c}</div>", unsafe_allow_html=True)
        else:
            uid = str(uuid.uuid4())[:8]
            st.markdown("<div class='char-btn-wrap'>", unsafe_allow_html=True)
            st.button(c, key=f"btn_{c}_{uid}", type="primary" if is_preview else "secondary",
                      on_click=list_tile_click, args=(c,), use_container_width=True)
            
            hint = "Click again to drill down" if is_preview else "Click once to preview"
            st.markdown(f"<div class='char-btn-hint { 'previewing' if is_preview else ''}'>{hint}</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='pen-btn-wrap'>", unsafe_allow_html=True)
            if st.button("🧠 link", key=f"lk_{c}_{uid}", use_container_width=True):
                st.session_state.update({"stroke_view_char": c, "stroke_view_active": True, 
                                       "show_inputs": False, "selected_comp": c})
                st.rerun()
            st.markdown("</div></div>", unsafe_allow_html=True)

    with col_details:
        st.markdown(generate_clean_card_html(c, usage_count=component_usage_count(c), is_static=is_static), unsafe_allow_html=True)
        if not is_static and (is_preview or is_selected) and st.session_state.display_mode != "Single Character":
            if html := _render_phrase_html(c): st.markdown(html, unsafe_allow_html=True)
    st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

# -----------------------------
# Main Views
# -----------------------------
def render_search_results_view():
    res = st.session_state.definition_search_results
    q = st.session_state.definition_search_query
    st.markdown(f"""<div class='status-line'><div style='font-size:1.2em; font-weight:700;'>Results for "{pyhtml.escape(q)}"</div>
                    <div style='font-size:0.85em; color:#666;'>Found {len(res['characters'])} chars, {len(res['phrases'])} phrases</div></div>""", unsafe_allow_html=True)
    
    if res['characters']:
        st.markdown("<div class='lineage-header'>📖 Characters</div>", unsafe_allow_html=True)
        for c in res['characters'][:30]: render_radix_row(c)
    
    if res['phrases']:
        st.markdown("<div class='lineage-header'>💬 Phrases</div>", unsafe_allow_html=True)
        for p in res['phrases']:
            st.markdown(f"""<div class='compound-item'><span class='cp-word'>{p['word']}</span>
                        <span class='cp-pinyin'>{p['pinyin']}</span><span class='cp-mean'>{pyhtml.escape(p['meanings'][:200])}</span></div>""", unsafe_allow_html=True)
    
    if not res['characters'] and not res['phrases']:
        st.info("No results found.")

def render_lineage_view():
    sel = st.session_state.selected_comp
    info = component_map.get(sel, {})
    
    decomp = [p for p in info.get("meta", {}).get("decomposition", "") if p in component_map and p not in IDC_CHARS and p != sel]
    parents = apply_script_filter(decomp, st.session_state.script_filter)
    
    rel = [c for c in info.get("related_characters", []) if c in component_map and len(c)==1 and c != sel]
    children = apply_script_filter(rel, st.session_state.script_filter)
    
    p_tags = "".join([f"<span class='status-tag' style='margin-right:5px;'>{p}</span>" for p in parents])
    c_tags = "".join([f"<span class='status-tag' style='margin-right:5px; opacity:0.8;'>{c}</span>" for c in children[:50]])
    
    st.markdown(f"""
        <div class='status-line'><div style='display:flex; justify-content:space-between;'>
        <div><div style='font-weight:800; font-size:1.2em;'>{sel}</div><div style='margin-top:4px;'><b>Components</b> {p_tags or "Basic Root"}</div></div>
        <div style='text-align:left; opacity:0.7;'><b>Derivatives</b><br/>{c_tags}{"..." if len(children)>50 else ""}</div></div></div>
    """, unsafe_allow_html=True)

    if parents:
        st.markdown("<div class='lineage-header'>🧱 Components</div>", unsafe_allow_html=True)
        for p in parents: render_radix_row(p)

    st.markdown("<div class='lineage-header'>🎯 Current Selection</div>", unsafe_allow_html=True)
    variants = [sel]
    if cc_t2s and cc_s2t:
        v = cc_t2s.convert(sel) if cc_t2s.convert(sel) != sel else cc_s2t.convert(sel)
        if v != sel and v in component_map: variants.append(v)
    for v in apply_script_filter(variants, st.session_state.script_filter): render_radix_row(v)

    if children:
        unique_children = list(dict.fromkeys(sorted(children, key=sort_key_usage_primary)))
        st.markdown(f"<div class='lineage-header'>🌲 Derivatives ({len(unique_children)})</div>", unsafe_allow_html=True)
        for c in unique_children[:120]: render_radix_row(c)
        if len(unique_children) > 120:
            st.markdown(f"<div style='text-align:center; margin:20px;'>⬇️ {len(unique_children)-120} More ⬇️</div>", unsafe_allow_html=True)
            for c in unique_children[120:]: render_radix_row(c, is_static=True)

def render_startup_file_choice():
    st.markdown("""<div class="splash-wrap"><div class="splash-card"><div class="splash-title">Radix 🈑 - Data Setup</div>
                   <div class="splash-sub" style="margin-top: 20px;">Do you have a local Radix user data file you'd like to use?</div></div></div>""", unsafe_allow_html=True)
    
    st.markdown("<div style='max-width: 600px; margin: 40px auto;'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("📱 Yes, upload my local file", use_container_width=True, type="primary"):
        st.session_state.startup_choice = "upload"
        st.rerun()
    if c2.button("☁️ No, use server defaults", use_container_width=True):
        st.session_state.startup_choice = "server"
        if st.session_state.get("server_data_available"):
            obj = st.session_state.server_data
            st.session_state.favourites_list = obj["favourites_list"]
            st.session_state.prompt_config = obj["prompt_config"]
            st.session_state.prompt_ui = obj["prompt_ui"]
        st.session_state.startup_file_choice_made = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.session_state.get("startup_choice") == "upload":
        st.markdown("<div style='max-width: 600px; margin: 40px auto;'><h3>📤 Upload Your Local File</h3>", unsafe_allow_html=True)
        if f := st.file_uploader("Choose file", type=["json"], key="startup_uploader"):
            _apply_uploaded_profile_bytes(f.getvalue())
            if st.session_state.get("_upload_applied"):
                 st.success("✅ File loaded successfully!")
                 if st.button("Continue to Radix", type="primary", use_container_width=True):
                    st.session_state.startup_file_choice_made = True
                    st.rerun()
            elif st.session_state.get("_upload_error"): st.error(st.session_state["_upload_error"])
        st.markdown("</div>", unsafe_allow_html=True)

def render_splash():
    st.markdown("""<div class="palace-entrance-container"><div class="grand-torii">⛩️</div>
        <div class="entrance-text">Grand Hall of Radix 🈑 Components</div></div>""", unsafe_allow_html=True)
    
    _, c, _ = st.columns([1,1,1])
    if c.button("🚪 Enter", use_container_width=True, type="primary"):
        st.session_state.onboarding_done = True
        st.rerun()

    st.markdown("<div style='max-width: 600px; margin: 40px auto;'>", unsafe_allow_html=True)
    with st.expander("🔍 Search", expanded=False):
        st.text_input("Char Search", key="splash_search", on_change=sync_splash_text, placeholder="e.g. 水")
        st.markdown("---")
        render_definition_search_ui("splash")
    st.markdown("</div>", unsafe_allow_html=True)

    if demos := st.session_state.favourites_list:
        st.markdown("<h4 style='text-align:center; color:#666; margin-top:20px;'>Quick Access Favourites</h4>", unsafe_allow_html=True)
        
        # --- RESTORED: Full Data Management Suite ---
        lc1, lc2, lc3 = st.columns([1, 2, 1])
        with lc2:
            with st.expander("📂 User Data (Save/Load/Review & Edit)", expanded=False):
                st.caption("Single JSON file for Favourites + AI Prompt Tasks.")
                if st.session_state.get("_manual_config_active"): st.info("🔒 Using uploaded configuration")
                elif st.session_state.get("server_data_available"): st.info("☁️ Using server default configuration")
                else: st.info("🆕 Using app default configuration")

                c_dl, c_ul = st.columns(2)
                with c_dl:
                    st.markdown(render_ipad_safe_download_html(export_profile_str(), PROFILE_FILENAME, "💾 Download user data"), unsafe_allow_html=True)
                with c_ul:
                    if uf := st.file_uploader("Upload", type=["json"], key="profile_uploader_persistent", label_visibility="collapsed"):
                        hash_val = hashlib.sha256(uf.getvalue()).hexdigest()
                        if hash_val != st.session_state.get('_last_upload_hash', ''):
                            st.warning("⚠️ New file detected")
                            if st.button("✅ Apply now", use_container_width=True, type="primary"):
                                st.session_state["_last_upload_hash"] = hash_val
                                _apply_uploaded_profile_bytes(uf.getvalue())
                                st.rerun()
                        else: st.success("✓ Active")
                        if st.button("♻️ Reset", use_container_width=True):
                            st.session_state.pop("_last_upload_hash", None)
                            st.session_state.pop("profile_uploader_persistent", None)
                            st.rerun()
                
                if st.session_state.get("_upload_error"): st.error(st.session_state["_upload_error"])
                elif st.session_state.get("_upload_applied") and st.button("Dismiss success msg"):
                    st.session_state["_upload_applied"] = False; st.rerun()

                st.markdown("---")
                st.subheader("Favourites")
                fav_txt = st.text_area("Favourites (space separated)", value=" ".join(st.session_state.favourites_list), height=90, key="fav_bulk_editor")
                c1, c2, c3 = st.columns([1, 1, 2])
                if c1.button("Apply"):
                    cleaned = list(dict.fromkeys([t for t in re.split(r"\s+", fav_txt.strip()) if len(t)==1]))
                    st.session_state.favourites_list = cleaned
                    st.toast("Updated"); st.rerun()
                if c2.button("Clear"): st.session_state.favourites_list = []; st.rerun()
                add_c = c3.text_input("Add", key="fav_add_one", placeholder="e.g. 我", label_visibility="collapsed")
                if c3.button("Add"):
                    if len(add_c.strip())==1 and add_c not in st.session_state.favourites_list:
                        st.session_state.favourites_list.append(add_c.strip()); st.rerun()

                st.markdown("---")
                st.subheader("AI Prompt Tasks")
                normalize_prompt_state()
                cfg = st.session_state.prompt_config
                tasks = cfg.get("tasks", [])
                
                # Default selection
                all_ids = [t["id"] for t in tasks]
                def_sel = st.multiselect("Defaults", options=all_ids, default=st.session_state.prompt_ui["default_selected_task_ids"], key="prompt_default_sel_editor")
                if st.button("Save Defaults"):
                    st.session_state.prompt_ui["default_selected_task_ids"] = def_sel
                    normalize_prompt_state(); st.toast("Saved"); st.rerun()

                # Task Editor
                edited_tasks = []
                for t in tasks:
                    tid = t["id"]
                    with st.expander(f"✏️ {t.get('title','?')}", expanded=False):
                        tit = st.text_input("Title", value=t.get("title",""), key=f"pt_title_{tid}")
                        tpl = st.text_area("Template", value=t.get("template",""), height=100, key=f"pt_tpl_{tid}")
                        if st.button("Delete", key=f"pt_del_{tid}"):
                            st.session_state.prompt_config["tasks"] = [x for x in tasks if x["id"]!=tid]
                            _clear_derived_widget_state(); st.rerun()
                    edited_tasks.append({"id": tid, "title": tit, "template": tpl})
                
                ca, cb = st.columns(2)
                if ca.button("Add Task"):
                    tasks.append({"id": f"task_{uuid.uuid4().hex[:8]}", "title": "New", "template": ""})
                    st.session_state.prompt_config["tasks"] = tasks
                    normalize_prompt_state(); st.rerun()
                if cb.button("Apply Edits"):
                    st.session_state.prompt_config["tasks"] = edited_tasks
                    normalize_prompt_state(); st.toast("Saved"); st.rerun()

        # Render Favourites Grid
        st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
        cols = st.columns(5)
        for i, ch in enumerate(list(dict.fromkeys(demos))):
             with cols[i % 5]:
                if st.button(f"Explore {ch}", key=f"sp_{i}", use_container_width=True, type="primary"):
                    st.session_state.onboarding_done = True
                    enter_component(ch)
                    st.rerun()
                st.caption(f"used in {component_usage_count(ch)} chars")
        st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Main Application Loop
# -----------------------------
def main():
    if not component_map: st.error("Dataset missing."); st.stop()
    apply_dynamic_css()
    
    defaults = {
        "startup_file_choice_made": False, "onboarding_done": False, "selected_comp": "", 
        "stroke_range": (3, 8), "radical": "none", "component_idc": "none", 
        "display_mode": "2-Characters", "page": 1, "show_inputs": True, "script_filter": "Any", 
        "favourites_list": [], "grid_sort_mode": "usage", "grid_script_filter": "Any"
    }
    for k,v in defaults.items(): 
        if k not in st.session_state: st.session_state[k] = v

    if st.session_state.get("_post_apply_rerun"): st.session_state["_post_apply_rerun"] = False

    if not st.session_state.startup_file_choice_made:
        render_startup_file_choice(); st.stop()
    if not st.session_state.onboarding_done:
        render_splash(); st.stop()

    with st.sidebar:
        curr = st.session_state.stroke_view_char if st.session_state.stroke_view_active else st.session_state.selected_comp
        if curr:
            hist = " → ".join(["🏠 Root"] + st.session_state.get("history", []) + [f"<b>{curr}</b>"])
            st.markdown(f"<div style='padding:10px; background:#667eea; color:white; border-radius:8px; text-align:center;'>{hist}</div>", unsafe_allow_html=True)
        
        if not st.session_state.show_inputs:
            c1, c2 = st.columns(2)
            if c1.button("← Back", use_container_width=True):
                st.session_state.stroke_view_active = False
                st.session_state.definition_search_mode = False
                if st.session_state.history: enter_component(st.session_state.history.pop())
                else: st.session_state.update({"show_inputs": True, "selected_comp": ""})
                st.rerun()
            if c2.button("🏠 Root", use_container_width=True):
                st.session_state.update({"history": [], "show_inputs": True, "selected_comp": "", "stroke_view_active": False, "definition_search_mode": False})
                st.rerun()
        
        target = st.session_state.stroke_view_char if st.session_state.stroke_view_active else (st.session_state.preview_comp or st.session_state.selected_comp)
        if target:
            h, ht = get_stroke_order_sidebar_html(target, size=140)
            if h: st_html(h, height=ht)
            # Count Logic
            rel = component_map.get(target, {}).get("related_characters", [])
            count = len(apply_script_filter([c for c in rel if c in component_map], st.session_state.script_filter))
            if count: st.markdown(f"<div style='font-size:0.8em; text-align:center; opacity:0.8'>{count} chars contain {target}</div>", unsafe_allow_html=True)
            st.checkbox("Favourite", key=f"fav_chk_{target}", value=target in st.session_state.favourites_list, on_change=toggle_favourite, args=(target,))
            if st.button("Show Favourites"): st.session_state.onboarding_done = False; st.rerun()
            
            if st.session_state.stroke_view_active:
                st.markdown("### Character Info")
                st.markdown(generate_clean_card_html(target), unsafe_allow_html=True)

        with st.expander("🔍 Search", expanded=False):
            st.text_input("Char Search", key="sb_search", on_change=sync_sidebar_text)
            st.markdown("---")
            render_definition_search_ui("sb")
        
        if not st.session_state.show_inputs:
             with st.expander("Display Phrases", expanded=False):
                modes = ["Single Character", "2-Characters", "3-Characters", "4-Characters"]
                idx = modes.index(st.session_state.display_mode) if st.session_state.display_mode in modes else 1
                if (nm := st.radio("Select mode", options=modes, index=idx, key="sidebar_display_mode")) != st.session_state.display_mode:
                    st.session_state.display_mode = nm; st.rerun()
            
        if not st.session_state.stroke_view_active:
             with st.expander("🔎 Filters", expanded=False):
                if not st.session_state.show_inputs:
                    st.radio("Script", options=SCRIPT_FILTERS, key="w_script_filter", 
                             index=SCRIPT_FILTERS.index(st.session_state.get("script_filter", "Any")), on_change=sync_script_filter)
                else:
                    st.slider("Strokes", 1, 30, key="w_stroke_range", value=st.session_state.stroke_range, on_change=sync_stroke_range)
                    
                    rads = ["none"] + sorted(list(set(i.get("meta",{}).get("radical") for i in component_map.values() if i.get("meta",{}).get("radical"))))
                    st.selectbox("Radical", options=rads, index=rads.index(st.session_state.radical) if st.session_state.radical in rads else 0, key="w_radical", on_change=sync_radical)
                    
                    idcs = ["none"] + sorted(stats_cache.get("idc_counts", {}).keys())
                    st.selectbox("Structure", options=idcs, index=idcs.index(st.session_state.component_idc) if st.session_state.component_idc in idcs else 0, key="w_idc", on_change=sync_idc)
                    
                    st.markdown("### Sort")
                    if st.radio("Key", ["Component frequency", "Character frequency"], index=0 if st.session_state.grid_sort_mode=="usage" else 1, key="g_sort") == "Component frequency":
                        st.session_state.grid_sort_mode = "usage"
                    else:
                        st.session_state.grid_sort_mode = "frequency"
                    
                    if st.session_state.grid_sort_mode == "frequency":
                        st.radio("Script", ["Simplified", "Traditional", "Any"], index=["Simplified", "Traditional", "Any"].index(st.session_state.grid_script_filter), key="g_script_f", on_change=lambda: st.session_state.update({"grid_script_filter": st.session_state.g_script_f}))

    if st.session_state.stroke_view_active:
        char = st.session_state.stroke_view_char
        main_html, _ = get_stroke_order_view_html(char, st.session_state.display_mode)
        st_html(main_html, height=450)
        st.markdown("### Common Phrases")
        st.markdown(_render_phrase_html(char), unsafe_allow_html=True)
        st.markdown("### ChatGPT Prompt")
        
        # Task Selection
        normalize_prompt_state()
        tasks = st.session_state.prompt_config.get("tasks", [])
        all_ids = [t["id"] for t in tasks]
        if st.button("Select All Tasks"):
            st.session_state.prompt_selected_task_ids = list(all_ids)
            for tid in all_ids: st.session_state[f"prompt_task_cb_{tid}"] = True
            st.rerun()
        
        sel = []
        for t in tasks:
            if st.checkbox(t.get("title", t["id"]), key=f"prompt_task_cb_{t['id']}"):
                sel.append(t["id"])
        st.session_state.prompt_selected_task_ids = sel

        prompt = render_combined_prompt(char, st.session_state.prompt_config, st.session_state.prompt_selected_task_ids, get_char_definition_en(char))
        st.text_area("Copy this", value=prompt, height=300)
        render_copy_to_clipboard(prompt, str(hash(char)))

    elif st.session_state.show_inputs:
        min_s, max_s = st.session_state.get("w_stroke_range", (3, 8))
        
        # Grid Status Summary
        parts = [f"Sort: {'Component' if st.session_state.grid_sort_mode=='usage' else 'Char'} Freq"]
        if min_s!=1 or max_s!=30: parts.append(f"{min_s}-{max_s} strokes")
        if st.session_state.radical != "none": parts.append(f"Rad: {st.session_state.radical}")
        if st.session_state.component_idc != "none": parts.append(f"IDC: {st.session_state.component_idc}")
        st.markdown(f"""<div class='status-line'><div style='display:flex; justify-content:space-between'>
            <div><b>Filters:</b> {" ".join([f"<span class='status-tag'>{p}</span>" for p in parts])}</div></div></div>""", unsafe_allow_html=True)
        
        filtered = [
            c for c in component_map
            if (s := get_stroke_count(c)) is not None and min_s <= s <= max_s
            and (st.session_state.radical == "none" or component_map[c]["meta"].get("radical") == st.session_state.radical)
            and (st.session_state.component_idc == "none" or component_map[c]["meta"].get("decomposition", "").startswith(st.session_state.component_idc))
            and (st.session_state.grid_sort_mode != "usage" or c in stats_cache["used_components"])
        ]
        
        if st.session_state.grid_sort_mode == "frequency":
            filtered = apply_script_filter(filtered, st.session_state.grid_script_filter)
            filtered.sort(key=sort_key_frequency_primary)
        else:
            filtered.sort(key=sort_key_usage_primary)

        page_size = 120
        total_pages = max(1, math.ceil(len(filtered) / page_size))
        curr_page = st.session_state.page = max(1, min(st.session_state.page, total_pages))
        
        c1, c2, c3 = st.columns([1,3,1])
        if c1.button("◀ Prev") and curr_page > 1: st.session_state.page -= 1; st.rerun()
        c2.markdown(f"<div style='text-align:center; padding:10px'>{curr_page} / {total_pages} ({len(filtered)} items)</div>", unsafe_allow_html=True)
        if c3.button("Next ▶") and curr_page < total_pages: st.session_state.page += 1; st.rerun()

        st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
        batch = filtered[(curr_page-1)*page_size : curr_page*page_size]
        cols = st.columns(10)
        for i, ch in enumerate(batch):
            with cols[i%10]:
                is_prev = st.session_state.preview_comp == ch
                st.button(ch, key=f"g_{ch}_{curr_page}", type="primary" if is_prev else "secondary", on_click=tile_click, args=(ch,), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        with st.expander("Search", expanded=False):
            st.text_input("Char Search", key="w_text", on_change=sync_text)
            render_definition_search_ui("w")

    elif st.session_state.definition_search_mode:
        render_search_results_view()
    else:
        render_lineage_view()

if __name__ == "__main__":
    main()
