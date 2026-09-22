"""WCAG contrast for the token pairs actually used. Read-only, stdlib only.

Two lists, and the second is the point. PAIRS asserts a minimum. MUST_FAIL
asserts a maximum: a colour that is documented as decoration or large-text-only
is held to that by a number, so "copper is never body text" cannot quietly
become false the way a comment can.

usage: python _tools/contrast.py
"""
import sys

TOK = {
    # Sampled from the logo itself. #5010D0 is the mark's dominant violet,
    # unmodified, because it already clears 8:1 on the page ground.
    "violet":      "#5010D0",
    "violet-deep": "#3D0EA8",
    "violet-wash": "#F1EDFD",
    "cyan":        "#0090E0",
    "cyan-text":   "#0A6FA8",

    "bg":     "#FFFFFF",
    "bg-2":   "#F4F3F8",
    "ink":    "#141220",
    "muted":  "#56536B",
    "rule":   "#E3E1EC",
    "on-fill": "#FFFFFF",

    "err":    "#C11B4B",
    "ok":     "#0F7A4A",
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
    ("ink", "bg", 7.0, "body copy, held to AAA"),
    ("ink", "bg-2", 7.0, "body on the tinted band"),
    ("ink", "violet-wash", 7.0, "body inside a violet panel"),
    ("muted", "bg", 4.5, "captions and meta"),
    ("muted", "bg-2", 4.5, "captions on the tinted band"),

    ("violet", "bg", 4.5, "the brand colour as text, eyebrows and figures"),
    ("violet", "bg-2", 4.5, "the same on the tinted band"),
    ("violet", "violet-wash", 4.5, "the same inside its own panel"),
    ("on-fill", "violet", 4.5, "button label on the brand fill"),
    ("on-fill", "violet-deep", 4.5, "button label on the pressed state"),

    ("cyan-text", "bg", 4.5, "cyan where it has to carry small text"),
    ("err", "bg", 4.5, "form errors"),
    ("ok", "bg", 4.5, "form success"),

    ("violet", "bg", 3.0, "focus ring on the page ground"),
    ("ink", "bg", 3.0, "outlined button border"),
]

# (foreground, background, must stay BELOW, why)
MUST_FAIL = [
    ("cyan", "bg", 4.5,
     "the logo's cyan is 3.32:1. It is for rules, marks and large type only. If "
     "it ever clears 4.5 somebody has darkened it and the rule has quietly "
     "become a lie."),
    ("rule", "bg", 3.0,
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
