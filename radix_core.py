# radix_core.py
# All non-UI logic, data loading, helpers and HTML generators for Radix

import json
import math
import html
import sqlite3
import unicodedata
import gc
import base64
import json as json_module  # for dumps in HTML
from typing import List, Dict, Optional

# --- Optional: OpenCC for Traditional/Simplified Conversion ---
try:
    from opencc import OpenCC
    cc_t2s = OpenCC("t2s")
    cc_s2t = OpenCC("s2t")
except ImportError:
    cc_t2s = None
    cc_s2t = None

IDC_CHARS = {"⿰", "⿱", "⿲", "⿳", "⿴", "⿵", "⿶", "⿷", "⿸", "⿹", "⿺", "⿻"}
SCRIPT_FILTERS = ["Any", "Simplified", "Traditional"]


# --- Zipf Frequency ---
def get_zipf_frequency():
    try:
        from wordfreq import zipf_frequency
        return zipf_frequency
    except Exception:
        return None


ZIPF = get_zipf_frequency()


def zipf_commonness_raw(ch: str) -> float:
    if not ch or ZIPF is None:
        return float("-inf")
    try:
        z = float(ZIPF(ch, "zh"))
    except:
        z = float("-inf")
    if z <= 0:
        if cc_s2t:
            try:
                z = max(z, float(ZIPF(cc_s2t.convert(ch), "zh")))
            except:
                pass
        if cc_t2s:
            try:
                z = max(z, float(ZIPF(cc_t2s.convert(ch), "zh")))
            except:
                pass
    return z


# --- Data Loading & Augmentation ---
def load_and_augment_map():
    try:
        with open("enhanced_component_map_with_etymology.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}

    for char, info in data.items():
        meta = info.get("meta", {})
        rel = info.get("related_characters", [])
        info['usage_count'] = len({c for c in rel if isinstance(c, str) and len(c) == 1})
        info['zipf_val'] = zipf_commonness_raw(char)

        s = meta.get("strokes")
        try:
            if isinstance(s, (int, float)) and s > 0:
                info['stroke_count'] = int(s)
            elif isinstance(s, str) and s.isdigit():
                info['stroke_count'] = int(s)
            else:
                info['stroke_count'] = None
        except:
            info['stroke_count'] = None

    gc.collect()
    return data


def get_component_stats(_component_map):
    r_groups = {}
    idc_counts = {}
    used_comps = set()

    for c, data in _component_map.items():
        r = data.get("meta", {}).get("radical")
        if r:
            gs = _component_map.get(r, {}).get('stroke_count') or 999
            r_groups.setdefault(gs, []).append(r)

        d = data.get("meta", {}).get("decomposition", "")
        if d and d[0] in IDC_CHARS:
            idc = d[0]
            idc_counts[idc] = idc_counts.get(idc, 0) + 1

        for ch in d:
            if ch not in IDC_CHARS:
                used_comps.add(ch)

    for gs in r_groups:
        r_groups[gs] = sorted(list(set(r_groups[gs])))

    gc.collect()
    return {
        "rad_groups": r_groups,
        "idc_counts": idc_counts,
        "used_components": used_comps
    }


component_map = load_and_augment_map()
stats_cache = get_component_stats(component_map) if component_map else {}


# --- Database ---
def get_db_connection():
    try:
        conn = sqlite3.connect("phrases.db", check_same_thread=False)
        return conn
    except Exception:
        return None


def batch_get_phrase_details(words, conn):
    if not conn or not words:
        return {}
    try:
        placeholders = ",".join(["?"] * len(words))
        cursor = conn.cursor()
        query = f"SELECT word, pinyin, meanings FROM phrases WHERE word IN ({placeholders})"
        cursor.execute(query, list(words))
        results = cursor.fetchall()
        return {row[0]: {"pinyin": row[1], "meanings": row[2]} for row in results}
    except Exception:
        return {}


# --- Pure Helpers ---
def get_stroke_count(char):
    return component_map.get(char, {}).get("stroke_count")


def component_usage_count(comp: str) -> int:
    return component_map.get(comp, {}).get("usage_count", 0)


def sort_key_usage_then_zipf(ch: str):
    info = component_map.get(ch, {})
    use = info.get('usage_count', 0)
    z = info.get('zipf_val', float("-inf"))
    strokes = info.get('stroke_count') or 999
    group = 0 if use >= 3 else 1
    if group == 0:
        return (group, -use, -z, strokes, ch)
    return (group, -z, strokes, ch)


def apply_script_filter(chars: List[str], script_filter: str) -> List[str]:
    if script_filter == "Any":
        return chars
    if script_filter == "Simplified":
        return [c for c in chars if not cc_t2s or cc_t2s.convert(c) == c]
    return [c for c in chars if not cc_s2t or cc_s2t.convert(c) == c]


def clean_field(field):
    return field[0] if isinstance(field, list) and field else field or "—"


def get_etymology_text(meta):
    etymology = meta.get("etymology", {})
    hint = clean_field(etymology.get("hint", ""))
    if not hint or hint.lower() == "no hint":
        hint = ""
    details = clean_field(etymology.get("details", ""))
    if details == "—":
        details = ""
    parts = [p for p in [hint, details] if p]
    return "; ".join(parts) if parts else None


def format_decomposition(char):
    d = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    return "—" if not d or "?" in d else d


def normalize_single_hanzi(raw: str) -> str:
    if not raw:
        return ""
    s = unicodedata.normalize("NFC", raw)
    chars = [ch for ch in s.strip() if not ch.isspace() and unicodedata.category(ch) != "Cf"]
    return chars[0] if len(chars) == 1 else ""


def resolve_to_known_variant(ch: str) -> str:
    if not ch:
        return ""
    if ch in component_map:
        return ch
    if cc_s2t:
        t = cc_s2t.convert(ch)
        if t in component_map:
            return t
    if cc_t2s:
        s = cc_t2s.convert(ch)
        if s in component_map:
            return s
    return ""


def build_chatgpt_prompt(char: str) -> str:
    char = (char or "").strip()[:1]
    meta = component_map.get(char, {}).get("meta", {})
    def_en = clean_field(meta.get("definition", ""))
    return f"""You are a bilingual Chinese dictionary editor.

Task:
For the single Hanzi below, give two example sentences that BEST illustrate the meaning (prefer everyday usage unless the character is primarily literary).

For each example, provide:
a) Traditional Chinese sentence
b) Simplified Chinese sentence
c) Natural English translation
d) Target word/phrase (must include the character)
e) Read-aloud pinyin of the full Chinese sentence (with tone marks, natural word grouping)

Hanzi: {char}
- English definition: {def_en}
"""


def generate_clean_card_html(c: str, usage_count: Optional[int] = None) -> str:
    if not c:
        return ""
    info = component_map.get(c, {})
    meta = info.get("meta", {})
    pinyin = clean_field(meta.get("pinyin", ""))
    strokes = info.get('stroke_count')
    radical = clean_field(meta.get("radical", ""))
    decomp = format_decomposition(c)
    definition = clean_field(meta.get("definition", ""))
    etymology = get_etymology_text(meta)

    meta_items = []
    if pinyin and pinyin != "—":
        meta_items.append(f"<span class='meta-pinyin'>{pinyin}</span>")
    if strokes:
        meta_items.append(f"<span class='meta-tag'>{strokes} strokes</span>")
    if radical and radical != "—":
        meta_items.append(f"<span class='meta-tag'>Rad. {radical}</span>")
    if decomp and decomp != "—":
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
    def_html = f"<div class='def-row'>{definition}</div>" if definition and definition != "—" else ""
    ety_html = f"<div class='ety-row'>{etymology}</div>" if etymology else ""
    return f"<div class='char-card'>{meta_html}{def_html}{ety_html}</div>"


# --- iPad-Safe Download HTML (exact original) ---
def render_ipad_safe_download_html(data_str: str, filename: str, label: str) -> str:
    b64 = base64.b64encode(data_str.encode()).decode()
    href = f'data:application/octet-stream;base64,{b64}'
    return f"""
    <div style="text-align:center; margin: 10px 0;">
        <a href="{href}" download="{filename}" target="_self" style="
            text-decoration: none;
            color: white;
            background-color: #d35400;
            padding: 12px 24px;
            border-radius: 12px;
            font-weight: 700;
            display: inline-block;
            box-shadow: 0 4px 12px rgba(211, 84, 0, 0.2);
            -webkit-appearance: none;
        ">
            {label}
        </a>
    </div>
    <script>
        const link = document.querySelector('a[download="{filename}"]');
        link.addEventListener('click', () => {{
            console.log('Download triggered');
        }});
    </script>
    """


# --- Stroke Order Sidebar HTML ---
def get_stroke_order_sidebar_html(char: str, size: int = 140) -> tuple[str, int]:
    char = (char or "").strip()[:1]
    if not char:
        return "", 0
    pinyin = clean_field(component_map.get(char, {}).get("meta", {}).get("pinyin", ""))
    h = size + 80
    html_content = f"""
    <div style="display:flex; flex-direction:column; align-items:center; margin:20px 0;">
        <div style="text-align:center; font-size:2.5rem; font-weight:bold; color:#e67e22; margin-bottom:10px;">{pinyin}</div>
        <div id="sb-hw-{hash(char)}" style="width:{size}px; height:{size}px;"></div>
    </div>
    <script>
    (function() {{
        const char = {json_module.dumps(char, ensure_ascii=False)};
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

        function speak(text) {{
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance(text);
                u.lang = 'zh-CN';
                const voices = window.speechSynthesis.getVoices();
                const zhVoice = voices.find(v => v.lang.replace('_', '-').toLowerCase().startsWith('zh'));
                if (zhVoice) u.voice = zhVoice;
                window.speechSynthesis.speak(u);
            }}
        }}

        async function init() {{
            try {{
                await ensureLib();
                const writer = window.HanziWriter.create(target, char, {{
                    width: {size}, height: {size}, padding: 8, showOutline: true, showCharacter: false,
                    strokeAnimationSpeed: 1.3, delayBetweenStrokes: 100
                }});
                writer.showCharacter();
                const el = document.getElementById(target);
                el.style.cursor = 'pointer';
                const trigger = (e) => {{
                    e.preventDefault(); 
                    speak(char);
                    writer.hideCharacter();
                    writer.animateCharacter();
                }};
                el.addEventListener('click', trigger);
                el.addEventListener('touchend', trigger);
            }} catch(e) {{
                document.getElementById(target).innerHTML = `<div style="font-size:${size*0.7}px; line-height:${size}px; text-align:center;">${{char}}</div>`;
            }}
        }}
        init();
    }})();
    </script>
    """
    return html_content, h


# --- Full Stroke Order View HTML ---
def get_stroke_order_view_html(primary_char: str, display_mode: str) -> tuple[str, Optional[str]]:
    primary_char = (primary_char or "").strip()[:1]
    if not primary_char:
        return "<p>No character selected.</p>", None

    s_char = cc_t2s.convert(primary_char) if cc_t2s else primary_char
    t_char = cc_s2t.convert(primary_char) if cc_s2t else primary_char

    chars_to_show = list(dict.fromkeys([c for c in [s_char, t_char] if c]))

    BOX_SIZE = 280
    container_html = ""
    for i, c in enumerate(chars_to_show):
        label_text = ""
        if s_char != t_char:
            label_text = "Simplified" if c == s_char else "Traditional"
        label_html = f"<div style='text-align:center; font-weight:bold; color:#555; margin-bottom:5px;'>{label_text}</div>" if label_text else ""
        pinyin = clean_field(component_map.get(c, {}).get("meta", {}).get("pinyin", ""))
        container_html += f"""
        <div style="display:flex; flex-direction:column; align-items:center;">
            {label_html}
            <div style="font-size:2.5rem; color:#e67e22; font-weight:bold; margin-bottom:10px;">{pinyin}</div>
            <div id="hw-target-{i}" style="width:{BOX_SIZE}px;height:{BOX_SIZE}px;border:1px solid #e0e0e0;border-radius:12px; background:white;"></div>
        </div>
        """

    # Phrases HTML — strictly 800px max-width
    phrases_html = None
    if display_mode != "Single Character" and primary_char:
        n = {"2-Character Phrases": 2, "3-Character Phrases": 3, "4-Character Phrases": 4}.get(display_mode, 0)
        meta_compounds = component_map.get(primary_char, {}).get("meta", {}).get("compounds", [])
        relevant = [w for w in meta_compounds if isinstance(w, str) and len(w) == n]
        if relevant:
            db_conn = get_db_connection()
            if db_conn:
                phrases_map = batch_get_phrase_details(sorted(relevant), db_conn)
                items = []
                for word in sorted(relevant):
                    entry = phrases_map.get(word)
                    if entry:
                        pinyin = entry.get("pinyin", "")
                        meanings = html.escape(entry.get("meanings", "")[:100] + ("..." if len(entry.get("meanings", "")) > 100 else ""))
                        items.append(f"<div class='compound-item'>"
                                     f"<span class='cp-word'>{word}</span>"
                                     f"<span class='cp-pinyin'>{pinyin}</span>"
                                     f"<span class='cp-mean'>{meanings}</span>"
                                     f"</div>")
                    else:
                        items.append(f"<div class='compound-item'><span class='cp-word'>{word}</span></div>")
                phrases_html = f"""
                <div style='padding:15px; background:#f1f8e9; border-radius:8px; 
                             margin:10px auto; border:1px solid #dcedc8; max-width:800px; max-height:400px; overflow-y:auto;'>
                  <div style='font-weight:bold; margin-bottom:10px; color:#2e7d32; 
                       border-bottom:2px solid #a5d6a7; padding-bottom:5px; text-align:center;'>
                    {display_mode} containing {primary_char}
                  </div>
                  {''.join(items)}
                </div>
                """

    full_html = f"""
    <div style="display:flex; gap:15px; align-items:flex-start; flex-wrap:wrap; justify-content:center;">
        {container_html}
    </div>
    <div style="display:flex; justify-content:center; margin-top:15px; gap:8px;">
         <button id="hw-reset">Reset</button><button id="hw-animate">Replay Animation</button>
    </div>
    <div id="hw-error" style="margin-top:10px; color:#b00020; text-align:center;"></div>
    <script>
    (function() {{
        const chars = {json_module.dumps(chars_to_show, ensure_ascii=False)};
        const boxSize = {BOX_SIZE};
        const errEl = document.getElementById('hw-error');

        function speak(text) {{
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance(text);
                u.lang = 'zh-CN';
                const voices = window.speechSynthesis.getVoices();
                const zhVoice = voices.find(v => v.lang.replace('_', '-').toLowerCase().startsWith('zh'));
                if (zhVoice) u.voice = zhVoice;
                window.speechSynthesis.speak(u);
            }}
        }}
        
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
                    const dataUrls = [`https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/${{char}}.json`,
                                      `https://unpkg.com/hanzi-writer-data@2.0.1/${{char}}.json`];
                    let hasData = false;
                    for (const url of dataUrls) {{ 
                        try {{ 
                            const res = await fetch(url); 
                            if (res.ok) {{ hasData = true; break; }} 
                        }} catch (e) {{}} 
                    }}
                    if(hasData) {{
                        const writer = window.HanziWriter.create(targetId, char, {{
                            width: boxSize, height: boxSize, padding: 10, showOutline: true, showCharacter: false,
                            strokeAnimationSpeed: 1, delayBetweenStrokes: 60
                        }});
                        writers.push({{w: writer, c: char}});
                    }} else {{
                        document.getElementById(targetId).innerHTML = `<div style="line-height:${{boxSize}}px; text-align:center; font-size:${{boxSize/2}}px; color:#ddd;">${{char}}</div>`;
                    }}
                }}
                autoAnimateAll(true);
            }} catch (e) {{ errEl.textContent = e.message || String(e); }}
        }}
        
        async function playSequence(item, silent) {{
            const writer = item.w;
            const char = item.c;
            for (let k = 0; k < 3; k++) {{
                if (!silent) speak(char);
                writer.hideCharacter();
                await writer.animateCharacter();
                await new Promise(r => setTimeout(r, 800));
            }}
            writer.showCharacter();
        }}
        
        function autoAnimateAll(silent = false) {{
            writers.forEach(item => {{ playSequence(item, silent); }});
        }}
        
        function resetAll() {{
            writers.forEach(item => {{ item.w.hideCharacter(); }});
        }}
        
        document.getElementById('hw-reset').addEventListener('click', resetAll);
        document.getElementById('hw-animate').addEventListener('click', () => autoAnimateAll(false));
        init();
    }})();
    </script>
    """
    return full_html, phrases_html