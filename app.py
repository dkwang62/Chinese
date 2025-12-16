import json
import math
import streamlit as st
import streamlit.components.v1 as components

# Set page configuration
st.set_page_config(layout="wide")

# Global IDC characters
IDC_CHARS = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}


# -------------------------------
# Session bootstrap (needed early)
# -------------------------------
def bootstrap_session_state():
    st.session_state.setdefault("diagnostic_messages", [])
    st.session_state.setdefault("font_scale", 1.0)
    st.session_state.setdefault("debug_info", "")

bootstrap_session_state()


# -------------------------------
# Dynamic CSS with font scaling + hide controls
# -------------------------------
def apply_dynamic_css():
    font_scale = st.session_state.get("font_scale", 1.0)
    hide_controls = "display: none;" if not st.session_state.get("show_inputs", True) else ""

    css = f"""
    <style>
        :root {{ --fontScale: __FONTSCALE__; }}

        .selected-card {{
            background-color: #e8f4f8;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            gap: 15px;
            border-left: 5px solid #3498db;
        }}

        .selected-char {{ font-size: calc(2.5em * var(--fontScale)); color: #e74c3c; margin: 0; }}
        .details {{ font-size: calc(1.5em * var(--fontScale)); color: #34495e; margin: 0; }}
        .details strong {{ color: #2c3e50; }}
        .results-header {{ font-size: calc(1.5em * var(--fontScale)); color: #2c3e50; margin: 20px 0 10px; }}

        .char-card {{
            background-color: #ffffff;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .char-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 3px 8px rgba(0,0,0,0.15);
        }}

        .compounds-section {{
            background-color: #f1f8e9;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }}
        .compounds-title {{ font-size: calc(1.1em * var(--fontScale)); color: #558b2f; margin: 0 0 5px; }}
        .compounds-list {{ font-size: calc(1em * var(--fontScale)); color: #34495e; margin: 0; }}

        /* Default Streamlit button styling */
        .stButton button {{
            background-color: #3498db;
            color: white;
            border-radius: 5px;
            font-size: calc(0.9em * var(--fontScale));
        }}
        .stButton button:hover {{
            background-color: #2980b9;
        }}

        /* Character grid tile overrides */
        .comp-grid .stButton button {{
            background: #ffffff;
            color: #e74c3c;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            font-size: calc(1.25em * var(--fontScale));
            padding: 0.55rem 0.25rem;
            line-height: 1;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        .comp-grid .stButton button:hover {{
            background: #fff5f5;
            color: #c0392b;
            border-color: #f2c6c6;
            box-shadow: 0 3px 8px rgba(0,0,0,0.12);
        }}

        .debug-section {{
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            margin-top: 20px;
        }}
        .diagnostic-message.error {{ color: #c0392b; }}
        .diagnostic-message.warning {{ color: #e67e22; }}

        .stSelectbox, .stTextInput, .stRadio, .stSlider {{
            font-size: calc(0.9em * var(--fontScale));
        }}

        /* Hide controls when component is selected */
        .controls-section {{ {hide_controls} }}

        @media (max-width: 768px) {{
            .selected-card {{ flex-direction: column; align-items: flex-start; padding: 10px; }}
            .selected-char {{ font-size: calc(2em * var(--fontScale)); }}
            .details, .compounds-list {{ font-size: calc(0.95em * var(--fontScale)); line-height: 1.5; }}
            .results-header {{ font-size: calc(1.3em * var(--fontScale)); }}
            .char-card {{ padding: 10px; }}
            .comp-grid .stButton button {{ font-size: calc(1.15em * var(--fontScale)); }}
        }}
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
    error_msg = f"Failed to load enhanced_component_map_with_etymology.json: {e}"
    st.error(error_msg)
    st.session_state.diagnostic_messages.append({"type": "error", "message": error_msg})


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
    return f"{hint}{'; Details: ' + details if details and details != '—' else ''}"

def format_decomposition(char):
    decomposition = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    if not decomposition or '?' in decomposition:
        return "—"
    return decomposition

def get_all_components(char, max_depth, depth=0, seen=None):
    if seen is None:
        seen = set()
    if char in seen or depth > max_depth or not isinstance(char, str) or len(char) != 1:
        return set()
    seen.add(char)

    components_set = set()
    decomposition = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    if decomposition:
        for comp in decomposition:
            if comp in IDC_CHARS or comp == '?' or not isinstance(comp, str) or len(comp) != 1:
                continue
            components_set.add(comp)
            components_set.update(get_all_components(comp, max_depth, depth + 1, seen.copy()))
    return components_set


# -------------------------------
# Session state initialization
# -------------------------------
def init_session_state():
    defaults = {
        "selected_comp": "",
        "stroke_count": 0,
        "radical": "No Filter",
        "display_mode": "Single Character",
        "selected_idc": "No Filter",
        "component_idc": "No Filter",
        "output_radical": "No Filter",
        "text_input_comp": "",
        "page": 1,
        "previous_selected_comp": "",
        "text_input_warning": None,
        "debug_info": st.session_state.get("debug_info", ""),
        "last_processed_input": "",
        "diagnostic_messages": st.session_state.get("diagnostic_messages", []),
        "font_scale": st.session_state.get("font_scale", 1.0),
        "show_inputs": True,
        "last_valid_selected_comp": "",
        "preview_comp": None,
        "preview_active": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    # Clean invalid decomposition markers
    for char, entry in component_map.items():
        decomposition = entry.get("meta", {}).get("decomposition", "")
        if isinstance(decomposition, str) and '?' in decomposition:
            st.session_state.diagnostic_messages.append({
                "type": "warning",
                "message": f"Invalid component '?' in decomposition for {char}: {decomposition}"
            })
            entry["meta"]["decomposition"] = ""

    # Default selected_comp
    if not st.session_state.selected_comp or st.session_state.selected_comp not in component_map:
        st.session_state.selected_comp = next(iter(component_map), '') if component_map else ''
        st.session_state.last_valid_selected_comp = st.session_state.selected_comp

init_session_state()


# -------------------------------
# Preview card renderer
# -------------------------------
def render_preview_card(c: str) -> None:
    meta = component_map.get(c, {}).get("meta", {})
    fields = {
        "Pinyin": clean_field(meta.get("pinyin", "—")),
        "Strokes": f"{get_stroke_count(c)} strokes" if get_stroke_count(c) is not None else "unknown strokes",
        "Radical": clean_field(meta.get("radical", "—")),
        "Decomposition": format_decomposition(c),
        "Definition": clean_field(meta.get("definition", "No definition available")),
        "Etymology": get_etymology_text(meta),
    }
    details = " ".join(f"<strong>{k}:</strong> {v}" for k, v in fields.items())

    st.markdown(
        f"""
        <div class="selected-card">
          <h2 class="selected-char">{c}</h2>
          <p class="details">{details}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Click the same character again to select. Click a different character to preview it.")


# -------------------------------
# Callbacks
# -------------------------------
def process_text_input(component_map_arg):
    text_value = st.session_state.text_input_comp.strip()

    if text_value == st.session_state.get("last_processed_input"):
        return

    if len(text_value) != 1:
        st.session_state.text_input_warning = "Please enter exactly one character."
        st.session_state.text_input_comp = ""
        st.session_state.last_processed_input = text_value
        return

    if text_value in component_map_arg:
        st.session_state.previous_selected_comp = st.session_state.get("selected_comp", "")
        st.session_state.selected_comp = text_value
        st.session_state.last_valid_selected_comp = text_value
        st.session_state.text_input_comp = text_value
        st.session_state.text_input_warning = None
        st.session_state.show_inputs = False
        st.session_state.preview_active = False
        st.session_state.preview_comp = None
        st.session_state.last_processed_input = text_value
    else:
        st.session_state.text_input_warning = "Invalid character. Please enter a valid component."
        st.session_state.text_input_comp = ""
        st.session_state.last_processed_input = text_value

def on_filter_change():
    st.session_state.page = 1

def on_display_mode_change():
    if st.session_state.get("selected_comp", "") in component_map:
        st.session_state.last_valid_selected_comp = st.session_state.selected_comp

def on_reset_filters():
    st.session_state.stroke_count = 0
    st.session_state.radical = "No Filter"
    st.session_state.component_idc = "No Filter"
    st.session_state.selected_idc = "No Filter"
    st.session_state.output_radical = "No Filter"
    st.session_state.display_mode = "Single Character"
    st.session_state.page = 1
    st.session_state.text_input_warning = None
    st.session_state.text_input_comp = ""
    st.session_state.show_inputs = True
    st.session_state.preview_active = False
    st.session_state.preview_comp = None

    if st.session_state.last_valid_selected_comp in component_map:
        st.session_state.selected_comp = st.session_state.last_valid_selected_comp
    else:
        st.session_state.selected_comp = next(iter(component_map), '') if component_map else ''
        st.session_state.last_valid_selected_comp = st.session_state.selected_comp

def on_component_tile_click(c: str) -> None:
    if st.session_state.get("preview_active") and st.session_state.get("preview_comp") == c:
        # SELECT
        st.session_state.previous_selected_comp = st.session_state.get("selected_comp", "")
        st.session_state.selected_comp = c
        st.session_state.last_valid_selected_comp = c
        st.session_state.text_input_comp = c
        st.session_state.text_input_warning = None
        st.session_state.show_inputs = False
        st.session_state.preview_active = False
        st.session_state.preview_comp = None
    else:
        # PREVIEW
        st.session_state.preview_active = True
        st.session_state.preview_comp = c

def back_to_selection() -> None:
    st.session_state.show_inputs = True
    st.session_state.preview_active = False
    st.session_state.preview_comp = None


# -------------------------------
# Controls (filters + grid selector)
# -------------------------------
def render_controls(component_map_arg):
    idc_descriptions = {
        "No Filter": "No Filter",
        "⿰": "Left Right",
        "⿱": "Top Bottom",
        "⿲": "Left Middle Right",
        "⿳": "Top Middle Bottom",
        "⿴": "Surround",
        "⿵": "Surround Top",
        "⿶": "Surround Bottom",
        "⿷": "Surround Left",
        "⿸": "Top Left Corner",
        "⿹": "Top Right Corner",
        "⿺": "Bottom Left Corner",
        "⿻": "Overlaid"
    }

    # Always render filters (with keys) but hide via CSS when not needed
    with st.container(css_class="controls-section"):
        st.markdown("### Component Filters")
        st.caption("Filter components by stroke count, radical, or structure.")
        col1, col2, col3 = st.columns([0.4, 0.4, 0.4])

        with col1:
            stroke_counts = sorted(set(
                sc for sc in (get_stroke_count(comp) for comp in component_map_arg if isinstance(comp, str) and len(comp) == 1)
                if isinstance(sc, int) and sc > 0
            ))
            st.selectbox(
                "Filter by Strokes:",
                options=[0] + stroke_counts if stroke_counts else [0],
                key="stroke_count",
                format_func=lambda x: "No Filter" if x == 0 else str(x),
                on_change=on_filter_change
            )

        with col2:
            pre_filtered = [comp for comp in component_map_arg if isinstance(comp, str) and len(comp) == 1 and
                            (st.session_state.stroke_count == 0 or get_stroke_count(comp) == st.session_state.stroke_count)]
            radicals = {"No Filter"} | {component_map_arg.get(comp, {}).get("meta", {}).get("radical", "") for comp in pre_filtered
                                       if component_map_arg.get(comp, {}).get("meta", {}).get("radical", "")}
            radical_options = ["No Filter"] + sorted(radicals - {"No Filter"})
            if st.session_state.radical not in radical_options:
                st.session_state.radical = "No Filter"
            st.selectbox(
                "Filter by Radical:",
                options=radical_options,
                index=radical_options.index(st.session_state.radical),
                key="radical",
                on_change=on_filter_change
            )

        with col3:
            pre_filtered = [comp for comp in component_map_arg if isinstance(comp, str) and len(comp) == 1 and
                            (st.session_state.stroke_count == 0 or get_stroke_count(comp) == st.session_state.stroke_count) and
                            (st.session_state.radical == "No Filter" or component_map_arg.get(comp, {}).get("meta", {}).get("radical", "") == st.session_state.radical)]
            component_idcs = {"No Filter"} | {component_map_arg.get(comp, {}).get("meta", {}).get("decomposition", "")[0]
                                              for comp in pre_filtered
                                              if component_map_arg.get(comp, {}).get("meta", {}).get("decomposition", "") and
                                                 component_map_arg.get(comp, {}).get("meta", {}).get("decomposition", "")[0] in IDC_CHARS}
            component_idc_options = ["No Filter"] + sorted(component_idcs - {"No Filter"})
            if st.session_state.component_idc not in component_idc_options:
                st.session_state.component_idc = "No Filter"
            st.selectbox(
                "Filter by Structure IDC:",
                options=component_idc_options,
                format_func=lambda x: f"{x} ({idc_descriptions.get(x, x)})" if x != "No Filter" else x,
                index=component_idc_options.index(st.session_state.component_idc),
                key="component_idc",
                on_change=on_filter_change
            )

        st.markdown("### Select Input Component")
        st.caption("Click a character to preview details. Click again to select it.")

        col4, col5 = st.columns([1.5, 0.2])

        with col4:
            filtered_components = [
                comp for comp in component_map_arg
                if isinstance(comp, str) and len(comp) == 1 and
                (st.session_state.stroke_count == 0 or get_stroke_count(comp) == st.session_state.stroke_count) and
                (st.session_state.radical == "No Filter" or component_map_arg.get(comp, {}).get("meta", {}).get("radical", "") == st.session_state.radical) and
                (st.session_state.component_idc == "No Filter" or component_map_arg.get(comp, {}).get("meta", {}).get("decomposition", "").startswith(st.session_state.component_idc))
            ]

            selected_char_components = get_all_components(st.session_state.get("selected_comp", ""), max_depth=5)
            filtered_components.extend([comp for comp in selected_char_components if comp not in filtered_components and comp in component_map_arg])

            sorted_components = sorted(filtered_components, key=lambda c: get_stroke_count(c) or 0)

            if not sorted_components:
                warning_msg = "No components match the current filters. Adjust filters and try again."
                st.warning(warning_msg)
                return []

            # Show preview card if active
            if st.session_state.get("preview_active") and st.session_state.get("preview_comp"):
                render_preview_card(st.session_state.preview_comp)

            # Grid pagination
            PAGE_SIZE = 96
            GRID_COLS = 12
            total = len(sorted_components)
            max_page = max(1, math.ceil(total / PAGE_SIZE))
            st.session_state.page = max(1, min(st.session_state.page, max_page))

            p1, p2, p3 = st.columns([1, 2, 1])
            with p1:
                if st.button("◀ Prev", disabled=(st.session_state.page <= 1), key="comp_prev"):
                    st.session_state.page -= 1
            with p2:
                start_i = (st.session_state.page - 1) * PAGE_SIZE + 1
                end_i = min(st.session_state.page * PAGE_SIZE, total)
                st.caption(f"Showing {start_i}–{end_i} of {total} components")
            with p3:
                if st.button("Next ▶", disabled=(st.session_state.page >= max_page), key="comp_next"):
                    st.session_state.page += 1

            start = (st.session_state.page - 1) * PAGE_SIZE
            end = min(start + PAGE_SIZE, total)
            page_components = sorted_components[start:end]

            st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
            cols = st.columns(GRID_COLS)
            for i, ch in enumerate(page_components):
                with cols[i % GRID_COLS]:
                    is_selected = (st.session_state.get("selected_comp") == ch)
                    is_preview = (st.session_state.get("preview_comp") == ch and st.session_state.get("preview_active"))
                    st.button(
                        ch,
                        key=f"comp_tile_{ch}_{st.session_state.page}",
                        use_container_width=True,
                        type="primary" if (is_selected or is_preview) else "secondary",
                        on_click=on_component_tile_click,
                        args=(ch,),
                    )
            st.markdown("</div>", unsafe_allow_html=True)

        with col5:
            if st.session_state.text_input_warning:
                st.warning(st.session_state.text_input_warning)
            st.text_input(
                "Or type:",
                value=st.session_state.text_input_comp,
                key="text_input_comp",
                on_change=process_text_input,
                args=(component_map_arg,),
                placeholder="Enter one Chinese character"
            )

    # Back / Reset buttons (shown only when a component is selected)
    if not st.session_state.show_inputs:
        with st.container():
            st.markdown("### Component Selection")
            st.info("Component selected. You can go back to the list without resetting your filters.")
            st.button("Back to component list", on_click=back_to_selection)
            st.button("Reset Filters", on_click=on_reset_filters)

    # Always show display mode selector
    with st.container():
        st.markdown("### Output Type")
        st.caption("Choose whether to display single characters or compound phrases.")
        st.radio(
            "Select Output Type:",
            ["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"],
            key="display_mode",
            on_change=on_display_mode_change
        )

    return sorted_components if st.session_state.show_inputs else []


# -------------------------------
# Render character card
# -------------------------------
def render_char_card(char, compounds):
    if not isinstance(char, str) or len(char) != 1:
        return

    meta = component_map.get(char, {}).get("meta", {})
    fields = {
        "Pinyin": clean_field(meta.get("pinyin", "—")),
        "Strokes": f"{get_stroke_count(char)} strokes" if get_stroke_count(char) is not None else "unknown strokes",
        "Radical": clean_field(meta.get("radical", "—")),
        "Decomposition": format_decomposition(char),
        "Definition": clean_field(meta.get("definition", "No definition available")),
        "Etymology": get_etymology_text(meta)
    }
    details = " ".join(f"<strong>{k}:</strong> {v}" for k, v in fields.items())

    st.button(char, key=f"char_button_{char}", on_click=on_component_tile_click, args=(char,))

    st.markdown(f"<div class='char-card'><p class='details'>{details}</p>", unsafe_allow_html=True)

    if compounds and st.session_state.display_mode != "Single Character":
        compounds_text = " ".join(sorted(compounds))
        st.markdown(
            f"""<div class='compounds-section'>
                    <p class='compounds-title'>{st.session_state.display_mode} for {char}:</p>
                    <p class='compounds-list'>{compounds_text}</p>
                </div>""",
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)


# -------------------------------
# Main
# -------------------------------
def main():
    if not component_map:
        st.error("No data available. Please check the JSON file.")
        return

    apply_dynamic_css()
    st.markdown("<h1>🈑 Radix</h1>", unsafe_allow_html=True)

    render_controls(component_map)

    if not st.session_state.get("selected_comp") or st.session_state.selected_comp not in component_map:
        st.info("Please select or type a component to view results.")
        return

    meta = component_map.get(st.session_state.selected_comp, {}).get("meta", {})
    fields = {
        "Pinyin": clean_field(meta.get("pinyin", "—")),
        "Strokes": f"{get_stroke_count(st.session_state.selected_comp)} strokes"
                  if get_stroke_count(st.session_state.selected_comp) is not None else "unknown strokes",
        "Radical": clean_field(meta.get("radical", "—")),
        "Decomposition": format_decomposition(st.session_state.selected_comp),
        "Definition": clean_field(meta.get("definition", "No definition available")),
        "Etymology": get_etymology_text(meta)
    }
    details = " ".join(f"<strong>{k}:</strong> {v}" for k, v in fields.items())

    st.markdown(
        f"""<div class='selected-card'>
                <h2 class='selected-char'>{st.session_state.selected_comp}</h2>
                <p class='details'>{details}</p>
            </div>""",
        unsafe_allow_html=True
    )

    related = component_map.get(st.session_state.selected_comp, {}).get("related_characters", [])
    filtered_chars = [c for c in related if isinstance(c, str) and len(c) == 1]

    char_compounds = {
        c: [] if st.session_state.display_mode == "Single Character" else [
            comp for comp in component_map.get(c, {}).get("meta", {}).get("compounds", [])
            if len(comp) == int(st.session_state.display_mode[0])
        ]
        for c in filtered_chars
    }
    filtered_chars = [c for c in filtered_chars if st.session_state.display_mode == "Single Character" or char_compounds.get(c)]

    st.markdown(
        f"<h2 class='results-header'>🧬 Results for {st.session_state.selected_comp} — {len(filtered_chars)} result(s)</h2>",
        unsafe_allow_html=True
    )

    for char in sorted(filtered_chars, key=lambda c: get_stroke_count(c) or 0):
        render_char_card(char, char_compounds.get(char, []))

    if filtered_chars and st.session_state.display_mode != "Single Character":
        with st.expander("Export Compounds"):
            st.caption("Copy this text to get pinyin and meanings for the displayed compounds.")
            export_text = "Give me the hanyu pinyin and meaning of each compound phrase in one line a phrase in a downloadable word file\n\n"
            export_text += "\n".join(
                compound
                for char in filtered_chars
                for compound in char_compounds.get(char, [])
            )
            st.text_area("Export Text", export_text, height=200)

    with st.expander("Debug Information (For Developers)", expanded=False):
        st.markdown("<div class='debug-section'>", unsafe_allow_html=True)
        st.slider("Adjust Font Size:", 0.7, 1.3, st.session_state.font_scale, 0.1, key="font_scale")
        st.write(f"Total components: {len(component_map)}")
        st.write(f"Current selected_comp: '{st.session_state.get('selected_comp', '')}'")
        st.write(f"Show inputs: {st.session_state.show_inputs}")
        st.write(f"Preview active: {st.session_state.preview_active}")
        st.write(f"Preview comp: '{st.session_state.get('preview_comp', '')}'")
        st.markdown("### Errors and Warnings")
        for msg in st.session_state.diagnostic_messages:
            class_name = "error" if msg["type"] == "error" else "warning"
            st.markdown(f"<p class='diagnostic-message {class_name}'>{msg['type'].capitalize()}: {msg['message']}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
