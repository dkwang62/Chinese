# app.py
# Radix – Component-first Chinese character explorer (with splash onboarding)
import json
import math
import html
import streamlit as st
from streamlit.components.v1 import html as st_html

# --- Optional: OpenCC for Traditional/Simplified Conversion ---
try:
    from opencc import OpenCC
    cc_t2s = OpenCC("t2s")
    cc_s2t = OpenCC("s2t")
except ImportError:
    cc_t2s = None
    cc_s2t = None

st.set_page_config(layout="wide", page_title="Radix", page_icon="🈑")

IDC_CHARS = {"⿰", "⿱", "⿲", "⿳", "⿴", "⿵", "⿶", "⿷", "⿸", "⿹", "⿺", "⿻"}

def apply_dynamic_css():
    css = """
    <style>
    .results-header-sidebar {font-size: 1.4em; font-weight: bold; color: #2c3e50; margin: 20px 0 10px 0; text-align: center;}
    /* Char card styling */
    .char-card {background: white; padding: 20px; border-radius: 10px; margin-bottom: 0px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);}
    .meta-row {font-size: 0.95em; color: #555; margin-bottom: 8px; display: flex; align-items: center; flex-wrap: wrap; gap: 10px;}
    .meta-pinyin {font-weight: bold; font-size: 1.1em; color: #2c3e50;}
    /* Tags */
    .meta-tag {background: #f1f3f5; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; color: #495057;}
    /* Traditional Tag (Yellow) */
    .meta-tag-trad {background: #fff8e1; color: #856404; border: 1px solid #ffeeba;}
    /* Simplified Tag (Green) */
    .meta-tag-simp {background: #d1e7dd; color: #0f5132; border: 1px solid #badbcc;}
    .def-row {font-size: 1.1em; line-height: 1.4; color: #2c3e50; margin-bottom: 8px;}
    .ety-row {font-size: 0.9em; color: #666; font-style: italic; border-top: 1px solid #eee; padding-top: 8px; margin-top: 4px;}
    /* Grid buttons */
    .comp-grid .stButton button {font-size: 2em; height: 80px; background: white; border: 1px solid #e0e0e0; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); padding: 0; line-height: 80px;}
    .comp-grid .stButton button:hover {background: #fff5f5; border-color: #f2c6c6; color: #c0392b;}
    /* Character explore buttons in results */
    div[data-testid="column"]:nth-child(2) .stButton button {font-size: 3.5em; font-weight: bold; background: white; border: 2px solid #e0e0e0; border-radius: 12px; padding: 10px; min-height: 100px; transition: all 0.2s ease;}
    div[data-testid="column"]:nth-child(2) .stButton button:hover {background: #f0f9ff; border-color: #3b82f6; transform: scale(1.05); box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);}
    /* Status line */
    .status-line {font-size: 1.1em; font-weight: 600; color: #0f5132; background-color: #d1e7dd; border: 1px solid #badbcc; padding: 15px; border-radius: 8px; margin: 20px 0 30px 0; text-align: center;}
    .status-tag {background-color: #f1f3f5; color: #2c3e50; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.9em; border: 1px solid #e9ecef; display: inline-flex; align-items: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);}
    .status-text {color: #0f5132; font-size: 0.95em; margin-left: 10px;}
    /* Sidebar Count Lines */
    .preview-count-line {font-size: 1.3em; text-align: center; color: #2c3e50; margin: 20px 0 25px 0;}
    .preview-count-line .char {font-size: 1.4em; font-weight: bold; color: #e74c3c;}
    /* General UI */
    .jump-footer {margin-top: 40px; padding: 20px; background: #f8f9fa; border-top: 1px solid #e0e0e0; text-align: center;}
    div[data-testid="stExpander"] .stButton button {font-size: 1.2rem; height: 40px; padding: 0; line-height: 1.2; border-radius: 4px; border: 1px solid #eee; transition: all 0.1s ease-in-out;}
    div[data-testid="stExpander"] .stButton button:hover {border-color: #bbb; background-color: #f0f0f0;}
    .stroke-header {font-size: 0.85em; color: #888; border-bottom: 1px solid #eee; margin: 10px 0 5px 0; padding-bottom: 2px;}
    /* Compound List Styling */
    .compound-item { display: flex; align-items: baseline; margin-bottom: 6px; padding-bottom: 6px; border-bottom: 1px solid #e0e0e0; }
    .compound-item:last-child { border-bottom: none; margin-bottom: 0; }
    .cp-word { font-weight: bold; font-size: 1.1em; color: #2c3e50; min-width: 80px; margin-right: 10px; }
    .cp-pinyin { color: #d35400; font-family: monospace; margin-right: 10px; font-weight: 500;}
    .cp-mean { color: #333; font-size: 0.95em; flex: 1; }
    /* Splash */
    .splash-wrap {max-width: 1100px; margin: 0 auto; padding: 34px 10px 10px 10px;}
    .splash-card {background: white; border: 1px solid #eee; border-radius: 18px; padding: 34px; box-shadow: 0 6px 22px rgba(0,0,0,0.06);}
    .splash-title {font-size: 2.3em; font-weight: 850; line-height: 1.12; color:#111;}
    .splash-sub {margin-top: 10px; font-size: 1.15em; color:#444; line-height: 1.5;}
    .splash-demo {margin-top: 18px; padding: 14px 16px; background:#f8f9fa; border:1px solid #eee; border-radius: 14px;}
    .splash-demo-h {font-weight: 750; color:#333; margin-bottom: 8px;}
    .splash-tip {text-align:center; color:#777; margin-top: 10px;}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

@st.cache_data
def load_all_data():
    try:
        with open("enhanced_component_map_with_etymology.json", "r", encoding="utf-8") as f:
            component_map = json.load(f)
    except FileNotFoundError:
        st.error("File 'enhanced_component_map_with_etymology.json' not found.")
        st.stop()

    # Pre-compute usage counts
    usage_counts = {}
    all_used_components = set()
    for comp, data in component_map.items():
        related = data.get("related_characters", [])
        unique_chars = {c for c in related if isinstance(c, str) and len(c) == 1}
        usage_counts[comp] = len(unique_chars)
        all_used_components.update(unique_chars)

    # Pre-compute stroke counts
    stroke_counts = {}
    for c, data in component_map.items():
        strokes = data.get("meta", {}).get("strokes")
        if isinstance(strokes, (int, float)) and strokes > 0:
            stroke_counts[c] = int(strokes)
        elif isinstance(strokes, str) and strokes.isdigit():
            stroke_counts[c] = int(strokes)
        else:
            stroke_counts[c] = None

    # Pre-compute filter data
    rad_groups = {}
    rad_counts = {}
    idc_counts = {}
    for c, data in component_map.items():
        meta = data.get("meta", {})
        radical = meta.get("radical")
        if radical:
            rad_counts[radical] = rad_counts.get(radical, 0) + 1
            gs = stroke_counts.get(radical, 999)
            rad_groups.setdefault(gs, []).append(radical)
        decomp = meta.get("decomposition", "")
        if decomp and decomp[0] in IDC_CHARS:
            idc = decomp[0]
            idc_counts[idc] = idc_counts.get(idc, 0) + 1

    for gs in rad_groups:
        rad_groups[gs].sort()

    return (
        component_map,
        usage_counts,
        stroke_counts,
        all_used_components,
        rad_groups,
        rad_counts,
        idc_counts
    )

component_map, usage_counts, stroke_counts, used_components, rad_groups, rad_counts, idc_counts = load_all_data()

@st.cache_data
def load_phrases():
    try:
        with open("phrases_dict.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

phrases_dict = load_phrases()

def clean_field(field):
    return field[0] if isinstance(field, list) and field else field or "–"

def get_etymology_text(meta):
    etymology = meta.get("etymology", {})
    hint = clean_field(etymology.get("hint", ""))
    if not hint or hint.lower() == "no hint":
        hint = ""
    details = clean_field(etymology.get("details", ""))
    if details == "–":
        details = ""
    parts = [p for p in [hint, details] if p]
    return "; ".join(parts) if parts else None

def format_decomposition(char):
    d = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    return "–" if not d or "?" in d else d

# --- Compact animated stroke order for sidebar ---
def render_stroke_order_sidebar(char: str, size: int = 110):
    char = (char or "").strip()[:1]
    if not char:
        return
    h = size + 40
    st_html(
        f"""
        <div style="display:flex; justify-content:center; margin:20px 0;">
            <div id="sb-hw-{hash(char)}" style="width:{size}px; height:{size}px;"></div>
        </div>
        <script>
        (function() {{
            const char = {json.dumps(char, ensure_ascii=False)};
            const target = "sb-hw-{hash(char)}";
            async function loadScript(src) {{
                return new Promise((resolve, reject) => {{
                    const s = document.createElement('script');
                    s.src = src; s.async = true; s.onload = resolve; s.onerror = reject;
                    document.head.appendChild(s);
                }});
            }}
            async function ensureLib() {{
                if (window.HanziWriter) return;
                const sources = ['https://cdn.jsdelivr.net/npm/hanzi-writer@3/dist/hanzi-writer.min.js',
                                 'https://unpkg.com/hanzi-writer@3/dist/hanzi-writer.min.js'];
                for (const src of sources) {{ try {{ await loadScript(src); if (window.HanziWriter) return; }} catch(e) {{}} }}
            }}
            const dataUrls = [`https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/${{char}}.json`,`https://unpkg.com/hanzi-writer-data@2.0.1/${{char}}.json`];
            async function loadData() {{
                for (const url of dataUrls) {{ try {{ const res = await fetch(url); if (res.ok) return await res.json(); }} catch(e) {{}} }}
                throw new Error('No data');
            }}
            async function init() {{
                try {{
                    await ensureLib();
                    const charData = await loadData();
                    const writer = window.HanziWriter.create(target, char, {{
                        width: {size}, height: {size}, padding: 8, showOutline: true, showCharacter: false,
                        strokeAnimationSpeed: 1.3, delayBetweenStrokes: 100
                    }});
                    writer.animateCharacter();
                    const el = document.getElementById(target);
                    el.style.cursor = 'pointer';
                    el.addEventListener('click', () => writer.animateCharacter());
                }} catch(e) {{
                    document.getElementById(target).innerHTML = `<div style="font-size:${size*0.7}px; line-height:${size}px; text-align:center;">${{char}}</div>`;
                }}
            }}
            init();
        }})();
        </script>
        """,
        height=h,
    )

def render_stroke_order_view(char_input: str):
    primary_char = (char_input or "").strip()[:1]
    if not primary_char:
        st.info("No character selected for stroke order.")
        return
    s_char = cc_t2s.convert(primary_char) if cc_t2s else primary_char
    t_char = cc_s2t.convert(primary_char) if cc_s2t else primary_char
    chars_to_show = []
    if s_char != t_char:
        if primary_char == t_char:
            chars_to_show = [t_char, s_char]
        else:
            chars_to_show = [s_char, t_char]
    else:
        chars_to_show = [primary_char]
    chars_to_show = list(dict.fromkeys(chars_to_show))
    BOX_SIZE = 280
    container_html = ""
    for i, c in enumerate(chars_to_show):
        label_text = ""
        if s_char != t_char:
            if c == s_char:
                label_text = "Simplified"
            elif c == t_char:
                label_text = "Traditional"
        label_html = (
            f"<div style='text-align:center; font-weight:bold; color:#555; margin-bottom:5px;'>{label_text}</div>"
            if label_text
            else ""
        )
        container_html += f"""
        <div style="display:flex; flex-direction:column; align-items:center;">
             {label_html}
            <div id="hw-target-{i}" style="width:{BOX_SIZE}px;height:{BOX_SIZE}px;border:1px solid #e0e0e0;border-radius:12px; background:white;"></div>
        </div>
        """
    st_html(
        f"""
        <div style="display:flex; gap:15px; align-items:flex-start; flex-wrap:wrap; justify-content:center;">
            {container_html}
        </div>
        <div style="display:flex; justify-content:center; margin-top:15px; gap:8px;">
             <button id="hw-reset">Reset</button><button id="hw-animate">Replay Animation</button>
        </div>
        <div id="hw-error" style="margin-top:10px; color:#b00020; text-align:center;"></div>
        <script>
        (function() {{
            const chars = {json.dumps(chars_to_show, ensure_ascii=False)};
            const boxSize = {BOX_SIZE};
            const errEl = document.getElementById('hw-error');
            function loadScript(src) {{ return new Promise((resolve, reject) => {{
                const s = document.createElement('script'); s.src = src; s.async = true;
                s.onload = () => resolve(src); s.onerror = () => reject();
                document.head.appendChild(s);
            }}); }}
            async function ensureLibLoaded() {{
                if (window.HanziWriter) return;
                const sources = ['https://cdn.jsdelivr.net/npm/hanzi-writer@3/dist/hanzi-writer.min.js',
                                 'https://unpkg.com/hanzi-writer@3/dist/hanzi-writer.min.js'];
                for (const src of sources) {{ try {{ await loadScript(src); if (window.HanziWriter) return; }} catch (e) {{}} }}
            }}
            const writers = [];
            async function init() {{
                try {{
                    await ensureLibLoaded();
                    for (let idx = 0; idx < chars.length; idx++) {{
                        const char = chars[idx];
                        const targetId = 'hw-target-' + idx;
                        const dataUrls = [`https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/${{char}}.json`,`https://unpkg.com/hanzi-writer-data@2.0.1/${{char}}.json`];
                        let hasData = false;
                        for (const url of dataUrls) {{ try {{ const res = await fetch(url); if (res.ok) {{ hasData = true; break; }} }} catch (e) {{}} }}
                        if(hasData) {{
                            const writer = window.HanziWriter.create(targetId, char, {{
                                width: boxSize, height: boxSize, padding: 10, showOutline: true, showCharacter: false,
                                strokeAnimationSpeed: 1, delayBetweenStrokes: 60
                            }});
                            writers.push(writer);
                        }} else {{
                            document.getElementById(targetId).innerHTML = `<div style="line-height:${{boxSize}}px; text-align:center; font-size:${{boxSize/2}}px; color:#ddd;">${{char}}</div>`;
                        }}
                    }}
                    autoAnimateAll();
                }} catch (e) {{ errEl.textContent = e.message || String(e); }}
            }}
            async function playSequence(writer) {{
                for (let k = 0; k < 3; k++) {{
                    writer.hideCharacter();
                    await writer.animateCharacter();
                    await new Promise(r => setTimeout(r, 800));
                }}
                writer.showCharacter();
            }}
            function autoAnimateAll() {{
                writers.forEach(w => {{ playSequence(w); }});
            }}
            function resetAll() {{
                writers.forEach(w => {{ w.hideCharacter(); }});
            }}
            document.getElementById('hw-reset').addEventListener('click', resetAll);
            document.getElementById('hw-animate').addEventListener('click', autoAnimateAll);
            init();
        }})();
        </script>
        """,
        height=400,
    )

def generate_clean_card_html(c, usage_count=None):
    if not c:
        return ""
    meta = component_map.get(c, {}).get("meta", {})
    pinyin = clean_field(meta.get("pinyin", ""))
    strokes = stroke_counts.get(c)
    radical = clean_field(meta.get("radical", ""))
    decomp = format_decomposition(c)
    definition = clean_field(meta.get("definition", ""))
    etymology = get_etymology_text(meta)
    meta_items = []
    if pinyin and pinyin != "–":
        meta_items.append(f"<span class='meta-pinyin'>{pinyin}</span>")
    if strokes:
        meta_items.append(f"<span class='meta-tag'>{strokes} strokes</span>")
    if radical and radical != "–":
        meta_items.append(f"<span class='meta-tag'>Rad. {radical}</span>")
    if decomp and decomp != "–":
        meta_items.append(f"<span class='meta-tag'>{decomp}</span>")
    if usage_count is not None and usage_count > 0:
        meta_items.append(f"<span class='meta-tag'>Used in {usage_count} chars</span>")
    if cc_t2s:
        simplified = cc_t2s.convert(c)
        if simplified != c:
            meta_items.append(f"<span class='meta-tag meta-tag-trad'>Trad. → {simplified}</span>")
    if cc_s2t:
        traditional = cc_s2t.convert(c)
        if traditional != c:
            meta_items.append(f"<span class='meta-tag meta-tag-simp'>Simp. → {traditional}</span>")
    meta_html = f"<div class='meta-row'>{''.join(meta_items)}</div>"
    def_html = f"<div class='def-row'>{definition}</div>" if definition and definition != "–" else ""
    ety_html = f"<div class='ety-row'>{etymology}</div>" if etymology else ""
    return f"<div class='char-card'>{meta_html}{def_html}{ety_html}</div>"

def enter_component(comp: str, script_override: str | None = None):
    st.session_state.selected_comp = comp
    st.session_state.last_valid_selected_comp = comp
    st.session_state.show_inputs = False
    st.session_state.preview_comp = None
    st.session_state.text_input_comp = comp
    st.session_state.text_input_warning = None
    if script_override:
        st.session_state.script_variant = script_override

# --- Splash screen ---
def render_splash():
    st.markdown(
        """
        <div class="splash-wrap">
          <div class="splash-card">
            <div class="splash-title">Radix 🈑 Explore Characters by Components</div>
            <div class="splash-sub">
              Learn to read and write Chinese characters by identifying <b>components</b>.
              <b>Components</b> are recurring parts that hint at meaning or pronunciation.
              As built-in <b>mnemonics</b>, they make characters easier to recognise and remember.
            </div>
            <div class="splash-sub">
              Choose a <b>component</b> to reveal its <b>character family</b>, with stroke order and phrases
              to reinforce what you've learned.
            </div>
            <div class="splash-demo">
              <div class="splash-demo-h">Demo: pick a component to unlock its character family</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    preferred = ["夂", "言", "月", "网", "臼", "貝"]
    comps_sorted = sorted(component_map.keys(), key=lambda c: -usage_counts.get(c, 0))
    MAX_DEMOS = 20
    demos = []
    seen = set()
    for c in preferred:
        if c in component_map and stroke_counts.get(c, 0) is not None and stroke_counts[c] >= 3 and c not in IDC_CHARS:
            demos.append(c)
            seen.add(c)
    for c in comps_sorted:
        if len(demos) >= MAX_DEMOS:
            break
        if c in seen or c in IDC_CHARS:
            continue
        demos.append(c)
        seen.add(c)
    COLS = 5
    rows = (len(demos) + COLS - 1) // COLS
    for r in range(rows):
        cols = st.columns(COLS)
        for j in range(COLS):
            idx = r * COLS + j
            if idx >= len(demos):
                continue
            ch = demos[idx]
            count = usage_counts.get(ch, 0)
            with cols[j]:
                if ch == "貝":
                    if st.button(f"Explore {ch} (Trad)", use_container_width=True, type="primary", key=f"splash_{ch}_{idx}"):
                        st.session_state.onboarding_done = True
                        enter_component(ch, script_override="Traditional")
                        st.rerun()
                else:
                    if st.button(f"Explore {ch}", use_container_width=True, type="primary", key=f"splash_{ch}_{idx}"):
                        st.session_state.onboarding_done = True
                        enter_component(ch)
                        st.rerun()
                st.caption(f"{count} characters")
    c1, c2, c3 = st.columns([2, 1, 2])
    with c2:
        if st.button("Enter Radix", use_container_width=True):
            st.session_state.onboarding_done = True
            st.rerun()

# --- Cached filtered components ---
@st.cache_data
def get_filtered_components(_component_map, _stroke_counts, _usage_counts, _used_components,
                            stroke_range, radical, component_idc, component_only):
    min_s, max_s = stroke_range
    filtered = [
        c for c in _component_map
        if (stroke_counts.get(c) is not None and min_s <= stroke_counts[c] <= max_s)
        and (radical == "none" or _component_map.get(c, {}).get("meta", {}).get("radical") == radical)
        and (component_idc == "none" or _component_map.get(c, {}).get("meta", {}).get("decomposition", "").startswith(component_idc))
        and (not component_only or c in _used_components)
    ]
    sorted_comps = sorted(
        filtered,
        key=lambda c: (-_usage_counts.get(c, 0), _stroke_counts.get(c) or 999, c)
    )
    return sorted_comps

# --- State init ---
defaults = {
    "onboarding_done": False,
    "selected_comp": "",
    "stroke_range": (1, 30),
    "radical": "none",
    "component_idc": "none",
    "display_mode": "Single Character",
    "text_input_comp": "",
    "page": 1,
    "text_input_warning": None,
    "show_inputs": True,
    "last_valid_selected_comp": "",
    "preview_comp": None,
    "stroke_view_active": False,
    "stroke_view_char": "",
    "script_variant": "Simplified",
    "component_only": True,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Dynamic max stroke
valid_strokes = [s for s in stroke_counts.values() if s is not None]
max_s_val = max(valid_strokes) if valid_strokes else 30
if st.session_state.stroke_range[1] > max_s_val:
    st.session_state.stroke_range = (st.session_state.stroke_range[0], max_s_val)

def clear_all_filters():
    st.session_state.stroke_range = (1, max_s_val)
    st.session_state.radical = "none"
    st.session_state.component_idc = "none"
    st.session_state.component_only = True
    st.session_state.page = 1

def tile_click(c):
    if st.session_state.preview_comp == c:
        enter_component(c)
    else:
        st.session_state.preview_comp = c

def back():
    st.session_state.show_inputs = True
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""

def end_stroke_view():
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""

def sync_text():
    v = st.session_state.w_text.strip()
    if len(v) != 1:
        st.session_state.text_input_warning = "One character only"
        return
    if v in component_map:
        enter_component(v)
    else:
        st.session_state.text_input_warning = "Not found"

def main():
    if not component_map:
        st.error("Component dataset not loaded.")
        st.stop()

    apply_dynamic_css()

    if not st.session_state.onboarding_done:
        render_splash()
        st.stop()

    with st.sidebar:
        st.markdown("<h1 style='text-align:center; margin-bottom:30px;'>🈑 Radix</h1>", unsafe_allow_html=True)
        if st.button("Show intro again", use_container_width=True):
            st.session_state.onboarding_done = False
            st.rerun()

        if st.button("🗑️ Clear all filters", use_container_width=True, type="secondary"):
            clear_all_filters()
            st.rerun()

        st.checkbox(
            "Show Components Only",
            value=st.session_state.component_only,
            key="component_only",
            help="Only characters that appear as parts of others"
        )

        with st.expander(f"Strokes: {st.session_state.stroke_range[0]}–{st.session_state.stroke_range[1]}", expanded=True):
            st.slider(
                "Stroke range",
                min_value=1,
                max_value=max_s_val,
                value=st.session_state.stroke_range,
                key="stroke_range",
                label_visibility="collapsed"
            )

        with st.expander(f"Radical: {'Any' if st.session_state.radical == 'none' else st.session_state.radical}"):
            if st.button("Clear radical", type="secondary"):
                st.session_state.radical = "none"
                st.rerun()
            for strokes in sorted(rad_groups.keys()):
                if strokes == 999:
                    continue
                st.markdown(f"<div class='stroke-header'>{strokes} strokes</div>", unsafe_allow_html=True)
                cols = st.columns(6)
                radicals_sorted = sorted(rad_groups[strokes], key=lambda x: -rad_counts.get(x, 0))
                for i, r in enumerate(radicals_sorted):
                    with cols[i % 6]:
                        count = rad_counts.get(r, 0)
                        if st.button(f"{r} ({count})", key=f"rad_{r}_{strokes}", use_container_width=True,
                                     type="primary" if st.session_state.radical == r else "secondary"):
                            st.session_state.radical = r
                            st.session_state.page = 1
                            st.rerun()

        with st.expander(f"Structure: {'Any' if st.session_state.component_idc == 'none' else st.session_state.component_idc}"):
            if st.button("Clear structure", type="secondary"):
                st.session_state.component_idc = "none"
                st.rerun()
            cols = st.columns(5)
            for i, idc in enumerate(sorted(idc_counts.keys())):
                with cols[i % 5]:
                    count = idc_counts[idc]
                    if st.button(f"{idc} ({count})", key=f"idc_{idc}", use_container_width=True,
                                 type="primary" if st.session_state.component_idc == idc else "secondary"):
                        st.session_state.component_idc = idc
                        st.session_state.page = 1
                        st.rerun()

        if st.session_state.preview_comp:
            render_stroke_order_sidebar(st.session_state.preview_comp, size=110)
            count = usage_counts.get(st.session_state.preview_comp, 0)
            st.markdown(f"<div class='preview-count-line'>{count} characters contain <span class='char'>{st.session_state.preview_comp}</span></div>", unsafe_allow_html=True)
            if st.button("Explore this component", use_container_width=True, type="primary"):
                enter_component(st.session_state.preview_comp)
                st.rerun()

        elif st.session_state.selected_comp and not st.session_state.show_inputs:
            st.button("← Back to list", on_click=back, use_container_width=True)
            selected_char = st.session_state.selected_comp
            if st.button("View full stroke order", use_container_width=True):
                st.session_state.stroke_view_char = selected_char
                st.session_state.stroke_view_active = True
                st.rerun()
            render_stroke_order_sidebar(selected_char, size=140)
            st.radio("Script Variant", ["Simplified", "Traditional"], index=0 if st.session_state.script_variant == "Simplified" else 1, key="script_variant")

    if st.session_state.stroke_view_active:
        render_stroke_order_view(st.session_state.stroke_view_char)
        st.stop()

    if st.session_state.show_inputs:
        st.markdown("### 🔍 Jump to component")
        colj1, colj2 = st.columns([3, 1])
        with colj1:
            st.text_input(
                "Go directly to a character/component",
                value="",
                key="w_text",
                on_change=sync_text,
                placeholder="e.g. 水, 月, 木",
                label_visibility="collapsed"
            )
        if st.session_state.text_input_warning:
            with colj2:
                st.warning(st.session_state.text_input_warning)

        all_sorted = get_filtered_components(
            component_map, stroke_counts, usage_counts, used_components,
            st.session_state.stroke_range,
            st.session_state.radical,
            st.session_state.component_idc,
            st.session_state.component_only
        )

        total = len(all_sorted)
        if total == 0:
            st.info("No components match current filters.")
            st.stop()

        PAGE_SIZE = 50
        GRID_COLS = 10
        max_page = math.ceil(total / PAGE_SIZE)
        st.session_state.page = max(1, min(st.session_state.page, max_page))

        filter_parts = []
        if st.session_state.stroke_range != (1, max_s_val):
            filter_parts.append(f"<span class='status-tag'>{st.session_state.stroke_range[0]}–{st.session_state.stroke_range[1]} strokes</span>")
        if st.session_state.radical != "none":
            filter_parts.append(f"<span class='status-tag'>Rad. {st.session_state.radical}</span>")
        if st.session_state.component_idc != "none":
            filter_parts.append(f"<span class='status-tag'>{st.session_state.component_idc}</span>")
        if st.session_state.component_only:
            filter_parts.append("<span class='status-tag'>Components Only</span>")
        filter_summary = " · ".join(filter_parts) if filter_parts else "All components"
        st.markdown(f"<div class='status-line'><span style='font-size:1.3em; font-weight:bold;'>{total}</span> matching components{': ' + filter_summary if filter_parts else ''}</div>", unsafe_allow_html=True)

        start = (st.session_state.page - 1) * PAGE_SIZE + 1
        end = min(st.session_state.page * PAGE_SIZE, total)
        p1, p2, p3 = st.columns([1, 3, 1])
        with p1:
            if st.button("◀ Prev", disabled=st.session_state.page <= 1):
                st.session_state.page -= 1
                st.rerun()
        with p2:
            st.markdown(f"<div style='text-align:center; padding:10px 0;'><strong>{start}–{end}</strong> of {total}<br><small>Sorted by usage frequency</small></div>", unsafe_allow_html=True)
        with p3:
            if st.button("Next ▶", disabled=st.session_state.page >= max_page):
                st.session_state.page += 1
                st.rerun()

        page_items = all_sorted[(st.session_state.page - 1) * PAGE_SIZE : st.session_state.page * PAGE_SIZE]
        st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
        cols = st.columns(GRID_COLS)
        for i, ch in enumerate(page_items):
            with cols[i % GRID_COLS]:
                is_preview = st.session_state.preview_comp == ch
                st.button(
                    ch,
                    key=f"btn_{ch}_{st.session_state.page}",
                    use_container_width=True,
                    type="primary" if is_preview else "secondary",
                    on_click=tile_click,
                    args=(ch,),
                )
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        # === Detailed character family view (your original logic) ===
        selected = st.session_state.selected_comp
        related = component_map[selected].get("related_characters", [])
        chars = list({c for c in related if isinstance(c, str) and len(c) == 1})
        chars = [c for c in chars if c in component_map]
        n = int(st.session_state.display_mode[0]) if st.session_state.display_mode != "Single Character" else 0
        compounds = (
            {c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if isinstance(w, str) and len(w) == n] for c in chars}
            if n else {c: [] for c in chars}
        )
        chars = [c for c in chars if n == 0 or compounds[c]]
        chars = sorted(
            chars,
            key=lambda x: (-usage_counts.get(x, 0), stroke_counts.get(x) or 999, x)
        )
        if st.session_state.script_variant == "Simplified":
            chars = [c for c in chars if not cc_t2s or cc_t2s.convert(c) == c]
        else:
            chars = [c for c in chars if not cc_s2t or cc_s2t.convert(c) == c]

        modes = ["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"]
        st.radio("", options=modes, index=modes.index(st.session_state.display_mode), key="w_display", horizontal=True)

        for c in chars:
            col_btn, col_char, col_details = st.columns([1, 2, 12])
            with col_btn:
                st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
                if st.button("🖊️", key=f"stroke_btn_{c}", help="View full stroke order"):
                    st.session_state.stroke_view_char = c
                    st.session_state.stroke_view_active = True
                    st.rerun()
            with col_char:
                if st.button(
                    c,
                    key=f"explore_char_{c}",
                    use_container_width=True,
                    help=f"Explore characters containing {c} as a component",
                ):
                    enter_component(c)
                    st.rerun()
            with col_details:
                st.markdown(
                    generate_clean_card_html(c, usage_count=usage_counts.get(c, 0)),
                    unsafe_allow_html=True
                )
                if compounds.get(c):
                    sorted_compounds = sorted(compounds[c])
                    items_html = []
                    for word in sorted_compounds:
                        entry = phrases_dict.get(word)
                        pinyin = entry.get("pinyin", "") if entry else ""
                        meanings = entry.get("meanings", "") if entry else ""
                        display_meanings = meanings[:100] + ("..." if len(meanings) > 100 else "")
                        display_meanings = html.escape(display_meanings)
                        if entry:
                            items_html.append(
                                f"<div class='compound-item'>"
                                f"<span class='cp-word'>{word}</span>"
                                f"<span class='cp-pinyin'>{pinyin}</span>"
                                f"<span class='cp-mean'>{display_meanings}</span>"
                                f"</div>"
                            )
                        else:
                            items_html.append(f"<div class='compound-item'><span class='cp-word'>{word}</span></div>")
                    full_list_html = "".join(items_html)
                    st.markdown(
                        f"""
                        <div style='padding:15px; background:#f1f8e9; border-radius:8px; margin-top:10px; border:1px solid #dcedc8; max-height:400px; overflow-y:auto;'>
                          <div style='font-weight:bold; margin-bottom:10px; color:#2e7d32; border-bottom:2px solid #a5d6a7; padding-bottom:5px;'>
                            {st.session_state.display_mode}
                          </div>
                          {full_list_html}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

        if chars and n:
            with st.expander("Export Compounds"):
                st.text_area("Copy list", "\n".join(w for c in chars for w in compounds[c]), height=150)

if __name__ == "__main__":
    main()
