import json
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components
import random
import os

st.set_page_config(layout="wide")

# --- Custom CSS ---
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
    .clickable-char {
        cursor: pointer;
        color: #e74c3c;
        transition: color 0.2s;
    }
    .clickable-char:hover {
        color: #c0392b;
        text-decoration: underline;
    }
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

# --- Initialize session state ---
def init_session_state():
    config_options = [
        {
            "selected_comp": "爫",
            "max_depth": 1,
            "stroke_range": (4, 14)
        },
        {
            "selected_comp": "⺌",
            "max_depth": 0,
            "stroke_range": (3, 14)
        }
    ]
    selected_config = random.choice(config_options)
    defaults = {
        "selected_comp": selected_config["selected_comp"],
        "max_depth": selected_config["max_depth"],
        "stroke_range": selected_config["stroke_range"],
        "display_mode": "Single Character",
        "selected_idc": "No Filter",
        "idc_refresh": False,
        "clicked_char": "",
        "text_input_comp": selected_config["selected_comp"]  # Initialize text_input_comp
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- Load character decomposition data ---
@st.cache_data
def load_char_decomp():
    if not os.path.exists("strokes1.json"):
        st.error("Error: strokes1.json not found in the app directory.")
        return {}
    try:
        with open("strokes1.json", "r", encoding="utf-8") as f:
            return {entry["character"]: entry for entry in json.load(f)}
    except Exception as e:
        st.error(f"Failed to load strokes1.json: {e}")
        return {}

char_decomp = load_char_decomp()

# --- Fallback UI if data is missing ---
if not char_decomp:
    st.markdown("<h1>🧩 Character Decomposition Explorer</h1>", unsafe_allow_html=True)
    st.error("Cannot load character data. Please ensure strokes1.json is available and correctly formatted.")
    st.stop()

# --- Utility functions ---
def is_valid_char(c):
    return ('一' <= c <= '鿿' or '⺀' <= c <= '⻿' or '㐀' <= c <= '䶿' or '𠀀' <= c <= '𪛟')

def get_stroke_count(char):
    return char_decomp.get(char, {}).get("strokes", -1)

def clean_field(field):
    if isinstance(field, list):
        return field[0] if field else "—"
    return field if field else "—"

def get_all_components(char, max_depth, depth=0, seen=None):
    if seen is None:
        seen = set()
    if char in seen or depth > max_depth:
        return set()
    seen.add(char)
    components = set()
    decomposition = char_decomp.get(char, {}).get("decomposition", "")
    idc_chars = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}
    for comp in decomposition:
        if comp in idc_chars or not is_valid_char(comp):
            continue
        components.add(comp)
        components.update(get_all_components(comp, max_depth, depth + 1, seen.copy()))
    return components

@st.cache_data
def build_component_map(max_depth):
    component_map = defaultdict(list)
    for char in char_decomp:
        components = set()
        decomposition = char_decomp.get(char, {}).get("decomposition", "")
        for comp in decomposition:
            if is_valid_char(comp):
                components.add(comp)
                components.update(get_all_components(comp, max_depth))
        components.add(char)
        for comp in components:
            component_map[comp].append(char)
    return component_map

# --- Handle text input ---
def on_text_input_change(component_map):
    # Safely access text_input_comp
    text_value = st.session_state.get("text_input_comp", "").strip()
    if not text_value:  # If still empty, use selected_comp as fallback
        text_value = st.session_state.selected_comp
    if text_value in component_map or text_value in char_decomp or is_valid_char(text_value):
        st.session_state.selected_comp = text_value
        st.session_state.idc_refresh = not st.session_state.idc_refresh
        st.session_state.text_input_comp = text_value  # Ensure it's set
        st.experimental_rerun()
    elif text_value:
        st.warning("Invalid character. Please enter a valid component.")

# --- Handle character click ---
def on_char_click(component_map):
    if "clicked_char" in st.session_state and st.session_state.clicked_char:
        char = st.session_state.clicked_char
        st.write(f"Clicked character: {char}")  # Debugging
        st.write(f"Valid char: {is_valid_char(char)}, In component_map: {char in component_map}, In char_decomp: {char in char_decomp}")
        if is_valid_char(char):
            st.session_state.selected_comp = char
            st.session_state.idc_refresh = not st.session_state.idc_refresh
            st.session_state.clicked_char = ""
            st.experimental_rerun()
        else:
            st.warning(f"Invalid character clicked: {char}")

# --- Render controls ---
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

    idc_chars = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}
    chars = [
        c for c in component_map.get(st.session_state.selected_comp, [])
        if min_strokes <= get_stroke_count(c) <= max_strokes and c in char_decomp
    ]
    dynamic_idc_options = {"No Filter"}
    for char in chars:
        decomposition = char_decomp.get(char, {}).get("decomposition", "")
        if decomposition and len(decomposition) > 0 and decomposition[0] in idc_chars:
            dynamic_idc_options.add(decomposition[0])
    idc_options = sorted(list(dynamic_idc_options))
    if st.session_state.selected_idc not in idc_options:
        st.session_state.selected_idc = "No Filter"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.selectbox("Select a component:", options=sorted_components,
                     format_func=lambda c: f"{c} ({get_stroke_count(c)} strokes)",
                     index=sorted_components.index(st.session_state.selected_comp),
                     key="selected_comp",
                     on_change=lambda: st.session_state.update(idc_refresh=not st.session_state.idc_refresh))
    with col2:
        st.text_input("Or type a component:", value=st.session_state.selected_comp,
                      key="text_input_comp", on_change=on_text_input_change, args=(component_map,))
    with col3:
        st.selectbox("Result filtered by IDC Character structure:", options=idc_options,
                     index=idc_options.index(st.session_state.selected_idc), key="selected_idc")

    st.radio("Display Mode:", options=["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"],
             key="display_mode")

# --- Render character card ---
def render_char_card(char, compounds):
    entry = char_decomp.get(char, {})
    idc_chars = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}
    decomposition = entry.get("decomposition", "")
    idc = decomposition[0] if decomposition and decomposition[0] in idc_chars else "—"
    fields = {
        "Pinyin": clean_field(entry.get("pinyin", "—")),
        "Definition": clean_field(entry.get("definition", "No definition available")),
        "Radical": clean_field(entry.get("radical", "—")),
        "Hint": clean_field(entry.get("etymology", {}).get("hint", "No hint available")),
        "Strokes": f"{get_stroke_count(char)} strokes" if get_stroke_count(char) != -1 else "unknown strokes",
        "IDC": idc
    }
    details = " ".join(f"<strong>{k}:</strong> {v}  " for k, v in fields.items())
    
    char_id = f"char_{char}_{random.randint(10000, 99999)}"
    st.markdown(
        f"""<div class='char-card'><h3 class='char-title'><span class='clickable-char' id='{char_id}' onclick='handleCharClick("{char}")'>{char}</span></h3><p class='details'>{details}</p>""",
        unsafe_allow_html=True
    )
    
    if compounds and st.session_state.display_mode != "Single Character":
        compounds_text = " ".join(sorted(compounds, key=lambda x: x[0]))
        st.markdown(
            f"""<div class='compounds-section'><p class='compounds-title'>{st.session_state.display_mode} for {char}:</p><p class='compounds-list'>{compounds_text}</p></div>""",
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

# --- Main function ---
def main():
    st.markdown("<h1>🧩 Character Decomposition Explorer</h1>", unsafe_allow_html=True)
    
    # Clear cache if max_depth changes
    if "prev_max_depth" not in st.session_state:
        st.session_state.prev_max_depth = st.session_state.max_depth
    if st.session_state.max_depth != st.session_state.prev_max_depth:
        st.cache_data.clear()
        st.session_state.prev_max_depth = st.session_state.max_depth

    component_map = build_component_map(st.session_state.max_depth)
    
    # Debugging: Show map sizes
    st.write(f"component_map size: {len(component_map)}, char_decomp size: {len(char_decomp)}")
    # st.write(f"Sample component_map keys: {list(component_map.keys())[:5]}")

    render_controls(component_map)

    if st.button("Reset App"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        init_session_state()
        st.cache_data.clear()
        st.experimental_rerun()

    if "clicked_char" not in st.session_state:
        st.session_state.clicked_char = ""

    # Debug: Display session state
    st.write(f"Current clicked_char: {st.session_state.clicked_char}")
    st.write(f"Current selected_comp: {st.session_state.selected_comp}")

    on_char_click(component_map)

    components.html(
        """
        <script>
        function handleCharClick(char) {
            console.log('Clicked char: ' + char);
            if (window.Streamlit) {
                window.Streamlit.setComponentValue(char, 'clicked_char');
            } else {
                console.error('Streamlit API not available, trying postMessage');
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: char,
                    dataType: 'string',
                    key: 'clicked_char'
                }, '*');
            }
        }
        </script>
        """,
        height=0
    )

    if not st.session_state.selected_comp:
        st.info("Please select or type a component to begin.")
        return

    entry = char_decomp.get(st.session_state.selected_comp, {})
    fields = {
        "Pinyin": clean_field(entry.get("pinyin", "—")),
        "Definition": clean_field(entry.get("definition", "No definition available")),
        "Radical": clean_field(entry.get("radical", "—")),
        "Hint": clean_field(entry.get("etymology", {}).get("hint", "No hint available")),
        "Strokes": f"{get_stroke_count(st.session_state.selected_comp)} strokes" if get_stroke_count(st.session_state.selected_comp) != -1 else "unknown strokes",
        "Depth": str(st.session_state.max_depth),
        "Stroke Range": f"{st.session_state.stroke_range[0]} – {st.session_state.stroke_range[1]}"
    }
    details = " ".join(f"<strong>{k}:</strong> {v}  " for k, v in fields.items())
    
    char_id = f"selected_char_{random.randint(10000, 99999)}"
    st.markdown(
        f"""<div class='selected-card'><h2 class='selected-char'><span class='clickable-char' id='{char_id}' onclick='handleCharClick("{st.session_state.selected_comp}")'>{st.session_state.selected_comp}</span></h2><p class='details'>{details}</p></div>""",
        unsafe_allow_html=True
    )

    min_strokes, max_strokes = st.session_state.stroke_range
    chars = [c for c in component_map.get(st.session_state.selected_comp, [])
             if min_strokes <= get_stroke_count(c) <= max_strokes]
    if st.session_state.selected_idc != "No Filter":
        chars = [c for c in chars if char_decomp.get(c, {}).get("decomposition", "").startswith(st.session_state.selected_idc)]

    char_compounds = {}
    for c in chars:
        compounds = char_decomp.get(c, {}).get("compounds", [])
        if st.session_state.display_mode == "Single Character":
            char_compounds[c] = []
        else:
            length = int(st.session_state.display_mode[0])
            char_compounds[c] = [comp for comp in compounds if len(comp) == length]

    filtered_chars = [c for c in chars if not char_compounds[c] == [] or st.session_state.display_mode == "Single Character"]
    st.markdown(f"<h2 class='results-header'>🧬 Characters with {st.session_state.selected_comp} — {len(filtered_chars)} result(s)</h2>", unsafe_allow_html=True)

    for char in sorted(filtered_chars, key=get_stroke_count):
        render_char_card(char, char_compounds.get(char, []))

    if filtered_chars:
        export_text = "Give me the full hanyu pinyin and meaning of each compound word\n\n"
        export_text += "\n".join(
            f"{compound}"
            for char in filtered_chars
            for compound in char_compounds.get(char, [])
        )
        st.text_area("Right click, Select all, copy; paste to ChatGPT", export_text, height=300, key="export_text")

        components.html(f"""
            <textarea id="copyTarget" style="opacity:0;position:absolute;left:-9999px;">{export_text}</textarea>
            <script>
            const copyText = document.getElementById("copyTarget");
            copyText.select();
            document.execCommand("copy");
            </script>
        """, height=0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Critical error: {e}")
        st.write("Please check the terminal or deployment logs for details.")
