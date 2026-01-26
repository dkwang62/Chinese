# app.py
# Main Streamlit app for Radix - Streamlined Edition (3 Tabs)

import streamlit as st
from streamlit.components.v1 import html as st_html
import math
import html as pyhtml
import uuid
import re
import unicodedata  # Required for fuzzy pinyin normalization
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


# Configure Streamlit
st.set_page_config(**PAGE_CONFIG)
apply_styles()

# Initialize managers
state = StateManager()
config = ConfigManager(state)
persistence = PersistenceManager(state)


# ==================== HELPERS ====================

def normalize_pinyin(pinyin_str):
    """
    Remove tone marks from pinyin for fuzzy search (e.g., 'nǐ' -> 'ni').
    Robust against None, non-strings, or other data types.
    """
    if not isinstance(pinyin_str, str):
        return ""
    # Decompose unicode characters and strip combining diacritical marks
    return ''.join(c for c in unicodedata.normalize('NFD', pinyin_str) if unicodedata.category(c) != 'Mn').lower()


# ==================== CALLBACKS ====================

def tile_click(c):
    """Handle click on a grid tile."""
    if state.is_showing_inputs() and state.get_preview_component() == c:
        state.enter_character_view(c)
    else:
        state.set("preview_comp", c)

def list_tile_click(c):
    """Handle click on a list/lineage tile."""
    if state.get_preview_component() == c:
        if state.get_selected_component():
            history = state.get_history()
            history.append(state.get_selected_component())
            state.set("history", history)
        state.enter_character_view(c)
    else:
        state.set("preview_comp", c)

def toggle_favourite(char):
    """Toggle favourite status via checkbox."""
    if state.get(f"fav_chk_{char}", False):
        state.add_to_favourites(char)
    else:
        state.remove_from_favourites(char)

def search_by_definition():
    """Execute search for English definitions (Legacy/Sidebar version)."""
    query = state.get("sidebar_def_search", "").strip()
    is_valid, error_msg = InputValidator.validate_definition_search(query)
    
    if not is_valid:
        st.toast(error_msg)
        return
    
    # 1. Search Characters
    char_results = []
    query_lower = query.lower()
    for char, info in component_map.items():
        definition = info.get("meta", {}).get("definition", "")
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

def execute_smart_search():
    """Execute Smart Search with pinyin and English meaning matches."""
    query = state.get("smart_search_input", "").strip()
    
    if not query:
        st.toast("Please enter a search term")
        return
    
    is_valid, error_msg = InputValidator.validate_definition_search(query)
    if not is_valid:
        st.toast(error_msg)
        return
    
    # Normalize query for pinyin matching
    query_lower = query.lower()
    query_normalized_pinyin = normalize_pinyin(query)
    
    # 1. Search Characters - separate pinyin and English matches
    char_pinyin_matches = []
    char_english_matches = []
    
    for char, info in component_map.items():
        meta = info.get("meta", {})
        pinyin = meta.get("pinyin", "")
        definition = meta.get("definition", "")
        
        # Check pinyin match
        if isinstance(pinyin, str):
            normalized_char_pinyin = normalize_pinyin(pinyin)
            if query_normalized_pinyin in normalized_char_pinyin or query_lower in pinyin.lower():
                char_pinyin_matches.append(char)
                continue
        
        # Check English definition match
        if isinstance(definition, str) and query_lower in definition.lower():
            char_english_matches.append(char)
    
    # 2. Search Phrases - separate pinyin and English matches
    db_conn = get_db_connection()
    phrase_pinyin_matches = []
    phrase_english_matches = []
    
    if db_conn:
        # Get all phrase results from definition search
        all_phrase_results = search_phrases_by_definition(query, db_conn, limit=400) or []
        
        # Categorize phrases
        for phrase_data in all_phrase_results:
            phrase_pinyin = phrase_data.get('pinyin', '')
            phrase_meanings = phrase_data.get('meanings', '')
            
            # Check if it's a pinyin match
            if isinstance(phrase_pinyin, str):
                normalized_phrase_pinyin = normalize_pinyin(phrase_pinyin)
                if query_normalized_pinyin in normalized_phrase_pinyin or query_lower in phrase_pinyin.lower():
                    phrase_pinyin_matches.append(phrase_data)
                    continue
            
            # Otherwise it's an English match
            phrase_english_matches.append(phrase_data)
    
    # 3. Combine results: Pinyin matches first, then English matches
    combined_char_results = char_pinyin_matches[:60] + char_english_matches[:60]
    combined_phrase_results = phrase_pinyin_matches[:100] + phrase_english_matches[:100]
    
    # 4. Update State
    state.update(
        definition_search_mode=True,
        definition_search_query=query,
        definition_search_results={
            "characters": combined_char_results[:120], 
            "phrases": combined_phrase_results[:200]
        },
        show_inputs=False,
        selected_comp="",
        preview_comp=None
    )

def execute_smart_search_sidebar():
    """Execute Smart Search from sidebar with pinyin and English meaning matches."""
    query = state.get("sidebar_smart_search_input", "").strip()
    
    if not query:
        st.toast("Please enter a search term")
        return
    
    is_valid, error_msg = InputValidator.validate_definition_search(query)
    if not is_valid:
        st.toast(error_msg)
        return
    
    # Normalize query for pinyin matching
    query_lower = query.lower()
    query_normalized_pinyin = normalize_pinyin(query)
    
    # 1. Search Characters - separate pinyin and English matches
    char_pinyin_matches = []
    char_english_matches = []
    
    for char, info in component_map.items():
        meta = info.get("meta", {})
        pinyin = meta.get("pinyin", "")
        definition = meta.get("definition", "")
        
        # Check pinyin match
        if isinstance(pinyin, str):
            normalized_char_pinyin = normalize_pinyin(pinyin)
            if query_normalized_pinyin in normalized_char_pinyin or query_lower in pinyin.lower():
                char_pinyin_matches.append(char)
                continue
        
        # Check English definition match
        if isinstance(definition, str) and query_lower in definition.lower():
            char_english_matches.append(char)
    
    # 2. Search Phrases - separate pinyin and English matches
    db_conn = get_db_connection()
    phrase_pinyin_matches = []
    phrase_english_matches = []
    
    if db_conn:
        # Get all phrase results from definition search
        all_phrase_results = search_phrases_by_definition(query, db_conn, limit=400) or []
        
        # Categorize phrases
        for phrase_data in all_phrase_results:
            phrase_pinyin = phrase_data.get('pinyin', '')
            phrase_meanings = phrase_data.get('meanings', '')
            
            # Check if it's a pinyin match
            if isinstance(phrase_pinyin, str):
                normalized_phrase_pinyin = normalize_pinyin(phrase_pinyin)
                if query_normalized_pinyin in normalized_phrase_pinyin or query_lower in phrase_pinyin.lower():
                    phrase_pinyin_matches.append(phrase_data)
                    continue
            
            # Otherwise it's an English match
            phrase_english_matches.append(phrase_data)
    
    # 3. Combine results: Pinyin matches first, then English matches
    combined_char_results = char_pinyin_matches[:60] + char_english_matches[:60]
    combined_phrase_results = phrase_pinyin_matches[:100] + phrase_english_matches[:100]
    
    # 4. Update State
    state.update(
        definition_search_mode=True,
        definition_search_query=query,
        definition_search_results={
            "characters": combined_char_results[:120], 
            "phrases": combined_phrase_results[:200]
        },
        show_inputs=False,
        selected_comp="",
        preview_comp=None
    )


# ==================== HTML HELPERS ====================

def _render_phrase_html(c: str) -> str:
    """Render phrases containing the character."""
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
        items_html_list = []
        for word in sorted(compounds):
            entry = phrases.get(word)
            if entry:
                p_mean = pyhtml.escape(entry.get('meanings', '')[:130] + ('...' if len(entry.get('meanings', '')) > 130 else ''))
                items_html_list.append(f"<div style='display:flex; align-items:baseline; padding:5px 8px; border-bottom:1px solid #eee;'><span style='font-weight:700; font-size:1.0rem; min-width:65px;'>{word}</span><span style='color:#d35400; font-size:0.85rem; font-family:monospace; margin-right:12px; font-weight:600;'>{entry.get('pinyin', '')}</span><span style='color:#444; font-size:0.85rem; flex:1; line-height:1.2;'>{p_mean}</span></div>")
        
        if items_html_list:
            return f"<div style='padding:12px; background:#f1f8e9; border-radius:8px; margin-top:10px; border:1px solid #dcedc8; max-height:400px; overflow-y:auto;'><div style='font-weight:bold; font-size:0.8rem; margin-bottom:8px; color:#2e7d32; text-transform:uppercase;'>{state.get_display_mode()} containing {c}</div>{''.join(items_html_list)}</div>"
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
                on_click=list_tile_click,
                args=(c,),
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
                horizontal=True,
                label_visibility="collapsed",
                on_change=update_phrase_len
            )

            if html := _render_phrase_html(c):
                st.markdown(html, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)


# ==================== VIEW RENDERERS ====================

def render_sidebar():
    """Render the sidebar with 3 tabs: Filter, Favourites, Smart Search."""
    with st.sidebar:
        st.title("🧠 Radix")
        st.caption("_Chinese Decomposition Toolkit_")
        
        # Create 3 tabs
        tab_filter, tab_favourites, tab_smart_search = st.tabs(["Filter", "Favourites", "Smart Search"])
        
        # TAB 1: FILTER
        with tab_filter:
            st.caption("Filter controls are available in the main grid view when you return to the grid.")
            
            if not state.is_showing_inputs():
                if st.button("↩️ Return to Grid", use_container_width=True, key="filter_return_grid"):
                    state.return_to_inputs()
                    st.rerun()
        
        # TAB 2: FAVOURITES
        with tab_favourites:
            st.markdown("**⭐ Favourites**")
            current_favs = state.get_favourites()
            
            if current_favs:
                fav_display_list = current_favs[::-1]
                fav_cols = st.columns(8)
                for idx, fchar in enumerate(fav_display_list):
                    col_idx = idx % 8
                    with fav_cols[col_idx]:
                        if st.button(fchar, key=f"fav_sb_{fchar}", help=f"View {fchar}", use_container_width=True):
                            state.enter_character_view(fchar)
                            st.rerun()
            else:
                st.caption("No favourites yet. Click ⭐ to add.")
            
            st.markdown("---")
            st.markdown("**📥 Export Favourites**")
            if current_favs:
                dl_html = render_ipad_safe_download_html(current_favs, filename="favourites.txt")
                st.markdown(dl_html, unsafe_allow_html=True)
            else:
                st.caption("Add favourites first.")
        
        # TAB 3: SMART SEARCH
        with tab_smart_search:
            # Instructions in blue info box
            st.info("💡 Enter pinyin (e.g., 'ni') or English meaning (e.g., 'water'). Results show pinyin matches first, then English matches.")
            
            st.text_input("Search...", key="sidebar_smart_search_input", placeholder="e.g., ni or water")
            if st.button("Search", use_container_width=True, key="sidebar_smart_search_btn"):
                execute_smart_search_sidebar()
        
        # Navigation section (outside tabs)
        st.markdown("---")
        st.markdown("**Navigation**")
        
        if not state.is_showing_inputs() and state.get_selected_component():
            if st.button("↩️ Return to Grid", use_container_width=True):
                state.return_to_inputs()
                st.rerun()
        
        if state.is_definition_search_active():
            if st.button("↩️ Return to Grid", use_container_width=True, key="def_search_return"):
                state.return_to_inputs()
                st.rerun()
        
        history_items = state.get_history()
        if history_items:
            st.markdown("**Recent**")
            for h_idx, h_char in enumerate(history_items[::-1][:6]):
                if st.button(h_char, key=f"hst_{h_idx}_{h_char}", help=f"Return to {h_char}", use_container_width=True):
                    state.enter_character_view(h_char)
                    st.rerun()

def render_grid():
    """Render the main grid view with 3 Tabs."""
    # Changed from 2 tabs to 3
    tab1, tab2, tab3 = st.tabs(["📊 Filter", "⭐ Favourites", "🔍 Smart Search"])
    
    with tab1:
        render_all_components_grid()
    
    with tab2:
        render_favourites_grid()

    with tab3:
        render_smart_search()

def render_smart_search():
    """Render the combined Fuzzy Pinyin + Meaning search tab."""
    st.markdown("<div style='background: #e3f2fd; padding: 20px; border-radius: 10px; margin-bottom: 25px; border: 1px solid #bbdefb;'>", unsafe_allow_html=True)
    st.markdown("### 🔍 Smart Search")
    st.markdown("Search by **Fuzzy Pinyin** (e.g., 'jiong' finds 'jiǒng') OR **English Meaning** (e.g., 'fire').")
    
    query = st.text_input("Enter Pinyin or Meaning", key="smart_search_input", placeholder="e.g. ma, ni, horse, water")
    st.markdown("</div>", unsafe_allow_html=True)

    if query:
        query = query.strip()
        if len(query) < 2:
            st.warning("Please enter at least 2 characters.")
            return

        results = []
        # Normalize the query for pinyin comparison (e.g. "jiong")
        query_norm = normalize_pinyin(query)
        query_lower = query.lower()

        # Iterate through all components
        for char, info in component_map.items():
            meta = info.get("meta", {})
            
            # 1. Pinyin Match (Fuzzy)
            # 'pinyin' in meta can be a list ["kān"] or string "kān"
            pinyin_data = meta.get("pinyin", [])
            pinyin_match = False
            
            if isinstance(pinyin_data, list):
                # Check if ANY pronunciation matches
                for p in pinyin_data:
                    if normalize_pinyin(p) == query_norm:
                        pinyin_match = True
                        break
            elif isinstance(pinyin_data, str):
                if normalize_pinyin(pinyin_data) == query_norm:
                    pinyin_match = True
            
            if pinyin_match:
                results.append(char)
                continue # Matched pinyin, skip checking definition to avoid duplicates in list

            # 2. Definition Match (English)
            definition = meta.get("definition", "")
            if isinstance(definition, str) and query_lower in definition.lower():
                results.append(char)
                continue

        # Display Results
        if not results:
            st.info(f"No matches found for '{query}'.")
        else:
            st.success(f"Found {len(results)} matches.")
            st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
            
            # Pagination for search results if too many (limit to first 100 for speed)
            display_results = results[:100]
            
            cols = st.columns(GRID_COLUMNS)
            for i, ch in enumerate(display_results):
                with cols[i % GRID_COLUMNS]:
                    st.button(ch, key=f"smart_res_{ch}_{i}", type="primary" if state.get_preview_component() == ch else "secondary", on_click=tile_click, args=(ch,), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            if len(results) > 100:
                st.caption(f"Showing first 100 of {len(results)} results.")

def render_all_components_grid():
    st.markdown("<div style='background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>", unsafe_allow_html=True)
    
    # Row 1: Sort and Script
    col_sort, col_script = st.columns([1, 1])
    with col_sort:
        sort_choice = st.radio("Sort by", options=["Component frequency", "Character frequency"], index=0 if state.get_grid_sort_mode() == "usage" else 1, horizontal=True, key="grid_sort_radio")
        state.set("grid_sort_mode", "usage" if "Component" in sort_choice else "frequency")
    
    with col_script:
        if state.get_grid_sort_mode() == "frequency":
            gsf = state.get("grid_script_filter", "Any")
            script_choice = st.radio("Script", options=["Simplified", "Traditional", "Any"], index=["Simplified", "Traditional", "Any"].index(gsf), horizontal=True, key="grid_script_radio")
            state.set("grid_script_filter", script_choice)
    
    # Row 2: Filters
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
            if rad == "none": return "none"
            rad_info = component_map.get(rad, {})
            strokes = rad_info.get('stroke_count')
            if strokes: return f"{rad} ({strokes} strokes)"
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

    # Filter Logic
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

    # Pagination
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
        st.markdown(f"<div style='text-align:center; padding:10px 0; color:#555;'><div style='font-size:1.1em; font-weight:bold;'>{(page - 1) * PAGE_SIZE + 1}–{min(page * PAGE_SIZE, total)} of {total}</div></div>", unsafe_allow_html=True)
    with p3:
        if st.button("Next ▶", disabled=page >= max_page, use_container_width=True, key="grid_next"):
            state.set("page", page + 1)
            st.rerun()

    # Tiles
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

def render_definition_search_results():
    """Render the results of an English definition search (Legacy Sidebar)."""
    results = state.get("definition_search_results")
    if not results:
        st.error("No results state found.")
        return

    st.markdown(f"<div style='font-size:1.2em; font-weight:700; margin-bottom:20px;'>Search Results for \"{pyhtml.escape(state.get('definition_search_query'))}\"</div><div style='font-size:0.85em; color:#666; margin-bottom:20px;'>Found {len(results['characters'])} characters and {len(results['phrases'])} phrases</div>", unsafe_allow_html=True)
    
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
    decomp = info.get("meta", {}).get("decomposition", "")
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
    for f in apply_script_filter(focus_group, state.get_script_filter()):
        render_radix_row(f)

    # Children
    rel = info.get("related_characters", [])
    children = [c for c in rel if isinstance(c, str) and len(c) == 1 and c in component_map and c != sel]

    if children:
        visible_children = apply_script_filter(sorted(children, key=sort_key_usage_primary), state.get_script_filter())
        unique_visible = list(dict.fromkeys(visible_children))
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
