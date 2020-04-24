import argparse
import logging
import os
import subprocess
import sys
import time

parser = argparse.ArgumentParser(description='Convert tif to jp2 and add watermart')
parser.add_argument('-i', '--input', required=True, help='Target directory')
args = parser.parse_args()


def search_targets(src_path):
    if not os.path.exists(os.path.join(src_path, 'PUB')):
        logging.error('PUB directory not found')
        sys.exit()

    targets = []
    for dirpath, dirnames, files in os.walk(os.path.join(src_path, 'PUB')):
        for file in files:
            if file.endswith(('.tiff', '.tif')):
                target = {
                    'tif_name': file,
                    'tif_path': os.path.join(dirpath, file),
                    'tif_w': 0, 'tif_h': 0,
                    'tif_d': 0, 'tif_u': '',
                    'tif_resample': False, 'tif_convert': False,
                    'jp2_name': os.path.splitext(file)[0] + '.jp2',
                    'jp2_path': os.path.join(dirpath, os.path.splitext(file)[0] + '.jp2'),
                    'jp2_rate': ''
                }
                targets.append(target)
    logging.info('Found %s tif file(s) in %s', len(targets), src_path)
    return targets


def characterize_target(input):
    target = input

    # ImageMagick 6.x command
    cmd_characterize = ['identify', '-quiet', '-format', '%w-%h-%x', target['tif_path']]

    try:
        result = subprocess.check_output(cmd_characterize).decode('utf-8')
    except:
        logging.error('Characterization failed, %s', target)
        pass
    else:
        temp_w, temp_h, temp_d_u = result.strip().split('-')
        target['tif_w'] = float(temp_w)
        target['tif_h'] = float(temp_h)
        target['tif_d'] = float(temp_d_u.split(' ')[0])
        target['tif_u'] = temp_d_u.split(' ')[1]
        if target['tif_u'] == 'PixelsPerInch':
            target['tif_resample'] = calculate_resample(target)
            target['tif_convert'] = True
            target['jp2_rate'] = calculate_jp2_rate(target)
        else:
            logging.error('Unknown density unit (%s), %s', target['tif_u'], target['tif_path'])

    return target


def calculate_resample(target):
    jp2_d = 150.0

    if target['tif_d'] > jp2_d:
        jp2_w = round(target['tif_w'] * (jp2_d / target['tif_d']))
        jp2_h = round(target['tif_h'] * (jp2_d / target['tif_d']))
        if jp2_w >= 500.0 and jp2_h >= 500.0:
            return True
        else:
            logging.warning('Low jp2 resolution (%sx%s), %s', jp2_w, jp2_h, target['tif_path'])
            return False
    else:
        return False


def calculate_jp2_rate(target):
    if target['tif_d'] >= 600.0:
        temp_rate = 'jp2:rate=0.02380'  # for ImageMagick 6.x
        # temp_rate = 'jp2:rate=42' # for ImageMagick 7.x
    elif target['tif_d'] >= 300.0:
        temp_rate = 'jp2:rate=0.125'
    else:
        logging.warning('Low tif dpi (%s dpi), %s', target['tif_d'], target['tif_path'])
        temp_rate = 'jp2:rate=0.5'
    return temp_rate


def convert_targets(input):
    target = input

    # ImageMagick command for converting tif to jp2 with resample
    cmd_jp2_resample = [
        'convert', '-quiet', target['tif_path'], '-density', str(target['tif_d']), '-resample', '150',
        '-define', 'numrlvls=7', '-define', 'jp2:tilewidth=1024', '-define', 'jp2:tileheight=1024',
        '-define', target['jp2_rate'], '-define', 'jp2:prg=rpcl', '-define', 'jp2:mode=int',
        '-define', 'jp2:prcwidth=16383', '-define', 'jp2:prcheight=16383', '-define', 'jp2:cblkwidth=64',
        '-define', 'jp2:cblkheight=64', '-define', 'jp2:sop', target['jp2_path']
    ]

    # ImageMagick command for converting tif to jp2 without resample
    cmd_jp2 = [
        'convert', '-quiet', target['tif_path'], '-density', '150',
        '-define', 'numrlvls=7', '-define', 'jp2:tilewidth=1024', '-define', 'jp2:tileheight=1024',
        '-define', target['jp2_rate'], '-define', 'jp2:prg=rpcl', '-define', 'jp2:mode=int',
        '-define', 'jp2:prcwidth=16383', '-define', 'jp2:prcheight=16383', '-define', 'jp2:cblkwidth=64',
        '-define', 'jp2:cblkheight=64', '-define', 'jp2:sop', target['jp2_path']
    ]

    # ImageMagick command for watermarking
    cmd_watermark = [
        'convert', '-quiet', target['jp2_path'], 'WM_20200311.png', '-gravity', 'center', '-compose', 'over',
        '-composite', target['jp2_path']
    ]

    try:
        if target['tif_resample'] is True:
            subprocess.call(cmd_jp2_resample)
        else:
            subprocess.call(cmd_jp2)
        subprocess.call(cmd_watermark)
    except:
        logging.error('Converting failed, %s', target['tif_path'])
        pass


def verify_jp2_counts(src_path, targets):
    tif_count = len(targets)
    jp2_count = 0
    for dirpath, dirnames, files in os.walk(os.path.join(src_path, 'PUB')):
        for file in files:
            if file.endswith('.jp2'):
                jp2_count = jp2_count + 1
    logging.info('Found %s tif file(s) and %s jp2 file(s)', tif_count, jp2_count)


def main():
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('convert_error_log.csv')
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
    targets = search_targets(args.input)

    for target in targets:
        logging.info('Converting %s', target['tif_name'])
        target = characterize_target(target)
        if target['tif_convert'] is True:
            convert_targets(target)

    verify_jp2_counts(args.input, targets)
    end_time = time.time()

    print([len(targets), round(end_time - start_time)])


if __name__ == "__main__":
    main()
