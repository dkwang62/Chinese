
import json
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components
import random

st.set_page_config(layout="wide")

# --- Constants ---
IDC_CHARS = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}

# --- Custom CSS ---
st.markdown("""
<style>
/* CSS styles remain unchanged */
</style>
""", unsafe_allow_html=True)

# --- Utilities ---
def is_valid_char(c):
    return ('一' <= c <= '鿿' or '⺀' <= c <= '⻿' or '㐀' <= c <= '䶿' or '𠀀' <= c <= '𪛟')

def is_idc(char):
    return char in IDC_CHARS

def clean_field(field):
    return field[0] if isinstance(field, list) and field else field or "—"

def get_stroke_count(char):
    return char_decomp.get(char, {}).get("strokes", -1)

def update_selected_comp(new_comp):
    st.session_state.previous_selected_comp = st.session_state.selected_comp
    st.session_state.selected_comp = new_comp
    st.session_state.text_input_comp = new_comp
    st.session_state.idc_refresh = not st.session_state.idc_refresh
    st.session_state.page = 1

# --- Initialization ---
def init_session_state():
    config_options = [
        {"selected_comp": "爫", "max_depth": 1, "stroke_range": (4, 14)},
        {"selected_comp": "心", "max_depth": 3, "stroke_range": (4, 14)},
        {"selected_comp": "⺌", "max_depth": 0, "stroke_range": (3, 14)}
    ]
    selected_config = random.choice(config_options)
    defaults = {
        "selected_comp": selected_config["selected_comp"],
        "max_depth": selected_config["max_depth"],
        "stroke_range": selected_config["stroke_range"],
        "display_mode": "Single Character",
        "selected_idc": "No Filter",
        "idc_refresh": False,
        "text_input_comp": selected_config["selected_comp"],
        "page": 1,
        "results_per_page": 50,
        "previous_selected_comp": selected_config["selected_comp"]
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

@st.cache_data
def load_char_decomp():
    try:
        with open("strokes1.json", "r", encoding="utf-8") as f:
            return {entry["character"]: entry for entry in json.load(f)}
    except Exception as e:
        st.error(f"Failed to load strokes1.json: {e}")
        return {}

char_decomp = load_char_decomp()

def get_all_components(char, max_depth, depth=0, seen=None):
    if seen is None:
        seen = set()
    if char in seen or depth > max_depth:
        return set()
    seen.add(char)
    components = set()
    decomposition = char_decomp.get(char, {}).get("decomposition", "")
    for comp in decomposition:
        if is_idc(comp) or not is_valid_char(comp):
            continue
        components.add(comp)
        components.update(get_all_components(comp, max_depth, depth + 1, seen.copy()))
    return components

@st.cache_data
def build_component_map(max_depth):
    component_map = defaultdict(list)
    for char in char_decomp:
        components = set()
        decomposition = char_decomp.get(char, {}).get("decomposition", "")
        for comp in decomposition:
            if is_valid_char(comp):
                components.add(comp)
                components.update(get_all_components(comp, max_depth))
        components.add(char)
        for comp in components:
            component_map[comp].append(char)
    return component_map

def on_text_input_change(component_map):
    text_value = st.session_state.text_input_comp.strip()
    if text_value in component_map or text_value in char_decomp:
        update_selected_comp(text_value)
    elif text_value:
        st.warning("Invalid character. Please enter a valid component.")
        st.session_state.text_input_comp = st.session_state.selected_comp

def on_selectbox_change():
    update_selected_comp(st.session_state.selected_comp)

def on_output_char_select(component_map):
    selected_char = st.session_state.output_char_select
    if selected_char != "Select a character..." and selected_char in component_map:
        update_selected_comp(selected_char)
    else:
        if selected_char != "Select a character...":
            st.warning("Invalid character selected. Reverting to previous character.")
        update_selected_comp(st.session_state.previous_selected_comp)
        st.session_state.output_char_select = "Select a character..."

def render_controls(component_map):
    min_strokes, max_strokes = st.session_state.stroke_range
    filtered_components = [comp for comp in component_map if min_strokes <= get_stroke_count(comp) <= max_strokes]
    sorted_components = sorted(filtered_components, key=get_stroke_count)
    if st.session_state.selected_comp not in sorted_components:
        sorted_components.insert(0, st.session_state.selected_comp)

    st.slider("Max Decomposition Depth", 0, 5, key="max_depth")
    st.slider("Strokes Range", 0, 30, key="stroke_range")

    chars = [c for c in component_map.get(st.session_state.selected_comp, [])
             if min_strokes <= get_stroke_count(c) <= max_strokes and c in char_decomp]

    idc_options = {"No Filter"}
    for char in chars:
        decomposition = char_decomp.get(char, {}).get("decomposition", "")
        if decomposition and decomposition[0] in IDC_CHARS:
            idc_options.add(decomposition[0])
    idc_options = sorted(idc_options)
    if st.session_state.selected_idc not in idc_options:
        st.session_state.selected_idc = "No Filter"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.selectbox("Select a component:", options=sorted_components,
                     format_func=lambda c: f"{c} ({get_stroke_count(c)} strokes)",
                     index=sorted_components.index(st.session_state.selected_comp),
                     key="selected_comp",
                     on_change=on_selectbox_change)
    with col2:
        st.text_input("Or type a component:", value=st.session_state.selected_comp,
                      key="text_input_comp", on_change=on_text_input_change, args=(component_map,))
    with col3:
        st.selectbox("Filter by IDC:", options=idc_options,
                     index=idc_options.index(st.session_state.selected_idc), key="selected_idc")

    st.radio("Display Mode:", options=["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"],
             key="display_mode")

def render_char_card(char, compounds):
    entry = char_decomp.get(char, {})
    decomposition = entry.get("decomposition", "")
    idc = decomposition[0] if decomposition and decomposition[0] in IDC_CHARS else "—"
    fields = {
        "Pinyin": clean_field(entry.get("pinyin", "—")),
        "Definition": clean_field(entry.get("definition", "No definition available")),
        "Radical": clean_field(entry.get("radical", "—")),
        "Hint": clean_field(entry.get("etymology", {}).get("hint", "No hint available")),
        "Strokes": f"{get_stroke_count(char)} strokes" if get_stroke_count(char) != -1 else "unknown strokes",
        "IDC": idc
    }
    details = " ".join(f"<strong>{k}:</strong> {v}  " for k, v in fields.items())
    st.markdown(f"<div class='char-card'><h3 class='char-title'>{char}</h3><p class='details'>{details}</p>", unsafe_allow_html=True)
    if compounds and st.session_state.display_mode != "Single Character":
        compounds_text = " ".join(sorted(compounds, key=lambda x: x[0]))
        st.markdown(f"<div class='compounds-section'><p class='compounds-title'>{st.session_state.display_mode} for {char}:</p><p class='compounds-list'>{compounds_text}</p></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def main():
    component_map = build_component_map(st.session_state.max_depth)
    st.markdown("<h1>🧩 Character Decomposition Explorer</h1>", unsafe_allow_html=True)
    render_controls(component_map)

    if st.button("Reset App"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        init_session_state()
        st.warning("Please refresh the page.")

    if not st.session_state.selected_comp:
        return

    selected = st.session_state.selected_comp
    entry = char_decomp.get(selected, {})
    fields = {
        "Pinyin": clean_field(entry.get("pinyin", "—")),
        "Definition": clean_field(entry.get("definition", "No definition available")),
        "Radical": clean_field(entry.get("radical", "—")),
        "Hint": clean_field(entry.get("etymology", {}).get("hint", "No hint available")),
        "Strokes": f"{get_stroke_count(selected)} strokes" if get_stroke_count(selected) != -1 else "unknown strokes",
        "Depth": str(st.session_state.max_depth),
        "Stroke Range": f"{st.session_state.stroke_range[0]} – {st.session_state.stroke_range[1]}"
    }
    details = " ".join(f"<strong>{k}:</strong> {v}  " for k, v in fields.items())
    st.markdown(f"<div class='selected-card'><h2 class='selected-char'>{selected}</h2><p class='details'>{details}</p></div>", unsafe_allow_html=True)

    min_s, max_s = st.session_state.stroke_range
    chars = [c for c in component_map.get(selected, []) if min_s <= get_stroke_count(c) <= max_s]
    if st.session_state.selected_idc != "No Filter":
        chars = [c for c in chars if char_decomp.get(c, {}).get("decomposition", "").startswith(st.session_state.selected_idc)]

    char_compounds = {}
    for c in chars:
        compounds = char_decomp.get(c, {}).get("compounds", [])
        if st.session_state.display_mode == "Single Character":
            char_compounds[c] = []
        else:
            length = int(st.session_state.display_mode[0])
            char_compounds[c] = [comp for comp in compounds if len(comp) == length]

    filtered_chars = [c for c in chars if char_compounds[c] or st.session_state.display_mode == "Single Character"]

    if filtered_chars:
        options = ["Select a character..."] + sorted(filtered_chars, key=get_stroke_count)
        if st.session_state.previous_selected_comp and st.session_state.previous_selected_comp not in filtered_chars:
            options.insert(1, st.session_state.previous_selected_comp)
        st.selectbox("Select a character from the list below:",
                     options=options,
                     key="output_char_select",
                     on_change=lambda: on_output_char_select(component_map),
                     format_func=lambda c: c if c == "Select a character..." else f"{c} ({clean_field(char_decomp.get(c, {}).get('pinyin', '—'))},{get_stroke_count(c)} strokes, {clean_field(char_decomp.get(c, {}).get('definition', 'No definition available'))})")

    st.markdown(f"<h2 class='results-header'>🧬 Characters with {selected} — {len(filtered_chars)} result(s)</h2>", unsafe_allow_html=True)

    for char in sorted(filtered_chars, key=get_stroke_count):
        render_char_card(char, char_compounds.get(char, []))

    if filtered_chars:
        export_text = "Give me the hanyu pinyin and meaning of each compound phrase in one line a phrase in a downloadable word file

"
        export_text += "\n".join(
            f"{compound}"
            for char in filtered_chars
            for compound in char_compounds.get(char, [])
        )
        st.text_area("Right click, Select all, copy; paste to ChatGPT", export_text, height=300, key="export_text")
        components.html(f"""
            <textarea id="copyTarget" style="opacity:0;position:absolute;left:-9999px;">{export_text}</textarea>
            <script>
            const copyText = document.getElementById("copyTarget");
            copyText.select();
            document.execCommand("copy");
            </script>
        """, height=0)

if __name__ == "__main__":
    init_session_state()
    main()
