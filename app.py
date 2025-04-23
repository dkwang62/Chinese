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
# Define a function to load character data from strokes.txt, cached to avoid reloading
@st.cache_data  # Cache the result to improve performance by reusing the data
def load_char_decomp():
    char_decomp = {}  # Initialize an empty dictionary to store character data
    # Open the strokes.txt file in read mode with UTF-8 encoding for Chinese characters
    with open("strokes.txt", "r", encoding="utf-8") as f:
        # Loop through each line in the file
        for line in f:
            try:
                # Parse the line as JSON and strip whitespace
                entry = json.loads(line.strip())
                # Get the "character" field from the JSON entry (e.g., "木")
                char = entry.get("character", "")
                # Store the entire JSON entry in the dictionary with the character as the key
                char_decomp[char] = entry
            except:
                # Skip any lines that fail to parse as JSON (e.g., malformed data)
                continue
    # Return the dictionary containing all character data
    return char_decomp

# Load the character data by calling the function and store it in char_decomp
char_decomp = load_char_decomp()

# === Step 2: Recursive decomposition ===
# Define a function to find all sub-components of a character up to a maximum depth
def get_all_components(char, max_depth=2, depth=0, seen=None):
    # Initialize an empty set to track seen characters if none provided (avoids infinite loops)
    if seen is None:
        seen = set()
    # Stop if the character was already seen or depth exceeds max_depth to prevent over-decomposition
    if char in seen or depth > max_depth:
        return set()
    # Add the current character to the seen set to avoid revisiting it
    seen.add(char)

    # Initialize an empty set to store components of the current character
    components = set()
    # Get the "decomposition" field for the character (e.g., sub-characters it’s made of)
    # Loop through each component in the decomposition string
    for comp in char_decomp.get(char, {}).get("decomposition", ""):
        # Check if the component is a Chinese character (Unicode range U+4E00 to U+9FFF)
        if '\u4e00' <= comp <= '\u9fff':
            # Add the component to the set
            components.add(comp)
            # Recursively get sub-components of this component, increasing depth by 1
            components.update(get_all_components(comp, max_depth, depth + 1, seen))
    # Return the set of all components found
    return components

# === Step 3: Build component map (cached) ===
# Define a function to create a map of components to characters that contain them
@st.cache_data  # Cache the result to avoid recomputing the map unnecessarily
def build_component_map(max_depth):
    # Initialize a defaultdict that auto-creates empty lists for new keys
    component_map = defaultdict(list)
    # Loop through each character in the loaded data
    for char in char_decomp:
        # Get all components of the character up to the specified max_depth
        all_components = get_all_components(char, max_depth=max_depth)
        # For each component, add the character to its list in the map
        for comp in all_components:
            component_map[comp].append(char)
    # Return the completed component map
    return component_map

# === Step 4: Controls (no sidebar) ===
# Initialize session state variables if they don’t exist to persist user selections
# Session state keeps values across script reruns (Streamlit reruns the script on each interaction)
if "selected_comp" not in st.session_state:
    st.session_state.selected_comp = "木"  # Default selected component is "木" (wood)
if "max_depth" not in st.session_state:
    st.session_state.max_depth = 1  # Default decomposition depth is 1
if "stroke_range" not in st.session_state:
    st.session_state.stroke_range = (4, 10)  # Default stroke range is 4 to 10

# Create two columns for sliders to organize the layout
col1, col2 = st.columns(2)
with col1:
    # Add a slider for max decomposition depth, bound to st.session_state.max_depth
    # Range: 0 to 5, default is st.session_state.max_depth
    st.slider("Max Decomposition Depth", 0, 5, key="max_depth")
with col2:
    # Add a slider for stroke count range, bound to st.session_state.stroke_range
    # Range: 0 to 30, default is st.session_state.stroke_range
    st.slider("Stroke Count Range", 0, 30, key="stroke_range")
# Unpack the stroke range tuple into min and max values
min_strokes, max_strokes = st.session_state.stroke_range

# Build the component map using the current max_depth from session state
component_map = build_component_map(max_depth=st.session_state.max_depth)

# === Helper: Get stroke count ===
# Define a function to get the stroke count of a character
def get_stroke_count(char):
    # Get the "strokes" field from char_decomp, default to infinity if not found
    return char_decomp.get(char, {}).get("strokes", float('inf'))

# === Filter dropdown options ===
# Create a list of components that have stroke counts within the selected range
filtered_components = [
    comp for comp in component_map
    if min_strokes <= get_stroke_count(comp) <= max_strokes
]
# Sort the components by stroke count for a user-friendly dropdown
sorted_components = sorted(filtered_components, key=get_stroke_count)

# === Component selection (dropdown + text input) ===
# Define a callback function to handle changes in the text input
def on_text_input_change():
    """Callback to handle text input changes."""
    # Get the text input value and remove whitespace
    text_value = st.session_state.text_input_comp.strip()
    # If the text is non-empty and a valid component, update the selected component
    if text_value and text_value in component_map:
        st.session_state.selected_comp = text_value
    # If the text is non-empty but invalid, show a warning
    elif text_value:
        st.warning("Invalid component entered. Please select from the dropdown or enter a valid component.")

# Create two columns for the dropdown and text input
col_a, col_b = st.columns(2)
with col_a:
    # Add a dropdown (selectbox) for choosing a component
    # Options are sorted_components, formatted to show character and stroke count
    # Index is set to the current selected_comp’s position in sorted_components, or 0 if not found
    # Key binds the dropdown to st.session_state.selected_comp
    st.selectbox(
        "Select a component:",
        options=sorted_components,
        format_func=lambda c: f"{c} ({get_stroke_count(c)} strokes)",  # Show e.g., "木 (4 strokes)"
        index=sorted_components.index(st.session_state.selected_comp) if st.session_state.selected_comp in sorted_components else 0,
        key="selected_comp"
    )
with col_b:
    # Add a text input for typing a component
    # Value is set to the current selected_comp to stay in sync with the dropdown
    # Key binds the input to st.session_state.text_input_comp
    # on_change calls the callback when the user types and presses Enter
    st.text_input(
        "Or type a component:",
        value=st.session_state.selected_comp,
        key="text_input_comp",
        on_change=on_text_input_change
    )

# === Display current selection ===
# Display the current selection using markdown with HTML styling
# Show the selected component, decomposition level, and stroke range
st.markdown(f"""
<h2 style='font-size: 1.2em;'>📌 Current Selection</h2>
<p><strong>Component:</strong> {st.session_state.selected_comp}    <strong>Level:</strong> {st.session_state.max_depth}    <strong>Stroke Range:</strong> {min_strokes} – {max_strokes}</p>
""", unsafe_allow_html=True)

# === Step 5: Display decomposed characters ===
# Check if a component is selected (non-empty)
if st.session_state.selected_comp:
    # Get characters that contain the selected component and have stroke counts in range
    chars = [
        c for c in component_map.get(st.session_state.selected_comp, [])
        if min_strokes <= get_stroke_count(c) <= max_strokes
    ]
    # Sort and remove duplicates from the character list
    chars = sorted(set(chars))

    # Display a header with the selected component and number of results
    st.markdown(
        f"<h2 style='font-size: 1.2em;'>🧬 Characters with: {st.session_state.selected_comp} — {len(chars)} result(s)</h2>",
        unsafe_allow_html=True
    )
    # Loop through each character and display its details
    for c in chars:
        # Get the character’s data from char_decomp
        entry = char_decomp.get(c, {})
        # Get pinyin and definition, with fallbacks if not available
        pinyin = entry.get("pinyin", "—")
        definition = entry.get("definition", "No definition available")
        # Display the character, pinyin, and definition in bold
        st.write(f"**{c}** — {pinyin} — {definition}")
