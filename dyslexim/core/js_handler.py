# dyslexim/core/js_handler.py

def get_js_gaze_handler(highlight_color, font, alignment, reading_mask, tts_hover_time):
    """Returns the JavaScript gaze handler with the specified highlight color, font, and alignment."""
    return f"""
    (function(){{
      if (window.__dyslexim_handler_installed) return;
      window.__dyslexim_handler_installed = true;
      window.__dyslexim_prevEl = null;
      let debounceTimeout;
      let ttsTimeout;

      const TEXT_TAGS = ['P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'SPAN', 'A', 'LI', 'TD', 'TH', 'CAPTION', 'PRE', 'CODE', 'BLOCKQUOTE'];

      function debounce(func, delay) {{
          return function(...args) {{
              clearTimeout(debounceTimeout);
              debounceTimeout = setTimeout(() => func.apply(this, args), delay);
          }};
      }}

      const handleGaze = function(normX, normY) {{
        try {{
          const w = document.documentElement.clientWidth || window.innerWidth;
          const h = document.documentElement.clientHeight || window.innerHeight;
          const x = Math.round(Math.max(0, Math.min(1, normX)) * w);
          const y = Math.round(Math.max(0, Math.min(1, normY)) * h);

          let el = document.elementFromPoint(x, y);

          if (!el || el.tagName === 'BODY' || el.tagName === 'HTML') return;

          if (!TEXT_TAGS.includes(el.tagName)) {{
              el = el.closest(TEXT_TAGS.map(t => t.toLowerCase()).join(','));
          }}

          if (!el) return;

          if (window.__dyslexim_prevEl === el) return;

          if (window.__dyslexim_prevEl) {{
            window.__dyslexim_prevEl.classList.remove('__dyslexim_highlight');
            if (window.__dyslexim_prevEl.__dyslexim_prevStyles) {{
              const prev = window.__dyslexim_prevEl.__dyslexim_prevStyles;
              for (const k in prev) {{
                window.__dyslexim_prevEl.style[k] = prev[k];
              }}
              window.__dyslexim_prevEl.__dyslexim_prevStyles = null;
            }}
          }}

          clearTimeout(ttsTimeout);
          speechSynthesis.cancel();

          el.classList.add('__dyslexim_highlight');
          el.__dyslexim_prevStyles = {{
            lineHeight: el.style.lineHeight || '',
            letterSpacing: el.style.letterSpacing || '',
            backgroundColor: el.style.backgroundColor || '',
            fontFamily: el.style.fontFamily || '',
            textAlign: el.style.textAlign || ''
          }};
          el.style.transition = 'all 0.12s ease';
          el.style.lineHeight = '1.8';
          el.style.letterSpacing = '0.04em';
          el.style.backgroundColor = 'rgba(255,255,0,0.03)';
          el.style.fontFamily = `'{font}'`;
          el.style.textAlign = '{alignment}';

          ttsTimeout = setTimeout(() => {{
            const text = el.innerText || el.textContent;
            if (text) {{
              const utterance = new SpeechSynthesisUtterance(text);
              speechSynthesis.speak(utterance);
            }}
          }}, {tts_hover_time * 1000});

          const rect = el.getBoundingClientRect();
          if ({str(reading_mask).lower()}) {{
            let readingMask = document.getElementById('__dyslexim_reading_mask');
            if (!readingMask) {{
                readingMask = document.createElement('div');
                readingMask.id = '__dyslexim_reading_mask';
                readingMask.style.position = 'fixed';
                readingMask.style.top = '0';
                readingMask.style.left = '0';
                readingMask.style.width = '100vw';
                readingMask.style.height = '100vh';
                readingMask.style.pointerEvents = 'none';
                readingMask.style.zIndex = '999999';
                readingMask.style.transition = 'all 0.2s ease-in-out';
                readingMask.style.boxShadow = '0 0 0 9999px rgba(0,0,0,0.7)';
                readingMask.style.backdropFilter = 'blur(5px)';
                document.body.appendChild(readingMask);
            }}
            const padding = 10;
            readingMask.style.clipPath = `inset(${{rect.top - padding}}px 0 ${{h - (rect.bottom + padding)}}px 0)`;

          }} else {{
            let readingMask = document.getElementById('__dyslexim_reading_mask');
            if (readingMask) {{
                readingMask.remove();
            }}
          }}

          if (rect.top < 24 || rect.bottom > h - 24) {{
            el.scrollIntoView({{behavior:'smooth', block:'center'}});
          }}

          window.__dyslexim_prevEl = el;
        }} catch (e) {{
          // console.error('Dyslexim gaze handler error', e);
        }}
      }};

      window.__dyslexim_handleGaze = debounce(handleGaze, 50);

      (function() {{
        const style = document.createElement('style');
        style.setAttribute('data-dyslexim', '1');
        style.textContent = `
          .__dyslexim_highlight {{
            outline: 3px solid {highlight_color} !important;
            outline-offset: 3px !important;
            background-color: rgba(255,255,0,0.04) !important;
            transition: outline 0.12s ease, background-color 0.12s ease !important;
            box-shadow: 0 0 15px {highlight_color};
          }}
        `;
        document.head && document.head.appendChild(style);
      }})();

    }})();
    """

def get_focus_mode_js(is_enabled):
    """Returns JavaScript to toggle focus mode (removing/restoring styles)."""
    if is_enabled:
        return """
        (function() {
            document.querySelectorAll('style, link[rel="stylesheet"]').forEach(el => {
                if (el.getAttribute('data-dyslexim') !== '1') {
                    el.setAttribute('data-dyslexim-disabled', 'true');
                    el.disabled = true;
                }
            });
        })();
        """
    else:
        return """
        (function() {
            document.querySelectorAll('[data-dyslexim-disabled="true"]').forEach(el => {
                el.disabled = false;
                el.removeAttribute('data-dyslexim-disabled');
            });
        })();
        """