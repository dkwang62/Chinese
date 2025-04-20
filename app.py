import json
from collections import defaultdict
import streamlit as st

st.title("Chinese Character Decomposition Explorer")

# === Step 1: Upload strokes.txt ===
uploaded_file = st.file_uploader("Upload `strokes.txt`", type="txt")

if uploaded_file:

    # === Step 2: Load and parse dictionary (cached) ===
    @st.cache_data
    def parse_uploaded_file(file):
        char_decomp = {}
        for line in file:
            try:
                entry = json.loads(line.decode('utf-8'))
                char = entry.get("character", "")
                char_decomp[char] = entry
            except:
                continue
        return char_decomp

    char_decomp = parse_uploaded_file(uploaded_file)

    # === Step 3: Recursive decomposition ===
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

    # === Step 4: Build component map (cached) ===
    @st.cache_data
    def build_component_map(max_depth):
        component_map = defaultdict(list)
        for char in char_decomp:
            all_components = get_all_components(char, max_depth=max_depth)
            for comp in all_components:
                component_map[comp].append(char)
        return component_map

    # === Step 5: Controls ===
    st.sidebar.header("Filters")
    max_depth = st.sidebar.slider("Max Decomposition Depth", 0, 5, 2)
    min_strokes = st.sidebar.slider("Minimum Stroke Count", 0, 20, 2)
    max_strokes = min_strokes + 2
    search_input = st.text_input("Search for a component (e.g. 木):")

    component_map = build_component_map(max_depth=max_depth)

    def get_stroke_count(char):
        return char_decomp.get(char, {}).get("strokes", float('inf'))

    # Filter dropdown options
    filtered_components = [
        comp for comp in component_map
        if min_strokes <= get_stroke_count(comp) <= max_strokes
    ]
    sorted_components = sorted(filtered_components, key=get_stroke_count)

    selected_comp = None
    if not search_input:
        selected_comp = st.selectbox(
            "Select a component:",
            options=sorted_components,
            format_func=lambda c: f"{c} ({get_stroke_count(c)} strokes)"
        )
    else:
        selected_comp = search_input.strip()

    # === Step 6: Display characters ===
    if selected_comp:
        chars = [
            c for c in component_map.get(selected_comp, [])
            if char_decomp.get(c, {}).get("strokes", 0) > min_strokes
        ]
        chars = sorted(set(chars))

        st.subheader(f"Component: {selected_comp} — {len(chars)} characters (strokes > {min_strokes})")
        for c in chars:
            entry = char_decomp.get(c, {})
            pinyin = entry.get("pinyin", "—")
            definition = entry.get("definition", "No definition available")
            st.write(f"**{c}** — {pinyin} — {definition}")
else:
    st.info("Please upload a valid `strokes.txt` file to begin.")
