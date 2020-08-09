import argparse
import os
import string
import unicodedata

parser = argparse.ArgumentParser(description='Sanitize directory names in target directory')
parser.add_argument('-i', '--input', required=True, help='Target directory')
args = parser.parse_args()

VALID_CHAR = '-_.()' + string.ascii_letters + string.digits
REPLACEMENT_CHAR = '_'


def get_dir(src_path):
    temp_list = []
    base_path = os.path.join(src_path)

    l = os.listdir(base_path)
    for i in l:
        if os.path.isdir(os.path.join(base_path, i)):
            temp_list.append([base_path, i, i])

    return temp_list


def sanitize_dir_name(dir_list):
    temp_list = []

    for dir in dir_list:
        # remove trailing leading space
        dir[2] = dir[2].strip()

        # replace accented characters with its nearest equivalent
        dir[2] = unicodedata.normalize('NFKD', dir[2]).encode('ascii', 'ignore').decode('utf8')

        # replace spaces and invalid characters with underscores
        # CRED: https://github.com/artefactual/archivematica/blob/b6dcfb07a6be5957a5085efd1fecd8462fdc3a91/src/MCPClient
        # /lib/clientScripts/sanitizeNames.py
        w = ''
        for c in dir[2]:
            if c in VALID_CHAR:
                w += c
            else:
                w += REPLACEMENT_CHAR
        dir[2] = w

        temp_list.append(dir)

    return temp_list


def rename_dir_name(dir_list):
    for dir in dir_list:
        if not dir[0] == dir[2] and not os.path.exists(os.path.join(dir[0], dir[2])):
            os.rename(os.path.join(dir[0], dir[1]), os.path.join(dir[0], dir[2]))
        else:
            print('ERROR: Same directory name exists', dir[1], 'to', dir[2])


def main():
    dir_list = get_dir(args.input)
    sanitized_list = sanitize_dir_name(dir_list)
    rename_dir_name(sanitized_list)


if __name__ == '__main__':
    main()
