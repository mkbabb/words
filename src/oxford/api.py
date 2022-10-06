import argparse
import json
import os
import time
import urllib.request
from typing import *

from src.utils import file_components, sanitize_string

API_ID = os.environ.get("OXFORD_API_ID")
API_KEY = os.environ.get("OXFORD_API_KEY")

LANG = "en-us"


def get_definition(word: str) -> Optional[dict]:
    url = f"https://od-api.oxforddictionaries.com:443/api/v2/entries/{LANG}/{word}"

    data = None
    try:
        req = urllib.request.Request(
            url,
            headers={"app_id": API_ID,
                     "app_key": API_KEY})

        data = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
    except Exception as e:
        print(e)
        print(f"**Could not get definition for word: {word}")

    return data


def parse_oxford_json(word_list: list) -> Dict[str, Any]:
    out_dict = {}

    for word_obj in word_list:
        results = word_obj["results"][0]
        name = str(results["id"])

        lexicalEntries = results["lexicalEntries"][0]
        lexicalCategory = lexicalEntries["lexicalCategory"]

        entries = lexicalEntries["entries"][0]

        senses = entries["senses"][0]
        definitions = senses.get("definitions", [])
        examples = senses.get("examples")
        synonyms = senses.get("synonyms")

        s = f"{str(name).capitalize()} ({lexicalCategory['id']}) {';'.join(definitions)}"
        out_dict[name] = s

    return out_dict


def main():
    parser = argparse.ArgumentParser(
        description="Queries the Oxford Dictionary API for either a list of words or a single word.")
    parser.add_argument("-i", "--input",
                        help="Input file path")
    args = parser.parse_args()

    definitions: List[dict] = []

    filepath = args.input
    dirpath, filename, ext = file_components(filepath)

    out_path = os.path.join(dirpath, filename + "_OUT")
    out_json_path = out_path + ".json"
    out_txt_path = out_path + ".txt"

    out_exists = os.path.exists(out_json_path)

    if (not os.path.exists(out_json_path)):
        with open(filepath, "r") as file:
            for line in file.readlines():
                word = line.strip().lower()
                definition = get_definition(word)

                if (definition != None):
                    definitions.append(definition)
                time.sleep(2)
        json.dump(definitions, open(out_json_path, "w"))
    else:
        definitions = json.load(open(out_json_path, "r"))

    with open(out_txt_path, "w") as out_file:
        for n, word in enumerate(filepath.readlines()):
            word = str(word).strip().lower()

            if (word in definitions):
                word = definitions[word]
            else:
                word = f"{word.capitalize()}"

            word = f"{word}\n"

            out_file.writelines(word)


if __name__ == "__main__":
    main()
