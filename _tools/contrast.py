"""WCAG contrast for the token pairs actually used. Read-only, stdlib only.

Two lists, and the second is the point. PAIRS asserts a minimum. MUST_FAIL
asserts a maximum: a colour that is documented as decoration or large-text-only
is held to that by a number, so "copper is never body text" cannot quietly
become false the way a comment can.

usage: python _tools/contrast.py
"""
import sys

TOK = {
    # Surfaces
    "paper":         "#FAF8F4",
    "paper-2":       "#F1EDE4",
    "ink":           "#17181B",
    "ink-2":         "#232529",
    # Text
    "text":          "#17181B",
    "text-2":        "#55565B",
    "text-on-ink":   "#F2F0EB",
    "text-2-on-ink": "#A8A6A0",
    # Rules
    "rule":          "#C6BEA9",
    "rule-ink":      "#3A3C42",
    # Copper carries measurement
    "copper-700":    "#8F4415",
    "copper-500":    "#B4631E",
    "copper-400":    "#C87A3C",
    # Signal, rationed
    "orange":        "#C84219",
    "orange-on-ink": "#E8734B",
    "green":         "#1D6B45",
}


def lum(hexc):
    h = hexc.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def f(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = lum(TOK[a]), lum(TOK[b])
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# (foreground, background, minimum, where)
PAIRS = [
    ("text", "paper", 7.0, "body copy, held to AAA not AA"),
    ("text", "paper-2", 7.0, "body on the alternate band"),
    ("text-2", "paper", 4.5, "captions and meta on paper"),
    ("text-2", "paper-2", 4.5, "captions on the alternate band"),

    ("text-on-ink", "ink", 7.0, "body reversed out of an ink band"),
    ("text-on-ink", "ink-2", 7.0, "body on a raised block inside ink"),
    ("text-2-on-ink", "ink", 4.5, "muted text on ink"),

    ("copper-700", "paper", 4.5, "footnote markers and source labels"),
    ("copper-700", "paper-2", 4.5, "same on the alternate band"),
    ("copper-400", "ink", 4.5, "copper inside an ink band"),

    ("orange", "paper", 4.5, "the loss figure, and form errors"),
    ("orange-on-ink", "ink", 4.5, "the same signal reversed out"),
    ("green", "paper", 4.5, "form success"),

    # Action is ink. Pill buttons, filled dark, paper text.
    ("text-on-ink", "ink", 4.5, "primary button label"),
    ("paper", "copper-700", 4.5, "button label on the copper hover state"),
    ("text", "paper", 3.0, "ink-outlined button border against paper"),

    # Focus must be visible on both surfaces.
    ("copper-700", "paper", 3.0, "focus ring on paper"),
    ("copper-400", "ink", 3.0, "focus ring inside an ink band"),
]

# (foreground, background, must stay BELOW, why)
MUST_FAIL = [
    ("copper-500", "paper", 4.5,
     "copper-500 is display numerals at 24px and over. If it ever clears 4.5 "
     "someone has darkened it, and the large-text-only rule has quietly become "
     "a lie."),
    ("copper-700", "ink", 3.0,
     "the paper copper is nearly invisible on ink at 2.54:1. This pair must "
     "never be used, which is why the dark containers redefine --clr-accent to "
     "copper-400. Found by measuring rendered pages, not this file: a static "
     "checker only tests the pairs somebody thought to list."),
    ("rule", "paper", 3.0,
     "the hairline is decoration. If it clears 3.0 it reads as a border and "
     "starts carrying meaning colour alone should not carry."),
]


def main():
    print("contrast, measured\n")
    failures = []

    for fg, bg, minimum, where in PAIRS:
        r = ratio(fg, bg)
        ok = r >= minimum
        mark = "ok  " if ok else "FAIL"
        print(f"  {mark} {r:6.2f}  need {minimum:>4}  {fg} on {bg:12} {where}")
        if not ok:
            failures.append(f"{fg} on {bg} is {r:.2f}, needs {minimum}: {where}")

    print()
    for fg, bg, ceiling, why in MUST_FAIL:
        r = ratio(fg, bg)
        ok = r < ceiling
        mark = "ok  " if ok else "FAIL"
        print(f"  {mark} {r:6.2f}  under {ceiling:>4}  {fg} on {bg:12} must stay below")
        if not ok:
            failures.append(f"{fg} on {bg} is {r:.2f} and must stay under {ceiling}. {why}")

    print()
    if failures:
        print(f"{len(failures)} problems:")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"{len(PAIRS)} pairs meet their minimum, "
          f"{len(MUST_FAIL)} stay under their ceiling.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
