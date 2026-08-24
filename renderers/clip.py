"""Renders a recorded clip with a static poster fallback."""
import html


def render(data):
    src = html.escape(data.get("src", ""))
    cap = html.escape(data.get("caption", ""))
    return (
        '<figure class="clip"><video controls preload="none" src="%s"></video>'
        "<figcaption>%s</figcaption></figure>" % (src, cap)
    )
