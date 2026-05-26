import sys
import os
sys.path.append(r"c:\Users\ange-\PycharmProjects\Roneat_Studio")

from ui.views.score_editor import ScoreEditor
from core.rendering.translation import NotationTranslator

# We will test _numeric_to_mode and _get_numeric_score_text directly using class/helper methods
print("--- TESTING NOTATION TRANSLATOR DIRECTLY ---")
# Bar 9 -> La2 in Syllabic, A2 in Letters
# Bar 8 -> Sol2 in Syllabic, G2 in Letters
assert NotationTranslator.index_to_string(9, "Syllabic") == "La2"
assert NotationTranslator.index_to_string(8, "Syllabic") == "Sol2"
assert NotationTranslator.index_to_string(9, "Letters") == "A2"
assert NotationTranslator.index_to_string(8, "Letters") == "G2"

assert NotationTranslator.string_to_index("La2", "Syllabic") == 9
assert NotationTranslator.string_to_index("Sol2", "Syllabic") == 8
assert NotationTranslator.string_to_index("A2", "Letters") == 9
assert NotationTranslator.string_to_index("G2", "Letters") == 8

# Test _numeric_to_mode
print("--- TESTING _numeric_to_mode ---")
numeric_text = "9 (9)8 9#3 (9)8#3 - _ /"
syllabic_expected = "La2 (La2)Sol2 La2#3 (La2)Sol2#3 - _ /"
letters_expected = "A2 (A2)G2 A2#3 (A2)G2#3 - _ /"

syllabic_out = ScoreEditor._numeric_to_mode(numeric_text, "Syllabic")
letters_out = ScoreEditor._numeric_to_mode(numeric_text, "Letters")
numeric_out = ScoreEditor._numeric_to_mode(numeric_text, "Numeric")

print("Numeric Input:   ", numeric_text)
print("Syllabic Output: ", syllabic_out)
print("Letters Output:  ", letters_out)

assert syllabic_out == syllabic_expected, f"Syllabic conversion mismatch: {syllabic_out} != {syllabic_expected}"
assert letters_out == letters_expected, f"Letters conversion mismatch: {letters_out} != {letters_expected}"
assert numeric_out == numeric_text, f"Numeric pass-through mismatch: {numeric_out} != {numeric_text}"

print("\n=== NOTATION TRANSITIONS VERIFICATION PASSED ===")
