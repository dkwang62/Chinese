import json
import time
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
    st.session_state.stroke_range = (4, 10)
    st.session_state.user_changed_stroke_range = False
    st.session_state.input_method = "dropdown"
    st.session_state.last_dropdown = "木"

def get_stroke_count(char):
    return char_decomp.get(char, {}).get("strokes", float("inf"))

# === Controls ===
st.session_state.max_depth = st.slider("Max Decomposition Depth", 0, 5, st.session_state.get("max_depth", 1))
component_map = build_component_map(max_depth=st.session_state.max_depth)

# === Determine auto stroke range ===
selected_stroke = get_stroke_count(st.session_state.selected_comp)
suggested_min = selected_stroke
suggested_max = max(suggested_min + 5, suggested_min + 1)

def on_slider_change():
    st.session_state.user_changed_stroke_range = True

if not st.session_state.user_changed_stroke_range:
    st.session_state.stroke_range = (suggested_min, suggested_max)

st.session_state.stroke_range = st.slider(
    "Stroke Count Range", 0, 30,
    st.session_state.stroke_range,
    on_change=on_slider_change
)

min_strokes, max_strokes = st.session_state.stroke_range

# === Filter components ===
filtered_components = [
    comp for comp in component_map
    if min_strokes <= get_stroke_count(comp) <= max_strokes
]
sorted_components = sorted(filtered_components, key=get_stroke_count)

# === Input UI ===
col1, col2 = st.columns(2)

with col1:
    dropdown = st.selectbox(
        "Select a component:",
        options=sorted_components,
        format_func=lambda c: f"{c} ({get_stroke_count(c)} strokes)",
        index=sorted_components.index(st.session_state.last_dropdown)
        if st.session_state.last_dropdown in sorted_components else 0
    )

with col2:
    typed = st.text_input("Or type a component:", value=st.session_state.selected_comp if st.session_state.input_method == "text" else "")

# === Priority handling ===
# Text input first
if typed and typed != st.session_state.selected_comp and st.session_state.input_method != "text":
    st.session_state.selected_comp = typed
    st.session_state.input_method = "text"
    st.session_state.user_changed_stroke_range = False
    st.experimental_rerun()

# Dropdown next
elif dropdown != st.session_state.selected_comp:
    st.session_state.selected_comp = dropdown
    st.session_state.last_dropdown = dropdown
    st.session_state.input_method = "dropdown"
    st.session_state.user_changed_stroke_range = False
    # 👇 Simulate the "second click"
    time.sleep(0.05)
    st.experimental_rerun()

selected_comp = st.session_state.selected_comp

# === Display current selection ===
st.markdown(f"""
<h2 style='font-size: 1.2em;'>📌 Current Selection</h2>
<p><strong>Component:</strong> {selected_comp} &nbsp;&nbsp;
<strong>Level:</strong> {st.session_state.max_depth} &nbsp;&nbsp;
<strong>Stroke Range:</strong> {min_strokes} – {max_strokes}</p>
""", unsafe_allow_html=True)

# === Display results ===
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
