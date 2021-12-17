import os
import re

import click
import yaml


@click.command()
@click.argument("translation_file")
def main(translation_file):
    """
    Check the translation file you want by
    reading all the translation keys used
    in the program and checking their exitence
    in the given file
    """

    print("Running...\r", end="")

    with open(translation_file, "r") as f:
        translation = yaml.safe_load(f)

    def getkeys(pre, d):
        keys = []
        for k in d:
            new_pre = str(k) if pre == "" else pre + "." + str(k)
            if type(d[k]) == dict:
                keys += getkeys(new_pre, d[k])
            else:
                keys.append(new_pre)
        return keys

    translation_keys = getkeys("", translation)

    btb_dir = "../btb_manager_telegram"
    main_text_output = ""
    for filename in os.listdir(btb_dir):
        full_path = os.path.join(btb_dir, filename)
        if not os.path.isfile(full_path):
            continue
        with open(full_path, "r") as f:
            content = f.read()

        finds = [
            i[4]
            for i in re.findall(
                "(i18n_format|i18n.t)\(((\n| )*)('|\")(([a-z]|[0-9]|_|\n|\.)*)('|\")",
                content,
            )
        ]

        text_output = ""
        for elt in finds:
            if elt not in translation_keys:
                text_output += f"\t\t{elt}\n"

        if text_output != "":
            main_text_output += f"\t{filename} :\n{text_output}\n"

    if main_text_output != "":
        print(f"Missing keys in '{translation_file}' from :\n{main_text_output}")
    else:
        print("No missing keys!")


if __name__ == "__main__":
    main()
