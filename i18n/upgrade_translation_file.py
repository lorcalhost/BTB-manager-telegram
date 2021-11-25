import os
import re
import shutil
import subprocess

import click
import yaml


@click.command()
@click.option("-c", "--commit")
@click.argument("file_to_upgrade")
def main(commit, file_to_upgrade):
    file_upgraded = ".tmp".join(os.path.splitext(file_to_upgrade))
    file_to_upgrade_final_name = ".old".join(os.path.splitext(file_to_upgrade))
    ref_file = "en.yml"
    ref_file_backup = ".bak".join(os.path.splitext(ref_file))
    old_ref_file = ".old".join(os.path.splitext(ref_file))

    if os.path.isfile(file_to_upgrade_final_name):
        answer = input(
            f"The file {file_to_upgrade_final_name} will be overwritten. Confirm? [y/N] "
        )
        if not answer.lower().replace(" ", "") in ("y", "yes"):
            print("Exiting...")
            return

    shutil.copyfile(ref_file, ref_file_backup)
    subprocess.run(["git", "checkout", "-q", commit, ref_file])
    shutil.copyfile(ref_file, old_ref_file)
    os.replace(ref_file_backup, ref_file)

    def extract_translation_flat_keys(filename):
        # Return a 1 dimensionnal dictionnary with keys in format a.b.c
        with open(filename, "r") as f:
            content = yaml.safe_load(f)

        def gettrans(pre, d):
            keys = {}
            for k in d:
                new_pre = k if pre == "" else pre + "." + k
                if type(d[k]) == dict:
                    keys.update(gettrans(new_pre, d[k]))
                else:
                    keys[new_pre] = d[k]
            return keys

        return gettrans("", content)

    old_ref = extract_translation_flat_keys(old_ref_file)
    new_ref = extract_translation_flat_keys(ref_file)

    mapping = {}
    for key_old, val_old in old_ref.items():
        found = False
        for key_new, val_new in new_ref.items():
            if val_old == val_new:
                mapping[key_old] = key_new
                found = True
                break
        if not found:
            print(f"Can't find mapping from {key_old}")

    to_upgrade = extract_translation(file_to_upgrade)
    upgraded = {}
    for key, val in to_upgrade.items():
        if not key in mapping:
            print(f"Can't upgrade key {key} from file")
            continue
        upgraded[mapping[key]] = val

    with open(ref_file, "r") as f:
        ref_content = f.readlines()

    path = []
    new_file = ""
    for raw_line in ref_content:
        line = raw_line.replace("/n", "")
        line = line.replace("  ", " ")
        search_for_key = re.findall("^ *(([a-z]|_|-|\.)*):(.*)", line)
        if len(search_for_key) == 0:
            new_file += "\n"
            continue
        key = search_for_key[0][0]
        val = search_for_key[0][2]
        level = 0
        for c in line:
            if c == " ":
                level += 1
            else:
                break
        if level > len(path):
            print("Badly formatted file. Halting.")
            break

        if level == len(path):
            path.append(key)
        else:
            path = path[:level]
            path.append(key)

        new_val = ""

        if val.replace(" ", "") != "":

            flat_key = ".".join(path)
            if not flat_key in upgraded:
                print(f"Cannot find key {flat_key} in update")
                continue

            new_val = f' "{upgraded[flat_key]}"'

        new_file += "  " * level + key + ":" + new_val + "\n"

    with open(file_upgraded, "w") as f:
        f.write(new_file)

    shutil.copyfile(file_to_upgrade, file_to_upgrade_final_name)
    shutil.copyfile(file_upgraded, file_to_upgrade)

    os.remove(file_upgraded)
    os.remove(old_ref_file)


if __name__ == "__main__":
    main()
