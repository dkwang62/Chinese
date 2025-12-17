import json
import math
import streamlit as st
from streamlit.components.v1 import html as st_html

st.set_page_config(layout="wide", page_title="Radix")

IDC_CHARS = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}

def apply_dynamic_css():
    css = """
    <style>
        /* General Cleanup */
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        
        /* Sidebar: Clean up spacing */
        section[data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
        }

        /* Sidebar: Selected Character */
        .sidebar-big-char {
            font-size: 4em; 
            text-align: center;
            color: #e74c3c; 
            margin: 10px 0 0 0;
            font-weight: bold;
            line-height: 1.1;
        }
        
        .sidebar-meta {
            font-size: 1em;
            text-align: center;
            color: #555;
            margin-bottom: 20px;
        }
        
        .preview-details-box {
            font-size: 0.95em;
            line-height: 1.5;
            color: #333;
            background: #fff;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #eee;
            margin-top: 15px;
        }

        /* Results: The Row Layout */
        .result-row {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .char-card {
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            border: 1px solid #f0f0f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            width: 100%;
        }

        /* Browsing Grid Buttons */
        .comp-grid .stButton button {
            font-size: 2.2em;
            height: 75px;
            background: white;
            border: 1px solid #eee;
            border-radius: 10px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            padding: 0;
            line-height: 75px;
            transition: all 0.2s;
        }
        .comp-grid .stButton button:hover {
            border-color: #e74c3c;
            color: #e74c3c;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(231, 76, 60, 0.15);
        }

        /* Navigation Row in Grid */
        .nav-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            color: #666;
        }

        /* Input styling */
        div[data-testid="stTextInput"] input {
            text-align: center;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

@st.cache_data
def load_component_map():
    try:
        with open("enhanced_component_map_with_etymology.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return {}

try:
    component_map = load_component_map()
except Exception as e:
    component_map = {}
    st.error(f"Data error: {e}")

def clean_field(field):
    return field[0] if isinstance(field, list) and field else field or "—"

def get_stroke_count(char):
    strokes = component_map.get(char, {}).get("meta", {}).get("strokes", None)
    try:
        if isinstance(strokes, (int, float)) and strokes > 0: return int(strokes)
        if isinstance(strokes, str) and strokes.isdigit(): return int(strokes)
    except: pass
    return None

def get_etymology_text(meta):
    etymology = meta.get("etymology", {})
    hint = clean_field(etymology.get("hint", ""))
    details = clean_field(etymology.get("details", ""))
    if not hint and not details: return "—"
    if hint and not details: return hint
    if details and not hint: return details
    return f"{hint}; {details}"

def format_decomposition(char):
    d = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    return "—" if not d or '?' in d else d

# State init
defaults = {
    "selected_comp": "", "stroke_count": 0, "radical": "none", "component_idc": "none",
    "display_mode": "Single Character", "text_input_comp": "", "page": 1, "text_input_warning": None,
    "show_inputs": True, "last_valid_selected_comp": "", "preview_comp": None,
    "stroke_view_active": False, "stroke_view_char": ""
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# Callbacks
def sync_stroke():
    val = st.session_state.w_stroke
    st.session_state.stroke_count = int(val) if val != 0 else 0
    st.session_state.page = 1

def sync_radical():
    st.session_state.radical = st.session_state.w_radical
    st.session_state.page = 1

def sync_idc():
    st.session_state.component_idc = st.session_state.w_idc
    st.session_state.page = 1

def sync_display():
    st.session_state.display_mode = st.session_state.w_display

def sync_text():
    v = st.session_state.w_text.strip()
    if len(v) != 1: return # Silent fail on length
    if v in component_map:
        st.session_state.selected_comp = v
        st.session_state.last_valid_selected_comp = v
        st.session_state.text_input_comp = v
        st.session_state.show_inputs = False
        st.session_state.preview_comp = None
        st.session_state.text_input_warning = None
    else:
        st.session_state.text_input_warning = "Not found"

def tile_click(c):
    if st.session_state.show_inputs:
        if st.session_state.preview_comp == c:
            st.session_state.selected_comp = c
            st.session_state.last_valid_selected_comp = c
            st.session_state.show_inputs = False
            st.session_state.preview_comp = None
            st.session_state.text_input_comp = c
        else:
            st.session_state.preview_comp = c

def back():
    st.session_state.show_inputs = True
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""
    st.session_state.text_input_comp = ""
    st.session_state.text_input_warning = None

def end_stroke_view():
    st.session_state.stroke_view_active = False

def reset():
    st.session_state.stroke_count = 0
    st.session_state.radical = "none"
    st.session_state.component_idc = "none"
    st.session_state.page = 1
    st.session_state.show_inputs = True
    st.session_state.preview_comp = None
    st.session_state.text_input_comp = ""
    st.session_state.text_input_warning = None

def render_sidebar_preview(c):
    if not c or c not in component_map: return

    related = component_map.get(c, {}).get("related_characters", [])
    chars_unique = list(set([ch for ch in related if len(ch) == 1]))
    count = len(chars_unique)

    meta = component_map.get(c, {}).get("meta", {})
    
    # Clean minimalist preview
    st.markdown(f"<div class='sidebar-big-char'>{c}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sidebar-meta'>{count} characters contain {c}</div>", unsafe_allow_html=True)

    f = {
        "Pinyin": clean_field(meta.get("pinyin", "—")),
        "Strokes": str(get_stroke_count(c)) if get_stroke_count(c) else "?",
        "Meaning": clean_field(meta.get("definition", "—")),
    }
    
    details_html = "".join([f"<div style='margin-bottom:4px;'><b style='color:#777; margin-right:5px;'>{k}</b> {v}</div>" for k,v in f.items()])
    st.markdown(f"<div class='preview-details-box'>{details_html}</div>", unsafe_allow_html=True)

def render_stroke_order_view(char: str):
    char = (char or "").strip()[:1]
    if not char: return

    # No title needed, visual context is enough
    st_html(
        f"""
        <div style="display:flex; justify-content:center; align-items:center; flex-direction:column;">
            <div id="hw-target" style="width:300px;height:300px;border:1px solid #eee;border-radius:12px; margin-bottom:15px;"></div>
            <div style="display:flex; gap:10px;">
              <button id="hw-animate" style="padding:8px 16px; border-radius:6px; border:1px solid #ddd; background:white; cursor:pointer;">Animate</button>
              <button id="hw-reset" style="padding:8px 16px; border-radius:6px; border:1px solid #ddd; background:white; cursor:pointer;">Reset</button>
            </div>
            <div id="hw-error" style="margin-top:10px; color:#b00020; font-size:0.8em;"></div>
        </div>

        <script>
          (function() {{
            const char = {json.dumps(char, ensure_ascii=False)};
            
            function loadScript(src) {{
                return new Promise((resolve, reject) => {{
                    if(window.HanziWriter) return resolve();
                    const s = document.createElement('script');
                    s.src = src;
                    s.async = true;
                    s.onload = resolve;
                    s.onerror = reject;
                    document.head.appendChild(s);
                }});
            }}

            async function init() {{
                try {{
                    await loadScript('https://cdn.jsdelivr.net/npm/hanzi-writer@3/dist/hanzi-writer.min.js');
                    
                    const writer = window.HanziWriter.create('hw-target', char, {{
                        width: 300, height: 300, padding: 10, showOutline: true,
                        strokeAnimationSpeed: 1, delayBetweenStrokes: 200,
                    }});
                    
                    document.getElementById('hw-animate').onclick = () => writer.animateCharacter();
                    document.getElementById('hw-reset').onclick = () => {{ writer.hideCharacter(); writer.showCharacter(); }};
                    writer.animateCharacter();
                }} catch(e) {{
                    document.getElementById('hw-error').innerText = "Could not load stroke data.";
                }}
            }}
            init();
          }})();
        </script>
        """,
        height=400,
    )

def main():
    if not component_map: st.stop()
    apply_dynamic_css()

    # === SIDEBAR ===
    with st.sidebar:
        st.markdown("<h2 style='text-align:center; color:#333; border-bottom:1px solid #eee; padding-bottom:10px;'>Radix</h2>", unsafe_allow_html=True)
        
        if st.session_state.stroke_view_active:
             st.button("← Back", on_click=end_stroke_view, use_container_width=True)
        
        elif st.session_state.show_inputs:
            # Filters
            stroke_set = {s for s in (get_stroke_count(c) for c in component_map) if isinstance(s, int)}
            stroke_opts = [0] + sorted(stroke_set)
            current = st.session_state.stroke_count if st.session_state.stroke_count in stroke_opts else 0
            st.selectbox("Strokes", options=stroke_opts, index=stroke_opts.index(current),
                         format_func=lambda x: "All" if x == 0 else str(x), key="w_stroke", on_change=sync_stroke)

            rad_set = {component_map.get(c, {}).get("meta", {}).get("radical", "") for c in component_map if component_map.get(c, {}).get("meta", {}).get("radical")}
            rad_opts = ["none"] + sorted(rad_set)
            st.selectbox("Radical", options=rad_opts, index=rad_opts.index(st.session_state.radical), key="w_radical", on_change=sync_radical)

            idc_set = {d[0] for d in (component_map.get(c, {}).get("meta", {}).get("decomposition", "") for c in component_map) if d and d[0] in IDC_CHARS}
            idc_opts = ["none"] + sorted(idc_set)
            st.selectbox("Structure", options=idc_opts, index=idc_opts.index(st.session_state.component_idc), key="w_idc", on_change=sync_idc)

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if st.button("Reset", use_container_width=True):
                reset()
                st.rerun()

            if st.session_state.preview_comp:
                st.markdown("---")
                render_sidebar_preview(st.session_state.preview_comp)

        else:
            # Results Mode Sidebar
            st.button("← Back", on_click=back, use_container_width=True)
            
            # Big Red Char
            st.markdown(f"<div class='sidebar-big-char'>{st.session_state.selected_comp}</div>", unsafe_allow_html=True)
            
            # Count
            related = component_map[st.session_state.selected_comp].get("related_characters", [])
            chars_unique = list(set([c for c in related if len(c) == 1]))
            n = int(st.session_state.display_mode[0]) if st.session_state.display_mode != "Single Character" else 0
            compounds = {c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w)==n] for c in chars_unique}
            valid_chars = [c for c in chars_unique if n == 0 or compounds[c]]
            
            st.markdown(f"<div class='sidebar-meta'>{len(valid_chars)} characters</div>", unsafe_allow_html=True)

            if st.button("Stroke Order", use_container_width=True):
                st.session_state.stroke_view_char = st.session_state.selected_comp
                st.session_state.stroke_view_active = True
                st.rerun()
            
            st.markdown("---")
            modes = ["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"]
            st.radio("View Mode", options=modes, index=modes.index(st.session_state.display_mode), key="w_display", on_change=sync_display, label_visibility="collapsed")

    # === MAIN ===
    if st.session_state.stroke_view_active:
        render_stroke_order_view(st.session_state.stroke_view_char)
        return

    if st.session_state.show_inputs:
        # --- BROWSING MODE ---
        filtered = [c for c in component_map if
            (st.session_state.stroke_count == 0 or get_stroke_count(c) == st.session_state.stroke_count) and
            (st.session_state.radical == "none" or component_map.get(c, {}).get("meta", {}).get("radical") == st.session_state.radical) and
            (st.session_state.component_idc == "none" or component_map.get(c, {}).get("meta", {}).get("decomposition", "").startswith(st.session_state.component_idc))
        ]

        def _result_count(comp):
            rel = component_map.get(comp, {}).get("related_characters", [])
            return len({x for x in rel if isinstance(x, str) and len(x) == 1})

        _counts = {c: _result_count(c) for c in filtered}
        sorted_comps = sorted(filtered, key=lambda c: (-_counts.get(c, 0), get_stroke_count(c) or 999, c))

        if not sorted_comps:
            st.info("No characters found.")
            return

        PAGE_SIZE = 100
        total = len(sorted_comps)
        max_page = max(1, math.ceil(total / PAGE_SIZE))
        st.session_state.page = max(1, min(st.session_state.page, max_page))

        # Minimal Navigation Top Row
        c1, c2, c3 = st.columns([1, 6, 1])
        with c1:
            if st.button("◀", disabled=st.session_state.page<=1): st.session_state.page -= 1
        with c2:
            start, end = (st.session_state.page-1)*PAGE_SIZE + 1, min(st.session_state.page*PAGE_SIZE, total)
            st.markdown(f"<div style='text-align:center; color:#999; line-height:35px;'>{start} – {end} of {total}</div>", unsafe_allow_html=True)
        with c3:
            if st.button("▶", disabled=st.session_state.page>=max_page): st.session_state.page += 1

        # The Grid
        page = sorted_comps[(st.session_state.page-1)*PAGE_SIZE : st.session_state.page*PAGE_SIZE]
        st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
        cols = st.columns(10)
        for i, ch in enumerate(page):
            with cols[i % 10]:
                is_prev = st.session_state.preview_comp == ch
                st.button(ch, key=f"b_{ch}_{st.session_state.page}", use_container_width=True,
                          type="primary" if is_prev else "secondary", on_click=tile_click, args=(ch,))
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Bottom Instructions
        st.markdown("<div style='text-align:center; margin-top:20px; color:#bbb; font-size:0.8em;'>Select to preview · Double-click to open</div>", unsafe_allow_html=True)

        # Minimal Jump Input
        st.markdown("---")
        col_space, col_inp, col_space2 = st.columns([1, 1, 1])
        with col_inp:
            if st.session_state.text_input_warning:
                st.caption(f"⚠️ {st.session_state.text_input_warning}")
            st.text_input("Jump", value=st.session_state.text_input_comp, key="w_text", on_change=sync_text, placeholder="Search character...", label_visibility="collapsed")

    else:
        # --- RESULTS MODE ---
        related = component_map[st.session_state.selected_comp].get("related_characters", [])
        chars = list(set([c for c in related if len(c)==1]))
        n = int(st.session_state.display_mode[0]) if st.session_state.display_mode != "Single Character" else 0
        compounds = {c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w)==n] for c in chars} if n else {c:[] for c in chars}
        chars = [c for c in chars if n==0 or compounds[c]]
        chars = sorted(chars, key=lambda x: get_stroke_count(x) or 999)

        for c in chars:
            meta = component_map.get(c, {}).get("meta", {})
            f_data = {
                "Pinyin": clean_field(meta.get("pinyin", "—")),
                "Radical": clean_field(meta.get("radical", "—")),
                "Strokes": str(get_stroke_count(c)) if get_stroke_count(c) else "?",
                "Meaning": clean_field(meta.get("definition", "—")),
            }
            
            # Layout: Button | Char | Details
            c_btn, c_char, c_det = st.columns([1, 2, 10])
            
            with c_btn:
                st.markdown("<div style='height:25px'></div>", unsafe_allow_html=True)
                if st.button("🖊️", key=f"s_{c}", help="Stroke Order"):
                    st.session_state.stroke_view_char = c
                    st.session_state.stroke_view_active = True
                    st.rerun()
            
            with c_char:
                 st.markdown(f"<div style='font-size:3em; font-weight:bold; text-align:center; color:#333;'>{c}</div>", unsafe_allow_html=True)
            
            with c_det:
                info_str = " &nbsp;·&nbsp; ".join([f"<span style='color:#888'>{k}</span> {v}" for k,v in f_data.items()])
                
                compound_html = ""
                if compounds.get(c):
                    compound_list = " ".join(sorted(compounds[c]))
                    compound_html = f"<div style='margin-top:8px; padding-top:8px; border-top:1px dashed #eee; color:#2c3e50; font-size:0.95em;'>{compound_list}</div>"
                
                st.markdown(f"""
                <div class='char-card'>
                    <div style='line-height:1.4;'>{info_str}</div>
                    {compound_html}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        if chars and n:
            with st.expander("Copy text"):
                st.text_area("", "\n".join(w for c in chars for w in compounds[c]), height=100, label_visibility="collapsed")

if __name__ == "__main__":
    main()
