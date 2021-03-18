import argparse
import csv
import logging
import os
import sys
import time

import pymsteams
from PIL import Image, ImageSequence, UnidentifiedImageError

parser = argparse.ArgumentParser(description='Convert tif to jp2 and add watermark')
parser.add_argument('path', help='Path to directory or file')
parser.add_argument('-t', '--type', choices=['pub', 'arch', 'any', 'csv'], required=True, help='Type')
args = parser.parse_args()


def validating_inputs(src_path, src_type):
    dir_target_paths = []
    file_target_paths = []

    # Validating input
    if src_type == 'pub':
        if not os.path.exists(os.path.join(src_path, 'PUB')):
            logging.error('Directory not found, , %s', os.path.join(src_path, 'PUB'))
            sys.exit()
        else:
            dir_target_paths.append(os.path.join(src_path, 'PUB'))
    elif src_type == 'arch':
        if not os.path.exists(os.path.join(src_path, 'ARCH')):
            logging.error('Directory not found, , %s', os.path.join(src_path, 'ARCH'))
            sys.exit()
        else:
            dir_target_paths.append(os.path.join(src_path, 'ARCH'))
    elif src_type == 'any':
        if not os.path.exists(os.path.join(src_path)):
            logging.error('Directory not found, , %s', os.path.join(src_path))
            sys.exit()
        else:
            dir_target_paths.append(os.path.join(src_path))
    elif src_type == 'csv':
        if not os.path.exists(os.path.join(src_path)):
            logging.error('File not found, , %s', src_path)
            sys.exit()
        else:
            with open(os.path.join(src_path), mode='r') as csv_file:
                csv_reader = csv.DictReader(csv_file)
                csv_reader.fieldnames = [fieldname.strip().lower() for fieldname in csv_reader.fieldnames]
                for row in csv_reader:
                    if os.path.exists(os.path.join(row['path'])):
                        if os.path.isdir(os.path.join(row['path'])):
                            dir_target_paths.append(row['path'])
                        else:
                            file_target_paths.append(row['path'])
                    else:
                        logging.error('Path not found, , %s', row['path'])
            logging.info('Found %s folder(s) and %s files(s) from %s', len(dir_target_paths), len(file_target_paths),
                         src_path)
    else:
        sys.exit()

    # Validating watermark
    if not os.path.exists(os.path.join('WM_20200311.png')):
        logging.error('Watermark not found, , %s', os.path.join('WM_20200311.png'))
        sys.exit()
    else:
        try:
            wm = Image.open('WM_20200311.png')
            wm.close()
        except UnidentifiedImageError:
            logging.error('Watermark cannot be opened, , %s', os.path.join(src_path))
            sys.exit()

    return dir_target_paths, file_target_paths


def parsing_targets(dir_target_paths, file_target_paths):
    targets = []

    # Parsing tif file folder paths:
    for target_path in dir_target_paths:
        for root, dirs, files in os.walk(os.path.join(target_path)):
            for file in files:
                if not file.startswith('._') and file.lower().endswith(('.tiff', '.tif')):
                    target = {
                        'tif_name': file,
                        'tif_path': os.path.join(root, file),
                        'jp2_path': os.path.join(root, os.path.splitext(file)[0].replace('_pub', '') + '.jp2')
                        # 'tif_width': '',
                        # 'tif_height': '',
                        # 'tif_mode': '',
                        # 'tif_dpi': '',
                        # 'tif_scene_index': '',
                        # 'jp2_resize': '',
                        # 'watermark_resize': '',
                        # 'watermark_position': ''
                    }
                    targets.append(target)

    # Parsing tif file file paths:
    for target_path in file_target_paths:
        root, file = os.path.split(os.path.join(target_path))
        if not file.startswith('._') and file.lower().endswith(('.tiff', '.tif')):
            target = {
                'tif_name': file,
                'tif_path': os.path.join(root, file),
                'jp2_path': os.path.join(root, os.path.splitext(file)[0].replace('_pub', '') + '.jp2')
                # 'tif_width': '',
                # 'tif_height': '',
                # 'tif_mode': '',
                # 'tif_dpi': '',
                # 'tif_scene_index': '',
                # 'jp2_resize': '',
                # 'watermark_resize': '',
                # 'watermark_position': ''
            }
            targets.append(target)

    # Removing duplicate tif file paths
    # https://stackoverflow.com/questions/9427163/remove-duplicate-dict-in-list-in-python
    targets = [dict(t) for t in {tuple(d.items()) for d in targets}]

    logging.info('Found %s tif file(s)', len(targets))
    print()

    return targets


def characterize_and_convert_targets(targets):
    tif_total = len(targets)
    tif_counter = 1
    jp2_counter = 0

    wm = Image.open('WM_20200311.png')

    for target in targets:
        try:
            # https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.open
            im = Image.open(target['tif_path'])
        except FileNotFoundError:
            logging.error('File not found, , %s', target['tif_path'])
            pass
        except UnidentifiedImageError:
            logging.error('File cannot be opened, , %s', target['tif_path'])
            pass
        except:
            logging.error('Unknown error, , %s', target['tif_path'])
            pass
        else:
            target.update({
                'tif_width': float(im.width),
                'tif_height': float(im.height),
                'tif_dpi': check_tif_dpi(im, target),
                'tif_scene_index': check_tif_scene(im, target)
            })

            if target['tif_scene_index'] is not False:
                jp2_resize, watermark_resize, watermark_position = calculate_jp2_watermark(target)
                target.update({
                    'tif_mode_convert': check_tif_mode_convert(im, target),
                    'jp2_resize': jp2_resize,
                    'watermark_resize': watermark_resize,
                    'watermark_position': watermark_position
                })

                # Converting tif file
                logging.info('Converting %s (%s/%s)', target['tif_name'], tif_counter, tif_total)
                jp2_counter = convert_target(im, wm, target, jp2_counter)
                tif_counter = tif_counter + 1
                im.close()
    print()
    logging.info('Converted %s jp2 file(s) from %s tif file(s)', jp2_counter, tif_total)


def check_tif_dpi(im, target):
    try:
        dpi = im.info['dpi']
    except KeyError:
        logging.warning('No dpi information tif, , %s', target['tif_path'])
        return False
    else:
        if dpi[0] == dpi[1]:
            return float(dpi[0])
        else:
            logging.warning('Irregular dpi tif, %sx%s dpi, %s', dpi[0], dpi[1], target['tif_path'])
            return False


def check_tif_scene(im, target):
    # https://pillow.readthedocs.io/en/stable/reference/Image.html?highlight=n_frames#PIL.Image.Image.seek
    scene_count = im.n_frames
    if scene_count == 1:
        return 0
    elif scene_count > 1:
        scenes = {}
        scene_index = 0
        for scene in ImageSequence.Iterator(im):
            # https://pillow.readthedocs.io/en/stable/reference/ImageSequence.html#imagesequence-module
            scene_size = sum(list(scene.size))
            scenes.update({scene_index: scene_size})
            scene_index += 1
        logging.warning('Multiple scene tif, %s, %s', scene_count, target['tif_path'])
        return max(scenes, key=scenes.get)
    else:
        logging.error('Irregular scene tif, %s, %s', scene_count, target['tif_path'])
        return False


def check_tif_mode_convert(im, target):
    # https://pillow.readthedocs.io/en/latest/handbook/image-file-formats.html?highlight=jpeg%202000#jpeg-2000
    # https://pillow.readthedocs.io/en/stable/handbook/concepts.html#modes
    if im.mode not in ['L', 'LA', 'RGB', 'RGBA']:
        logging.warning('Unsupported mode tif, %s, %s', im.mode, target['tif_path'])
        return True
    else:
        return False


def calculate_jp2_watermark(target):
    # Calculating jp2_dpi
    if target['tif_dpi'] is not False:
        if target['tif_dpi'] >= 600.0:
            jp2_dpi = round((target['tif_dpi'] / 4))
        elif target['tif_dpi'] >= 150.0:
            jp2_dpi = 150.0
        else:
            jp2_dpi = target['tif_dpi']
            logging.warning('Low dpi tif, %s dpi, %s', target['tif_dpi'], target['tif_path'])
            logging.info('Generating %sx%s jp2 for %s', target['tif_width'], target['tif_height'], target['tif_name'])
        # Calculating jp2_resize
        jp2_w = round(target['tif_width'] * (jp2_dpi / target['tif_dpi']))
        jp2_h = round(target['tif_height'] * (jp2_dpi / target['tif_dpi']))
    else:
        logging.info('Generating %sx%s jp2 for %s', target['tif_width'], target['tif_height'], target['tif_name'])
        jp2_w = target['tif_width']
        jp2_h = target['tif_height']

    # Calculating watermark_resize and watermark_position
    # Flagging jp2 files with low resolution to exclude from resize
    if max(jp2_w, jp2_h) > 480.0:
        jp2_resize = (jp2_w, jp2_h)
        watermark_m = round(min(jp2_w, jp2_h))
        watermark_resize = (watermark_m, watermark_m)
        watermark_position = (round((jp2_w - watermark_m) // 2), round((jp2_h - watermark_m) // 2))
    else:
        jp2_resize = False
        watermark_m = round(min(target['tif_width'], target['tif_height']))
        watermark_resize = (watermark_m, watermark_m)
        watermark_position = (
            round((target['tif_width'] - watermark_m) // 2), round((target['tif_height'] - watermark_m) // 2)
        )
        logging.warning('Low resolution jp2, %sx%s, %s', jp2_w, jp2_h, target['tif_path'])
        logging.info('Generating %sx%s jp2 for %s', target['tif_width'], target['tif_height'], target['tif_name'])

    return jp2_resize, watermark_resize, watermark_position


def convert_target(tif, wm, target, jp2_counter):
    # Preparing watermark
    wm_resized = wm.resize(target['watermark_resize'], resample=1)

    # Preparing tif
    tif.seek(target['tif_scene_index'])
    jp2 = tif
    if target['tif_mode_convert'] is True:
        jp2 = tif.convert('RGB')
    if target['jp2_resize'] is not False:
        jp2 = jp2.resize(target['jp2_resize'], resample=1)
    jp2.paste(wm_resized, target['watermark_position'], wm_resized)

    # Saving jp2
    # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#jpeg-2000
    # https://wiki.harvard.edu/confluence/display/DigitalImaging/Encoding+JPEG2000+images+using+the+Aware+codec
    # https://www.dpconline.org/docs/miscellaneous/events/161-using-psnr-thresholds-to-modulate-the-degree-of-lossy-compression-in-jpeg2000-files-comstock/file
    try:
        jp2.save(
            target['jp2_path'], 'JPEG2000', tile_size=(1024, 1024), num_resolutions=7, codeblock_size=(64, 64),
            precinct_size=(16383, 16383), quality_mode='dB', quality_layers=[46], irreversible=True, progression='RPCL')
    except OSError:
        logging.error('File cannot be saved, , $%s', os.path.join(target['jp2_path']))
        pass
    except:
        logging.error('Unknown error, , %s', os.path.join(target['jp2_path']))
        pass
    else:
        jp2_counter = jp2_counter + 1

        return jp2_counter


def main():
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('convert_tif_to_jp2.log')
    fh.setLevel(logging.WARNING)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fh_formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    ch_formatter = logging.Formatter('%(levelname)s - %(message)s')
    fh.setFormatter(fh_formatter)
    ch.setFormatter(ch_formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)

    start_time = time.time()
    dir_target_paths, file_target_paths = validating_inputs(args.path, args.type)
    targets = parsing_targets(dir_target_paths, file_target_paths)
    characterize_and_convert_targets(targets)
    end_time = time.time()

    logging.info('Conversion complete: %s second(s)', round(end_time - start_time))

    # msg_to_teams_channel = pymsteams.connectorcard('')
    # msg_to_teams_channel.text('Conversion complete: ' + args.path)
    # msg_to_teams_channel.send()


if __name__ == '__main__':
    main()
