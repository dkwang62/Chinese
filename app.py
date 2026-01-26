# app.py - Streamlined Radix (Grid-first, no splash screens)

import streamlit as st
from streamlit.components.v1 import html as st_html
import math
import html as pyhtml
import uuid
import re
from radix_core import (
    component_map, get_db_connection, batch_get_phrase_details,
    get_stroke_count, component_usage_count, apply_script_filter,
    get_char_definition_en, render_combined_prompt, get_stroke_order_view_html,
    SCRIPT_FILTERS, IDC_CHARS, sort_key_usage_primary, sort_key_frequency_primary,
    stats_cache, cc_t2s, cc_s2t, analyze_component_structure
)
from radix_state import (
    StateManager, ConfigManager, InputValidator,
    PAGE_CONFIG, PAGE_SIZE, GRID_COLUMNS
)
from radix_ui import (
    apply_styles, generate_clean_card_html, render_ipad_safe_download_html,
    render_copy_to_clipboard, get_stroke_order_sidebar_html,
    render_learning_insights_html
)
from radix_persistence import PersistenceManager

st.set_page_config(**PAGE_CONFIG)
apply_styles()

state = StateManager()
config = ConfigManager(state)
persistence = PersistenceManager(state)

def tile_click(c):
    if state.is_showing_inputs() and state.get_preview_component() == c:
        state.enter_character_view(c)
    else:
        state.set("preview_comp", c)

def list_tile_click(c):
    if state.get_preview_component() == c:
        if state.get_selected_component():
            history = state.get_history()
            history.append(state.get_selected_component())
            state.set("history", history)
        state.enter_character_view(c)
    else:
        state.set("preview_comp", c)

def toggle_favourite(char):
    if state.get(f"fav_chk_{char}", False):
        state.add_to_favourites(char)
    else:
        state.remove_from_favourites(char)

def _render_phrase_html(c: str) -> str:
    n_map = {"Single Character": 1, "2-Characters": 2, "3-Characters": 3, "4-Characters": 4}
    n = n_map.get(state.get_display_mode(), 2)
    raw_compounds = component_map.get(c, {}).get("meta", {}).get("compounds", [])
    if not raw_compounds and cc_t2s:
        s_c = cc_t2s.convert(c)
        if s_c != c:
            raw_compounds = component_map.get(s_c, {}).get("meta", {}).get("compounds", [])
    compounds = [w for w in (raw_compounds or []) if len(w) == n]
    if compounds and (db := get_db_connection()):
        phrases = batch_get_phrase_details(sorted(compounds), db)
        items = []
        for word in sorted(compounds):
            entry = phrases.get(word)
            if entry:
                p_mean = pyhtml.escape(entry.get('meanings', '')[:130] + ('...' if len(entry.get('meanings', '')) > 130 else ''))
                items.append(f"<div style='display:flex; align-items:baseline; padding:5px 8px; border-bottom:1px solid #eee;'><span style='font-weight:700; font-size:1.0rem; min-width:65px;'>{word}</span><span style='color:#d35400; font-size:0.85rem; margin-right:12px;'>{entry.get('pinyin', '')}</span><span style='color:#444; font-size:0.85rem;'>{p_mean}</span></div>")
        if items:
            return f"<div style='padding:12px; background:#f1f8e9; border-radius:8px; margin-top:10px;'><div style='font-weight:bold; margin-bottom:8px;'>{state.get_display_mode()} containing {c}</div>{''.join(items)}</div>"
    return ""

def render_radix_row(c, is_static=False, minimal=False):
    col_char, col_details = st.columns([2, 10])
    is_preview = state.get_preview_component() == c
    is_active_focus = is_preview or (state.get_preview_component() is None and c == state.get_selected_component())
    uid = str(uuid.uuid4())[:8]
    with col_char:
        if is_static:
            st.markdown(f"<div class='char-static-box'>{c}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='char-btn-wrap'>", unsafe_allow_html=True)
            st.button(c, key=f"char_{c}_{uid}", type="primary" if is_preview else "secondary", on_click=list_tile_click, args=(c,), use_container_width=True)
            st.markdown(f"<div class='char-btn-hint {'previewing' if is_preview else ''}'>{'Click again to drill down' if is_preview else 'Click once to preview'}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    with col_details:
        st.markdown(generate_clean_card_html(c, usage_count=component_usage_count(c), is_static=is_static, minimal=minimal), unsafe_allow_html=True)
        if not is_static and is_active_focus:
            current_mode_str = state.get_display_mode()
            try:
                current_int = int(current_mode_str[0])
            except:
                current_int = 2
            if current_int not in [2, 3, 4]:
                current_int = 2
            def update_phrase_len():
                val = st.session_state[f"ph_len_{c}_{uid}"]
                state.set("display_mode", f"{val}-Characters")
            st.radio("Phrase Length", options=[2, 3, 4], index=[2, 3, 4].index(current_int), key=f"ph_len_{c}_{uid}", horizontal=True, label_visibility="collapsed", on_change=update_phrase_len)
            if html := _render_phrase_html(c):
                st.markdown(html, unsafe_allow_html=True)
    st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.markdown("# 🈳 Radix")
        current_char = state.get("stroke_view_char") if state.is_stroke_view_active() else state.get_selected_component()
        if current_char:
            path_items = ["🏠 Grid"] + state.get_history()
            if state.is_stroke_view_active():
                path_items.append(f"<i>{current_char}</i> (AI)")
            else:
                path_items.append(f"<b>{current_char}</b>")
            st.markdown(f"<div style='font-size:0.85em; padding:10px; color:#fff; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius:8px; text-align:center; margin-bottom:12px;'>{' → '.join(path_items)}</div>", unsafe_allow_html=True)
        if not state.is_showing_inputs() or state.is_stroke_view_active():
            nav_col1, nav_col2 = st.columns(2)
            with nav_col1:
                if state.is_stroke_view_active():
                    st.button("← Lineage", on_click=state.exit_stroke_view, use_container_width=True, type="primary")
                else:
                    st.button("← Back", on_click=state.go_back, use_container_width=True, type="primary")
            with nav_col2:
                st.button("🏠 Grid", on_click=state.go_to_root, use_container_width=True)
        current_char_for_sidebar = state.get("stroke_view_char") if state.is_stroke_view_active() else (state.get_preview_component() or state.get_selected_component())
        if current_char_for_sidebar:
            show_lineage = state.is_showing_inputs() or state.is_stroke_view_active() or (current_char_for_sidebar != state.get_selected_component())
            show_ai_link = not state.is_stroke_view_active()
            if show_lineage or show_ai_link:
                if show_lineage and show_ai_link:
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("🌳 Lineage", key="sb_lineage", use_container_width=True, type="primary"):
                            if state.get_selected_component() and state.get_selected_component() != current_char_for_sidebar:
                                history = state.get_history()
                                history.append(state.get_selected_component())
                                state.set("history", history)
                            state.enter_character_view(current_char_for_sidebar)
                            st.rerun()
                    with b2:
                        if st.button("🧠 AI", key="sb_ai", use_container_width=True):
                            state.enter_stroke_view(current_char_for_sidebar)
                            st.rerun()
                else:
                    if show_lineage:
                        if st.button("🌳 Lineage", key="sb_lineage_full", use_container_width=True, type="primary"):
                            if state.get_selected_component() and state.get_selected_component() != current_char_for_sidebar:
                                history = state.get_history()
                                history.append(state.get_selected_component())
                                state.set("history", history)
                            state.enter_character_view(current_char_for_sidebar)
                            st.rerun()
                    if show_ai_link:
                        if st.button("🧠 AI", key="sb_ai_full", use_container_width=True):
                            state.enter_stroke_view(current_char_for_sidebar)
                            st.rerun()
            sidebar_html, sidebar_height = get_stroke_order_sidebar_html(current_char_for_sidebar, size=140)
            if sidebar_html:
                st_html(sidebar_html, height=sidebar_height)
            card_html = generate_clean_card_html(current_char_for_sidebar, usage_count=component_usage_count(current_char_for_sidebar), is_static=True)
            st.markdown(f"<div style='margin-top: 15px;'>{card_html}</div>", unsafe_allow_html=True)
            analysis = analyze_component_structure(current_char_for_sidebar)
            if analysis['semantic'] or analysis['phonetic']:
                s_txt = f"💡 <b>{analysis['semantic']}</b> = Meaning" if analysis['semantic'] else ""
                p_txt = f"📊 <b>{analysis['phonetic']}</b> = Sound" if analysis['phonetic'] else ""
                st.markdown(f"<div style='background:#f0f2f6; padding:12px; border-radius:10px; margin-top:15px;'><div style='font-weight:bold; margin-bottom:6px; font-size:0.9em;'>🧠 Logic</div><div style='font-size:0.85em; margin-bottom:4px;'>{s_txt}</div><div style='font-size:0.85em;'>{p_txt}</div></div>", unsafe_allow_html=True)
            st.markdown("---")
            st.checkbox("⭐ Favourite", value=(current_char_for_sidebar in state.get_favourites()), key=f"fav_chk_{current_char_for_sidebar}", on_change=toggle_favourite, args=(current_char_for_sidebar,))
        st.markdown("---")
        st.markdown("### 🔍 Search")
        search_input = st.text_input("Character", key="sidebar_search", placeholder="e.g., 水", label_visibility="collapsed")
        if st.button("Search", use_container_width=True, type="primary", key="sidebar_search_btn"):
            validated = InputValidator.validate_character_input(search_input, st.toast)
            if validated:
                state.state["sidebar_search"] = ""
                state.enter_character_view(validated)
                st.rerun()
        st.markdown("---")
        with st.expander("💾 User Data", expanded=False):
            st.markdown(render_ipad_safe_download_html(config.export_profile_str(), "radix_user_data.json", "📥 Download"), unsafe_allow_html=True)
            if uf := st.file_uploader("📤 Upload JSON", type=["json"], key="sidebar_uploader", label_visibility="collapsed"):
                import hashlib
                hash_val = hashlib.sha256(uf.getvalue()).hexdigest()
                if hash_val != state.get('_last_upload_hash', ''):
                    st.warning("⚠️ New file detected")
                    if st.button("✅ Apply Now", use_container_width=True, type="primary", key="apply_upload"):
                        state.set("_last_upload_hash", hash_val)
                        config.import_profile_bytes(uf.getvalue())
                        st.rerun()
                else:
                    st.success("✓ Current file active")

def render_grid():
    tab1, tab2 = st.tabs(["📊 All Components", "⭐ Favourites"])
    with tab1:
        render_all_components_grid()
    with tab2:
        render_favourites_grid()

def render_all_components_grid():
    st.markdown("<div style='background:#f8f9fa; padding:20px; border-radius:10px; margin-bottom:25px;'>", unsafe_allow_html=True)
    col_sort, col_script = st.columns([1, 1])
    with col_sort:
        sort_choice = st.radio("Sort by", options=["Component frequency", "Character frequency"], index=0 if state.get_grid_sort_mode() == "usage" else 1, horizontal=True, key="grid_sort_radio")
        state.set("grid_sort_mode", "usage" if "Component" in sort_choice else "frequency")
    with col_script:
        if state.get_grid_sort_mode() == "frequency":
            gsf = state.get("grid_script_filter", "Any")
            script_choice = st.radio("Script", options=["Simplified", "Traditional", "Any"], index=["Simplified", "Traditional", "Any"].index(gsf), horizontal=True, key="grid_script_radio")
            state.set("grid_script_filter", script_choice)
    col_stroke, col_radical, col_idc = st.columns([2, 2, 2])
    with col_stroke:
        stroke_range = st.slider("Strokes", 1, 30, value=state.get_stroke_range(), key="grid_stroke_slider")
        state.set("stroke_range", stroke_range)
    with col_radical:
        rad_groups = stats_cache.get("rad_groups", {})
        radical_options = ["none"]
        for stroke_count in sorted(rad_groups.keys()):
            rads_in_group = rad_groups[stroke_count]
            if rads_in_group:
                for rad in rads_in_group:
                    radical_options.append(rad)
        def format_radical(rad):
            if rad == "none":
                return "none"
            rad_info = component_map.get(rad, {})
            strokes = rad_info.get('stroke_count')
            if strokes:
                return f"{rad} ({strokes} strokes)"
            return rad
        current_rad = state.get("radical", "none")
        current_index = radical_options.index(current_rad) if current_rad in radical_options else 0
        radical_choice = st.selectbox("Radical", options=radical_options, format_func=format_radical, index=current_index, key="grid_radical_select")
        state.set("radical", radical_choice)
    with col_idc:
        idcs = sorted(stats_cache.get("idc_counts", {}).keys())
        idc = state.get("component_idc", "none")
        idc_choice = st.selectbox("Structure", options=["none"] + idcs, index=(["none"] + idcs).index(idc) if idc in idcs else 0, key="grid_idc_select")
        state.set("component_idc", idc_choice)
    st.markdown("</div>", unsafe_allow_html=True)
    cur_min, cur_max = state.get_stroke_range()
    filtered = [c for c in component_map if (s := get_stroke_count(c)) is not None and cur_min <= s <= cur_max]
    if state.get("radical") != "none":
        filtered = [c for c in filtered if component_map[c]["meta"].get("radical") == state.get("radical")]
    if state.get("component_idc") != "none":
        filtered = [c for c in filtered if component_map[c]["meta"].get("decomposition", "").startswith(state.get("component_idc"))]
    if state.get_grid_sort_mode() == "usage":
        filtered = [c for c in filtered if c in stats_cache["used_components"]]
    if state.get_grid_sort_mode() == "frequency":
        filtered = apply_script_filter(filtered, state.get("grid_script_filter"))
    sorted_comps = sorted(filtered, key=sort_key_frequency_primary if state.get_grid_sort_mode() == "frequency" else sort_key_usage_primary)
    if not sorted_comps:
        st.info("No components match filters.")
        return
    total = len(sorted_comps)
    max_page = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(state.get_current_page(), max_page))
    state.set("page", page)
    p1, p2, p3 = st.columns([1, 3, 1])
    with p1:
        if st.button("◀ Prev", disabled=page <= 1, use_container_width=True, key="grid_prev"):
            state.set("page", page - 1)
            st.rerun()
    with p2:
        st.markdown(f"<div style='text-align:center; padding:10px 0;'><div style='font-size:1.1em; font-weight:bold;'>{(page - 1) * PAGE_SIZE + 1}–{min(page * PAGE_SIZE, total)} of {total}</div></div>", unsafe_allow_html=True)
    with p3:
        if st.button("Next ▶", disabled=page >= max_page, use_container_width=True, key="grid_next"):
            state.set("page", page + 1)
            st.rerun()
    st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
    cols = st.columns(GRID_COLUMNS)
    for i, ch in enumerate(sorted_comps[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]):
        with cols[i % GRID_COLUMNS]:
            st.button(ch, key=f"grid_{ch}_{page}", type="primary" if state.get_preview_component() == ch else "secondary", on_click=tile_click, args=(ch,), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

def render_favourites_grid():
    favs = state.get_favourites()
    if not favs:
        st.info("No favourites yet. Click the ⭐ button in the sidebar to add characters.")
        return
    st.markdown(f"### {len(favs)} Favourites")
    with st.expander("📝 Edit Favourites List", expanded=False):
        fav_txt = st.text_area("Edit (space/newline separated)", value=" ".join(favs), height=90, key="fav_bulk_editor")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Apply", use_container_width=True, key="fav_apply"):
                tokens = [t for t in re.split(r"\s+", (fav_txt or "").strip()) if t]
                cleaned = []
                seen = set()
                for c in [t for t in tokens if len(t) == 1]:
                    if c not in seen:
                        cleaned.append(c)
                        seen.add(c)
                state.set("favourites_list", cleaned)
                st.toast("Favourites updated.", icon="✅")
                st.rerun()
        with c2:
            if st.button("Clear All", use_container_width=True, key="fav_clear"):
                state.set("favourites_list", [])
                st.toast("Cleared.", icon="✅")
                st.rerun()
    st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
    cols = st.columns(GRID_COLUMNS)
    for i, ch in enumerate(favs):
        with cols[i % GRID_COLUMNS]:
            st.button(ch, key=f"fav_{ch}_{i}", type="primary" if state.get_preview_component() == ch else "secondary", on_click=tile_click, args=(ch,), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

def render_lineage():
    sel = state.get_selected_component()
    info = component_map.get(sel, {})
    st.markdown("<div style='background:#f8f9fa; padding:15px; border-radius:10px; margin-bottom:20px;'>", unsafe_allow_html=True)
    script_choice = st.radio("Filter Results", options=SCRIPT_FILTERS, index=SCRIPT_FILTERS.index(state.get_script_filter())), horizontal=True, key="lineage_script_filter")
    state.set("script_filter", script_choice[0])
    st.markdown("</div>", unsafe_allow_html=True)
    decomp = info.get("meta", {}).get("decomposition", "")
    parents = [p for p in decomp if p in component_map and p not in IDC_CHARS and p not in ["?", "—"] and p != sel]
    parents = apply_script_filter(parents, state.get_script_filter())
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
        visible_children = apply_script_filter(sorted(children, key=sort_key_usage_primary), state.get_script_filter())
        unique_visible = list(dict.fromkeys(visible_children))
        BATCH_SIZE = 25
        total_derivs = len(unique_visible)
        current_page = min(state.get("derivative_page", 0), max(0, math.ceil(total_derivs / BATCH_SIZE) - 1))
        start_idx = current_page * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, total_derivs)
        current_batch = unique_visible[start_idx:end_idx]
        st.markdown(f"<div class='lineage-header'>🌲 Derivatives (Used in {total_derivs} characters)</div>", unsafe_allow_html=True)
        nav_c1, nav_c2, nav_c3 = st.columns([1, 2, 1])
        with nav_c1:
            if current_page > 0:
                if st.button("⬅️ Prev 25", key="deriv_prev", use_container_width=True):
                    state.set("derivative_page", current_page - 1)
                    st.rerun()
        with nav_c2:
            st.markdown(f"<div style='text-align:center; padding:8px; font-weight:600;'>Batch {current_page + 1} · {start_idx + 1}–{end_idx}</div>", unsafe_allow_html=True)
        with nav_c3:
            if end_idx < total_derivs:
                if st.button("Next 25 ➡️", key="deriv_next", use_container_width=True):
                    state.set("derivative_page", current_page + 1)
                    st.rerun()
        chars_html = "".join([f"<span style='display:inline-block; margin:2px 6px; font-size:1.4em; font-weight:bold; color:#444;'>{c}</span>" for c in current_batch])
        st.markdown(f"<div style='background:#f8f9fa; border:1px solid #e9ecef; border-radius:12px; padding:15px; margin-bottom:20px; text-align:center;'><div style='font-size:0.85em; color:#888; margin-bottom:8px; text-transform:uppercase; font-weight:700;'>Batch {current_page + 1} &middot; {start_idx + 1}–{end_idx}</div><div style='line-height:1.6;'>{chars_html}</div></div>", unsafe_allow_html=True)
        for child in current_batch:
            render_radix_row(child, minimal=True)

def render_ai_link():
    char = state.get("stroke_view_char")
    st.markdown("### Stroke Order Animation")
    main_html, _ = get_stroke_order_view_html(char, state.get_display_mode())
    st_html(main_html, height=450)
    insights_result = render_learning_insights_html(char)
    if isinstance(insights_result, tuple):
        if len(insights_result) == 3:
            insights_html, insights_height, prompt_text = insights_result
        elif len(insights_result) == 2:
            insights_html, insights_height = insights_result
            prompt_text = None
        else:
            insights_html, insights_height, prompt_text = None, 0, None
        if insights_html:
            st_html(insights_html, height=insights_height)
        if prompt_text:
            st.markdown("---")
            st.markdown("**🤖 Verify Logic & Patterns with AI**")
            render_copy_to_clipboard(prompt_text, f"verify_{char}")
    if state.get_display_mode() != "Single Character":
        if phrase_html := _render_phrase_html(char):
            st.markdown(phrase_html, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### ChatGPT Prompt")
    config.normalize_prompt_state()
    cfg = state.get("prompt_config")
    tasks = cfg.get("tasks", []) or []
    all_task_ids = [t.get("id") for t in tasks if t.get("id")]
    cur_sel = [tid for tid in (state.get("prompt_selected_task_ids") or []) if tid in all_task_ids]
    if not cur_sel:
        cur_sel = list(state.get("prompt_ui").get("default_selected_task_ids", all_task_ids)) or list(all_task_ids)
    state.set("prompt_selected_task_ids", cur_sel)
    with st.expander("Prompt tasks (choose what to include)", expanded=False):
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
    prompt_text = render_combined_prompt(char=char, prompt_config=state.get("prompt_config"), selected_task_ids=state.get("prompt_selected_task_ids"), definition_en=get_char_definition_en(char))
    st.text_area("Copy this prompt into ChatGPT", value=prompt_text, height=320, label_visibility="collapsed")
    render_copy_to_clipboard(prompt_text, str(hash(char)))

def main():
    if not component_map:
        st.error("Component dataset not loaded.")
        st.stop()
    state.initialize()
    config.load_server_data()
    config.initialize_prompt_config()
    persistence.try_restore()
    render_sidebar()
    persistence.add_heartbeat()
    if state.is_stroke_view_active():
        render_ai_link()
    elif state.is_showing_inputs():
        render_grid()
    else:
        render_lineage()
    persistence.auto_save()

if __name__ == "__main__":
    main()
