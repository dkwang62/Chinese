import json
from collections import defaultdict
import streamlit as st

st.set_page_config(layout="wide")  # Optional: better use of space on larger screens
st.title("📖 Chinese Character Decomposition Explorer")

# === Step 1: Load strokes.txt from local file (cached) ===
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

# === Step 2: Recursive decomposition ===
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

# === Step 3: Build component map (cached) ===
@st.cache_data
def build_component_map(max_depth):
    component_map = defaultdict(list)
    for char in char_decomp:
        all_components = get_all_components(char, max_depth=max_depth)
        for comp in all_components:
            component_map[comp].append(char)
    return component_map

# === Step 4: Unified Controls ===
st.markdown("### 🧮 Controls")

col1, col2, col3 = st.columns([1, 2, 2])

with col1:
    depth = st.slider(
        "Decomposition Depth",
        0, 5, 2,
        help="How deeply to break down each character.",
        key="depth"
    )

with col2:
    stroke_range = st.slider(
        "Stroke Count Range",
        0, 30, (2, 4),
        help="Filters both components and output characters.",
        key="stroke_range"
    )

with col3:
    search_input = st.text_input(
        "Search or Select Component (e.g. 木)",
        key="search"
    )

component_map = build_component_map(max_depth=st.session_state.depth)

def get_stroke_count(char):
    return char_decomp.get(char, {}).get("strokes", float('inf'))

filtered_components = [
    comp for comp in component_map
    if stroke_range[0] <= get_stroke_count(comp)_
