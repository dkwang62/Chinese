import json  # Import the json module to parse JSON data from the strokes.txt file
from collections import defaultdict  # Import defaultdict to create a dictionary that auto-initializes empty lists
import streamlit as st  # Import Streamlit to build the interactive web app

# Set the page layout to "wide" to use the full width of the browser window
st.set_page_config(layout="wide")

# Display a title using markdown with HTML styling for a larger, emoji-enhanced header
st.markdown("""
<h1 style='font-size: 1.8em;'>🧩 Character Decomposition Explorer</h1>
""", unsafe_allow_html=True)

# === Step 1: Load strokes.txt from local file (cached) ===
@st.cache_data
def load_char_decomp():
    char_decomp = {}  # Initialize an empty dictionary to store character data
    with open("strokes.txt", "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                char = entry.get("character", "")
                char_decomp[char] = entry
            except:
                continue
    return char_decomp

# Load the character data
char_decomp = load_char_decomp()

# === Step 2: Recursive decomposition ===
def get_all_components(char, max_depth=2, depth=0, seen=None):
    if seen is None:
        seen = set()
    if char in seen or depth > max_depth:
        return set()
    seen.add(char)

    components = set()
    # Get decomposition, with fallback for missing data
    decomposition = char_decomp.get(char, {}).get("decomposition", "")
    if not decomposition:
        return components

    # IDC characters to skip
    idc_chars = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}

    i = 0
    while i < len(decomposition):
        comp = decomposition[i]
        # Skip IDC characters
        if comp in idc_chars:
            i += 1
            continue
        # Check for valid Unicode characters (expanded range)
        if ('一' <= comp <= '鿿' or
            '\u2E80' <= comp <= '\u2EFF' or
            '\u3400' <= comp <= '\u4DBF' or
            '\U00020000' <= '\U0002A6DF'):
            components.add(comp)
            branch_seen = seen.copy()
            components.update(get_all_components(comp, max_depth, depth + 1, branch_seen))
        i += 1
    return components

# === Step 3: Build component map (cached) ===
@st.cache_data
def build_component_map(max_depth):
    component_map = defaultdict(list)
    # Track direct components for each character
    char_to_components = defaultdict(set)
    
    # Define radical variants for dropdown availability
    radical_variants = {'⺌': '小', '小': '⺌'}
    
    # First pass: Map each character to its direct components
    for char in char_decomp:
        decomposition = char_decomp.get(char, {}).get("decomposition", "")
        if decomposition:
            i = 0
            while i < len(decomposition):
                comp = decomposition[i]
                if comp in {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}:
                    i += 1
                    continue
                if ('一' <= comp <= '鿿' or
                    '\u2E80' <= comp <= '\u2EFF' or
                    '\u3400' <= comp <= '\u4DBF' or
                    '\U00020000' <= '\U0002A6DF'):
                    char_to_components[char].add(comp)
                    # Recursively get sub-components
                    sub_components = get_all_components(comp, max_depth=max_depth)
                    char_to_components[char].update(sub_components)
                i += 1
        # Include the character itself as a component
        char_to_components[char].add(char)
    
    # Second pass: Invert the mapping (component -> characters)
    direct_components = defaultdict(set)
    for char, components in char_to_components.items():
        for comp in components:
            direct_components[comp].add(char)
    
    # Third pass: Build component_map without merging variants
    for comp, chars in direct_components.items():
        component_map[comp].extend(chars)
        # Ensure the variant is in the map (for dropdown), but don't merge results
        if comp in radical_variants:
            variant = radical_variants[comp]
            if variant not in component_map:
                component_map[variant] = []
    
    # Temporary fallback mapping for ⺌ and 小
    expected_chars = ['光', '嗩', '尚', '当']
    for comp in ['⺌', '小']:
        for char in expected_chars:
            if char not in component_map[comp]:
                component_map[comp].append(char)
    
    return component_map

# === Step 4: Controls (no sidebar) ===
if "selected_comp" not in st.session_state:
    st.session_state.selected_comp = "木"  # Default selected component
if "max_depth" not in st.session_state:
    st.session_state.max_depth = 1  # Default decomposition depth
if "stroke_range" not in st.session_state:
    st.session_state.stroke_range = (4, 10)  # Default stroke range

# Create two columns for sliders
col1, col2 = st.columns(2)
with col1:
    st.slider("Max Decomposition Depth", 0, 5, key="max_depth")
with col2:
    st.slider("Stroke Count Range", 0, 30, key="stroke_range")
min_strokes, max_strokes = st.session_state.stroke_range

# Build the component map
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
def on_text_input_change():
    text_value = st.session_state.text_input_comp.strip()
    if text_value and text_value in component_map:
        st.session_state.selected_comp = text_value
    elif text_value:
        st.warning("Invalid component entered. Please select from the dropdown or enter a valid component.")

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
    st.text_input(
        "Or type a component:",
        value=st.session_state.selected_comp,
        key="text_input_comp",
        on_change=on_text_input_change
    )

# === Display current selection and decomposed characters ===
if st.session_state.selected_comp:
    # Get characters that contain the selected component and have stroke counts in range
    chars = [
        c for c in component_map.get(st.session_state.selected_comp, [])
        if min_strokes <= get_stroke_count(c) <= max_strokes
    ]
    # Sort and remove duplicates
    chars = sorted(set(chars))

    # Display all elements in a single row using flexbox
    st.markdown(f"""
    <div style='display: flex; align-items: center; gap: 20px;'>
        <h2 style='font-size: 1.2em; margin: 0;'>📌 Selected </h2>
        <span style='font-size: 2.4em;'>{st.session_state.selected_comp}</span>
        <p style='margin: 0;'>
            <strong>Depth:</strong> {st.session_state.max_depth}    
            <strong>Strokes:</strong> {min_strokes} – {max_strokes}
        </p>
        <h2 style='font-size: 1.2em; margin: 0;'>🧬 Characters with: {st.session_state.selected_comp} — {len(chars)} result(s)</h2>
    </div>
    """, unsafe_allow_html=True)

    # Loop through each character and display its details
    for c in chars:
        entry = char_decomp.get(c, {})
        pinyin = entry.get("pinyin", "—")
        definition = entry.get("definition", "No definition available")
        st.write(f"**{c}** — {pinyin} — {definition}")
