# app.py
# Main Streamlit app for Radix - consolidated 4-file structure

import streamlit as st
from streamlit.components.v1 import html as st_html
import math
import html as pyhtml
import uuid
import re
from radix_core import (
    component_map, get_db_connection, batch_get_phrase_details,
    search_phrases_by_definition, get_stroke_count, component_usage_count,
    apply_script_filter, get_char_definition_en, render_combined_prompt,
    get_stroke_order_view_html, SCRIPT_FILTERS, IDC_CHARS,
    sort_key_usage_primary, sort_key_frequency_primary, stats_cache,
    cc_t2s, cc_s2t
)
from radix_state import (
    StateManager, ConfigManager, InputValidator,
    PAGE_CONFIG, PAGE_SIZE, GRID_COLUMNS
)
from radix_ui import (
    apply_styles, generate_clean_card_html, render_ipad_safe_download_html,
    render_copy_to_clipboard, get_stroke_order_sidebar_html,
    render_definition_search_ui
)

# Configure Streamlit
st.set_page_config(**PAGE_CONFIG)
apply_styles()

# Initialize managers
state = StateManager()
config = ConfigManager(state)

state.initialize()
config.load_server_data()
config.initialize_prompt_config()

# ==================== CALLBACKS ====================

def _validate_and_search(raw: str, error_callback=None):
    """Shared search validation logic."""
    validated = InputValidator.validate_character_input(raw, error_callback)
    if validated:
        state.enter_character_view(validated)

def sync_text():
    _validate_and_search(state.get("w_text", ""), lambda msg: state.set("text_input_warning", msg))

def sync_sidebar_text():
    _validate_and_search(state.get("sb_search", ""), st.toast)

def sync_splash_text():
    raw = state.get("splash_search", "")
    if InputValidator.validate_character_input(raw):
        state.complete_onboarding()
    state.set("sb_search", raw)
    sync_sidebar_text()

def sync_stroke_range():
    state.set("stroke_range", state.get("w_stroke_range"))
    state.set("page", 1)

def sync_radical():
    state.set("radical", state.get("w_radical"))
    state.set("page", 1)

def sync_idc():
    state.set("component_idc", state.get("w_idc"))
    state.set("page", 1)

def sync_script_filter():
    state.set("script_filter", state.get("w_script_filter"))

def tile_click(c):
    if state.is_showing_inputs() and state.get_preview_component() == c:
        state.enter_character_view(c)
    else:
        state.set("preview_comp", c)

def list_tile_click(c):
    if state.get_preview_component() == c:
        if not state.get("has_drilled_down", False):
            st.toast("Feature Discovered: You have entered the Character Lineage view!", icon="🌳")
            state.set("has_drilled_down", True)
        if state.get_selected_component():
            history = state.get_history()
            history.append(state.get_selected_component())
            state.set("history", history)
        state.update(
            selected_comp=c,
            show_inputs=False,
            preview_comp=None,
            derivative_page=0 # Reset pagination on drill down
        )
    else:
        state.set("preview_comp", c)

def toggle_favourite(char):
    if state.get(f"fav_chk_{char}", False):
        state.add_to_favourites(char)
    else:
        state.remove_from_favourites(char)

def search_by_definition():
    query = state.get("w_def_search", "").strip()
    is_valid, error_msg = InputValidator.validate_definition_search(query)
    
    if not is_valid:
        st.toast(error_msg)
        return
    
    # Search characters
    char_results = []
    query_lower = query.lower()
    for char, info in component_map.items():
        definition = info.get("meta", {}).get("definition", "")
        if isinstance(definition, str) and query_lower in definition.lower():
            char_results.append(char)
    
    # Search phrases
    db_conn = get_db_connection()
    phrase_results = search_phrases_by_definition(query, db_conn, limit=200) if db_conn else []
    
    state.update(
        definition_search_mode=True,
        definition_search_query=query,
        definition_search_results={"characters": char_results[:120], "phrases": phrase_results[:200]},
        show_inputs=False,
        selected_comp="",
        preview_comp=None
    )

# ==================== UI RENDERING HELPERS ====================

def _render_phrase_html(c: str) -> str:
    """Render phrase table HTML for character."""
    n_map = {"Single Character": 1, "2-Characters": 2, "3-Characters": 3, "4-Characters": 4}
    n = n_map.get(state.get_display_mode(), 2)
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
            return f"<div style='padding:12px; background:#f1f8e9; border-radius:8px; margin-top:10px; border:1px solid #dcedc8; max-height:400px; overflow-y:auto;'><div style='font-weight:bold; font-size:0.8rem; margin-bottom:8px; color:#2e7d32; text-transform:uppercase;'>{state.get_display_mode()} containing {c}</div>{''.join(items_html_list)}</div>"
    return ""

def render_radix_row(c, context="detail", is_static=False, minimal=False):
    """Render a character row with button and card."""
    col_char, col_details = st.columns([2, 10])
    is_preview = state.get_preview_component() == c
    is_active_focus = is_preview or (state.get_preview_component() is None and c == state.get_selected_component())

    with col_char:
        if is_static:
            st.markdown(f"<div class='char-static-box'>{c}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='char-btn-wrap'>", unsafe_allow_html=True)
            uid = str(uuid.uuid4())[:8]
            st.button(
                c,
                key=f"explore_char_{context}_{c}_{ord(c)}_{uid}",
                type="primary" if is_preview else "secondary",
                help="Previewing..." if is_preview else "Click to preview",
                on_click=list_tile_click,
                args=(c,),
                use_container_width=True
            )
            st.markdown(f"<div class='char-btn-hint {'previewing' if is_preview else ''}'>{'Click again to drill down' if is_preview else 'Click once to preview'}</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='pen-btn-wrap'>", unsafe_allow_html=True)
            if st.button("🧠 link", key=f"stroke_btn_{c}_{ord(c)}_{uid}", help="Write AI prompt", use_container_width=True, on_click=lambda: state.enter_stroke_view(c)):
                pass
            st.markdown("</div></div>", unsafe_allow_html=True)
        
    with col_details:
        st.markdown(generate_clean_card_html(c, usage_count=component_usage_count(c), is_static=is_static, minimal=minimal), unsafe_allow_html=True)
        if not is_static and is_active_focus and state.get_display_mode() != "Single Character":
            if html := _render_phrase_html(c):
                st.markdown(html, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

# ==================== PAGE RENDERERS ====================

def render_startup_file_choice():
    """Render startup file choice screen."""
    st.markdown("""
    <div class="splash-wrap">
        <div class="splash-card">
            <div class="splash-title">Radix 🈑 - Data Setup</div>
            <div class="splash-sub" style="margin-top: 20px;">
                Do you have a local Radix user data file you'd like to use?
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='max-width: 600px; margin: 40px auto;'>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    if c1.button("📱 Yes, upload my local file", use_container_width=True, type="primary"):
        state.set("startup_choice", "upload")
        st.rerun()
    if c2.button("☁️ No, use server defaults", use_container_width=True):
        state.set("startup_choice", "server")
        if state.get("server_data_available"):
            obj = state.get("server_data")
            state.update(
                favourites_list=obj["favourites_list"],
                prompt_config=obj["prompt_config"],
                prompt_ui=obj["prompt_ui"]
            )
        state.complete_startup()
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    if state.get("startup_choice") == "upload":
        st.markdown("<div style='max-width: 600px; margin: 40px auto;'><h3>📤 Upload Your Local File</h3>", unsafe_allow_html=True)
        if f := st.file_uploader("Choose your radix_user_data.json file", type=["json"], key="startup_uploader"):
            config.import_profile_bytes(f.getvalue())
            if state.get("_upload_applied"):
                st.success("✅ File loaded successfully!")
                if st.button("Continue to Radix", type="primary", use_container_width=True):
                    state.complete_startup()
                    st.rerun()
            elif state.get("_upload_error"):
                st.error(state.get("_upload_error"))
        if st.button("← Back to choice", use_container_width=True):
            state.set("startup_choice", None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def render_splash():
    """Render splash/onboarding screen."""
    st.markdown("""<div class="palace-entrance-container"><div class="grand-torii">⛩️</div><div class="entrance-text">Grand Hall of Radix 🈑 Components</div></div>""", unsafe_allow_html=True)
    
    _, c, _ = st.columns([1, 1, 1])
    if c.button("🚪 Enter", key="entrance_btn", use_container_width=True, type="primary"):
        state.complete_onboarding()
        st.rerun()

    st.markdown("<div style='margin: 40px auto;'>", unsafe_allow_html=True)
    
    # Search and User Data side-by-side
    col_search, col_data = st.columns([1, 1], gap="medium")
    
    with col_search:
        with st.expander("🔍 Search", expanded=False):
            st.markdown("**Character Search**")
            st.text_input("Paste or type a character to explore", key="splash_search", on_change=sync_splash_text, placeholder="e.g., 水", label_visibility="collapsed")
            st.caption("Enter one Chinese character to jump directly to its details")
            st.markdown("---")
            search_key = render_definition_search_ui("splash")
            if st.button("Search Definitions", use_container_width=True, type="primary", key="splash_def_btn"):
                state.set("w_def_search", state.get(search_key, ""))
                search_by_definition()
                state.complete_onboarding()
                st.rerun()
            st.caption("Search across character definitions and phrase meanings")
    
    with col_data:
        with st.expander("📂 User Data (Save/Load/Review & Edit)", expanded=False):
            st.caption("Single JSON file for **Favourites** + **AI Prompt Tasks**. Upload applies immediately; download is your backup/export.")
            
            if state.get("_manual_config_active"):
                st.info("🔒 Using uploaded configuration (overrides server defaults)")
            elif state.get("server_data_available"):
                st.info("☁️ Using server default configuration")
            else:
                st.info("🆕 Using app default configuration")

            c_dl, c_ul = st.columns(2)
            with c_dl:
                st.markdown(render_ipad_safe_download_html(config.export_profile_str(), "radix_user_data.json", "💾 Download user data"), unsafe_allow_html=True)
            with c_ul:
                if uf := st.file_uploader("Upload user data (JSON)", type=["json"], key="profile_uploader_persistent", label_visibility="collapsed"):
                    import hashlib
                    hash_val = hashlib.sha256(uf.getvalue()).hexdigest()
                    if hash_val != state.get('_last_upload_hash', ''):
                        st.warning("⚠️ New file detected - click Apply to use it")
                        if st.button("✅ Apply uploaded file now", use_container_width=True, type="primary", key="apply_upload_btn"):
                            state.set("_last_upload_hash", hash_val)
                            config.import_profile_bytes(uf.getvalue())
                            st.rerun()
                    else:
                        st.success("✓ Current file is active")
                    if st.button("♻️ Upload different file", use_container_width=True, key="reset_uploader_btn"):
                        state.pop("_last_upload_hash", None)
                        state.pop("_upload_error", None)
                        state.pop("_upload_applied", None)
                        state.pop("profile_uploader_persistent", None)
                        st.rerun()
            
            if state.get("_upload_error"):
                st.error(state.get("_upload_error"))
            elif state.get("_upload_applied"):
                st.success("✅ Upload applied successfully! Download to save changes.")
                if st.button("Dismiss", key="dismiss_success"):
                    state.set("_upload_applied", False)
                    st.rerun()
            
            if state.get("_post_apply_rerun"):
                state.set("_post_apply_rerun", False)
                st.rerun()

            with st.expander("🔎 Review current data snapshot", expanded=False):
                st.json(config.build_profile_dict())

            st.markdown("---")
            st.subheader("Favourites")
            fav_txt = st.text_area(
                "Favourites (space or newline separated)",
                value=" ".join(state.get_favourites()),
                height=90,
                key="fav_bulk_editor",
                label_visibility="collapsed"
            )
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                if st.button("Apply favourites", use_container_width=True, key="fav_apply"):
                    tokens = [t for t in re.split(r"\s+", (fav_txt or "").strip()) if t]
                    cleaned = []
                    seen = set()
                    for c in [t for t in tokens if len(t) == 1]:
                        if c not in seen:
                            cleaned.append(c)
                            seen.add(c)
                    state.set("favourites_list", cleaned)
                    state.set("fav_cursor", 0)
                    st.toast("Favourites updated.", icon="✅")
                    st.rerun()
            with c2:
                if st.button("Clear", use_container_width=True, key="fav_clear"):
                    state.set("favourites_list", [])
                    state.set("fav_cursor", 0)
                    st.toast("Cleared favourites.", icon="✅")
                    st.rerun()
            with c3:
                add_char = st.text_input(
                    "Add a character",
                    value="",
                    key="fav_add_one",
                    placeholder="e.g., 我",
                    label_visibility="collapsed"
                )
                if st.button("Add", use_container_width=True, key="fav_add_btn"):
                    c = (add_char or "").strip()
                    if len(c) != 1:
                        st.toast("Please enter exactly 1 character.", icon="⚠️")
                    else:
                        favs = state.get_favourites()
                        if c not in favs:
                            favs.append(c)
                            state.set("favourites_list", favs)
                            st.toast("Added.", icon="✅")
                            st.rerun()

            favs = state.get_favourites()
            if favs:
                st.markdown("**Current favourites**")
                for i, c in enumerate(favs):
                    cc1, cc2 = st.columns([6, 1])
                    with cc1:
                        st.write(c)
                    with cc2:
                        if st.button("✕", key=f"fav_rm_{i}", help="Remove"):
                            favs.pop(i)
                            state.set("favourites_list", favs)
                            st.toast("Removed.", icon="✅")
                            st.rerun()

            st.markdown("---")
            st.subheader("AI Prompt Tasks (Task 1–10)")
            config.normalize_prompt_state()
            cfg = state.get("prompt_config") or {}
            tasks = cfg.get("tasks", []) or []
            all_task_ids = [t.get("id") for t in tasks if t.get("id")]
            
            default_sel = st.multiselect(
                "Default selected tasks",
                options=all_task_ids,
                default=list(state.get("prompt_ui").get("default_selected_task_ids", all_task_ids)),
                key="prompt_default_sel_editor"
            )
            if st.button("Save default selection", key="save_default_task_sel"):
                pui = state.get("prompt_ui")
                pui["default_selected_task_ids"] = list(default_sel)
                state.set("prompt_ui", pui)
                config.normalize_prompt_state()
                st.toast("Default task selection updated.", icon="✅")
                st.rerun()

            st.caption("Edit titles/templates below. Changes persist in-session and will be included in the next download.")
            edited_tasks = []
            for idx, t in enumerate(tasks):
                tid = t.get("id")
                if not tid:
                    continue
                with st.expander(f"✏️ {t.get('title','(untitled)')} — {tid}", expanded=False):
                    title = st.text_input("Title", value=t.get("title", ""), key=f"pt_title_{tid}")
                    template = st.text_area("Template", value=t.get("template", ""), height=160, key=f"pt_tpl_{tid}")
                    cA, cB = st.columns([1, 3])
                    with cA:
                        if st.button("Delete task", key=f"pt_del_{tid}"):
                            cfg["tasks"] = [tt for tt in tasks if tt.get("id") != tid]
                            state.set("prompt_config", cfg)
                            state.pop(f"pt_title_{tid}", None)
                            state.pop(f"pt_tpl_{tid}", None)
                            state.pop(f"prompt_task_cb_{tid}", None)
                            config.normalize_prompt_state()
                            st.toast("Task deleted.", icon="✅")
                            st.rerun()
                    with cB:
                        st.caption("Tip: Keep the template as plain instructions. The character and definition are inserted separately.")
                edited_tasks.append({"id": tid, "title": title, "template": template})
            
            c_add, c_apply = st.columns([1, 1])
            with c_add:
                if st.button("Add new task", key="pt_add_new_home", use_container_width=True):
                    new_id = f"task_{uuid.uuid4().hex[:8]}"
                    tasks.append({"id": new_id, "title": "New task", "template": "Write your task instructions here.\n"})
                    cfg["tasks"] = tasks
                    state.set("prompt_config", cfg)
                    config.normalize_prompt_state()
                    st.toast("Task added. Edit it below.", icon="✅")
                    st.rerun()
            with c_apply:
                if st.button("Apply task edits", key="pt_apply_home", use_container_width=True):
                    cfg["tasks"] = edited_tasks
                    state.set("prompt_config", cfg)
                    config.normalize_prompt_state()
                    st.toast("Tasks updated.", icon="✅")
                    st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

    # Quick access favourites
    if demos := state.get_favourites():
        st.markdown("<h4 style='text-align:center; color:#666; margin-top:20px;'>Quick Access Favourites</h4>", unsafe_allow_html=True)
        st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
        unique_demos = list(dict.fromkeys(demos))
        
        for r in range((len(unique_demos) + 5 - 1) // 5):
            cols = st.columns(5)
            for j in range(5):
                idx = r * 5 + j
                if idx < len(unique_demos):
                    ch = unique_demos[idx]
                    with cols[j]:
                        if st.button(f"Explore {ch}", key=f"v4_splash_btn_{idx}_{ord(ch)}", use_container_width=True, type="primary"):
                            state.complete_onboarding()
                            state.enter_character_view(ch)
                            st.rerun()
                        st.caption(f"used in {component_usage_count(ch)} characters")
        st.markdown("</div>", unsafe_allow_html=True)

def render_sidebar():
    """Render sidebar content."""
    with st.sidebar:
        current_main_char = state.get("stroke_view_char") if state.is_stroke_view_active() else state.get_selected_component()
        
        if current_main_char:
            path_items = ["🏠 Root"] + state.get_history() + ([f"<i>{current_main_char}</i> (🧠)"] if state.is_stroke_view_active() else [f"<b>{current_main_char}</b>"])
            st.markdown(f"<div style='font-size:0.85em; margin:0 0 12px 0; padding:10px; color:#fff; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius:8px; text-align:center; font-weight:600; box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);'>{' → '.join(path_items)}</div>", unsafe_allow_html=True)
        
        if not state.is_showing_inputs():
            nav_col1, nav_col2 = st.columns(2)
            with nav_col1:
                if state.is_stroke_view_active():
                    st.button("← Back", on_click=state.exit_stroke_view, use_container_width=True, type="primary")
                else:
                    st.button("← Back", on_click=state.go_back, use_container_width=True, type="primary")
            with nav_col2:
                st.button("🏠 Root", on_click=state.go_to_root, use_container_width=True)
            st.markdown("---")

        current_char_for_sidebar = state.get("stroke_view_char") if state.is_stroke_view_active() else (state.get_preview_component() or state.get_selected_component())
        if current_char_for_sidebar:
            sidebar_html, sidebar_height = get_stroke_order_sidebar_html(current_char_for_sidebar, size=140)
            if sidebar_html:
                st_html(sidebar_html, height=sidebar_height)
            
            card_html = generate_clean_card_html(current_char_for_sidebar, usage_count=component_usage_count(current_char_for_sidebar), is_static=True)
            card_html = card_html.replace("search box at the top", "search box")
            st.markdown(f"<div style='margin-top: 15px;'>{card_html}</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            st.checkbox("Show in Favourites", value=(current_char_for_sidebar in state.get_favourites()), key=f"fav_chk_{current_char_for_sidebar}", on_change=toggle_favourite, args=(current_char_for_sidebar,))
            if st.button("Show Favourites", use_container_width=True):
                state.go_to_root()
                state.set("onboarding_done", False)
                st.rerun()

        if not state.is_showing_inputs():
            with st.expander("Display Phrases", expanded=False):
                modes = ["Single Character", "2-Characters", "3-Characters", "4-Characters"]
                idx = modes.index(state.get_display_mode()) if state.get_display_mode() in modes else 1
                if (nm := st.radio("Select mode", options=modes, index=idx, key="sidebar_display_mode", label_visibility="collapsed")) != state.get_display_mode():
                    state.set("display_mode", nm)
                    st.rerun()

        with st.expander("🔍 Search", expanded=False):
            st.markdown("**Character Search**")
            st.text_input("Paste or type a character", key="sb_search", on_change=sync_sidebar_text, placeholder="e.g., 水", label_visibility="collapsed")
            st.markdown("---")
            search_key = render_definition_search_ui("sb")
            if st.button("Search Definitions", use_container_width=True, type="primary", key="sb_def_btn"):
                state.set("w_def_search", state.get(search_key, ""))
                search_by_definition()
                st.rerun()
            st.caption("Search across character definitions and phrase meanings")

        if not state.is_stroke_view_active():
            with st.expander("📎 Filters", expanded=False):
                if not state.is_showing_inputs():
                    st.radio("Filter Results", options=SCRIPT_FILTERS, index=SCRIPT_FILTERS.index(state.get_script_filter()), key="w_script_filter", on_change=sync_script_filter)
                if state.is_showing_inputs():
                    st.slider("Stroke count", 1, 30, value=state.get_stroke_range(), key="w_stroke_range", on_change=sync_stroke_range)
                    
                    # Build radical dropdown grouped by stroke count
                    rad_groups = stats_cache.get("rad_groups", {})
                    radical_options = ["none"]
                    
                    for stroke_count in sorted(rad_groups.keys()):
                        rads_in_group = rad_groups[stroke_count]
                        if rads_in_group:
                            # Add radicals in this group with stroke count prefix
                            for rad in rads_in_group:
                                radical_options.append(rad)
                    
                    # Format function to show stroke counts
                    def format_radical(rad):
                        if rad == "none":
                            return "none"
                        rad_info = component_map.get(rad, {})
                        strokes = rad_info.get('stroke_count')
                        if strokes:
                            return f"{rad} ({strokes} strokes)"
                        return rad
                    
                    current_rad = state.get("radical")
                    current_index = radical_options.index(current_rad) if current_rad in radical_options else 0
                    
                    st.selectbox(
                        "Radical",
                        options=radical_options,
                        format_func=format_radical,
                        index=current_index,
                        key="w_radical",
                        on_change=sync_radical
                    )
                    
                    idcs = sorted(stats_cache.get("idc_counts", {}).keys())
                    idc = state.get("component_idc")
                    st.selectbox("Structure (IDC)", options=["none"] + idcs, index=(["none"] + idcs).index(idc) if idc in idcs else 0, key="w_idc", on_change=sync_idc)
                    
                    st.markdown("### Sort Grid By")
                    def update_grid_sort_mode():
                        state.set("grid_sort_mode", "usage" if state.get("grid_sort_mode_radio") == "Component frequency" else "frequency")
                        state.set("page", 1)
                    st.radio("Sort key", options=["Component frequency", "Character frequency"], index=0 if state.get_grid_sort_mode() == "usage" else 1, key="grid_sort_mode_radio", on_change=update_grid_sort_mode)
                    
                    if state.get_grid_sort_mode() == "frequency":
                        st.markdown("#### Script Preference")
                        gsf = state.get("grid_script_filter")
                        st.radio("Show characters in:", options=["Simplified", "Traditional", "Any"], index=["Simplified", "Traditional", "Any"].index(gsf), key="grid_script_radio", on_change=lambda: state.update(grid_script_filter=state.get("grid_script_radio"), page=1), horizontal=True)

def render_stroke_view():
    """Render stroke order and prompt generation view."""
    st.markdown("### Stroke Order Animation")
    main_html, _ = get_stroke_order_view_html(state.get("stroke_view_char"), state.get_display_mode())
    st_html(main_html, height=450)
    
    if state.get_display_mode() != "Single Character":
        if phrase_html := _render_phrase_html(state.get("stroke_view_char")):
            st.markdown(phrase_html, unsafe_allow_html=True)

    char = state.get("stroke_view_char", "").strip()
    if not char:
        st.info("Select a character to generate the ChatGPT prompt.")
        st.stop()

    st.markdown("### ChatGPT Prompt")
    config.normalize_prompt_state()
    cfg = state.get("prompt_config")
    tasks = cfg.get("tasks", []) or []
    all_task_ids = [t.get("id") for t in tasks if t.get("id")]
    cur_sel = [tid for tid in (state.get("prompt_selected_task_ids") or []) if tid in all_task_ids]
    if not cur_sel:
        cur_sel = list(state.get("prompt_ui").get("default_selected_task_ids", all_task_ids)) or list(all_task_ids)
    state.set("prompt_selected_task_ids", cur_sel)

    with st.expander("Prompt tasks (choose what to include)", expanded=True):
        if st.button("Select all tasks", key="select_all_prompt_tasks"):
            state.set("prompt_selected_task_ids", list(all_task_ids))
            for tid in all_task_ids:
                state.state[f"prompt_task_cb_{tid}"] = True
            st.rerun()
        sel = []
        for t in tasks:
            tid = t.get("id", "")
            if tid and st.checkbox(t.get("title", tid), key=f"prompt_task_cb_{tid}"):
                sel.append(tid)
        state.set("prompt_selected_task_ids", sel)

    prompt_text = render_combined_prompt(
        char=char,
        prompt_config=state.get("prompt_config"),
        selected_task_ids=state.get("prompt_selected_task_ids"),
        definition_en=get_char_definition_en(char)
    )
    st.text_area("Copy this prompt into ChatGPT", value=prompt_text, height=320)
    render_copy_to_clipboard(prompt_text, str(hash(state.get("stroke_view_char"))))

def render_definition_search_results():
    """Render definition search results."""
    results = state.get("definition_search_results")
    st.markdown(f"<div class='status-line'><div style='font-size:1.2em; font-weight:700;'>Search Results for \"{pyhtml.escape(state.get('definition_search_query'))}\"</div><div class='status-text' style='font-size:0.85em; color:#666; margin-top:8px;'>Found {len(results['characters'])} characters and {len(results['phrases'])} phrases</div></div>", unsafe_allow_html=True)
    
    if results['characters']:
        st.markdown("<div class='lineage-header'>📖 Characters</div>", unsafe_allow_html=True)
        for char in results['characters'][:30]:
            render_radix_row(char)
    
    if results['phrases']:
        st.markdown("<div class='lineage-header'>💬 Phrases</div>", unsafe_allow_html=True)
        st.markdown("<div style='max-width:900px; margin:0 auto;'>", unsafe_allow_html=True)
        for phrase_data in results['phrases']:
            st.markdown(f"<div class='compound-item' style='margin-bottom:15px;'><span class='cp-word' style='font-size:1.4em;'>{phrase_data['word']}</span><span class='cp-pinyin'>{phrase_data['pinyin']}</span><span class='cp-mean'>{pyhtml.escape(phrase_data['meanings'][:200] + ('...' if len(phrase_data['meanings']) > 200 else ''))}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    if not results['characters'] and not results['phrases']:
        st.info(f"No results found for '{state.get('definition_search_query')}'. Try different search terms.")

def render_grid_view():
    """Render main grid view with filters and pagination."""
    cur_min, cur_max = state.get_stroke_range()
    filter_parts = [f"<span class='status-tag'>Sort: {'Component' if state.get_grid_sort_mode() == 'usage' else 'Character'} frequency</span>"]
    
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
    
    if state.get("radical") != "none":
        filter_parts.append(f"<span class='status-tag'>Rad. {state.get('radical')}</span>")
    if state.get("component_idc") != "none":
        filter_parts.append(f"<span class='status-tag'>{state.get('component_idc')}</span>")
    if state.get_grid_sort_mode() == "usage":
        filter_parts.append("<span class='status-tag'>View: Components only</span>")
    if state.get_grid_sort_mode() == "frequency":
        filter_parts.append(f"<span class='status-tag'>Script: {state.get('grid_script_filter')}</span>")
    
    st.markdown(f"<div class='status-line' style='display: flex; flex-direction: column; gap: 8px;'><div style='display: flex; justify-content: space-between; align-items: center;'><div style='display: flex; flex-wrap: wrap; gap: 8px;'><span style='font-weight: 800; margin-right: 5px;'>📎 Filters:</span> {''.join(filter_parts)}</div><div style='font-size: 0.8em; color: rgba(15, 81, 50, 0.7); font-weight: 700;'>Click once to preview in the sidebar; click the same button again to drill down.</div></div></div>", unsafe_allow_html=True)

    filtered = [c for c in component_map if (s := get_stroke_count(c)) is not None and cur_min <= s <= cur_max and (state.get("radical") == "none" or component_map[c]["meta"].get("radical") == state.get("radical")) and (state.get("component_idc") == "none" or component_map[c]["meta"].get("decomposition", "").startswith(state.get("component_idc"))) and (state.get_grid_sort_mode() != "usage" or c in stats_cache["used_components"])]
    
    if state.get_grid_sort_mode() == "frequency":
        filtered = apply_script_filter(filtered, state.get("grid_script_filter"))
    
    sorted_comps = sorted(filtered, key=sort_key_frequency_primary if state.get_grid_sort_mode() == "frequency" else sort_key_usage_primary)

    if not sorted_comps:
        st.info("No components match current filters.")
    else:
        total = len(sorted_comps)
        max_page = max(1, math.ceil(total / PAGE_SIZE))
        page = max(1, min(state.get_current_page(), max_page))
        state.set("page", page)
        
        p1, p2, p3 = st.columns([1, 3, 1])
        with p1:
            if st.button("◀ Prev", disabled=page <= 1, use_container_width=True):
                state.set("page", page - 1)
                st.rerun()
        with p2:
            st.markdown(f"<div style='text-align:center; padding:10px 0; color:#555;'><div style='font-size:1.1em; font-weight:bold;'>{(page - 1) * PAGE_SIZE + 1}–{min(page * PAGE_SIZE, total)} of {total}</div></div>", unsafe_allow_html=True)
        with p3:
            if st.button("Next ▶", disabled=page >= max_page, use_container_width=True):
                state.set("page", page + 1)
                st.rerun()

        st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
        cols = st.columns(GRID_COLUMNS)
        for i, ch in enumerate(sorted_comps[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]):
            with cols[i % GRID_COLUMNS]:
                st.button(ch, key=f"b_{ch}_{page}", type="primary" if state.get_preview_component() == ch else "secondary", on_click=tile_click, args=(ch,), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("🔍 Search", expanded=False):
            st.markdown("**Character Search**")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if state.get("text_input_warning"):
                    st.warning(state.get("text_input_warning"))
                st.text_input("Go to component/character", value=state.get("text_input_comp"), key="w_text", on_change=sync_text, placeholder="Type one Hanzi, e.g. 水", label_visibility="collapsed")
                st.caption("Enter one Chinese character to jump directly to its details")
            st.markdown("---")
            col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
            with col_s2:
                search_key = render_definition_search_ui("w")
                if st.button("Search Definitions", use_container_width=True, type="primary", key="w_def_btn"):
                    state.set("w_def_search", state.get(search_key, ""))
                    search_by_definition()
                    st.rerun()
                st.caption("Search across character definitions and phrase meanings")

def render_character_lineage_view():
    """Render character lineage breakdown."""
    from radix_core import IDC_CHARS
    
    sel = state.get_selected_component()
    info = component_map.get(sel, {})
    decomp = info.get("meta", {}).get("decomposition", "")
    parents = [p for p in decomp if p in component_map and p not in IDC_CHARS and p not in ["?", "—"] and p != sel]
    parents = apply_script_filter(parents, state.get_script_filter())
    
    # REMOVED GREEN STATUS BANNER HERE
    
    if parents:
        st.markdown("<div class='lineage-header'>🧱 Components (How it's built)</div>", unsafe_allow_html=True)
        for p in parents:
            render_radix_row(p)

    st.markdown("<div class='lineage-header'>🎯 Current Selection</div>", unsafe_allow_html=True)
    focus_group = [sel]
    if cc_t2s and cc_s2t:
        s_cand = cc_t2s.convert(sel)
        t_cand = cc_s2t.convert(sel)
        variant = s_cand if s_cand != sel else t_cand
        if variant != sel and variant in component_map:
            focus_group.append(variant)
    
    for f in apply_script_filter(focus_group, state.get_script_filter()):
        render_radix_row(f)

    rel = info.get("related_characters", [])
    children = [c for c in rel if isinstance(c, str) and len(c) == 1 and c in component_map and c != sel]

    if children:
        children_sorted = sorted(children, key=sort_key_usage_primary)
        visible_children = apply_script_filter(children_sorted, state.get_script_filter())
        unique_visible = list(dict.fromkeys(visible_children))
        
        # --- ROLLING 25 CARDS PAGINATION with TOP NAV & BANNER ---
        BATCH_SIZE = 25
        total_derivs = len(unique_visible)
        current_page = state.get("derivative_page", 0)
        
        max_page = max(0, math.ceil(total_derivs / BATCH_SIZE) - 1)
        if current_page > max_page:
            current_page = max_page
            state.set("derivative_page", current_page)
        
        start_idx = current_page * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, total_derivs)
        current_batch = unique_visible[start_idx:end_idx]

        st.markdown(f"<div class='lineage-header'>🌲 Derivatives (Used in {total_derivs} characters)</div>", unsafe_allow_html=True)

        # Top Navigation
        nav_c1, nav_c2, nav_c3 = st.columns([1, 2, 1])
        with nav_c1:
            if current_page > 0:
                if st.button("⬅️ Previous 25", key="deriv_prev_top", use_container_width=True):
                    state.set("derivative_page", current_page - 1)
                    st.rerun()
        with nav_c3:
            if end_idx < total_derivs:
                remaining = total_derivs - end_idx
                if st.button(f"Next 25 ➡️", key="deriv_next_top", use_container_width=True, help=f"{remaining} more"):
                    state.set("derivative_page", current_page + 1)
                    st.rerun()
        
        # Quick-View Banner
        chars_html = "".join([f"<span style='display:inline-block; margin: 2px 6px; font-size: 1.4em; font-weight: bold; color: #444;'>{c}</span>" for c in current_batch])
        st.markdown(
            f"""
            <div style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 12px; padding: 15px; margin-bottom: 20px; text-align: center;">
                <div style="font-size: 0.85em; color: #888; margin-bottom: 8px; text-transform: uppercase; font-weight: 700;">
                    Batch {current_page + 1} of {max_page + 1} &middot; Showing {start_idx + 1}–{end_idx}
                </div>
                <div style="line-height: 1.6;">{chars_html}</div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        for child in current_batch:
            render_radix_row(child, minimal=True)

# ==================== MAIN ====================

def main():
    """Main application entry point with routing."""
    if not component_map:
        st.error("Component dataset not loaded.")
        st.stop()
    
    # Route to appropriate page
    if not state.is_startup_complete():
        render_startup_file_choice()
        st.stop()
    
    if not state.is_onboarding_complete():
        render_splash()
        st.stop()
    
    # Render sidebar (always present after onboarding)
    render_sidebar()
    
    # Route main content
    if state.is_stroke_view_active():
        render_stroke_view()
    elif state.is_definition_search_active():
        render_definition_search_results()
    elif state.is_showing_inputs():
        render_grid_view()
    else:
        render_character_lineage_view()

if __name__ == "__main__":
    main()
