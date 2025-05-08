import json
import random
from collections import defaultdict
import streamlit as st
import os

st.set_page_config(layout="wide")

# --- Custom CSS ---
st.markdown("""<style>
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
    defaults = {
        "selected_comp": "⺌",
        "max_depth": 1,
        "stroke_range": (3, 14),
        "display_mode": "Single Character",
        "selected_idc": "No Filter",
        "text_input_comp": "⺌"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

@st.cache_data
def load_char_decomp():
    try:
        with open("strokes1.json", "r", encoding="utf-8") as f:
            return {entry["character"]: entry for entry in json.load(f)}
    except Exception as e:
        st.error(f"Failed to load strokes1.json: {e}")
        return {}

char_decomp = load_char_decomp()

def is_valid_char(c):
    return ('一' <= c <= '鿿' or '⺀' <= c <= '⻿' or '㐀' <= c <= '䶿' or '𠀀' <= c <= '𪛟') and len(c) == 1

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

def on_text_input_change(component_map):
    text_value = st.session_state.text_input_comp.strip()
    if text_value in component_map or text_value in char_decomp:
        st.session_state.selected_comp = text_value
        st.session_state.text_input_comp = text_value
        st.rerun()
    elif text_value:
        st.warning("Invalid character. Please enter a valid component.")

def on_output_char_select():
    selected_char = st.session_state.output_char_select
    if selected_char != "Select a character...":
        st.session_state.selected_comp = selected_char
        st.session_state.text_input_comp = selected_char
        st.rerun()

component_map = build_component_map(st.session_state.max_depth)

# --- Input box for character ---
st.text_input("Enter a Chinese character component:",
              key="text_input_comp",
              value=st.session_state.text_input_comp,
              on_change=on_text_input_change, args=(component_map,))

# --- Display Selected Character Info ---
selected_char = st.session_state.selected_comp
char_info = char_decomp.get(selected_char, {})
st.markdown(f"""
<div class='selected-card'>
    <div class='selected-char'>{selected_char}</div>
    <div class='details'>
        <p><strong>Strokes:</strong> {char_info.get('strokes', '—')}</p>
        <p><strong>Decomposition:</strong> {char_info.get('decomposition', '—')}</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Display related characters ---
st.markdown("<div class='results-header'>Related Characters</div>", unsafe_allow_html=True)
related_chars = component_map.get(selected_char, [])
for char in sorted(related_chars):
    strokes = get_stroke_count(char)
    decomposition = clean_field(char_decomp.get(char, {}).get("decomposition", "—"))
    st.markdown(f"""
    <div class='char-card'>
        <p class='char-title'>{char}</p> — {strokes} strokes — Decomposition: {decomposition}
    </div>
    """, unsafe_allow_html=True)

# --- Dropdown for selecting a single character from results ---
single_chars_only = sorted(set([c for c in related_chars if len(c) == 1 and is_valid_char(c)]))
if single_chars_only:
    options = ["Select a character..."] + single_chars_only
    st.selectbox("🔍 Choose a character from results:", options=options,
                 key="output_char_select", on_change=on_output_char_select)
