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

    tif_list = []
    for dirpath, dirnames, files in os.walk(os.path.join(src_path, 'PUB')):
        for file in files:
            if file.endswith(('.tiff', '.tif')):
                file_path = os.path.join(dirpath, file)
                tif_list.append(file_path)
    logging.info('Found %s tif file(s) in %s', len(tif_list), src_path)
    return tif_list


def characterize_targets(target):
    tif = target
    jp2 = os.path.splitext(target)[0] + '.jp2'

    # ImageMagick command for identifying tif dpi
    cmd_characterize = ['identify', '-quiet', '-format', '%w-%h-%x', tif]

    try:
        result = subprocess.check_output(cmd_characterize).decode('utf-8')
        tif_w, tif_h, tif_dpi = result.replace(' PixelsPerInch', '').strip().split('-')
    except:
        logging.error('Characterization failed, %s', tif)
        tif_dpi = '0'
        tif_resample = False
        jp2_rate = '0'
        tif_convert = False
        pass
    else:
        tif_resample = calculate_resample(tif, tif_w, tif_h, tif_dpi)
        jp2_rate = calculate_jp2_rate(tif, tif_dpi)
        tif_convert = True
    return tif, tif_dpi, tif_convert, tif_resample, jp2, jp2_rate


def calculate_resample(tif, tif_w, tif_h, tif_dpi):
    jp2_dpi = 150

    if int(tif_dpi) > 150:
        jp2_w = round(int(tif_w) * (int(jp2_dpi) / int(tif_dpi)))
        jp2_h = round(int(tif_h) * (int(jp2_dpi) / int(tif_dpi)))

        if int(jp2_w) >= 500 and int(jp2_h) >= 500:
            return True
        else:
            logging.warning('Low jp2 resolution (%sx%s), %s', str(jp2_w), str(jp2_h), tif)
            return False
    else:
        return False


def calculate_jp2_rate(tif, tif_dpi):
    if int(tif_dpi) >= 600:
        jp2_rate = 'jp2:rate=0.02380'  # for ImageMagick 6.x
        # jp2_rate = 'jp2:rate=42' # for ImageMagick 7.x
    elif int(tif_dpi) >= 300:
        jp2_rate = 'jp2:rate=0.125'
    else:
        logging.warning('Low tif dpi (%s dpi), %s', tif_dpi, tif)
        jp2_rate = 'jp2:rate=0.5'
    return jp2_rate


def convert_targets(tif, tif_dpi, tif_resample, jp2, jp2_rate):
    # ImageMagick command for converting tif to jp2 with resample
    cmd_jp2_resample = [
        'convert', '-quiet', tif, '-density', tif_dpi, '-resample', '150',
        '-define', 'numrlvls=7', '-define', 'jp2:tilewidth=1024', '-define', 'jp2:tileheight=1024', '-define', jp2_rate,
        '-define', 'jp2:prg=rpcl', '-define', 'jp2:mode=int', '-define', 'jp2:prcwidth=16383',
        '-define', 'jp2:prcheight=16383', '-define', 'jp2:cblkwidth=64', '-define', 'jp2:cblkheight=64', '-define',
        'jp2:sop', jp2
    ]

    # ImageMagick command for converting tif to jp2 without resample
    cmd_jp2 = [
        'convert', '-quiet', tif, '-density', '150',
        '-define', 'numrlvls=7', '-define', 'jp2:tilewidth=1024', '-define', 'jp2:tileheight=1024', '-define', jp2_rate,
        '-define', 'jp2:prg=rpcl', '-define', 'jp2:mode=int', '-define', 'jp2:prcwidth=16383',
        '-define', 'jp2:prcheight=16383', '-define', 'jp2:cblkwidth=64', '-define', 'jp2:cblkheight=64', '-define',
        'jp2:sop', jp2
    ]

    # ImageMagick command for watermarking
    cmd_watermark = [
        'convert', '-quiet', jp2, 'WM_20200311.png', '-gravity', 'center', '-compose', 'over', '-composite', jp2
    ]

    logging.info('Converting %s', tif)
    try:
        if tif_resample is True:
            subprocess.call(cmd_jp2_resample)
        else:
            subprocess.call(cmd_jp2)
        subprocess.call(cmd_watermark)
    except:
        logging.error('Converting failed, %s', tif)
        pass


def verify_jp2_counts(src_path, target_list):
    tif_count = len(target_list)
    jp2_count = 0
    for dirpath, dirnames, files in os.walk(os.path.join(src_path, 'PUB')):
        for file in files:
            if file.endswith(('.jp2')):
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
    target_list = search_targets(args.input)
    for target in target_list:
        tif, tif_dpi, tif_convert, tif_resample, jp2, jp2_rate = characterize_targets(target)
        if tif_convert is True:
            convert_targets(tif, tif_dpi, tif_resample, jp2, jp2_rate)
    verify_jp2_counts(args.input, target_list)
    end_time = time.time()

    print([len(target_list), round(end_time - start_time)])


if __name__ == "__main__":
    main()
