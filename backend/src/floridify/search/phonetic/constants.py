"""ICU transliteration rules for cross-linguistic phonetic normalization.

These rules are compiled ONCE at module load time into ICU transliterator
automata. Per-query cost is a single C++ string pass (sub-microsecond).

The rules collapse sound equivalences across major European languages so
that jellyfish Metaphone produces identical codes for words that "sound
the same" regardless of source orthography.

Sources:
- Unicode CLDR transliteration tables (via PyICU built-in transforms)
- Cross-linguistic phonological correspondences from standard references
"""

import icu

# ─── Stage 1: Script normalization (CLDR built-in) ────────────────────
# Converts any script to Latin, then strips diacritics to ASCII.
# This is the CLDR-standard pipeline used by ICU worldwide.
SCRIPT_NORMALIZER = icu.Transliterator.createInstance(
    "Any-Latin; Latin-ASCII; Lower",
    icu.UTransDirection.FORWARD,
)

# ─── Stage 2: Cross-linguistic phonetic normalization ─────────────────
# ICU rule syntax reference: https://unicode-org.github.io/icu/userguide/transforms/general/rules.html
#
# These rules are applied AFTER script normalization (input is lowercase ASCII).
# They collapse sound equivalences that Metaphone doesn't handle because
# Metaphone is English-phonology-only.
#
# Rule ordering: ICU processes rules in order; first match wins.
# Context syntax: { = before, } = after (lookahead/lookbehind)

_PHONETIC_RULES = r"""
# ═══ French nasal vowels ═══
# en/an/on/in/un before consonant or word-end → unified 'an'
# This makes "en coulisses" and "on coulisses" produce the same code.
e i n } [bcdfghjklmnpqrstvwxyz] → a n ;
a i n } [bcdfghjklmnpqrstvwxyz] → a n ;
o i n } [bcdfghjklmnpqrstvwxyz] → a n ;
e n } [bcdfghjklmnpqrstvwxyz] → a n ;
a n } [bcdfghjklmnpqrstvwxyz] → a n ;
o n } [bcdfghjklmnpqrstvwxyz] → a n ;
i n } [bcdfghjklmnpqrstvwxyz] → a n ;
u n } [bcdfghjklmnpqrstvwxyz] → a n ;

# Standalone nasal function words (French prepositions/articles)
# \b not available in ICU rules; use space context
' ' e n ' ' → ' ' a n ' ' ;
' ' o n ' ' → ' ' a n ' ' ;
' ' u n ' ' → ' ' a n ' ' ;

# Word-initial nasal before space (e.g., "en coulisses" at start of string)
^ e n ' ' → a n ' ' ;
^ o n ' ' → a n ' ' ;
^ u n ' ' → a n ' ' ;

# Word-final nasal
e n $ → a n ;
o n $ → a n ;
i n $ → a n ;
u n $ → a n ;

# ═══ French vowel digraphs ═══
e a u x → o ;
e a u → o ;
a u x → o ;
o u i → w ee ;
o i s → w a ;
o i → w a ;
o u → oo ;
e u → oy ;

# ═══ French consonant patterns ═══
t i o n → s i o n ;
g n e → n y e ;
g n → n y ;
i l l e → ee y ;
q u → k ;

# ═══ German consonant clusters ═══
t s c h → ch ;
s c h → sh ;
t c h → ch ;

# ═══ German vowel patterns ═══
e i e → a y e ;
e i → a y ;
i e → ee ;

# ═══ Cross-linguistic consonant equivalences ═══
g h t → t ;
p h → f ;
c k → k ;
w h → w ;

# ═══ Double consonant simplification ═══
# (Metaphone handles some of these, but normalizing here
# improves consistency of the pre-Metaphone representation)
s s → s ;
l l → l ;
f f → f ;
t t → t ;
p p → p ;
n n → n ;
m m → m ;
r r → r ;
d d → d ;
b b → b ;
g g → g ;
c c → k ;
z z → z ;
"""

PHONETIC_NORMALIZER = icu.Transliterator.createFromRules(
    "floridify-phonetic",
    _PHONETIC_RULES,
    icu.UTransDirection.FORWARD,
)

# ─── Combined chain ──────────────────────────────────────────────────
# Script normalization → phonetic normalization in one pass.
# ICU chains transliterators via CompoundTransliterator.
FULL_PHONETIC_CHAIN = icu.Transliterator.createInstance(
    "Any-Latin; Latin-ASCII; Lower",
    icu.UTransDirection.FORWARD,
)
# We apply PHONETIC_NORMALIZER as a second step (can't easily chain
# custom rules with built-in transforms in one createInstance call).
# The PhoneticEncoder.normalize() method applies both in sequence.


__all__ = [
    "SCRIPT_NORMALIZER",
    "PHONETIC_NORMALIZER",
    "FULL_PHONETIC_CHAIN",
]
