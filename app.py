import json
from collections import defaultdict
import streamlit as st

# Set page configuration
st.set_page_config(layout="wide")

# Custom CSS for styling
st.markdown("""
<style>
    .selected-card {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        display: flex;
        align-items: center;
        gap: 15px;
        border-left: 5px solid #3498db;
    }
    .selected-char { font-size: 2.5em; color: #e74c3c; margin: 0; }
    .details { font-size: 1.1em; color: #34495e; margin: 0; }
    .details strong { color: #2c3e50; }
    .results-header { font-size: 1.5em; color: #2c3e50; margin: 20px 0 10px; }
    .char-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .char-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 3px 8px rgba(0,0,0,0.15);
    }
    .char-title { font-size: 1.4em; color: #e74c3c; margin: 0; display: inline; }
    .compounds-section {
        background-color: #f1f8e9;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
    .compounds-title { font-size: 1.1em; color: #558b2f; margin: 0 0 5px; }
    .compounds-list { font-size: 1em; color: #34495e; margin: 0; }
    .debug-section { 
        background-color: #fef9e7; 
        padding: 10px; 
        border-radius: 5px; 
        margin-top: 10px; 
        font-size: 0.9em; 
        color: #7f8c8d; 
    }
    @media (max-width: 768px) {
        .selected-card { flex-direction: column; align-items: flex-start; padding: 10px; }
        .selected-char { font-size: 2em; }
        .details, .compounds-list { font-size: 0.95em; line-height: 1.5; }
        .results-header { font-size: 1.3em; }
        .char-card { padding: 10px; }
        .char-title { font-size: 1.2em; }
        .compounds-title { font-size: 1em; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    defaults = {
        "selected_comp": "⺌",
        "max_depth": 0,
        "stroke_range": (3, 14),
        "display_mode": "Single Character",
        "idc_filter": "Any"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# Load character decomposition data
@st.cache_data
def load_char_decomp():
    try:
        with open("strokes1.json", "r", encoding="utf-8") as f:
            return {entry["character"]: entry for entry in json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.error(f"Error loading strokes1.json: {str(e)}")
        return {}

char_decomp = load_char_decomp()

# Fallback decompositions for missing characters
FALLBACK_DECOMPS = {
    '尕': {'decomposition': '⿱⺌四', 'strokes': 5, 'pinyin': ['gǎ'], 'definition': 'small, little', 'radical': '小'}
}

# Utility functions
def is_valid_char(c):
    return ('一' <= c <= '鿿' or '\u2E80' <= c <= '\u2EFF' or
            '\u3400' <= c <= '\u4DBF' or '\U00020000' <= c <= '\U0002A6DF')

def get_stroke_count(char):
    return FALLBACK_DECOMPS.get(char, {}).get('strokes', char_decomp.get(char, {}).get("strokes", -1))

def clean_field(field):
    if isinstance(field, list):
        return field[0] if field else "—"
    return field if field else "—"

def get_idc(char):
    decomposition = FALLBACK_DECOMPS.get(char, {}).get('decomposition', char_decomp.get(char, {}).get("decomposition", ""))
    idc_chars = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}
    return decomposition[0] if decomposition and decomposition[0] in idc_chars else "—"

# IDC definitions
IDC_PATTERNS = {
    "Any": "Any structure",
    "⿰": "Left to right",
    "⿱": "Top to bottom",
    "⿲": "Left, middle, right",
    "⿳": "Top, middle, bottom",
    "⿴": "Full surround",
    "⿵": "Surround from above",
    "⿶": "Surround from below",
    "⿷": "Surround from left",
    "⿸": "Surround from upper left",
    "⿹": "Surround from upper right",
    "⿺": "Surround from lower left",
    "⿻": "Overlaid"
}

# Recursive decomposition
def get_all_components(char, max_depth, depth=0, seen=None):
    if seen is None:
        seen = set()
    if char in seen or depth > max_depth:
        return set()
    seen.add(char)
    components = set()
    decomposition = FALLBACK_DECOMPS.get(char, {}).get('decomposition', char_decomp.get(char, {}).get("decomposition", ""))
    idc_chars = set(IDC_PATTERNS.keys()) - {"Any"}
    
    for comp in decomposition:
        if comp in idc_chars:
            continue
        if is_valid_char(comp):
            components.add(comp)
            components.update(get_all_components(comp, max_depth, depth + 1, seen.copy()))
    return components

# Check if character matches IDC pattern
def matches_idc_pattern(char, selected_comp, idc_filter):
    if idc_filter == "Any":
        return True
    decomposition = FALLBACK_DECOMPS.get(char, {}).get('decomposition', char_decomp.get(char, {}).get("decomposition", ""))
    if not decomposition:
        return False
    # Apply radical variant mapping for ⺌ and 小
    radical_variants = {'⺌': '小', '小': '⺌'}
    effective_comp = [selected_comp]
    if selected_comp in radical_variants:
        effective_comp.append(radical_variants[selected_comp])
    # Check if decomposition starts with the IDC and contains the component or its variant
    idc_match = decomposition.startswith(idc_filter)
    comp_match = any(comp in decomposition for comp in effective_comp)
    return idc_match and comp_match

# Build component map
@st.cache_data
def build_component_map(max_depth):
    component_map = defaultdict(list)
    radical_variants = {'⺌': '小', '小': '⺌'}
    
    for char in char_decomp:
        components = set([char])  # Include the character itself
        decomposition = char_decomp.get(char, {}).get("decomposition", "")
        for comp in decomposition:
            if is_valid_char(comp):
                components.add(comp)
                components.update(get_all_components(comp, max_depth))
        
        for comp in components:
            component_map[comp].append(char)
    
    # Add variant mappings and expected characters
    for comp, variant in radical_variants.items():
        component_map[variant].extend(component_map[comp])
    for comp in ['⺌', '小']:
        for char in ['光', '嗩', '尚', '当', '尕', '尗']:
            if char not in component_map[comp]:
                component_map[comp].append(char)
    
    return component_map

# Component selection handler
def on_text_input_change():
    text_value = st.session_state.text_input_comp.strip()
    if text_value in component_map or text_value in char_decomp or text_value in FALLBACK_DECOMPS:
        st.session_state.selected_comp = text_value
    elif text_value:
        st.warning("Invalid character. Please enter a valid component.")

# UI Controls
def render_controls(component_map):
    min_strokes, max_strokes = st.session_state.stroke_range
    filtered_components = [
        comp for comp in component_map
        if min_strokes <= get_stroke_count(comp) <= max_strokes
    ]
    sorted_components = sorted(filtered_components, key=get_stroke_count)
    
    if st.session_state.selected_comp not in sorted_components:
        sorted_components.insert(0, st.session_state.selected_comp)
    
    st.slider("Max Decomposition Depth", 0, 5, key="max_depth")
    st.slider("Strokes Range", 0, 30, key="stroke_range")
    col1, col2 = st.columns(2)
    
    with col1:
        st.selectbox(
            "Select a component:",
            options=sorted_components,
            format_func=lambda c: f"{c} ({get_stroke_count(c)} strokes)",
            index=sorted_components.index(st.session_state.selected_comp) if st.session_state.selected_comp in sorted_components else 0,
            key="selected_comp"
        )
    with col2:
        st.text_input(
            "Or type a component:",
            value=st.session_state.selected_comp,
            key="text_input_comp",
            on_change=on_text_input_change
        )
    st.radio(
        "Display Mode:",
        options=["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"],
        key="display_mode"
    )
    st.selectbox(
        "Filter by Structure (IDC):",
        options=list(IDC_PATTERNS.keys()),
        format_func=lambda x: f"{x} {IDC_PATTERNS[x]}" if x != "Any" else IDC_PATTERNS[x],
        key="idc_filter"
    )

# Render character card
def render_char_card(char, compounds):
    entry = FALLBACK_DECOMPS.get(char, char_decomp.get(char, {}))
    fields = {
        "Pinyin": clean_field(entry.get("pinyin", "—")),
        "Definition": clean_field(entry.get("definition", "No definition available")),
        "Radical": clean_field(entry.get("radical", "—")),
        "Hint": clean_field(entry.get("etymology", {}).get("hint", "No hint available")),
        "Strokes": f"{get_stroke_count(char)} strokes" if get_stroke_count(char) != -1 else "unknown strokes",
        "IDC": get_idc(char)
    }
    
    details = " ".join(f"<strong>{k}:</strong> {v}  " for k, v in fields.items())
    st.markdown(f"""
    <div class='char-card'>
        <h3 class='char-title'>{char}</h3>
        <p class='details'>{details}</p>
    """, unsafe_allow_html=True)
    
    # Debug information for all characters
    decomposition = FALLBACK_DECOMPS.get(char, {}).get('decomposition', char_decomp.get(char, {}).get("decomposition", "No decomposition"))
    source = "FALLBACK_DECOMPS" if char in FALLBACK_DECOMPS else "strokes1.json"
    idc_match = decomposition.startswith(st.session_state.idc_filter) if st.session_state.idc_filter != "Any" else True
    comp_match = any(comp in decomposition for comp in [st.session_state.selected_comp, '小' if st.session_state.selected_comp == '⺌' else '⺌'])
    st.markdown(f"""
    <div class='debug-section'>
        <strong>Debug for {char}:</strong> Decomposition: {decomposition}, 
        Stroke Count: {get_stroke_count(char)}, 
        IDC Match: {idc_match}, 
        Component Match: {comp_match}, 
        Source: {source}
    </div>
    """, unsafe_allow_html=True)
    
    if compounds and st.session_state.display_mode != "Single Character":
        compounds_text = " ".join(sorted(compounds, key=lambda x: x[0]))
        st.markdown(f"""
        <div class='compounds-section'>
            <p class='compounds-title'>{st.session_state.display_mode} for {char}:</p>
            <p class='compounds-list'>{compounds_text}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# Main rendering
def main():
    st.markdown("<h1>🧩 Character Decomposition Explorer</h1>", unsafe_allow_html=True)
    component_map = build_component_map(st.session_state.max_depth)
    render_controls(component_map)
    
    if not st.session_state.selected_comp:
        return
    
    entry = FALLBACK_DECOMPS.get(st.session_state.selected_comp, char_decomp.get(st.session_state.selected_comp, {}))
    fields = {
        "Pinyin": clean_field(entry.get("pinyin", "—")),
        "Definition": clean_field(entry.get("definition", "No definition available")),
        "Radical": clean_field(entry.get("radical", "—")),
        "Hint": clean_field(entry.get("etymology", {}).get("hint", "No hint available")),
        "Strokes": f"{get_stroke_count(st.session_state.selected_comp)} strokes" if get_stroke_count(st.session_state.selected_comp) != -1 else "unknown strokes",
        "Depth": str(st.session_state.max_depth),
        "Stroke Range": f"{st.session_state.stroke_range[0]} – {st.session_state.stroke_range[1]}",
        "Structure": f"{st.session_state.idc_filter} {IDC_PATTERNS[st.session_state.idc_filter]}" if st.session_state.idc_filter != "Any" else IDC_PATTERNS[st.session_state.idc_filter]
    }
    details = " ".join(f"<strong>{k}:</strong> {v}  " for k, v in fields.items())
    
    st.markdown(f"""
    <div class='selected-card'>
        <h2 class='selected-char'>{st.session_state.selected_comp}</h2>
        <p class='details'>{details}</p>
    </div>
    """, unsafe_allow_html=True)
    
    min_strokes, max_strokes = st.session_state.stroke_range
    chars = [
        c for c in component_map.get(st.session_state.selected_comp, [])
        if min_strokes <= get_stroke_count(c) <= max_strokes and
        matches_idc_pattern(c, st.session_state.selected_comp, st.session_state.idc_filter)
    ]
    
    char_compounds = {}
    for c in chars:
        compounds = FALLBACK_DECOMPS.get(c, char_decomp.get(c, {})).get("compounds", [])
        if st.session_state.display_mode == "Single Character":
            char_compounds[c] = []
        else:
            length = int(st.session_state.display_mode[0])
            char_compounds[c] = [comp for comp in compounds if len(comp) == length]
    
    filtered_chars = [c for c in chars if not char_compounds[c] == [] or st.session_state.display_mode == "Single Character"]
    st.markdown(f"<h2 class='results-header'>🧬 Characters with {st.session_state.selected_comp} ({st.session_state.idc_filter} {IDC_PATTERNS[st.session_state.idc_filter]}) — {len(filtered_chars)} result(s)</h2>", unsafe_allow_html=True)
    
    for char in sorted(filtered_chars, key=get_stroke_count):
        render_char_card(char, char_compounds.get(char, []))

if __name__ == "__main__":
    main()
