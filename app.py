import json
from collections import defaultdict
import streamlit as st

# === App Title ===
st.markdown(
    "<h1 style='font-size: 2em;'>🧩 Character Decomposition Explorer</h1>",
    unsafe_allow_html=True
)

# === Load strokes.txt from local file (cached) ===
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

# === Recursive decomposition ===
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

# === Component map ===
@st.cache_data
def build_component_map(max_depth):
    component_map = defaultdict(list)
    for char in char_decomp:
        all_components = get_all_components(char, max_depth=max_depth)
        for comp in all_components:
            component_map[comp].append(char)
    return component_map

# === Main screen controls ===
st.markdown("### 🔧 Filters and Settings")

col1, col2 = st.columns(2)

with col1:
    max_depth = st.slider(
        "🧱 Max Decomposition Depth",
        min_value=0, max_value=5, value=1,
        help="How many levels deep to decompose the selected character"
    )

with col2:
    min_strokes, max_strokes = st.slider(
        "✂️ Stroke Count Range",
        min_value=0, max_value=30, value=(4, 10),
        help="Only show characters within this stroke count range"
    )

search_input = st.text_input("🔍 Search for a component (e.g. 木):", value="木")

component_map = build_component_map(max_depth=max_depth)

# === Helper: Get stroke count ===
def get_stroke_count(char):
    return char_decomp.get(char, {}).get("strokes", float('inf'))

# === Filter dropdown options ===
filtered_components = [
    comp for comp in component_map
    if min_strokes <= get_stroke_count(comp) <= max_strokes
]
sorted_components = sorted(filtered_components, key=get_stroke_count)

# === Component selection ===
selected_comp = None
if not search_input:
    selected_comp = st.selectbox(
        "Select a component:",
        options=sorted_components,
        format_func=lambda c: f"{c} ({get_stroke_count(c)} strokes)"
    )
else:
    selected_comp = search_input.strip()

# === Current selection ===
if selected_comp:
    st.markdown(
        "<h2 style='font-size: 1.3em;'>📌 Current Selection</h2>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"""
        <div style='display: flex; gap: 2em; font-size: 1.1em; padding: 0.5em 0;'>
            <div><strong>Component:</strong> {selected_comp}</div>
            <div><strong>Level:</strong> {max_depth}</div>
            <div><strong>Stroke Range:</strong> {min_strokes} – {max_strokes}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # === Display decomposed characters ===
    chars = [
        c for c in component_map.get(selected_comp, [])
        if min_strokes <= get_stroke_count(c) <= max_strokes
    ]
    chars = sorted(set(chars))

    st.markdown(
        f"<h2 style='font-size: 1.3em;'>🧬 Characters with: {selected_comp} — {len(chars)} result(s)</h2>",
        unsafe_allow_html=True
    )
    for c in chars:
        entry = char_decomp.get(c, {})
        pinyin = entry.get("pinyin", "—")
        definition = entry.get("definition", "No definition available")
        st.write(f"**{c}** — {pinyin} — {definition}")
