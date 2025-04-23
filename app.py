import json
from collections import defaultdict
import streamlit as st

st.set_page_config(layout="wide")

st.markdown("""
<h1 style='font-size: 1.8em;'>🧩 Character Decomposition Explorer</h1>
""", unsafe_allow_html=True)

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

# === Step 4: Controls (no sidebar) ===
if "selected_comp" not in st.session_state:
    st.session_state.selected_comp = "木"
if "max_depth" not in st.session_state:
    st.session_state.max_depth = 1
if "stroke_range" not in st.session_state:
    st.session_state.stroke_range = (4, 10)

col1, col2 = st.columns(2)
with col1:
    st.slider("Max Decomposition Depth", 0, 5, key="max_depth")
with col2:
    st.slider("Stroke Count Range", 0, 30, key="stroke_range")
min_strokes, max_strokes = st.session_state.stroke_range

component_map = build_component_map(max_depth=st.session_state.max_depth)

# === Helper: Get stroke count ===
def get_stroke_count(char):
    return char_decomp.get(char, {}).get("strokes", float('inf'))

# === Filter dropdown options ===
filtered_components = [
    comp for comp in component_map
    if min_strokes <= get_stroke_count(comp) <= max_strokes
]
sorted_components = sorted(filtered_components, key=get_stroke_count)

# === Component selection (dropdown + text input) ===
col_a, col_b = st.columns(2)
with col_a:
    st.selectbox(
        "Select a component:",
        options=sorted_components,
        format_func=lambda c: f"{c} ({get_stroke_count(c)} strokes)",
        index=sorted_components.index(st.session_state.selected_comp) if st.session_state.selected_comp in sorted_components else 0,
        key="selected_comp"
    )
with col_b:
    text_input = st.text_input("Or type a component:", key="text_input_comp")

# Sync text input with dropdown if valid
if st.session_state.text_input_comp.strip() and st.session_state.text_input_comp in component_map:
    if st.session_state.text_input_comp != st.session_state.selected_comp:
        st.session_state.selected_comp = st.session_state.text_input_comp.strip()
elif st.session_state.text_input_comp.strip() and st.session_state.text_input_comp not in component_map:
    st.warning("Invalid component entered. Please select from the dropdown or enter a valid component.")

# === Display current selection ===
st.markdown(f"""
<h2 style='font-size: 1.2em;'>📌 Current Selection</h2>
<p><strong>Component:</strong> {st.session_state.selected_comp}    <strong>Level:</strong> {st.session_state.max_depth}    <strong>Stroke Range:</strong> {min_strokes} – {max_strokes}</p>
""", unsafe_allow_html=True)

# === Step 5: Display decomposed characters ===
if st.session_state.selected_comp:
    chars = [
        c for c in component_map.get(st.session_state.selected_comp, [])
        if min_strokes <= get_stroke_count(c) <= max_strokes
    ]
    chars = sorted(set(chars))

    st.markdown(
        f"<h2 style='font-size: 1.2em;'>🧬 Characters with: {st.session_state.selected_comp} — {len(chars)} result(s)</h2>",
        unsafe_allow_html=True
    )
    for c in chars:
        entry = char_decomp.get(c, {})
        pinyin = entry.get("pinyin", "—")
        definition = entry.get("definition", "No definition available")
        st.write(f"**{c}** — {pinyin} — {definition}")
