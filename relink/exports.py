"""Private JSON downloads without Streamlit's unauthenticated global media URLs."""
import base64
import hashlib
from html import escape

import streamlit as st

from relink.history_access import current_access


def json_download(label, data, *, file_name, key, help=None):
    if current_access().mode == 'local':
        return st.download_button(label, data=data, file_name=file_name, mime='application/json', key=key, help=help)
    # Only owned, constant code executes. Remote/user data is base64 bytes in an
    # inert attribute, never interpolated as HTML or JavaScript. The payload is
    # delivered with this session's page, not registered in the global /media store.
    payload = base64.b64encode(data.encode('utf-8')).decode('ascii')
    identifier = 'relink-export-' + hashlib.sha256(key.encode()).hexdigest()[:24]
    html = ('<button type="button" id="' + identifier + '" data-payload="' + payload +
            '" data-filename="' + escape(file_name, quote=True) + '" title="' + escape(help or '', quote=True) +
            '" style="background:transparent;color:inherit;border:1px solid #52616b;border-radius:8px;'
            'padding:10px 16px;font:inherit;cursor:pointer">' + escape(label) + '</button>')
    script = '''<script>
    (() => {
      const button = document.getElementById("IDENTIFIER");
      if (!button) return;
      button.onclick = () => {
        const bytes = Uint8Array.from(atob(button.dataset.payload), c => c.charCodeAt(0));
        const url = URL.createObjectURL(new Blob([bytes], {type: "application/json;charset=utf-8"}));
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = button.dataset.filename;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      };
    })();
    </script>'''.replace('IDENTIFIER', identifier)
    st.html(html + script, unsafe_allow_javascript=True)
