import json
import math
import streamlit as st
from streamlit.components.v1 import html as st_html

st.set_page_config(layout="wide")

IDC_CHARS = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}

def apply_dynamic_css():
    css = """
    <style>
        /* SIDEBAR: Results Count Header */
        .results-header-sidebar {
            font-size: 1.05em;
            font-weight: 600;
            color: #2c3e50;
            margin: 14px 0 8px 0;
            text-align: center;
            opacity: 0.9;
        }

        /* SIDEBAR: Selected Component (big) */
        .selected-char-sidebar {
            font-size: 3em;
            text-align: center;
            color: #b00020;
            font-weight: 700;
            margin-top: 10px;
            margin-bottom: 10px;
            line-height: 1.05;
        }

        /* MAIN: Status line */
        .status-line {
            margin: 6px 0 10px 0;
            color: #555;
        }

        /* MAIN: Character Card */
        .char-card {
            border: 1px solid #eee;
            border-radius: 12px;
            padding: 12px;
            background: #fff;
        }

        /* MAIN: phrases box */
        .phrases-box{
            padding:10px;
            background:#e9f7ef;
            border:1px solid #c9efd8;
            border-radius:10px;
            margin-top:6px;
        }

        /* SIDEBAR: compact preview panel */
        .preview-panel {
            border: 1px solid #eee;
            border-radius: 10px;
            padding: 10px;
            background: #fff;
            margin-top: 10px;
        }
        .preview-grid {
            display: grid;
            grid-template-columns: 90px 1fr;
            row-gap: 6px;
            column-gap: 10px;
            font-size: 0.92em;
            color: #333;
        }
        .preview-title {
            font-weight: 700;
            margin-bottom: 8px;
            color: #2c3e50;
        }
        .preview-muted {
            color: #6b7280;
            font-size: 0.85em;
            margin-top: 8px;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

@st.cache_data
def load_component_map():
    # Ensure this file exists in your directory
    with open("enhanced_component_map_with_etymology.json", "r", encoding="utf-8") as f:
        return json.load(f)

try:
    component_map = load_component_map()
except FileNotFoundError:
    component_map = {}
    st.error("Missing data file: enhanced_component_map_with_etymology.json")
except Exception as e:
    component_map = {}
    st.error(f"Failed to load data: {e}")

def clean_field(field):
    return field[0] if isinstance(field, list) and field else field or "—"

def get_stroke_count(char):
    strokes = component_map.get(char, {}).get("meta", {}).get("strokes", None)
    try:
        if isinstance(strokes, (int, float)) and strokes > 0:
            return int(strokes)
        if isinstance(strokes, str) and strokes.isdigit():
            return int(strokes)
    except Exception:
        pass
    return None

def result_count(comp: str) -> int:
    rel = component_map.get(comp, {}).get("related_characters", [])
    return len({x for x in rel if isinstance(x, str) and len(x) == 1})

# -----------------------------
# Session state defaults
# -----------------------------
defaults = {
    "selected_comp": "",
    "selected_result_char": "",     # NEW: selected character from results list
    "stroke_count": 0,
    "radical": "none",
    "component_idc": "none",
    "display_mode": "Single Character",
    "text_input_comp": "",
    "page": 1,
    "text_input_warning": None,
    "show_inputs": True,
    "last_valid_selected_comp": "",
    "preview_comp": None,
    "preview_active": False,

    # Stroke order view
    "stroke_view_active": False,
    "stroke_view_char": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -----------------------------
# Callbacks / navigation
# -----------------------------
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
    # If output type changes, selection might become invalid
    st.session_state.selected_result_char = ""

def sync_text():
    v = st.session_state.w_text.strip()
    if len(v) != 1:
        st.session_state.text_input_warning = "One character only"
        return
    if v in component_map:
        st.session_state.selected_comp = v
        st.session_state.last_valid_selected_comp = v
        st.session_state.text_input_comp = v
        st.session_state.text_input_warning = None
        st.session_state.show_inputs = False
        st.session_state.preview_active = False
        st.session_state.preview_comp = None
        st.session_state.selected_result_char = ""
    else:
        st.session_state.text_input_warning = "Not found in dataset"

def back():
    # Return to browsing list (primary grid)
    st.session_state.show_inputs = True
    st.session_state.preview_active = False
    st.session_state.preview_comp = None
    st.session_state.selected_result_char = ""
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""

def reset():
    st.session_state.selected_comp = ""
    st.session_state.last_valid_selected_comp = ""
    st.session_state.selected_result_char = ""
    st.session_state.preview_comp = None
    st.session_state.preview_active = False
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""
    st.session_state.stroke_count = 0
    st.session_state.radical = "none"
    st.session_state.component_idc = "none"
    st.session_state.page = 1
    st.session_state.show_inputs = True
    st.session_state.display_mode = "Single Character"
    st.session_state.text_input_comp = ""
    st.session_state.text_input_warning = None

def end_stroke_view():
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""

def tile_click(c):
    # Two-step click: preview first; click the same tile again to open results.
    if st.session_state.preview_active and st.session_state.preview_comp == c:
        st.session_state.selected_comp = c
        st.session_state.last_valid_selected_comp = c
        st.session_state.show_inputs = False
        st.session_state.preview_active = False
        st.session_state.preview_comp = None
        st.session_state.selected_result_char = ""  # NEW: clear selection when entering results
    else:
        st.session_state.preview_active = True
        st.session_state.preview_comp = c

# -----------------------------
# Sidebar preview panel
# -----------------------------
def render_preview_sidebar(comp: str):
    if not comp:
        return
    meta = component_map.get(comp, {}).get("meta", {})
    pinyin = clean_field(meta.get("pinyin", "—"))
    strokes = get_stroke_count(comp)
    strokes_txt = f"{strokes}" if strokes else "—"
    radical = clean_field(meta.get("radical", "—"))
    decomp = clean_field(meta.get("decomposition", "—"))
    definition = clean_field(meta.get("definition", "—"))

    st.markdown(
        f"""
        <div class="preview-panel">
          <div class="preview-title">Preview</div>
          <div class="preview-grid">
            <div><b>Meaning</b></div><div>{definition}</div>
            <div><b>Pinyin</b></div><div>{pinyin}</div>
            <div><b>Strokes</b></div><div>{strokes_txt}</div>
            <div><b>Radical</b></div><div>{radical}</div>
            <div><b>Decomp</b></div><div>{decomp}</div>
          </div>
          <div class="preview-muted">Tip: click the same tile again to open the full results list.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# Stroke order view (HanziWriter, with CDN fallback)
# -----------------------------
def render_stroke_order_view(char: str):
    char = (char or "").strip()[:1]
    if not char:
        st.info("No character selected for stroke order.")
        return

    st.markdown(f"## Stroke order — {char}")

    st_html(
        f"""
        <div style="display:flex; gap:20px; flex-wrap:wrap; align-items:flex-start;">
          <div>
            <div id="target" style="width:360px;height:360px;border:1px solid #ddd;"></div>

            <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
              <button id="btnPrev">Back</button>
              <button id="btnNext">Next</button>
              <button id="btnReset">Reset</button>
              <button id="btnAnimate">Animate</button>
            </div>

            <div id="status" style="margin-top:10px; font-family:ui-monospace, SFMono-Regular, Menlo, monospace; color:#444;"></div>
            <div id="err" style="margin-top:10px; color:#b00020;"></div>
          </div>

          <div style="max-width:520px;">
            <div style="font-size:18px; font-weight:600;">Instructions</div>
            <ul style="margin-top:8px; color:#444;">
              <li>Use <b>Next</b> to animate the next stroke.</li>
              <li>Use <b>Back</b> to step back (resets and replays up to the previous stroke).</li>
              <li><b>Animate</b> plays the full character.</li>
            </ul>
          </div>
        </div>

        <script>
          const CHAR = {json.dumps(char, ensure_ascii=False)};

          const LIB_URLS = [
            "https://cdn.jsdelivr.net/npm/hanzi-writer@3/dist/hanzi-writer.min.js",
            "https://unpkg.com/hanzi-writer@3/dist/hanzi-writer.min.js"
          ];

          const DATA_URLS = [
            (c) => `https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/${{c}}.json`,
            (c) => `https://unpkg.com/hanzi-writer-data@2.0.1/${{c}}.json`
          ];

          function setStatus(msg) {{
            document.getElementById("status").textContent = msg || "";
          }}
          function setErr(msg) {{
            document.getElementById("err").textContent = msg || "";
          }}

          function loadScript(url) {{
            return new Promise((resolve, reject) => {{
              const s = document.createElement("script");
              s.src = url;
              s.async = true;
              s.onload = resolve;
              s.onerror = () => reject(new Error("Failed to load: " + url));
              document.head.appendChild(s);
            }});
          }}

          async function ensureLibLoaded() {{
            if (window.HanziWriter) return true;
            for (const url of LIB_URLS) {{
              try {{
                await loadScript(url);
                if (window.HanziWriter) return true;
              }} catch (e) {{
                // try next
              }}
            }}
            return false;
          }}

          async function fetchJsonWithFallback(urlFns, c) {{
            for (const fn of urlFns) {{
              const url = fn(c);
              try {{
                const r = await fetch(url);
                if (!r.ok) throw new Error("HTTP " + r.status);
                return await r.json();
              }} catch (e) {{
                // try next
              }}
            }}
            throw new Error("Failed to load character data from all CDNs.");
          }}

          let writer = null;
          let data = null;
          let i = -1;

          function totalStrokes() {{
            return (data && data.medians && data.medians.length) ? data.medians.length : 0;
          }}

          function updateStatus() {{
            const t = totalStrokes();
            setStatus(`Stroke: ${{Math.max(i+1, 0)}} / ${{t}}`);
          }}

          async function resetAll() {{
            i = -1;
            if (writer) writer.hideCharacter();
            updateStatus();
          }}

          async function animateAll() {{
            if (!writer) return;
            i = -1;
            writer.hideCharacter();
            await writer.animateCharacter();
            i = totalStrokes() - 1;
            updateStatus();
          }}

          async function nextStroke() {{
            if (!writer) return;
            const t = totalStrokes();
            if (i + 1 >= t) return;
            i += 1;
            await writer.animateStroke(i);
            updateStatus();
          }}

          async function prevStroke() {{
            if (!writer) return;
            if (i <= -1) return;
            i -= 1;
            writer.hideCharacter();
            for (let k = 0; k <= i; k++) {{
              await writer.animateStroke(k);
            }}
            updateStatus();
          }}

          async function init() {{
            setErr("");
            setStatus("Loading stroke order…");

            const ok = await ensureLibLoaded();
            if (!ok) {{
              setErr("Failed to load HanziWriter library (CDN blocked or unreachable).");
              setStatus("");
              return;
            }}

            try {{
              data = await fetchJsonWithFallback(DATA_URLS, CHAR);
            }} catch (e) {{
              setErr("Failed to load stroke data for this character.");
              setStatus("");
              return;
            }}

            writer = window.HanziWriter.create("target", CHAR, {{
              width: 360,
              height: 360,
              padding: 12,
              showOutline: true,
              showCharacter: false,
              strokeAnimationSpeed: 1,
              delayBetweenStrokes: 120,
              charDataLoader: function() {{
                return Promise.resolve(data);
              }}
            }});

            document.getElementById("btnPrev").onclick = prevStroke;
            document.getElementById("btnNext").onclick = nextStroke;
            document.getElementById("btnReset").onclick = resetAll;
            document.getElementById("btnAnimate").onclick = animateAll;

            await resetAll();
          }}

          init();
        </script>
        """,
        height=520,
    )

# -----------------------------
# Main
# -----------------------------
def main():
    apply_dynamic_css()

    st.title("Chinese Components Explorer")

    if not component_map:
        st.stop()

    # -------------------------
    # Sidebar
    # -------------------------
    with st.sidebar:
        # Stroke order mode sidebar (minimal)
        if st.session_state.stroke_view_active:
            st.markdown("### Actions")
            st.button("← Back", on_click=end_stroke_view, use_container_width=True)
            st.button("← Back to list", on_click=back, use_container_width=True)
            st.button("Reset Filters", on_click=reset, use_container_width=True)
        else:
            if st.session_state.show_inputs:
                st.markdown("### Filters")

                st.slider("Stroke count", 0, 25, st.session_state.stroke_count, key="w_stroke", on_change=sync_stroke)

                radicals = ["none"] + sorted({component_map[k].get("meta", {}).get("radical")
                                              for k in component_map
                                              if component_map[k].get("meta", {}).get("radical")})
                st.selectbox("Radical", radicals, index=radicals.index(st.session_state.radical) if st.session_state.radical in radicals else 0,
                             key="w_radical", on_change=sync_radical)

                idc_opts = ["none"] + sorted(IDC_CHARS)
                st.selectbox("Structure (IDC)", idc_opts,
                             index=idc_opts.index(st.session_state.component_idc) if st.session_state.component_idc in idc_opts else 0,
                             key="w_idc", on_change=sync_idc)

                st.markdown("---")
                st.text_input("Jump to character", value=st.session_state.text_input_comp, key="w_text", on_change=sync_text)
                if st.session_state.text_input_warning:
                    st.warning(st.session_state.text_input_warning)

                st.button("Reset Filters", on_click=reset, use_container_width=True)

                # Preview in sidebar (always visible)
                if st.session_state.preview_active and st.session_state.preview_comp:
                    render_preview_sidebar(st.session_state.preview_comp)

            else:
                # Results mode sidebar
                st.markdown("### Actions")
                st.button("← Back to list", on_click=back, use_container_width=True)
                st.button("Reset Filters", on_click=reset, use_container_width=True)

                st.markdown("---")

                # Stroke order action uses selected_result_char if available, otherwise selected_comp
                so_char = (st.session_state.selected_result_char or st.session_state.selected_comp or "").strip()[:1]
                btn_label = "View stroke order" if not st.session_state.selected_result_char else f"View stroke order for {so_char}"
                if so_char and st.button(btn_label, use_container_width=True):
                    st.session_state.stroke_view_char = so_char
                    st.session_state.stroke_view_active = True
                    st.rerun()

                # Selected component (big)
                st.markdown(f"<div class='selected-char-sidebar'>{st.session_state.selected_comp}</div>", unsafe_allow_html=True)

                # Build sidebar results count (respect output mode)
                related = component_map[st.session_state.selected_comp].get("related_characters", [])
                chars_raw = [c for c in related if isinstance(c, str) and len(c) == 1]
                chars_unique = list(set(chars_raw))

                n = int(st.session_state.display_mode[0]) if st.session_state.display_mode != "Single Character" else 0
                compounds = {
                    c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", [])
                        if isinstance(w, str) and len(w) == n]
                    for c in chars_unique
                } if n else {c: [] for c in chars_unique}
                valid_chars = [c for c in chars_unique if n == 0 or compounds.get(c)]

                # If current selected result char is no longer valid under this mode, clear it
                if st.session_state.selected_result_char and st.session_state.selected_result_char not in valid_chars:
                    st.session_state.selected_result_char = ""

                count = len(valid_chars)
                label = "character" if count == 1 else "characters"
                comp = (st.session_state.selected_comp or "").strip()[:1]
                st.markdown(
                    f"<div class='results-header-sidebar'>{count} {label} with {comp}</div>",
                    unsafe_allow_html=True
                )

                modes = ["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"]
                st.radio("", options=modes, index=modes.index(st.session_state.display_mode),
                         key="w_display", on_change=sync_display)

                if st.session_state.selected_result_char:
                    st.caption(f"Selected character: {st.session_state.selected_result_char}")

    # -------------------------
    # Main content
    # -------------------------
    if st.session_state.stroke_view_active:
        render_stroke_order_view(st.session_state.stroke_view_char)
        return

    if st.session_state.show_inputs:
        # Browsing mode
        filter_parts = []
        if st.session_state.stroke_count > 0:
            filter_parts.append(f"{st.session_state.stroke_count} strokes")
        if st.session_state.radical != "none":
            filter_parts.append(f"Radical: {st.session_state.radical}")
        if st.session_state.component_idc != "none":
            filter_parts.append(f"Structure: {st.session_state.component_idc}")

        filter_summary = " · ".join(filter_parts) if filter_parts else "none"
        instruction = "Click TILE twice to see characters built on this component" if st.session_state.preview_active else "Click a TILE to preview"
        st.markdown(f"<div class='status-line'>Filtered: {filter_summary} — {instruction}</div>", unsafe_allow_html=True)

        filtered = [
            c for c in component_map
            if (st.session_state.stroke_count == 0 or get_stroke_count(c) == st.session_state.stroke_count)
            and (st.session_state.radical == "none" or component_map.get(c, {}).get("meta", {}).get("radical") == st.session_state.radical)
            and (st.session_state.component_idc == "none" or component_map.get(c, {}).get("meta", {}).get("decomposition", "").startswith(st.session_state.component_idc))
        ]

        counts = {c: result_count(c) for c in filtered}

        # Utility-first sorting: most results first, then fewer strokes, then stable tie-break
        sorted_comps = sorted(filtered, key=lambda c: (-counts.get(c, 0), get_stroke_count(c) or 999, c))

        if not sorted_comps:
            st.info("No components match current filters.")
            return

        PAGE_SIZE = 120
        GRID_COLS = 10
        total = len(sorted_comps)
        max_page = max(1, math.ceil(total / PAGE_SIZE))
        st.session_state.page = max(1, min(st.session_state.page, max_page))

        p1, p2, p3 = st.columns([1, 3, 1])
        with p1:
            if st.button("◀ Prev", disabled=st.session_state.page <= 1):
                st.session_state.page -= 1
        with p2:
            start = (st.session_state.page - 1) * PAGE_SIZE + 1
            end = min(st.session_state.page * PAGE_SIZE, total)
            st.markdown(f"<div style='text-align:center; padding:4px 0; color:#555;'>{start}–{end} of {total}</div>", unsafe_allow_html=True)
        with p3:
            if st.button("Next ▶", disabled=st.session_state.page >= max_page):
                st.session_state.page += 1

        page = sorted_comps[(st.session_state.page - 1) * PAGE_SIZE: st.session_state.page * PAGE_SIZE]
        cols = st.columns(GRID_COLS)
        for i, ch in enumerate(page):
            with cols[i % GRID_COLS]:
                preview = st.session_state.preview_active and st.session_state.preview_comp == ch
                st.button(
                    ch,
                    key=f"b_{ch}_{st.session_state.page}",
                    use_container_width=True,
                    type="primary" if preview else "secondary",
                    on_click=tile_click,
                    args=(ch,),
                )

    else:
        # Results mode (secondary list)
        related = component_map[st.session_state.selected_comp].get("related_characters", [])

        # Deduplicate and filter single characters
        chars = list(set([c for c in related if isinstance(c, str) and len(c) == 1]))

        # Phrases mode length
        n = int(st.session_state.display_mode[0]) if st.session_state.display_mode != "Single Character" else 0

        # Compounds dictionary preserved (this keeps your phrases working)
        compounds = {
            c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", [])
                if isinstance(w, str) and len(w) == n]
            for c in chars
        } if n else {c: [] for c in chars}

        valid_chars = [c for c in chars if n == 0 or compounds.get(c)]
        valid_chars = sorted(valid_chars, key=lambda x: get_stroke_count(x) or 999)

        # If the selected result char is no longer present, clear it
        if st.session_state.selected_result_char and st.session_state.selected_result_char not in valid_chars:
            st.session_state.selected_result_char = ""

        for c in valid_chars:
            pick_col, info_col = st.columns([1, 9], vertical_alignment="top")

            with pick_col:
                selected = (st.session_state.selected_result_char == c)
                if st.button("Select", key=f"pick_{c}", use_container_width=True, type="primary" if selected else "secondary"):
                    st.session_state.selected_result_char = c
                    st.rerun()

            with info_col:
                meta = component_map.get(c, {}).get("meta", {})
                fd = {
                    "Pinyin": clean_field(meta.get("pinyin", "—")),
                    "Strokes": f"{get_stroke_count(c)} strokes" if get_stroke_count(c) else "unknown",
                    "Radical": clean_field(meta.get("radical", "—")),
                    "Decomposition": clean_field(meta.get("decomposition", "—")),
                    "Definition": clean_field(meta.get("definition", "—")),
                }

                st.markdown(
                    f"""
                    <div class="char-card">
                      <div style="display:flex; gap:14px; align-items:flex-start;">
                        <div style="font-size:44px; line-height:1;">{c}</div>
                        <div style="flex:1;">
                          <div style="display:grid; grid-template-columns: 120px 1fr; row-gap:4px; column-gap:10px;">
                            <div><b>Pinyin</b></div><div>{fd["Pinyin"]}</div>
                            <div><b>Strokes</b></div><div>{fd["Strokes"]}</div>
                            <div><b>Radical</b></div><div>{fd["Radical"]}</div>
                            <div><b>Decomposition</b></div><div>{fd["Decomposition"]}</div>
                            <div><b>Definition</b></div><div>{fd["Definition"]}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Phrases box (unchanged behavior)
                if n > 0 and compounds.get(c):
                    st.markdown(
                        "<div class='phrases-box'><b>Phrases</b><br>" + " ".join(sorted(compounds[c])) + "</div>",
                        unsafe_allow_html=True
                    )

            st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)

        if valid_chars and n:
            with st.expander("Export Compounds"):
                st.text_area("Copy list", "\n".join(w for c in valid_chars for w in compounds[c]), height=150)

if __name__ == "__main__":
    main()
