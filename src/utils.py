import pathlib
import re

RE_WHITESPACE = re.compile(r"\s+")


def sanitize_string(s: str, white_space: str = "") -> str:
    if white_space != "":
        s = re.sub(RE_WHITESPACE, white_space, s)
    return s.lower().strip()


def parse_word_list(word_list_path: pathlib.Path) -> set[str]:
    words: dict[str, int] = {}
    word_re = re.compile(r".*\. ?(\w+)")

    with open(word_list_path) as word_list_file:
        for line in word_list_file.readlines():
            if (match := re.match(word_re, line)) is not None:
                word = match.group(1).strip().lower()
                words[word] = 0

    return set(words.keys())
