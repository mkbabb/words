import pathlib
import re
from typing import *

RE_WHITESPACE = re.compile("\s+")


def sanitize_string(s: str, white_space: str = "") -> str:
    if white_space != "":
        s = re.sub(RE_WHITESPACE, white_space)
    return s.lower().strip()


def parse_word_list(word_list_path: pathlib.Path) -> set:
    words = {}
    word_re = re.compile(".*\. ?(\w+)")

    with open(word_list_path, "r") as word_list_file:
        for line in word_list_file.readlines():
            if (match := re.match(word_re, line)) is not None:
                word = match.group(1).strip().lower()
                words[word] = 0

    return words.keys()
