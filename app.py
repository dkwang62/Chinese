import json
from collections import defaultdict
import streamlit as st

st.set_page_config(layout="wide")

st.markdown("""
<h1 style='font-size: 1.8em;'>🧩 Character Decomposition Explorer</h1>
""", unsafe_allow_html=True)

@st.cache_data
def load_char_decomp():
    char_decomp = {}
    with open("strokes.txt", "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                char = entry.get("character", "")
                char_decomp[char] = entry
            except:
                continue
    return char_decomp

char_decomp = load_char_decomp()

def get_all_components(char, max_depth=2, depth=0, seen=None):
    if seen is None:
        seen = set()
    if char in seen or depth > max_depth:
        return set()
    seen.add(char)

    components = set()
    for comp in char_decomp.get(char, {}).get("decomposition", ""):
        if '\u4e00' <= comp <= '\u9fff':
            components.add(comp)
            components.update(get_all_components(comp, max_depth, depth + 1, seen))
    return components

@st.cache_data
def build_component_map(max_depth):
    component_map = defaultdict(list)
    for char in char_decomp:
        all_components = get_all_components(char, max_depth=max_depth)
        for comp in all_components:
            component_map[comp].append(char)
    return component_map

# === Session State Setup ===
if "selected_comp" not in st.session_state:
    st.session_state.selected_comp = "木"
    st.session_state.input_method = "dropdown"  # or 'text'
    st.session_state.stroke_range = (4, 10)
    st.session_state.user_changed_stroke_range = False

# === Controls ===
st.session_state.max_depth = st.slider("Max Decomposition Depth", 0, 5, st.session_state.get("max_depth", 1))

char_decomp = load_char_decomp()
component_map = build_component_map(max_depth=st.session_state.max_depth)

def get_stroke_count(char):
    return char_decomp.get(char, {}).get("strokes", float("inf"))

# === Calculate dropdown options ===
min_strokes, max_strokes = st.session_state.stroke_range
filtered_components = [
    comp for comp in component_map
    if min_strokes <= get_stroke_count(comp) <= max_strokes
]
sorted_components = sorted(filtered_components, key=get_stroke_count)

# === Suggested range based on component ===
selected_stroke = get_stroke_count(st.session_state.selected_comp)
suggested_min = selected_stroke
suggested_max = max(selected_stroke + 5, selected_stroke + 1)

def on_slider_change():
    st.session_state.user_changed_stroke_range = True

if not st.session_state.user_changed_stroke_range:
    st.session_state.stroke_range = (suggested_min, suggested_max)

st.session_state.stroke_range = st.slider(
    "Stroke Count Range",
    0, 30,
    st.session_state.stroke_range,
    on_change=on_slider_change
)

# === UI Inputs ===
col1, col2 = st.columns(2)

with col1:
    dropdown_val = st.selectbox(
        "Select a component:",
        options=sorted_components,
        index=sorted_components.index(st.session_state.selected_comp)
            if st.session_state.selected_comp in sorted_components else 0,
        key="dropdown_box"
    )
    if st.session_state.input_method != "dropdown" and dropdown_val != st.session_state.selected_comp:
        st.session_state.selected_comp = dropdown_val
        st.session_state.input_method = "dropdown"
        st.rerun()

with col2:
    if st.session_state.input_method == "text":
        text_val = st.session_state.selected_comp
    else:
        text_val = ""
    user_input = st.text_input("Or type a component:", value=text_val, key="text_box")

    if user_input and user_input != st.session_state.selected_comp:
        st.session_state.selected_comp = user_input
        st.session_state.input_method = "text"
        st.session_state.user_changed_stroke_range = False
        st.rerun()

selected_comp = st.session_state.selected_comp

# === Display Selection ===
st.markdown(f"""
<h2 style='font-size: 1.2em;'>📌 Current Selection</h2>
<p><strong>Component:</strong> {selected_comp} &nbsp;&nbsp; 
<strong>Level:</strong> {st.session_state.max_depth} &nbsp;&nbsp; 
<strong>Stroke Range:</strong> {min_strokes} – {max_strokes}</p>
""", unsafe_allow_html=True)

# === Show Characters ===
if selected_comp:
    chars = [
        c for c in component_map.get(selected_comp, [])
        if min_strokes <= get_stroke_count(c) <= max_strokes
    ]
    chars = sorted(set(chars))

    st.markdown(
        f"<h2 style='font-size: 1.2em;'>🧬 Characters with: {selected_comp} — {len(chars)} result(s)</h2>",
        unsafe_allow_html=True
    )
    for c in chars:
        entry = char_decomp.get(c, {})
        pinyin = entry.get("pinyin", "—")
        definition = entry.get("definition", "No definition available")
        st.write(f"**{c}** — {pinyin} — {definition}")
