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

# === Initialize state ===
st.session_state.setdefault("selected_comp", "木")
st.session_state.setdefault("typed_comp", "木")
st.session_state.setdefault("last_input_method", "dropdown")  # or 'text'
st.session_state.setdefault("max_depth", 1)
st.session_state.setdefault("stroke_range", (4, 10))
st.session_state.setdefault("user_changed_stroke_range", False)

def get_stroke_count(char):
    return char_decomp.get(char, {}).get("strokes", float('inf'))

col1, col2 = st.columns(2)
with col1:
    max_depth = st.slider("Max Decomposition Depth", 0, 5, st.session_state.max_depth)
    st.session_state.max_depth = max_depth

component_map = build_component_map(max_depth=max_depth)

# Determine stroke range auto-suggestion
selected_stroke = get_stroke_count(st.session_state.selected_comp)
suggested_min = selected_stroke
suggested_max = max(suggested_min + 5, suggested_min + 1)

def on_slider_change():
    st.session_state.user_changed_stroke_range = True

with col2:
    if not st.session_state.user_changed_stroke_range:
        st.session_state.stroke_range = (suggested_min, suggested_max)
    stroke_range = st.slider(
        "Stroke Count Range", 0, 30, st.session_state.stroke_range, on_change=on_slider_change
    )
    st.session_state.stroke_range = stroke_range

min_strokes, max_strokes = stroke_range

# Filter options for dropdown
filtered_components = [
    comp for comp in component_map
    if min_strokes <= get_stroke_count(comp) <= max_strokes
]
sorted_components = sorted(filtered_components, key=get_stroke_count)

# === Component selection ===
col_a, col_b = st.columns(2)

with col_a:
    if st.session_state.last_input_method == "dropdown":
        dropdown_value = st.session_state.selected_comp
    else:
        # fallback to something in list or first option
        dropdown_value = st.session_state.selected_comp if st.session_state.selected_comp in sorted_components else sorted_components[0]
    dropdown_selection = st.selectbox(
        "Select a component:",
        options=sorted_components,
        format_func=lambda c: f"{c} ({get_stroke_count(c)} strokes)",
        index=sorted_components.index(dropdown_value) if dropdown_value in sorted_components else 0,
        key="dropdown_comp"
    )

with col_b:
    if st.session_state.last_input_method == "text":
        text_value = st.session_state.typed_comp
    else:
        text_value = st.session_state.selected_comp
    text_input = st.text_input("Or type a component:", value=text_value, key="text_comp")

# === Handle interactions ===
# Priority 1: text input
if text_input != st.session_state.selected_comp and text_input.strip() != "":
    st.session_state.selected_comp = text_input.strip()
    st.session_state.typed_comp = text_input.strip()
    st.session_state.last_input_method = "text"
    st.session_state.user_changed_stroke_range = False

# Priority 2: dropdown
elif dropdown_selection != st.session_state.selected_comp:
    st.session_state.selected_comp = dropdown_selection
    st.session_state.typed_comp = dropdown_selection
    st.session_state.last_input_method = "dropdown"
    st.session_state.user_changed_stroke_range = False

selected_comp = st.session_state.selected_comp

# === Display current selection ===
st.markdown("""
<h2 style='font-size: 1.2em;'>📌 Current Selection</h2>
<p><strong>Component:</strong> {0} &nbsp;&nbsp; <strong>Level:</strong> {1} &nbsp;&nbsp; <strong>Stroke Range:</strong> {2} – {3}</p>
""".format(selected_comp, max_depth, min_strokes, max_strokes), unsafe_allow_html=True)

# === Display decomposed characters ===
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
