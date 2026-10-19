"""Original chiptune soundtrack, written as MML note-sequence data.

Each song has four voices: pulse 1 (lead), pulse 2 (harmony / arpeggio),
triangle (bass) and noise (drums). Helper functions expand chord
progressions into arpeggios and bass lines so the data stays compact.
"""

CHORDS = {
    "C": ("c4", "e4", "g4"), "Cm": ("c4", "d#4", "g4"),
    "D": ("d4", "f#4", "a4"), "Dm": ("d4", "f4", "a4"),
    "E": ("e4", "g#4", "b4"), "Em": ("e4", "g4", "b4"),
    "F": ("f4", "a4", "c5"), "Fm": ("f4", "g#4", "c5"),
    "G": ("g4", "b4", "d5"), "Gm": ("g4", "a#4", "d5"),
    "A": ("a3", "c#4", "e4"), "Am": ("a3", "c4", "e4"),
    "B": ("b3", "d#4", "f#4"), "Bb": ("a#3", "d4", "f4"),
    "Ab": ("g#3", "c4", "d#4"),
}


def _n(note, length, shift=0):
    name = note[:-1].replace("#", "+")
    octave = int(note[-1]) + shift
    return "o%d%s%s" % (octave, name, length)


def arp(chords, pattern="01210121", length=8, shift=0):
    """Broken-chord arpeggio: pattern digits index chord tones (3 = root+8va)."""
    out = []
    for ch in chords:
        tones = CHORDS[ch]
        for p in pattern:
            idx = int(p)
            if idx == 3:
                out.append(_n(tones[0], length, shift + 1))
            else:
                out.append(_n(tones[idx], length, shift))
        out.append("|")
    return " ".join(out)


def bass(chords, style="oct", octave=3):
    """Triangle bass line from chord roots (triangle sounds an octave low)."""
    out = []
    for ch in chords:
        root = CHORDS[ch][0][:-1]
        fifth = CHORDS[ch][2][:-1]
        r = root.replace("#", "+")
        f = fifth.replace("#", "+")
        if style == "oct":
            out.append(("o%d%s8 o%d%s8 " % (octave, r, octave + 1, r)) * 4)
        elif style == "pump":
            out.append(("o%d%s8 " % (octave, r)) * 8)
        elif style == "gallop":
            out.append(("o%d%s8 o%d%s16 o%d%s16 " % (octave, r, octave, r, octave + 1, r)) * 4)
        elif style == "half":
            fo = octave + (1 if f < r else 0)
            out.append("o%d%s2 o%d%s2 " % (octave, r, fo, f))
        elif style == "whole":
            out.append("o%d%s1 " % (octave, r))
        out.append("|")
    return " ".join(out)


def drums(pattern, bars):
    return " ".join([pattern] * bars)


def song(tempo, lead, harmony, tri, noise, loop=True):
    return {"tempo": tempo, "loop": loop, "ch": [lead, harmony, tri, noise]}


# ---------------------------------------------------------------------------
# TITLE THEME - heroic, A minor
# ---------------------------------------------------------------------------
_title_chords = ["Am", "F", "C", "G", "Am", "F", "G", "E",
                 "Am", "F", "C", "G", "Am", "F", "G", "Am"]
TITLE = song(
    138,
    "v11 @1 y6 q7 "
    "o5e4a4>c4.<b8 | o5a4g8f8e4c4 | o5e4.g8g4e4 | o5d2r4d8e8 | "
    "o5e4a4>c4e4 | o6d4c8<a8>c4<a4 | o5b4>d4<b4g4 | o5g+2e2 | "
    "o5a4>c8<b8a4e4 | o5f4a4>c4<a4 | o5g4.e8g4>c4 | o5b2>d4<b4 | "
    "o5a4>c4e4a4 | o6f4e8d8c4<a4 | o5b4>c4d4<b4 | o5a1 ",
    "v5 @0 y3 q6 " + arp(_title_chords, "01230123", 8),
    "q7 " + bass(_title_chords, "oct", 3),
    "v10 " + drums("k8h8s8h8k8k8s8h8", 15) + " k8h8s8h8s16s16s16s16x4",
)

# ---------------------------------------------------------------------------
# STORY THEME - slow, mysterious, D minor
# ---------------------------------------------------------------------------
_story_chords = ["Dm", "Bb", "F", "C", "Dm", "Bb", "Gm", "A"]
STORY = song(
    76,
    "v9 @0 y12 s5 q8 "
    "o5a2.g4 | o5f2d2 | o5c2.f4 | o5e2g2 | o5a2>d2 | o5a+2.a4 | o5g2a+2 | o5a1 ",
    "v4 @2 y4 q5 " + arp(_story_chords, "01210121", 8),
    "q8 " + bass(_story_chords, "whole", 3),
    "v6 " + drums("r4h4r4h4", 7) + " r4h4r4j4",
)

# ---------------------------------------------------------------------------
# LEVEL THEME A - driving, E minor (Sectors 1 & 4)
# ---------------------------------------------------------------------------
_lv1_chords = ["Em", "C", "G", "D", "Em", "C", "D", "B",
               "Am", "Em", "C", "D", "Am", "Em", "C", "D"]
LEVEL1 = song(
    150,
    "v11 @1 y5 q7 "
    "o5b4e8g8b4>e4 | o6d8c8<b8g8e4g4 | o5d4g8b8>d4g4 | o6f+8e8d8<a8f+2 | "
    "o5b4e8g8b4>e8g8 | o6a8g8e8c8<g4>c4 | o6d4c8<a8f+4a4 | o5b2d+4f+4 | "
    "o5a4>c8e8a4e4 | o6g8f+8e8d8e2 | o6c4e4g4e4 | o6f+4.e8d2 | "
    "o5a8>c8e8a8g8e8c8e8 | o5b4>e4g4b4 | o6a4g8e8c4e4 | o6d2f+2 ",
    "v5 @2 y3 q5 " + arp(_lv1_chords, "02120212", 8),
    "q6 " + bass(_lv1_chords, "oct", 3),
    "v10 " + drums("k8h8s8h8k8h8s8k8", 7) + " k8h8s8h8s8s8s16s16s8 "
    + drums("k8h8s8h8k8h8s8k8", 7) + " k8k8s8h8s16s16s16s16x4",
)

# ---------------------------------------------------------------------------
# LEVEL THEME B - urgent, D minor (Sectors 2 & 5)
# ---------------------------------------------------------------------------
_lv2_chords = ["Dm", "Bb", "C", "A", "Dm", "Bb", "C", "Dm",
               "Gm", "Dm", "Bb", "C", "Gm", "Dm", "Bb", "A"]
LEVEL2 = song(
    158,
    "v11 @2 y5 q6 "
    "o5d8f8a8>d8c8<a8f8a8 | o5a+4f8d8f4a+4 | o6c8<g8e8g8>c4e4 | o6c+4<a8e8a2 | "
    "o6d4f8e8d4<a4 | o5a+4>d8f8d4<a+4 | o5g4>c8e8g4e4 | o6d2.r4 | "
    "o5g4a+8>d8g4f4 | o6f8e8d8c8d2 | o5a+4>d4f4a+4 | o6g4.e8c2 | "
    "o5g8a+8>d8g8f8d8<a+8>d8 | o5a4>d4f4a4 | o6a+4a8f8d4f4 | o6e2c+2 ",
    "v5 @1 y3 q5 " + arp(_lv2_chords, "01230123", 8, -1),
    "q6 " + bass(_lv2_chords, "gallop", 3),
    "v10 " + drums("k8h8s8k8h8k8s8h8", 7) + " k8h8s8k8s16s16s16s16s8s8 "
    + drums("k8h8s8k8h8k8s8h8", 7) + " k8h8s8k8s16s16s16s16x4",
)

# ---------------------------------------------------------------------------
# LEVEL THEME C - dark, C minor (Sectors 3 & 6)
# ---------------------------------------------------------------------------
_lv3_chords = ["Cm", "Ab", "Bb", "G", "Cm", "Ab", "Bb", "G",
               "Fm", "Cm", "Ab", "Bb", "Fm", "Cm", "Ab", "G"]
LEVEL3 = song(
    166,
    "v11 @1 y4 q7 "
    "o5c8d+8g8c8>c8<a+8g8d+8 | o5g+4d+8c8d+4g+4 | o5a+4f8d8f4a+4 | o5b4g8d8g2 | "
    "o6c4d+8c8<g4>c4 | o6d+4c8<g+8>c4d+4 | o6f4d8<a+8>d4f4 | o6d2<b2 | "
    "o5f4g+8>c8f4d+4 | o6d+8d8c8<g8>c2 | o5g+4>c4d+4g+4 | o6f4.d8<a+2 | "
    "o5f8g+8>c8f8d+8c8<g+8>c8 | o5g4>c4d+4g4 | o6g+4f8d+8c4d+4 | o5b2>d2 ",
    "v5 @2 y2 q4 " + arp(_lv3_chords, "01210121", 8),
    "q6 " + bass(_lv3_chords, "pump", 3),
    "v11 " + drums("k8h8s8h8k8k8s8h8", 7) + " k8s8s8s8s16s16s16s16s8s8 "
    + drums("k8h8s8h8k8k8s8h8", 7) + " k8s8k8s8s16s16s16s16x4",
)

# ---------------------------------------------------------------------------
# BOSS THEME - menacing, E minor with tritones
# ---------------------------------------------------------------------------
_boss_chords = ["Em", "F", "Em", "F", "C", "B", "Em", "B",
                "Am", "Em", "F", "B", "Am", "Em", "F", "B"]
BOSS = song(
    174,
    "v12 @2 y4 q6 "
    "o5e8e8g8e8a+8e8a8g8 | o5f8f8a8f8b8a8g8f8 | o5e8e8g8b8>e4d+4 | o6f4e8c8<a4f4 | "
    "o5g4>c8e8g4e4 | o5f+4b8>d+8f+4d+4 | o5e8g8b8>e8g8e8<b8g8 | o5a+4b4>d+2 | "
    "o5a8>c8e8a8g+8e8c8<a8 | o5b8g8e8g8b4>e4 | o6f8e8d8c8<a4f4 | o5f+4a8b8>d+4f+4 | "
    "o6a4g+8a8e4c4 | o5b4a8g8e2 | o5f4a4>c4f4 | o5b2>d+2 ",
    "v6 @1 y2 q4 " + arp(_boss_chords, "0202020202020202", 16, -1),
    "q5 " + bass(_boss_chords, "pump", 3),
    "v12 " + drums("k8h8s8h8k8k8s8s16s16", 15) + " k8s8k8s8s16s16s16s16x4",
)

# ---------------------------------------------------------------------------
# VICTORY JINGLE (plays once)
# ---------------------------------------------------------------------------
VICTORY = song(
    150,
    "v12 @1 y6 q7 o5g8g8g8>c4<g8>c8e8 | o6d8c8d8g2r8 | o6c2.r4",
    "v7 @2 y6 q7 o5e8e8e8g4e8g8>c8 | o5b8a8b8>d2r8 | o5g2.r4",
    "q7 o4c4c4c4c4 | o3g4g4g4g4 | o4c2.r4",
    "v10 k8h8s8h8k8h8s8h8 | k8h8s8h8k8h8s8s8 | x2.r4",
    loop=False,
)

# ---------------------------------------------------------------------------
# GAME OVER (plays once)
# ---------------------------------------------------------------------------
GAMEOVER = song(
    88,
    "v10 @2 y10 s4 q7 o5e4d4c4<b4 | o4a4g+4a2 | o4f4e4d4c4 | o3b2>e2 | o4a1",
    "v5 @0 y8 q7 o4c2<b2 | o4c2e2 | o3a2a2 | o3g+2b2 | o3e1",
    "q8 o3a1 | o3f1 | o3d1 | o3e1 | o3a1",
    "v6 r1 r1 r1 r2 h4h4 x1",
    loop=False,
)

# ---------------------------------------------------------------------------
# HIGH SCORE ENTRY - cheerful, C major
# ---------------------------------------------------------------------------
_hs_chords = ["C", "Am", "F", "G", "C", "Am", "F", "G"]
HIGHSCORE = song(
    120,
    "v10 @1 y6 q7 "
    "o5e4g4>c4<g4 | o5a4>c4e4c4 | o5f4a4>c4<a8f8 | o5g4b4>d2 | "
    "o6e4d8c8<g4e4 | o5a4g8e8c4e4 | o5f4a8>c8d4c4 | o5b2>d2 ",
    "v5 @2 y3 q5 " + arp(_hs_chords, "01210121", 8, -1),
    "q6 " + bass(_hs_chords, "oct", 3),
    "v8 " + drums("k8h8s8h8k8h8s8h8", 7) + " k8h8s8h8s8s8s8s8",
)

SONGS = {
    "title": TITLE,
    "story": STORY,
    "level1": LEVEL1,
    "level2": LEVEL2,
    "level3": LEVEL3,
    "boss": BOSS,
    "victory": VICTORY,
    "gameover": GAMEOVER,
    "highscore": HIGHSCORE,
}
