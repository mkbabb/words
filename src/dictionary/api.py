import copy
import json
import pathlib
import time

import requests

from ..utils import parse_word_list

API_URL = "https://thor-graphql.dictionary.com/graphql"

CONFIG_PATH = pathlib.Path("auth/config.json")
CONFIG = json.loads(CONFIG_PATH.read_bytes())

DICTIONARY_CONFIG = CONFIG["dictionary"]

AUTHORIZATION = DICTIONARY_CONFIG["authorization"]


POST = {
    "headers": {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:104.0) Gecko/20100101 Firefox/104.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "content-type": "application/json",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "authorization": AUTHORIZATION,
    },
    "method": "POST",
    "url": API_URL,
}


def upsert_word(
    word: str,
    word_list_short_id: str,
):
    body = {
        "operationName": "upsertWord",
        "variables": {
            "slug": word,
            "displayForm": word,
            "wordListShortId": word_list_short_id,
            "productSource": "dcom",
        },
        "query": "mutation upsertWord($wordListShortId: ID!, $slug: String!, $displayForm: String!, $definition: String, $definitionPath: String, $pos: String, $pronunciationAudio: String, $productSource: String) {\n  upsertWord(\n    wordListShortId: $wordListShortId\n    slug: $slug\n    definition: $definition\n    definitionPath: $definitionPath\n    pronunciationAudio: $pronunciationAudio\n    displayForm: $displayForm\n    pos: $pos\n    productSource: $productSource\n  ) {\n    wordListId\n    slug\n    pos\n    definition\n    definitionPath\n    pronunciationAudio\n    __typename\n  }\n}\n",
    }

    t_post = copy.deepcopy(POST)
    t_post["json"] = body

    return t_post


word_list_short_id = "jtuXvoDR1Sg"

word_list_path = pathlib.Path("data/words.txt")
words = parse_word_list(word_list_path)

for word in words:
    request = upsert_word(word=word, word_list_short_id=word_list_short_id)

    r = requests.request(**request)
    time.sleep(0.1)
    print(r)
