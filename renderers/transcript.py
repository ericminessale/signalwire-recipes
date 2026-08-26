"""Renders an annotated transcript. Discovered by filename; never imported by name.

Every turn carries its index and its character count. The replay player reads
those to pace itself, so timing is a presentation choice made in the browser
rather than a number stored in the data. A transcript is a specimen of what
the code does, and inventing precise durations for it would be a claim nobody
measured.

The whole transcript is always in the DOM and always in the accessibility
tree. The player fades turns rather than hiding them, so a reader without
JavaScript, any crawler, and any screen reader get the entire thing whatever
the player is doing.
"""
import html


def render(data):
    lines = data.get("lines", [])
    out = ['<div class="tr" data-turns="%d">' % len(lines)]
    for i, line in enumerate(lines):
        if line.get("note"):
            text = line["note"]
            out.append(
                '<span class="sys" data-i="%d" data-n="%d">%s</span>'
                % (i, len(text), html.escape(text))
            )
        else:
            who = html.escape(line.get("who", ""))
            cls = " ai" if line.get("ai") else ""
            text = line.get("text", "")
            out.append(
                '<div class="l" data-i="%d" data-n="%d">'
                '<span class="w%s">%s</span><span>%s</span></div>'
                % (i, len(text), cls, who, html.escape(text))
            )
    out.append("</div>")
    return "".join(out)
