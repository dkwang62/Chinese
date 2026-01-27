# app.py - CLEANED VERSION
# Main Streamlit app for Radix - Now using consolidated utilities

import streamlit as st
from streamlit.components.v1 import html as st_html
import math
import uuid
from radix_core import (
    component_map, get_db_connection, batch_get_phrase_details,
    search_phrases_by_definition, get_stroke_count, component_usage_count,
    apply_script_filter, get_char_definition_en, render_combined_prompt,
    get_stroke_order_view_html, SCRIPT_FILTERS, IDC_CHARS,
    sort_key_usage_primary, sort_key_frequency_primary, stats_cache,
    cc_t2s, cc_s2t, analyze_component_structure
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
# NEW: Import consolidated utilities
from radix_utils import normalize_pinyin, get_char_field, deduplicate_list
from radix_html import build_phrase_list


# Configure Streamlit
st.set_page_config(**PAGE_CONFIG)
apply_styles()

# Initialize managers
state = StateManager()
config = ConfigManager(state)
persistence = PersistenceManager(state)


# ==================== CALLBACKS ====================

def handle_tile_click(c, is_list_view=False):
    """
    Consolidated tile click handler.
    Replaces both tile_click() and list_tile_click().
    """
    if state.get_preview_component() == c:
        # Second click - enter character view
        if is_list_view and state.get_selected_component():
            # Save to history in list view
            history = state.get_history()
            history.append(state.get_selected_component())
            state.set("history", history)
        state.enter_character_view(c)
    else:
        # First click - preview
        state.set("preview_comp", c)


def toggle_favourite(char):
    """Toggle favourite status via checkbox."""
    if state.get(f"fav_chk_{char}", False):
        state.add_to_favourites(char)
    else:
        state.remove_from_favourites(char)


def search_by_definition():
    """Execute search for English definitions."""
    query = state.get("sidebar_def_search", "").strip()
    is_valid, error_msg = InputValidator.validate_definition_search(query)
    
    if not is_valid:
        st.toast(error_msg)
        return
    
    # 1. Search Characters
    char_results = []
    query_lower = query.lower()
    for char, info in component_map.items():
        # Use utility instead of nested get()
        definition = get_char_field(char, "meta", "definition")
        if isinstance(definition, str) and query_lower in definition.lower():
            char_results.append(char)
    
    # 2. Search Phrases
    db_conn = get_db_connection()
    phrase_results = search_phrases_by_definition(query, db_conn, limit=200) if db_conn else []
    
    # 3. Update State
    state.update(
        definition_search_mode=True,
        definition_search_query=query,
        definition_search_results={"characters": char_results[:120], "phrases": phrase_results[:200]},
        show_inputs=False,
        selected_comp="",
        preview_comp=None
    )


# ==================== HTML HELPERS ====================

def _render_phrase_html(c: str) -> str:
    """Render phrases containing the character using consolidated HTML builder."""
    n_map = {"Single Character": 1, "2-Characters": 2, "3-Characters": 3, "4-Characters": 4}
    n = n_map.get(state.get_display_mode(), 2)
    
    # Get compounds from character or its variant
    raw_compounds = get_char_field(c, "meta", "compounds", default=[])
    
    if not raw_compounds and cc_t2s:
        s_c = cc_t2s.convert(c)
        if s_c != c:
            raw_compounds = get_char_field(s_c, "meta", "compounds", default=[])
            
    compounds = [w for w in (raw_compounds or []) if len(w) == n]
    
    if compounds and (db := get_db_connection()):
        phrases = batch_get_phrase_details(sorted(compounds), db)
        phrase_list = []
        for word in sorted(compounds):
            entry = phrases.get(word)
            if entry:
                phrase_list.append({
                    'word': word,
                    'pinyin': entry.get('pinyin', ''),
                    'meanings': entry.get('meanings', '')
                })
        
        if phrase_list:
            # Use consolidated HTML builder
            title = f"{state.get_display_mode()} containing {c}"
            return build_phrase_list(phrase_list, title)
    
    return ""


def render_radix_row(c, is_static=False, minimal=False):
    """Render a standard list row for a character."""
    col_char, col_details = st.columns([2, 10])
    is_preview = state.get_preview_component() == c
    is_active_focus = is_preview or (state.get_preview_component() is None and c == state.get_selected_component())
    
    uid = str(uuid.uuid4())[:8]

    with col_char:
        if is_static:
            st.markdown(f"<div class='char-static-box'>{c}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='char-btn-wrap'>", unsafe_allow_html=True)
            st.button(
                c,
                key=f"char_{c}_{uid}",
                type="primary" if is_preview else "secondary",
                help="Previewing..." if is_preview else "Click to preview",
                on_click=handle_tile_click,  # Use consolidated handler
                args=(c, True),  # is_list_view=True
                use_container_width=True
            )
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

            st.radio(
                "Phrase Length",
                options=[2, 3, 4],
                index=[2, 3, 4].index(current_int),
                key=f"ph_len_{c}_{uid}",
                on_change=update_phrase_len,
                horizontal=True
            )
            
            if phrase_html := _render_phrase_html(c):
                st.markdown(phrase_html, unsafe_allow_html=True)


# ==================== SIDEBAR ====================

def render_sidebar():
    """Render the sidebar with navigation and controls."""
    with st.sidebar:
        # Logo/Title
        st.markdown("# 🈑 Radix")
        
        # Main search
        st.markdown("---")
        st.markdown("### Character Search")
        
        def handle_search():
            raw = st.session_state.get("char_search_input", "").strip()
            if raw:
                validated = InputValidator.validate_character_input(
                    raw, 
                    error_callback=lambda msg: st.toast(msg, icon="⚠️")
                )
                if validated:
                    st.session_state["char_search_input"] = ""
                    state.complete_onboarding()
                    state.enter_character_view(validated)
                    st.rerun()
        
        st.text_input(
            "Enter a Chinese character",
            key="char_search_input",
            on_change=handle_search,
            placeholder="e.g., 水, 火, 山",
            label_visibility="collapsed"
        )
        
        # Navigation buttons
        if state.get_selected_component():
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Back", use_container_width=True):
                    state.go_back()
                    st.rerun()
            with col2:
                if st.button("🏠 Home", use_container_width=True):
                    state.show_inputs()
                    st.rerun()
        
        # Definition search
        st.markdown("---")
        st.markdown("### Definition Search")
        
        def handle_def_search():
            search_by_definition()
            st.rerun()
        
        st.text_input(
            "Search by English meaning",
            key="sidebar_def_search",
            on_change=handle_def_search,
            placeholder="e.g., water, fire",
            label_visibility="collapsed"
        )
        
        # Favourites
        st.markdown("---")
        with st.expander("⭐ Favourites", expanded=False):
            favs = state.get_favourites()
            if favs:
                for fav in favs:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button(fav, key=f"fav_btn_{fav}", use_container_width=True):
                            state.enter_character_view(fav)
                            st.rerun()
                    with col2:
                        if st.button("❌", key=f"fav_del_{fav}"):
                            state.remove_from_favourites(fav)
                            st.rerun()
            else:
                st.info("No favourites yet")
        
        # Persistence controls
        st.markdown("---")
        persistence.render_controls()
        
        # Profile management
        st.markdown("---")
        with st.expander("💾 Profile", expanded=False):
            if st.download_button(
                "📥 Export Profile",
                data=config.export_profile_str(),
                file_name="radix_profile.json",
                mime="application/json",
                use_container_width=True
            ):
                st.toast("Profile exported!", icon="✅")
            
            uploaded = st.file_uploader("📤 Import Profile", type=["json"])
            if uploaded:
                config.import_profile_bytes(uploaded.read())
                st.toast("Profile imported!", icon="✅")
                st.rerun()


# ==================== MAIN VIEWS ====================

def render_grid():
    """Render the character grid."""
    st.markdown("## Character Grid")
    
    # Filters
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        stroke_range = st.slider(
            "Stroke Count",
            min_value=1,
            max_value=30,
            value=state.get_stroke_range(),
            key="stroke_slider"
        )
        state.set("stroke_range", stroke_range)
    
    with col2:
        script_filter = st.radio(
            "Script",
            options=SCRIPT_FILTERS,
            index=SCRIPT_FILTERS.index(state.get("grid_script_filter", "Any")),
            horizontal=True,
            key="grid_script_radio"
        )
        state.set("grid_script_filter", script_filter)
    
    with col3:
        sort_mode = st.radio(
            "Sort",
            options=["usage", "frequency"],
            index=0 if state.get_grid_sort_mode() == "usage" else 1,
            horizontal=True,
            key="grid_sort_radio"
        )
        state.set("grid_sort_mode", sort_mode)
    
    # Filter characters
    filtered = []
    min_strokes, max_strokes = stroke_range
    
    for char in component_map:
        stroke_count = get_stroke_count(char)
        if stroke_count and min_strokes <= stroke_count <= max_strokes:
            filtered.append(char)
    
    # Apply script filter
    filtered = apply_script_filter(filtered, script_filter)
    
    # Sort
    if sort_mode == "usage":
        filtered.sort(key=sort_key_usage_primary, reverse=True)
    else:
        filtered.sort(key=sort_key_frequency_primary, reverse=True)
    
    # Use deduplicate utility
    filtered = deduplicate_list(filtered)
    
    # Pagination
    total = len(filtered)
    max_page = max(1, math.ceil(total / PAGE_SIZE))
    current_page = min(state.get_current_page(), max_page)
    
    start_idx = (current_page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total)
    page_chars = filtered[start_idx:end_idx]
    
    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if current_page > 1:
            if st.button("⬅️ Previous", use_container_width=True):
                state.set("page", current_page - 1)
                st.rerun()
    with col2:
        st.markdown(f"<div style='text-align:center; padding:8px;'>Page {current_page} of {max_page} ({total} chars)</div>", unsafe_allow_html=True)
    with col3:
        if current_page < max_page:
            if st.button("Next ➡️", use_container_width=True):
                state.set("page", current_page + 1)
                st.rerun()
    
    # Grid
    st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
    cols = st.columns(GRID_COLUMNS)
    for idx, char in enumerate(page_chars):
        with cols[idx % GRID_COLUMNS]:
            is_preview = state.get_preview_component() == char
            st.button(
                char,
                key=f"grid_{char}_{idx}",
                type="primary" if is_preview else "secondary",
                on_click=handle_tile_click,  # Use consolidated handler
                args=(char, False),  # is_list_view=False
                use_container_width=True
            )
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Preview
    if preview := state.get_preview_component():
        st.markdown("---")
        st.markdown("### Preview")
        render_radix_row(preview, is_static=True)


def render_definition_search_results():
    """Render definition search results."""
    results = state.get("definition_search_results") or {}
    query = state.get("definition_search_query", "")
    
    st.markdown(f"## Search Results: '{query}'")
    
    if st.button("⬅️ Back to Grid"):
        state.update(
            definition_search_mode=False,
            definition_search_results=None,
            show_inputs=True
        )
        st.rerun()
    
    if results['characters']:
        st.markdown("<div class='lineage-header'>📖 Characters</div>", unsafe_allow_html=True)
        for char in results['characters'][:30]:
            render_radix_row(char)
    
    if results['phrases']:
        st.markdown("<div class='lineage-header'>💬 Phrases</div>", unsafe_allow_html=True)
        # Use consolidated phrase list builder
        phrase_data = [
            {
                'word': p['word'],
                'pinyin': p['pinyin'],
                'meanings': p['meanings']
            }
            for p in results['phrases']
        ]
        st.markdown(build_phrase_list(phrase_data, "Matching Phrases"), unsafe_allow_html=True)
    
    if not results['characters'] and not results['phrases']:
        st.info(f"No results found for '{query}'. Try different search terms.")


def render_lineage():
    """Render the lineage/list view."""
    sel = state.get_selected_component()
    info = component_map.get(sel, {})
    
    # Filter
    st.markdown("<div style='background: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)
    script_choice = st.radio("Filter Results", options=SCRIPT_FILTERS, index=SCRIPT_FILTERS.index(state.get_script_filter()), horizontal=True, key="lineage_script_filter")
    state.set("script_filter", script_choice)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Parents
    decomp = get_char_field(sel, "meta", "decomposition", default="")
    parents = [p for p in decomp if p in component_map and p not in IDC_CHARS and p not in ["?", "—"] and p != sel]
    parents = apply_script_filter(parents, state.get_script_filter())
    
    if parents:
        st.markdown("<div class='lineage-header'>🧱 Components (How it's built)</div>", unsafe_allow_html=True)
        for p in parents:
            render_radix_row(p)

    # Current
    st.markdown("<div class='lineage-header'>🎯 Current Selection</div>", unsafe_allow_html=True)
    focus_group = [sel]
    if cc_t2s and cc_s2t:
        s_cand, t_cand = cc_t2s.convert(sel), cc_s2t.convert(sel)
        variant = s_cand if s_cand != sel else t_cand
        if variant != sel and variant in component_map:
            focus_group.append(variant)
    # Use deduplicate utility
    for f in deduplicate_list(apply_script_filter(focus_group, state.get_script_filter())):
        render_radix_row(f)

    # Children
    rel = info.get("related_characters", [])
    children = [c for c in rel if isinstance(c, str) and len(c) == 1 and c in component_map and c != sel]

    if children:
        visible_children = apply_script_filter(sorted(children, key=sort_key_usage_primary), state.get_script_filter())
        # Use deduplicate utility
        unique_visible = deduplicate_list(visible_children)
        BATCH_SIZE, total_derivs = 25, len(unique_visible)
        
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
            st.markdown(f"<div style='text-align:center; padding:8px; font-weight:600; color:#666;'>Batch {current_page + 1} · {start_idx + 1}–{end_idx}</div>", unsafe_allow_html=True)
        with nav_c3:
            if end_idx < total_derivs:
                if st.button("Next 25 ➡️", key="deriv_next", use_container_width=True):
                    state.set("derivative_page", current_page + 1)
                    st.rerun()
        
        chars_html = "".join([f"<span style='display:inline-block; margin: 2px 6px; font-size: 1.4em; font-weight: bold; color: #444;'>{c}</span>" for c in current_batch])
        st.markdown(f"""<div style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 12px; padding: 15px; margin-bottom: 20px; text-align: center;"><div style="font-size: 0.85em; color: #888; margin-bottom: 8px; text-transform: uppercase; font-weight: 700;">Visible in this batch</div><div style="line-height: 1.6;">{chars_html}</div></div>""", unsafe_allow_html=True)
        
        for child in current_batch:
            render_radix_row(child, minimal=True)


def render_ai_link():
    """Render the AI Link / Stroke View."""
    char = state.get("stroke_view_char")
    
    st.markdown("### Stroke Order Animation")
    main_html, _ = get_stroke_order_view_html(char, state.get_display_mode())
    st_html(main_html, height=450)
    
    # Insights
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
    
    # Phrases
    if state.get_display_mode() != "Single Character":
        if phrase_html := _render_phrase_html(char):
            st.markdown(phrase_html, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ChatGPT Prompt")
    
    # Prompt Config
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

    prompt_text = render_combined_prompt(
        char=char,
        prompt_config=state.get("prompt_config"),
        selected_task_ids=state.get("prompt_selected_task_ids"),
        definition_en=get_char_definition_en(char)
    )
    st.text_area("Copy this prompt into ChatGPT", value=prompt_text, height=320, label_visibility="collapsed")
    render_copy_to_clipboard(prompt_text, str(hash(char)))


# ==================== MAIN ====================

def main():
    if not component_map:
        st.error("Component dataset not loaded.")
        st.stop()

    # Initialize
    state.initialize()
    config.load_server_data()
    config.initialize_prompt_config()

    # Restore from URL
    persistence.try_restore()

    # Layout
    render_sidebar()
    persistence.add_heartbeat()

    # Routing
    if state.is_stroke_view_active():
        render_ai_link()
    elif state.is_definition_search_active():
        render_definition_search_results()
    elif state.is_showing_inputs():
        render_grid()
    else:
        render_lineage()
    
    # Auto-save
    persistence.auto_save()

if __name__ == "__main__":
    main()
