import json
import re
import os


def sanitize_filename(filename):
     # Replace slashes with underscores first to avoid directory paths
    filename = filename.replace('/', '_')
    invalid_chars = '<>:"/\\|?*'
    return "".join([c if c.isalnum() or c in ['_', '.'] else '_' for c in filename if c not in invalid_chars])



def extract_chip_sn(lines, chip_index, offset, pattern):

    chip_key = f"* Chip {chip_index} "

    for i, line in enumerate(lines):

        if line.startswith(chip_key):
            target_line = lines[i + offset].strip()
            if re.match(pattern, target_line):
                return target_line

    return "Not found"



def create_json(front_file, back_file, name, output_dir):

    with open(front_file, 'r', encoding='utf-8') as f:
        front_lines = f.readlines()
    with open(back_file, 'r', encoding='utf-8') as f:
        back_lines = f.readlines()

    # Extract required information
    #qr_code = front_lines[0].strip()
    qr_code = front_lines[0].replace("FEMB SN: ", "").strip()
    sanitized_qr_code = sanitize_filename(qr_code)
    date = front_lines[2].strip()

    specifications = {
        "FEMB ID": qr_code,
        "(F) COLDATA 1 SN": extract_chip_sn(front_lines, 0, 5, r'\d{5}'),
        "(F) COLDATA 2 SN": extract_chip_sn(front_lines, 1, 5, r'\d{5}'),
        "(F) ColdADC 1 SN": extract_chip_sn(front_lines, 2, 5, r'\d{5}'),
        "(F) ColdADC 2 SN": extract_chip_sn(front_lines, 3, 5, r'\d{5}'),
        "(F) ColdADC 3 SN": extract_chip_sn(front_lines, 4, 5, r'\d{5}'),
        "(F) ColdADC 4 SN": extract_chip_sn(front_lines, 5, 5, r'\d{5}'),
        "(F) LArASIC 1 SN": extract_chip_sn(front_lines, 6, 8, r'\d{3}-\d{5}'),
        "(F) LArASIC 2 SN": extract_chip_sn(front_lines, 7, 8, r'\d{3}-\d{5}'),
        "(F) LArASIC 3 SN": extract_chip_sn(front_lines, 8, 8, r'\d{3}-\d{5}'),
        "(F) LArASIC 4 SN": extract_chip_sn(front_lines, 9, 8, r'\d{3}-\d{5}'),
        "(B) ColdADC 1 SN": extract_chip_sn(back_lines, 0, 5, r'\d{5}'),
        "(B) ColdADC 2 SN": extract_chip_sn(back_lines, 1, 5, r'\d{5}'),
        "(B) ColdADC 3 SN": extract_chip_sn(back_lines, 2, 5, r'\d{5}'),
        "(B) ColdADC 4 SN": extract_chip_sn(back_lines, 3, 5, r'\d{5}'),
        "(B) LArASIC 1 SN": extract_chip_sn(back_lines, 4, 8, r'\d{3}-\d{5}'),
        "(B) LArASIC 2 SN": extract_chip_sn(back_lines, 5, 8, r'\d{3}-\d{5}'),
        "(B) LArASIC 3 SN": extract_chip_sn(back_lines, 6, 8, r'\d{3}-\d{5}'),
        "(B) LArASIC 4 SN": extract_chip_sn(back_lines, 7, 8, r'\d{3}-\d{5}')
    }

    json_data = {
        "component_type": {
            "part_type_id": "D08100400001"
        },
        "country_code": "US",
        "comments": f"Picture taken on {date}, by {name}",
        "institution": {
            "id": 128
        },
        "manufacturer": {
            "id": 58
        },
        "specifications": specifications
    }

    #output_filename = f"{qr_code}.json"
    output_filename = os.path.join(output_dir, f"{sanitized_qr_code}.JSON")
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4)

    print(f"JSON file '{output_filename}' created successfully.")


def process_all_folders(base_dir, name):
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        if os.path.isdir(folder_path):
            front_file = os.path.join(folder_path, "front_results.txt")
            back_file = os.path.join(folder_path, "back_results.txt")
            if os.path.exists(front_file) and os.path.exists(back_file):
                create_json(front_file, back_file, name, folder_path)
            else:
                print(f"Skipping folder '{folder_name}' (missing front_results.txt or back_results.txt)")

# User input
NAME = "Karla F."
BASE_DIR = "results"

process_all_folders(BASE_DIR, NAME)


