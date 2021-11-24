import yaml
import os
import re

translation_file = 'en.yml'
with open(translation_file,'r') as f:
    translation = yaml.safe_load(f)
def getkeys(pre,d):
    keys = []
    for k in d:
        new_pre = k if pre == "" else pre + '.' + k
        if type(d[k])==dict:
            keys += getkeys(new_pre, d[k])
        else:
            keys.append(new_pre)
    return keys
translation_keys = getkeys('', translation)

btb_dir = '../btb_manager_telegram'
print(f'Missing keys in {translation_file} from :')
for filename in os.listdir(btb_dir):
    print(f'\t{filename} :')
    full_path = os.path.join(btb_dir, filename)
    if not os.path.isfile(full_path):
        continue
    with open(full_path, 'r') as f:
        content = f.read()

    finds = [i[2] for i in re.findall(
        "(i18n_format|i18n.t)\((\'|\")(([a-z]|_|\n|\.)*)(\'|\")\)",
        content
    )]

    for elt in finds:
        if elt not in translation_keys:
            print(f'\t\t{elt}')
