import json
import math
import streamlit as st
import streamlit.components.v1 as components

# Set page configuration
st.set_page_config(layout="wide")

# Global IDC characters
IDC_CHARS = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}


# -------------------------------
# Session bootstrap (early defaults)
# -------------------------------
def bootstrap_session_state():
    st.session_state.setdefault("diagnostic_messages", [])
    st.session_state.setdefault("font_scale", 1.0)
    st.session_state.setdefault("debug_info", "")

bootstrap_session_state()


# -------------------------------
# Dynamic CSS (now simpler — no need to hide via CSS)
# -------------------------------
def apply_dynamic_css():
    font_scale = st.session_state.get("font_scale", 1.0)

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

        /* Grid tiles */
        .comp-grid .stButton button {{
            background: #ffffff;
            color: #e74c3c;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            font-size: calc(1.25em * var(--fontScale));
            padding: 0.55rem 0.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        .comp-grid .stButton button:hover {{
            background: #fff5f5;
            color: #c0392b;
            border-color: #f2c6c6;
        }}

        @media (max-width: 768px) {{
            .selected-card {{ flex-direction: column; align-items: flex-start; padding: 10px; }}
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
    st.error(f"Failed to load JSON: {e}")


# -------------------------------
# Utilities
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
    except:
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
# One-time state initialization
# -------------------------------
if "selected_comp" not in st.session_state:
    st.session_state.selected_comp = ""
if "stroke_count" not in st.session_state:
    st.session_state.stroke_count = 0
if "radical" not in st.session_state:
    st.session_state.radical = "No Filter"
if "component_idc" not in st.session_state:
    st.session_state.component_idc = "No Filter"
if "display_mode" not in st.session_state:
    st.session_state.display_mode = "Single Character"
if "text_input_comp" not in st.session_state:
    st.session_state.text_input_comp = ""
if "page" not in st.session_state:
    st.session_state.page = 1
if "text_input_warning" not in st.session_state:
    st.session_state.text_input_warning = None
if "show_inputs" not in st.session_state:
    st.session_state.show_inputs = True
if "last_valid_selected_comp" not in st.session_state:
    st.session_state.last_valid_selected_comp = ""
if "preview_comp" not in st.session_state:
    st.session_state.preview_comp = None
if "preview_active" not in st.session_state:
    st.session_state.preview_active = False

# Default selected_comp if needed
if not st.session_state.selected_comp and component_map:
    st.session_state.selected_comp = next(iter(component_map), '')
    st.session_state.last_valid_selected_comp = st.session_state.selected_comp


# -------------------------------
# Preview card
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
    st.caption("Click the same character again to select it.")


# -------------------------------
# Sync callbacks (Shadow Key Pattern)
# -------------------------------
def sync_stroke_count():
    st.session_state.stroke_count = st.session_state.stroke_count_widget
    st.session_state.page = 1

def sync_radical():
    st.session_state.radical = st.session_state.radical_widget
    st.session_state.page = 1

def sync_component_idc():
    st.session_state.component_idc = st.session_state.component_idc_widget
    st.session_state.page = 1

def sync_display_mode():
    st.session_state.display_mode = st.session_state.display_mode_widget

def sync_text_input():
    value = st.session_state.text_input_widget.strip()
    if len(value) != 1:
        st.session_state.text_input_warning = "Please enter exactly one character."
        st.session_state.text_input_comp = ""
        return
    if value in component_map:
        st.session_state.selected_comp = value
        st.session_state.last_valid_selected_comp = value
        st.session_state.text_input_comp = value
        st.session_state.text_input_warning = None
        st.session_state.show_inputs = False
        st.session_state.preview_active = False
        st.session_state.preview_comp = None
    else:
        st.session_state.text_input_warning = "Invalid character."
        st.session_state.text_input_comp = ""

def on_component_tile_click(c: str):
    if st.session_state.preview_active and st.session_state.preview_comp == c:
        # SELECT → hide entire input section
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

def back_to_selection():
    st.session_state.show_inputs = True
    st.session_state.preview_active = False
    st.session_state.preview_comp = None

def on_reset_filters():
    st.session_state.stroke_count = 0
    st.session_state.radical = "No Filter"
    st.session_state.component_idc = "No Filter"
    st.session_state.page = 1
    st.session_state.text_input_comp = ""
    st.session_state.text_input_warning = None
    st.session_state.show_inputs = True
    st.session_state.preview_active = False
    st.session_state.preview_comp = None
    if st.session_state.last_valid_selected_comp in component_map:
        st.session_state.selected_comp = st.session_state.last_valid_selected_comp


# -------------------------------
# Controls — only shown when browsing
# -------------------------------
def render_controls():
    if not st.session_state.show_inputs:
        # When a component is selected → show only back/reset buttons
        st.markdown("### Component Selected")
        st.info("Selection complete. Return to browse other components.")
        col1, col2 = st.columns(2)
        with col1:
            st.button("← Back to component list", on_click=back_to_selection, use_container_width=True)
        with col2:
            st.button("Reset Filters", on_click=on_reset_filters, use_container_width=True)
        return

    # === Full controls when show_inputs == True ===
    idc_descriptions = {
        "No Filter": "No Filter", "⿰": "Left Right", "⿱": "Top Bottom", "⿲": "Left Middle Right",
        "⿳": "Top Middle Bottom", "⿴": "Surround", "⿵": "Surround Top", "⿶": "Surround Bottom",
        "⿷": "Surround Left", "⿸": "Top Left Corner", "⿹": "Top Right Corner",
        "⿺": "Bottom Left Corner", "⿻": "Overlaid"
    }

    st.markdown("### Component Filters")
    col1, col2, col3 = st.columns([0.4, 0.4, 0.4])

    with col1:
        stroke_counts = sorted({sc for sc in (get_stroke_count(c) for c in component_map) if sc is not None})
        options = [0] + stroke_counts
        index = options.index(st.session_state.stroke_count) if st.session_state.stroke_count in options else 0
        st.selectbox(
            "Filter by Strokes:",
            options=options,
            index=index,
            format_func=lambda x: "No Filter" if x == 0 else str(x),
            key="stroke_count_widget",
            on_change=sync_stroke_count
        )

    with col2:
        all_radicals = {component_map.get(c, {}).get("meta", {}).get("radical", "") for c in component_map if component_map.get(c, {}).get("meta", {}).get("radical")}
        radical_options = ["No Filter"] + sorted(all_radicals)
        index = radical_options.index(st.session_state.radical) if st.session_state.radical in radical_options else 0
        st.selectbox(
            "Filter by Radical:",
            options=radical_options,
            index=index,
            key="radical_widget",
            on_change=sync_radical
        )

    with col3:
        all_idcs = {d[0] for d in (component_map.get(c, {}).get("meta", {}).get("decomposition", "") for c in component_map) if d and d[0] in IDC_CHARS}
        idc_options = ["No Filter"] + sorted(all_idcs)
        index = idc_options.index(st.session_state.component_idc) if st.session_state.component_idc in idc_options else 0
        st.selectbox(
            "Filter by Structure IDC:",
            options=idc_options,
            index=index,
            format_func=lambda x: f"{x} ({idc_descriptions.get(x, x)})" if x != "No Filter" else x,
            key="component_idc_widget",
            on_change=sync_component_idc
        )

    st.markdown("### Select Input Component")
    st.caption("Click a character tile to preview → click again to select and view results.")

    col4, col5 = st.columns([1.5, 0.2])

    with col4:
        filtered = [
            c for c in component_map
            if (st.session_state.stroke_count == 0 or get_stroke_count(c) == st.session_state.stroke_count) and
               (st.session_state.radical == "No Filter" or component_map.get(c, {}).get("meta", {}).get("radical") == st.session_state.radical) and
               (st.session_state.component_idc == "No Filter" or component_map.get(c, {}).get("meta", {}).get("decomposition", "").startswith(st.session_state.component_idc))
        ]
        extra = get_all_components(st.session_state.selected_comp, max_depth=5)
        filtered = list(set(filtered) | (extra & set(component_map)))
        sorted_comps = sorted(filtered, key=lambda c: get_stroke_count(c) or 0)

        if not sorted_comps:
            st.warning("No components match the current filters.")
            return

        if st.session_state.preview_active and st.session_state.preview_comp:
            render_preview_card(st.session_state.preview_comp)

        PAGE_SIZE = 96
        GRID_COLS = 12
        total = len(sorted_comps)
        max_page = max(1, math.ceil(total / PAGE_SIZE))
        st.session_state.page = max(1, min(st.session_state.page, max_page))

        p1, p2, p3 = st.columns([1, 2, 1])
        with p1:
            if st.button("◀ Prev", disabled=st.session_state.page <= 1):
                st.session_state.page -= 1
        with p2:
            start_i = (st.session_state.page - 1) * PAGE_SIZE + 1
            end_i = min(st.session_state.page * PAGE_SIZE, total)
            st.caption(f"Showing {start_i}–{end_i} of {total}")
        with p3:
            if st.button("Next ▶", disabled=st.session_state.page >= max_page):
                st.session_state.page += 1

        page_comps = sorted_comps[(st.session_state.page - 1) * PAGE_SIZE : st.session_state.page * PAGE_SIZE]

        st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
        cols = st.columns(GRID_COLS)
        for i, ch in enumerate(page_comps):
            with cols[i % GRID_COLS]:
                is_preview = st.session_state.preview_active and st.session_state.preview_comp == ch
                is_selected = st.session_state.selected_comp == ch
                st.button(
                    ch,
                    key=f"tile_{ch}_{st.session_state.page}",
                    use_container_width=True,
                    type="primary" if (is_preview or is_selected) else "secondary",
                    on_click=on_component_tile_click,
                    args=(ch,)
                )
        st.markdown("</div>", unsafe_allow_html=True)

    with col5:
        if st.session_state.text_input_warning:
            st.warning(st.session_state.text_input_warning)
        st.text_input(
            "Or type one character:",
            value=st.session_state.text_input_comp,
            key="text_input_widget",
            on_change=sync_text_input,
            placeholder="e.g. 水"
        )


# -------------------------------
# Result card rendering
# -------------------------------
def render_result_card(char, compounds):
    meta = component_map.get(char, {}).get("meta", {})
    fields = {
        "Pinyin": clean_field(meta.get("pinyin", "—")),
        "Strokes": f"{get_stroke_count(char)} strokes" if get_stroke_count(char) is not None else "unknown",
        "Radical": clean_field(meta.get("radical", "—")),
        "Decomposition": format_decomposition(char),
        "Definition": clean_field(meta.get("definition", "No definition")),
        "Etymology": get_etymology_text(meta)
    }
    details = " ".join(f"<strong>{k}:</strong> {v}" for k, v in fields.items())
    st.button(char, key=f"result_{char}", on_click=on_component_tile_click, args=(char,))
    st.markdown(f"<div class='char-card'><p class='details'>{details}</p>", unsafe_allow_html=True)
    if compounds:
        st.markdown(f"<div class='compounds-section'><p class='compounds-title'>{st.session_state.display_mode}:</p><p class='compounds-list'>{' '.join(sorted(compounds))}</p></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# -------------------------------
# Main
# -------------------------------
def main():
    if not component_map:
        st.error("No data loaded.")
        return

    apply_dynamic_css()
    st.markdown("<h1>🈑 Radix</h1>", unsafe_allow_html=True)

    # Always show output type selector
    st.markdown("### Output Type")
    modes = ["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"]
    index = modes.index(st.session_state.display_mode)
    st.radio(
        "Display:",
        options=modes,
        index=index,
        key="display_mode_widget",
        on_change=sync_display_mode,
        horizontal=True
    )

    render_controls()

    if not st.session_state.selected_comp or st.session_state.selected_comp not in component_map:
        st.info("👆 Select a component from the list above to view its details and related characters.")
        return

    # Selected component header
    meta = component_map[st.session_state.selected_comp]["meta"]
    fields = {
        "Pinyin": clean_field(meta.get("pinyin", "—")),
        "Strokes": f"{get_stroke_count(st.session_state.selected_comp)} strokes" if get_stroke_count(st.session_state.selected_comp) is not None else "unknown",
        "Radical": clean_field(meta.get("radical", "—")),
        "Decomposition": format_decomposition(st.session_state.selected_comp),
        "Definition": clean_field(meta.get("definition", "No definition")),
        "Etymology": get_etymology_text(meta)
    }
    details = " ".join(f"<strong>{k}:</strong> {v}" for k, v in fields.items())
    st.markdown(
        f'<div class="selected-card"><h2 class="selected-char">{st.session_state.selected_comp}</h2><p class="details">{details}</p></div>',
        unsafe_allow_html=True
    )

    # Results
    related = component_map[st.session_state.selected_comp].get("related_characters", [])
    chars = [c for c in related if isinstance(c, str) and len(c) == 1]
    n = int(st.session_state.display_mode[0]) if st.session_state.display_mode != "Single Character" else 0
    compounds = {
        c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w) == n]
        for c in chars
    } if n else {c: [] for c in chars}
    chars = [c for c in chars if n == 0 or compounds[c]]

    st.markdown(f"<h2 class='results-header'>🧬 Results — {len(chars)} found</h2>", unsafe_allow_html=True)

    for char in sorted(chars, key=lambda c: get_stroke_count(c) or 0):
        render_result_card(char, compounds.get(char, []))

    if chars and n:
        with st.expander("Export Compounds for Lookup"):
            text = "\n".join(comp for char in chars for comp in compounds[char])
            st.text_area("Copy list:", text, height=200)


if __name__ == "__main__":
    main()
