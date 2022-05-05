# BCAH Image Derivative Generator

## Requirements
- Python 3.0 or higher
- pillow: For image processing
- pymsteams: For posting a notification to a Microsoft Teams channel
- watermark.png: For watermarking images

## Installation
- Clone this repository to your computer
- `pip install -r requirements.txt`

## Usage
1. (Optional) Install and activate [the python virtual environment](https://docs.python.org/3.9/tutorial/venv.html) 
```
python3 -m venv env
source env/bin/activate
```

2. Run the script
```
python3 convert_tif_to_jp2.py /path/to/directoy/or/csv_file.csv -t/--type [pub, arch, any, csv]
```

The script requires two arguments:
- A path to 
  - a directory where the TIFF files are OR
  - a csv file that lists directories
- An argument (`-t, --type`) to designate which TIFF files to target
  - `pub` will convert all TIFF files in `/path/to/directory/PUB`
  - `arch` will convert all TIFF files in `/path/to/directory/ARCH`
  - `any` will convert all TIFF files in `/path/to/directory`
  - `csv` will convert listed TIFF files AND TIFF files in listed directories in the csv file

Here are examples:
```
python3 convert_tif_to_jp2.py /path/to/directory -t any
python3 convert_tif_to_jp2.py /path/to/csv_file.csv -t csv
```

Here is a csv file example:

| path                  |
|-----------------------|
| /path/to/directory    |
| /path/to/tif_file.tif |

2.1 Large batch

If you are expecting to convert a lot of TIFFs (e.g., 5000+ files), use `nohup` to prevent your server connection from being disconnected. You will be able to track the terminal output via `tail nohup.out -f`.

Here is an example:
```
nohup python convert_tif_to_jp2.py /path/to/directoy -t any &
```

2.2 Microsoft Teams notification

When the script finishes, it can post a notification in a Microsoft Teams channel. To receive the notification, uncomment `msg_to_teams_channel` lines and provide the Incoming Webhook URL in `pymsteams.connectorcard('')`.

2.3 Error report

If the script encounters errors or warnings during the conversion, it will show them in the console and log them in `convert_tif_to_jp2.log`, which can be opened as a csv file.

Here is an error log example:
```
YYYY-MM-DD HH:MM:SS, ERROR, Directory not found, , /path/to/directory
YYYY-MM-DD HH:MM:SS, ERROR, File cannot be opened, , /path/to/tif_file.tif
YYYY-MM-DD HH:MM:SS, WARNING, Multiple scene tif, 2, /path/to/tif_file.tif
YYYY-MM-DD HH:MM:SS, WARNING, Low dpi tif, 72.0 dpi, /path/to/tif_file.tif
...
```

3. (Optional) Deactivate the python virtual environment
`deactivate`