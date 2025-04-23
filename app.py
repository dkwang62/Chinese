import streamlit as st
import json
from collections import defaultdict

st.set_page_config(layout="wide")
st.title("🧩 Character Decomposition Explorer")

# Load character decomposition data
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

# Function to get stroke count
def get_stroke_count(char):
    return char_decomp.get(char, {}).get("strokes", float('inf'))

# Build component map
@st.cache_data
def build_component_map(max_depth):
    component_map = defaultdict(list)
    for char in char_decomp:
        components = set()
        decomposition = char_decomp.get(char, {}).get("decomposition", "")
        for comp in decomposition:
            if '\u4e00' <= comp <= '\u9fff':
                components.add(comp)
        for comp in components:
            component_map[comp].append(char)
    return component_map

# User inputs
max_depth = st.slider("Max Decomposition Depth", 0, 5, 1)
stroke_range = st.slider("Stroke Count Range", 0, 30, (4, 10))
min_strokes, max_strokes = stroke_range

component_map = build_component_map(max_depth)

# Filter components based on stroke range
filtered_components = [
    comp for comp in component_map
    if min_strokes <= get_stroke_count(comp) <= max_strokes
]
sorted_components = sorted(filtered_components, key=get_stroke_count)

# Component selection
selected_comp = st.selectbox(
    "Select a component:",
    options=sorted_components,
    format_func=lambda c: f"{c} ({get_stroke_count(c)} strokes)"
)

# Display current selection
st.markdown(f"""
**Component:** {selected_comp}  
**Level:** {max_depth}  
**Stroke Range:** {min_strokes} – {max_strokes}
""")

# Display decomposed characters
if selected_comp:
    chars = [
        c for c in component_map.get(selected_comp, [])
        if min_strokes <= get_stroke_count(c) <= max_strokes
    ]
    chars = sorted(set(chars))

    st.markdown(f"**Characters with '{selected_comp}':** {len(chars)} result(s)")
    for c in chars:
        entry = char_decomp.get(c, {})
        pinyin = entry.get("pinyin", "—")
        definition = entry.get("definition", "No definition available")
        st.write(f"**{c}** — {pinyin} — {definition}")
