
# dyslexim/core/js_handler.py

def get_js_gaze_handler(highlight_color, font, alignment):
    """Returns the JavaScript gaze handler with the specified highlight color, font, and alignment."""
    return f"""
    (function(){{
      if (window.__dyslexim_handler_installed) return;
      window.__dyslexim_handler_installed = true;
      window.__dyslexim_prevEl = null;
      let debounceTimeout;

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
          if (!el || el.tagName === 'BODY' || el.tagName === 'HTML') {{
            const els = document.elementsFromPoint(x+6, y) || [];
            el = els[0] || null;
          }}
          if (!el || el.tagName === 'BODY' || el.tagName === 'HTML') return;

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

          el.classList.add('__dyslexim_highlight');
          const tag = el.tagName ? el.tagName.toLowerCase() : '';
          const textLike = tag === 'p' || tag === 'span' || tag === 'div' || el.closest('article') || el.closest('p');
          if (textLike) {{
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
          }}

          const rect = el.getBoundingClientRect();
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
