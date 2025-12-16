import json
import math
import streamlit as st
import streamlit.components.v1 as components

# Set page configuration
st.set_page_config(layout="wide", page_title="Radix")

# Global IDC characters
IDC_CHARS = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}


# -------------------------------
# Session bootstrap
# -------------------------------
def bootstrap_session_state():
    st.session_state.setdefault("diagnostic_messages", [])
    st.session_state.setdefault("font_scale", 1.0)
    st.session_state.setdefault("debug_info", "")
    
    # --- PERSISTENT FILTER STATE (The "Shadow" State) ---
    # These variables survive even when widgets are hidden/destroyed
    st.session_state.setdefault("filter_strokes", 0)
    st.session_state.setdefault("filter_radical", "No Filter")
    st.session_state.setdefault("filter_idc", "No Filter")
    
    # Navigation States
    st.session_state.setdefault("selected_comp", "")
    st.session_state.setdefault("page", 1)
    st.session_state.setdefault("show_inputs", True)
    st.session_state.setdefault("display_mode", "Single Character")

bootstrap_session_state()


# -------------------------------
# Dynamic CSS with font scaling
# -------------------------------
def apply_dynamic_css():
    font_scale = st.session_state.get("font_scale", 1.0)

    css = """
    <style>
        :root { --fontScale: __FONTSCALE__; }

        /* --- Detail Card Styles --- */
        .selected-card {
            background-color: #e8f4f8;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            display: flex;
            align-items: center;
            gap: 20px;
            border-left: 6px solid #3498db;
        }
        .selected-char { font-size: calc(3em * var(--fontScale)); color: #e74c3c; margin: 0; line-height: 1;}
        .details { font-size: calc(1.1em * var(--fontScale)); color: #34495e; margin: 0; line-height: 1.6; }
        .details strong { color: #2c3e50; font-weight: 600; }
        
        .results-header { font-size: calc(1.5em * var(--fontScale)); color: #2c3e50; margin: 30px 0 15px; border-bottom: 2px solid #eee; padding-bottom: 10px; }

        /* --- Sub-result Card Styles --- */
        .char-card {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            border: 1px solid #f0f0f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }
        .char-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            border-color: #e0e0e0;
        }
        .char-card button {
            font-size: calc(1.4em * var(--fontScale));
            color: #e74c3c;
            background: none;
            border: none;
            padding: 0;
            margin: 0;
            cursor: pointer;
            display: inline;
            font-weight: bold;
        }
        .char-card button:hover {
            color: #c0392b;
            text-decoration: underline;
        }

        /* --- Compounds Section --- */
        .compounds-section {
            background-color: #f9fbf7;
            padding: 12px;
            border-radius: 6px;
            margin-top: 12px;
            border: 1px solid #eef5e6;
        }
        .compounds-title { font-size: calc(0.95em * var(--fontScale)); color: #558b2f; margin: 0 0 5px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }
        .compounds-list { font-size: calc(1em * var(--fontScale)); color: #2c3e50; margin: 0; line-height: 1.5; }

        .stContainer {
            padding: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 20px;
            background: white;
        }

        /* --- Default Streamlit Button --- */
        .stButton button {
            border-radius: 6px;
            font-size: calc(1em * var(--fontScale));
            font-weight: 500;
        }

        /* --- CLEAN GRID TILES --- */
        .comp-grid .stButton button {
            background: #ffffff;
            color: #2c3e50;
            border: 1px solid #d1d9e0;
            border-radius: 8px;
            font-size: calc(1.6em * var(--fontScale));
            padding: 0px; 
            min-height: 56px;
            line-height: 1;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            transition: all 0.2s ease;
        }
        .comp-grid .stButton button:hover {
            background: #f0f7fb;
            color: #3498db;
            border-color: #3498db;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(52, 152, 219, 0.15);
            z-index: 2;
        }
        .comp-grid .stButton button:active {
            transform: translateY(0);
            box-shadow: none;
        }
        .comp-grid .stButton button[kind="primary"] {
             border: 2px solid #3498db;
             background-color: #e8f4f8;
        }

        .debug-section {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            margin-top: 20px;
            font-family: monospace;
            font-size: 0.85em;
        }
        .diagnostic-message.error { color: #c0392b; }
        .diagnostic-message.warning { color: #e67e22; }

        .stSelectbox label, .stTextInput label { font-weight: 600; color: #444; }

        @media (max-width: 768px) {
            .selected-card { flex-direction: column; align-items: flex-start; padding: 15px; }
            .selected-char { font-size: calc(2.5em * var(--fontScale)); }
            .comp-grid .stButton button { font-size: calc(1.4em * var(--fontScale)); min-height: 48px; }
        }
    </style>
    """.replace("__FONTSCALE__", str(font_scale))

    st.markdown(css, unsafe_allow_html=True)


# -------------------------------
# Load component map
# -------------------------------
@st.cache_data
def load_component_map():
    with open("enhanced_component_map_with_etymology.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

try:
    component_map = load_component_map()
except Exception as e:
    component_map = {}
    st.error(f"Failed to load data file: {e}")


# -------------------------------
# Utility functions
# -------------------------------
def clean_field(field):
    return field[0] if isinstance(field, list) and field else field or "—"

def get_stroke_count(char):
    strokes = component_map.get(char, {}).get("meta", {}).get("strokes", None)
    try:
        if isinstance(strokes, (int, float)) and strokes > 0:
            return int(strokes)
        if isinstance(strokes, str) and strokes.isdigit():
            return int(strokes)
    except (TypeError, ValueError):
        pass
    return None

def get_etymology_text(meta):
    etymology = meta.get("etymology", {})
    hint = clean_field(etymology.get("hint", "No hint available"))
    details = clean_field(etymology.get("details", ""))
    if details and details != '—':
        return f"{hint}; {details}"
    return hint

def format_decomposition(char):
    decomposition = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    if not decomposition or '?' in decomposition:
        return "—"
    return decomposition


# -------------------------------
# Callbacks (State Logic)
# -------------------------------

def sync_filters():
    """
    Called when UI widgets change. 
    Syncs the temporary 'ui_*' widget values to the persistent 'filter_*' state.
    """
    # 1. Update Strokes
    if "ui_strokes" in st.session_state:
        st.session_state.filter_strokes = st.session_state.ui_strokes
    
    # 2. Update Radical
    if "ui_radical" in st.session_state:
        st.session_state.filter_radical = st.session_state.ui_radical
        
    # 3. Update IDC
    if "ui_idc" in st.session_state:
        st.session_state.filter_idc = st.session_state.ui_idc

    # Reset page on filter change
    st.session_state.page = 1
    st.session_state.show_inputs = True

def on_reset_filters():
    """Wipes all persistent filters."""
    st.session_state.filter_strokes = 0
    st.session_state.filter_radical = "No Filter"
    st.session_state.filter_idc = "No Filter"
    
    st.session_state.page = 1
    st.session_state.text_input_warning = None
    st.session_state.text_input_comp = ""
    st.session_state.show_inputs = True
    
    # Force UI widgets to reset by deleting their keys? 
    # Not strictly necessary if we rely on the Shadow State index logic.
    
    if "last_valid_selected_comp" in st.session_state and st.session_state.last_valid_selected_comp in component_map:
        st.session_state.selected_comp = st.session_state.last_valid_selected_comp
    else:
        st.session_state.selected_comp = next(iter(component_map), '') if component_map else ''

def on_char_button_click(char):
    """Selects a char and hides the grid."""
    if char and char in component_map:
        st.session_state.previous_selected_comp = st.session_state.get("selected_comp", "")
        st.session_state.selected_comp = char
        st.session_state.last_valid_selected_comp = char
        
        st.session_state.text_input_warning = None
        st.session_state.text_input_comp = char
        st.session_state.show_inputs = False # Switch to Detail View

def on_back_to_search():
    """Shows the grid. Persistent filters remain untouched."""
    st.session_state.show_inputs = True

def process_text_input(component_map_arg):
    val = st.session_state.text_input_comp.strip()
    if val and len(val) == 1 and val in component_map_arg:
        on_char_button_click(val)
    elif val:
        st.session_state.text_input_warning = "Please enter exactly one valid character."


# -------------------------------
# Controls (Filters & Grid)
# -------------------------------
def render_controls(component_map_arg):
    idc_descriptions = {
        "No Filter": "No Filter", "⿰": "Left Right", "⿱": "Top Bottom", 
        "⿲": "Left Middle Right", "⿳": "Top Middle Bottom", "⿴": "Surround", 
        "⿵": "Surround Top", "⿶": "Surround Bottom", "⿷": "Surround Left", 
        "⿸": "Top Left Corner", "⿹": "Top Right Corner", "⿺": "Bottom Left Corner", 
        "⿻": "Overlaid"
    }

    # 1. Filtering Logic (Uses PERSISTENT state)
    filtered_components = [
        comp for comp in component_map_arg
        if isinstance(comp, str) and len(comp) == 1 and
        (st.session_state.filter_strokes == 0 or get_stroke_count(comp) == st.session_state.filter_strokes) and
        (st.session_state.filter_radical == "No Filter" or component_map_arg.get(comp, {}).get("meta", {}).get("radical", "") == st.session_state.filter_radical) and
        (st.session_state.filter_idc == "No Filter" or component_map_arg.get(comp, {}).get("meta", {}).get("decomposition", "").startswith(st.session_state.filter_idc))
    ]
    
    sorted_components = sorted(filtered_components, key=lambda c: get_stroke_count(c) or 0)

    # 2. Render Loop
    if st.session_state.show_inputs:
        # --- VIEW A: SEARCH GRID ---
        with st.container():
            st.markdown("### Component Filters")
            col1, col2, col3 = st.columns([0.33, 0.33, 0.34])

            with col1:
                # STROKES
                all_strokes_raw = sorted(set(
                    sc for sc in (get_stroke_count(comp) for comp in component_map_arg)
                    if isinstance(sc, int) and sc > 0
                ))
                stroke_options = [0] + all_strokes_raw
                
                # Determine Index from Persistent State
                try:
                    s_idx = stroke_options.index(st.session_state.filter_strokes)
                except ValueError:
                    s_idx = 0
                
                st.selectbox(
                    "Filter by Strokes:",
                    options=stroke_options,
                    index=s_idx, # Force index
                    key="ui_strokes", # Temporary UI key
                    format_func=lambda x: "No Filter" if x == 0 else str(x),
                    on_change=sync_filters
                )

            with col2:
                # RADICAL
                pre_filtered = [c for c in component_map_arg 
                                if (st.session_state.filter_strokes == 0 or get_stroke_count(c) == st.session_state.filter_strokes)]
                radicals = {"No Filter"} | {
                    component_map_arg.get(c, {}).get("meta", {}).get("radical", "") for c in pre_filtered
                }
                rad_options = ["No Filter"] + sorted([r for r in radicals if r and r != "No Filter"])
                
                # Validate Persistent State against new Options
                current_rad = st.session_state.filter_radical
                if current_rad not in rad_options:
                    current_rad = "No Filter"
                    # We implicitly update persistent state if it's invalid for the current view
                    st.session_state.filter_radical = "No Filter"
                    
                st.selectbox(
                    "Filter by Radical:",
                    options=rad_options,
                    index=rad_options.index(current_rad),
                    key="ui_radical", # Temporary UI key
                    on_change=sync_filters
                )

            with col3:
                # IDC (Structure)
                idc_options = ["No Filter"] + sorted([k for k in idc_descriptions if k in IDC_CHARS])
                
                try:
                    idc_idx = idc_options.index(st.session_state.filter_idc)
                except ValueError:
                    idc_idx = 0

                st.selectbox(
                    "Filter by Structure:",
                    options=idc_options,
                    index=idc_idx,
                    key="ui_idc", # Temporary UI key
                    format_func=lambda x: f"{x} {idc_descriptions.get(x,'')}" if x != "No Filter" else x,
                    on_change=sync_filters
                )

        with st.container():
            st.markdown("### Select Character")
            
            if not sorted_components:
                st.warning("No characters match your filters.")
            else:
                # Pagination
                PAGE_SIZE = 96
                GRID_COLS = 12
                total = len(sorted_components)
                max_page = max(1, math.ceil(total / PAGE_SIZE))
                st.session_state.page = max(1, min(st.session_state.page, max_page))

                c_prev, c_info, c_next = st.columns([1, 4, 1])
                with c_prev:
                    if st.button("◀ Prev", disabled=(st.session_state.page <= 1)):
                        st.session_state.page -= 1
                        st.rerun()
                with c_info:
                    start_i = (st.session_state.page - 1) * PAGE_SIZE + 1
                    end_i = min(st.session_state.page * PAGE_SIZE, total)
                    st.markdown(f"<div style='text-align:center; padding-top:5px; color:#666;'>Showing {start_i}–{end_i} of {total}</div>", unsafe_allow_html=True)
                with c_next:
                    if st.button("Next ▶", disabled=(st.session_state.page >= max_page)):
                        st.session_state.page += 1
                        st.rerun()

                # Render Grid
                start = (st.session_state.page - 1) * PAGE_SIZE
                end = min(start + PAGE_SIZE, total)
                page_components = sorted_components[start:end]

                st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
                cols = st.columns(GRID_COLS)
                for i, ch in enumerate(page_components):
                    with cols[i % GRID_COLS]:
                        is_active = (ch == st.session_state.selected_comp)
                        st.button(
                            ch,
                            key=f"btn_{ch}_{i}",
                            use_container_width=True,
                            type="primary" if is_active else "secondary",
                            on_click=on_char_button_click,
                            args=(ch,)
                        )
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Text Input fallback
            st.text_input("Or type a character directly:", key="text_input_comp", on_change=process_text_input, args=(component_map_arg,))
            if st.session_state.text_input_warning:
                st.warning(st.session_state.text_input_warning)

    else:
        # --- VIEW B: DETAILS / ACTIONS ---
        # Show Navigation Buttons
        with st.container():
            c_back, c_spacer, c_reset = st.columns([0.2, 0.6, 0.2])
            with c_back:
                st.button("⬅ Back to Search", on_click=on_back_to_search, type="primary", use_container_width=True)
            with c_reset:
                st.button("Reset All Filters", on_click=on_reset_filters, use_container_width=True)

        # Show Display Mode Selector
        st.radio(
            "Display Mode:",
            ["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"],
            key="display_mode",
            horizontal=True,
        )


# -------------------------------
# Render Character Card
# -------------------------------
def render_char_card(char, compounds):
    meta = component_map.get(char, {}).get("meta", {})
    
    fields = [
        ("Pinyin", clean_field(meta.get("pinyin", "—"))),
        ("Strokes", str(get_stroke_count(char) or "?")),
        ("Radical", clean_field(meta.get("radical", "—"))),
        ("Structure", format_decomposition(char)),
        ("Definition", clean_field(meta.get("definition", "—"))),
        ("Etymology", get_etymology_text(meta))
    ]
    
    details_html = " | ".join(f"<strong>{k}:</strong> {v}" for k, v in fields if v != "—")
    
    st.markdown(f"""
    <div class='char-card'>
        <div style='display:flex; align-items:center; gap:10px;'>
            <h3 style='margin:0; color:#e74c3c; font-size:1.5em;'>{char}</h3>
            <span style='color:#7f8c8d;'>{details_html}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if compounds and st.session_state.display_mode != "Single Character":
        compounds_text = "   ".join(sorted(compounds))
        st.markdown(f"""
        <div class='compounds-section'>
            <div class='compounds-list'>{compounds_text}</div>
        </div>
        """, unsafe_allow_html=True)


# -------------------------------
# Main Application
# -------------------------------
def main():
    if not component_map:
        return

    apply_dynamic_css()
    st.markdown("## 🈑 Radix Explorer")

    # 1. Render Controls (and Grid if show_inputs is True)
    render_controls(component_map)

    # 2. Render Details (Only if a character is selected AND we are not in grid view)
    if not st.session_state.show_inputs and st.session_state.selected_comp:
        
        target_char = st.session_state.selected_comp
        meta = component_map.get(target_char, {}).get("meta", {})
        
        # --- Main Selected Card ---
        st.markdown(f"""
        <div class='selected-card'>
            <div class='selected-char'>{target_char}</div>
            <div class='details'>
                <strong>Pinyin:</strong> {clean_field(meta.get("pinyin", "—"))}<br>
                <strong>Meaning:</strong> {clean_field(meta.get("definition", "—"))}<br>
                <strong>Decomposition:</strong> {format_decomposition(target_char)}<br>
                <strong>Etymology:</strong> {get_etymology_text(meta)}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- Related Results ---
        related = component_map.get(target_char, {}).get("related_characters", [])
        filtered_chars = [c for c in related if isinstance(c, str) and len(c) == 1]
        
        if not filtered_chars:
            filtered_chars = [target_char]
            
        st.markdown(f"<div class='results-header'>Found {len(filtered_chars)} Related Characters</div>", unsafe_allow_html=True)
        
        # Prepare compounds map
        char_compounds = {}
        target_len = int(st.session_state.display_mode[0]) if st.session_state.display_mode[0].isdigit() else 1
        
        for c in filtered_chars:
            all_comps = component_map.get(c, {}).get("meta", {}).get("compounds", [])
            valid_comps = [x for x in all_comps if len(x) == target_len]
            if target_len == 1 or valid_comps:
                char_compounds[c] = valid_comps

        # Render list
        valid_display_chars = [c for c in filtered_chars if c in char_compounds]
        
        for char in sorted(valid_display_chars, key=lambda c: get_stroke_count(c) or 0):
            render_char_card(char, char_compounds[char])

        # --- Export Tool ---
        if st.session_state.display_mode != "Single Character" and valid_display_chars:
            with st.expander("📂 Export Compounds to Word/Text"):
                text_out = ""
                for c in valid_display_chars:
                    if char_compounds[c]:
                        text_out += f"--- {c} ---\n" + "\n".join(char_compounds[c]) + "\n"
                st.text_area("Copy content:", text_out, height=150)

    # Debug footer (Optional)
    # with st.expander("Debug Info", expanded=False):
    #     st.write(f"Persistent Filter Strokes: {st.session_state.filter_strokes}")
    #     st.write(f"Persistent Filter Radical: {st.session_state.filter_radical}")

if __name__ == "__main__":
    main()
