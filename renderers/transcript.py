"""Renders an annotated transcript. Discovered by filename; never imported by name."""
import html


def render(data):
    out = ['<div class="tr">']
    for line in data.get("lines", []):
        if line.get("note"):
            out.append('<span class="sys">%s</span>' % html.escape(line["note"]))
        else:
            who = html.escape(line.get("who", ""))
            cls = " ai" if line.get("ai") else ""
            out.append(
                '<div class="l"><span class="w%s">%s</span><span>%s</span></div>'
                % (cls, who, html.escape(line.get("text", "")))
            )
    out.append("</div>")
    return "".join(out)
