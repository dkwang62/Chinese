import json
from collections import defaultdict
import streamlit as st

st.title("Chinese Character Decomposition Explorer")

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

# === Step 4: Sidebar Controls ===
st.sidebar.header("🔧 Filters & Settings")

max_depth = st.sidebar.slider(
    "Max Decomposition Depth",
    0, 5, 2,
    help="Controls how deeply each character is decomposed into components.",
    key="depth"
)

min_strokes, max_strokes = st.sidebar.slider(
    "Stroke Count Range",
    0, 30, (2, 4),
    help="Filter both components and resulting characters by their number of strokes.",
    key="stroke_range"
)

search_input = st.sidebar.text_input("🔍 Search for a component (e.g. 木):", key="search")

# === Step 5: Track and persist selected component ===
component_map = build_component_map(max_depth=st.session_state.depth)

def get_stroke_count(char):
    return char_decomp.get(char, {}).get("strokes", float('inf'))

filtered_components = [
    comp for comp in component_map
    if min_strokes <= get_stroke_count(comp) <= max_strokes
]
sorted_components = sorted(filtered_components, key=get_stroke_count)

# Determine selected component
if "selected_comp" not in st.session_state:
    st.session_state.selected_comp = sorted_components[0] if sorted_components else None

if st.session_state.search:
    if st.session_state.search in component_map:
        st.session_state.selected_comp = st.session_state.search.strip()
else:
    selected = st.selectbox(
        "Select a component:",
        options=sorted_components,
        index=sorted_components.index(st.session_state.selected_comp) if st.session_state.selected_comp in sorted_components else 0,
        format_func=lambda c: f"{c} ({get_stroke_count(c)} strokes)"
    )
    st.session_state.selected_comp = selected

# === Step 6: Show current state clearly ===
st.markdown(f"""
### 📌 Current Selection
- **Root Component:** `{st.session_state.selected_comp}`
- **Decomposition Level:** `{st.session_state.depth}`
- **Stroke Count Range for Output Characters:** `{st.session_state.stroke_range[0]} – {st.session_state.stroke_range[1]}`
""")

# === Step 7: Display characters ===
if st.session_state.selected_comp:
    chars = [
        c for c in component_map.get(st.session_state.selected_comp, [])
        if min_strokes <= get_stroke_count(c) <= max_strokes
    ]
    chars = sorted(set(chars))

    st.subheader(f"Characters with component '{st.session_state.selected_comp}' ({len(chars)} found):")
    for c in chars:
        entry = char_decomp.get(c, {})
        pinyin = entry.get("pinyin", "—")
        definition = entry.get("definition", "No definition available")
        st.write(f"**{c}** — {pinyin} — {definition}")
