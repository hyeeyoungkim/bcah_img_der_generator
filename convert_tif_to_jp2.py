import argparse
import logging
import os
import subprocess
import sys
import time

parser = argparse.ArgumentParser(description='Convert tif to jp2 and add watermark')
parser.add_argument('-i', '--input', required=True, help='Target directory')
args = parser.parse_args()


def search_targets(src_path):
    if not os.path.exists(os.path.join(src_path, 'PUB')):
        logging.error('PUB directory not found')
        sys.exit()

    targets = []

    for dirpath, dirnames, files in os.walk(os.path.join(src_path, 'PUB')):
        for file in files:
            if not file.startswith('._') and file.endswith(('.tiff', '.tif')):
                file_path = os.path.join(dirpath, file)
                scene_count = count_tif_scene(file_path)

                if scene_count == 1:
                    target = {
                        'tif_name': file,
                        'tif_path': file_path,
                        'jp2_path': os.path.join(dirpath, os.path.splitext(file)[0].replace('_pub', '') + '.jp2')
                        # 'tif_width': 0,
                        # 'tif_height': 0,
                        # 'tif_density': 0,
                        # 'tif_density_unit': '',
                        # 'tif_convert': '',
                        # 'jp2_density': '',
                        # 'jp2_rate': ''
                        # 'watermark_min': ''
                    }
                    targets.append(target)
                elif scene_count > 1:
                    logging.warning('Multiple tiff scenes, %s, %s', scene_count, file_path)
                    for i in range(scene_count):
                        target = {
                            'tif_name': os.path.splitext(file)[0] + '-' + str(i) + os.path.splitext(file)[1],
                            'tif_path': os.path.join(dirpath, file) + '[' + str(i) + ']',
                            'jp2_path': os.path.join(dirpath, os.path.splitext(file)[0] + '-' + str(i) + '.jp2')
                        }
                        targets.append(target)
                else:
                    pass

    logging.info('Found %s tif file(s) in %s', len(targets), src_path)

    return targets


def count_tif_scene(file_path):
    # ImageMagick 6.x and 7.x command
    cmd_count_scene = ['identify', '-quiet', '-format', '%s', file_path]

    try:
        result = subprocess.check_output(cmd_count_scene).decode('utf-8')
        scene_count = len(result.strip())
    except:
        logging.error('Scene count failed, %s', file_path)
        scene_count = 0
        pass

    return scene_count


def characterize_target(target):
    # ImageMagick 6.x command
    # cmd_characterize = ['identify', '-quiet', '-format', '%w-%h-%x', target['tif_path']]
    # ImageMagick 7.x command
    cmd_characterize = ['identify', '-quiet', '-format', '%w-%h-%x %U', target['tif_path']]

    try:
        result = subprocess.check_output(cmd_characterize).decode('utf-8')
    except:
        logging.error('Characterization failed, %s', target['tif_path'])
        pass
    else:
        temp_w, temp_h, temp_d_u = result.strip().split('-')
        target.update({
            'tif_width': float(temp_w),
            'tif_height': float(temp_h),
            'tif_density': round(float(temp_d_u.split(' ')[0])),
            'tif_density_unit': temp_d_u.split(' ')[1]
        })

        if target['tif_density_unit'] == 'PixelsPerInch':
            tif_resample_result, jp2_rate_result, watermark_result = calculate_jp2_watermark(target)
            target.update({
                'tif_convert': True,
                'jp2_density': tif_resample_result,
                'jp2_rate': jp2_rate_result,
                'watermark_min': watermark_result
            })
        else:
            logging.error('Unknown density unit, %s, %s', target['tif_density_unit'], target['tif_path'])

    return target


def calculate_jp2_watermark(target):
    if target['tif_density'] >= 600.0:
        jp2_density = round((target['tif_density'] / 4))
        # jp2_rate = 'jp2:rate=0.02380'  # for ImageMagick 6.x
        jp2_rate = 'jp2:rate=42'  # for ImageMagick 7.x
    elif target['tif_density'] >= 300.0:
        jp2_density = 150.0
        # jp2_rate = 'jp2:rate=0.02380'  # for ImageMagick 6.x
        jp2_rate = 'jp2:rate=42'  # for ImageMagick 7.x
    elif target['tif_density'] >= 150.0:
        jp2_density = 150.0
        # jp2_rate = 'jp2:rate=0.125'  # for ImageMagick 6.x
        jp2_rate = 'jp2:rate=8'  # for ImageMagick 7.x
    else:
        jp2_density = target['tif_density']
        # jp2_rate = 'jp2:rate=0.50'  # for ImageMagick 6.x
        jp2_rate = 'jp2:rate=2'  # for ImageMagick 7.x
        logging.warning('Low tif dpi, %s dpi, %s', target['tif_density'], target['tif_path'])

    jp2_w = round(target['tif_width'] * (jp2_density / target['tif_density']))
    jp2_h = round(target['tif_height'] * (jp2_density / target['tif_density']))
    watermark_m = str(min(jp2_w, jp2_h))
    watermark_min = watermark_m + 'x' + watermark_m

    if max(jp2_w, jp2_h) < 480.0:
        logging.warning('Low jp2 resolution, %sx%s, %s', jp2_w, jp2_h, target['tif_path'])
        print('>>> Generating %sx%s jp2', target['tif_width'], target['tif_height'])
        jp2_density = target['tif_density']
        watermark_m = str(min(target['tif_width'], target['tif_height']))
        watermark_min = watermark_m + 'x' + watermark_m

    return jp2_density, jp2_rate, watermark_min


def convert_targets(target):
    # ImageMagick command for conversion
    cmd_jp2 = [
        'convert', '-quiet', target['tif_path'],
        '-density', str(target['tif_density']), '-resample', str(target['jp2_density']),
        '-define', 'numrlvls=7', '-define', 'jp2:tilewidth=1024', '-define', 'jp2:tileheight=1024',
        '-define', target['jp2_rate'], '-define', 'jp2:prg=rpcl', '-define', 'jp2:mode=int',
        '-define', 'jp2:prcwidth=16383', '-define', 'jp2:prcheight=16383', '-define', 'jp2:cblkwidth=64',
        '-define', 'jp2:cblkheight=64', '-define', 'jp2:sop', target['jp2_path']
    ]

    # ImageMagick command for watermarking
    cmd_watermark_a = [
        'convert', '-quiet', '-background', 'none', '-resize', target['watermark_min'],
        'WM_20200311.png', 'WM_20200311_temp.png'
    ]
    cmd_watermark_b = [
        'convert', '-quiet', target['jp2_path'], 'WM_20200311_temp.png', '-gravity', 'center',
        '-composite', target['jp2_path']
    ]

    try:
        subprocess.call(cmd_jp2)
        subprocess.call(cmd_watermark_a)
        subprocess.call(cmd_watermark_b)
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

    target_count = 1
    for target in targets:
        logging.info('Converting %s (%s/%s)', target['tif_name'], target_count,len(targets))
        target = characterize_target(target)
        if target['tif_convert'] is True:
            convert_targets(target)
        target_count = target_count + 1

    verify_jp2_counts(args.input, targets)
    end_time = time.time()

    print([len(targets), round(end_time - start_time)])
    print('\a\a\a')


if __name__ == '__main__':
    main()
