# This program crops all chips from the input picture
# based on chips coordinates. This is based on MiniCPM
# to perform OCR

# Code reads EITHER QR codes or Data Matrices.
# Code processes both FRONT and BACK chip readings.

import cv2
import numpy as np
from PIL import Image
import re
import os

import base64
import io

from pylibdmtx.pylibdmtx import decode as decode_dm
from qreader import QReader


import pandas as pd
import requests
import json



# Function to encode the image for MiniCPM:
def encode_image(image):

    if not isinstance(image, Image.Image):
        image = Image.open(image).convert("RGB")

    max_size = 448 * 16
    if max(image.size) > max_size:
        w, h = image.size
        if w > h:
            new_w = max_size
            new_h = int(h * max_size / w)
        else:
            new_h = max_size
            new_w = int(w * max_size / h)
        image = image.resize((new_w, new_h), resample=Image.BICUBIC)

    # Convert image to base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    im_b64 = base64.b64encode(buffered.getvalue()).decode()

    return im_b64



# Function to perform OCR using MiniCPM API
def perform_ocr_minicpm(image_path):

    # Load and encode the image
    image = Image.open(image_path)
    encoded_image = encode_image(image)

    # API:
    url = "http://localhost:XXXXX/api/generate"

    headers = {
        "Content-Type": "application/json",
    }

    # Set up:
    data = {
        "model": "aiden_lu/minicpm-v2.6:Q4_K_M",
        "prompt": "Please OCR this image with all output texts in one line with no space",
        "images": [encoded_image],
        "sampling": False,
        "stream": False,
        "num_beams": 3,
        "repetition_penalty": 1.2,
        "max_new_tokens": 2048,
        "max_inp_length": 4352,
        "decode_type": "beam_search",
        "options": {
            "seed": 42,
            "temperature": 0.0,
            "top_p": 0.1,
            "top_k": 10,
            "repeat_penalty": 1.0,
            "repeat_last_n": 0,
            "num_predict": 42,
        },
    }

    # Send the request to MiniCPM API
    response = requests.post(url, headers=headers, data=json.dumps(data))

    # Process the response
    if response.status_code == 200:
        try:
            responses = response.text.strip().split('\n')
            for line in responses:
                data = json.loads(line)
                actual_response = data.get("response", "")
                if actual_response:
                    return actual_response.strip()
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return "Error: Unable to process OCR"
    else:
        print(f"Error {response.status_code}: {response.text}")
        return "Error: API request failed"


# Configuration variable: Choose between 'QR' or 'DM' (Data Matrix)
barcode_type = 'DM'


# Define the positions for QR and DM
qr_position = (1048, 1497, 142, 142)
dm_position = (1056, 1510, 164, 172) # pictures 09-25

# Define the coordinates and sizes for each chip
chip_coordinates_front = [#For chip's region of interest only:
    (866, 397, 505, 505),  # coordinates and size for COLDATA 1
    (2593, 393, 505, 505), # COLDATA 2
    (618,1162,291,291), #  ColdADC 1
    (1326,1158,291,291), #  ColdADC 2
    (2343,1157,291,291), #  ColdADC 3
    (3056,1157,291,291), #  ColdADC 4
    (619,1789,287,292), #  LArASIC 1
    (1326,1790,287,292), #LArASIC 2
    (2349,1791,287,292), #LArASIC 3
    (3063,1788,287,292), #LArASIC 4

]

chip_coordinates_back = [
    (623, 1160, 284, 296),  # coordinates and size for ColdADC 1
    (1333, 1155, 284, 296), # ColdADC 2
    (2349,1156,284,296), #  ColdADC 3
    (3064,1154,284,296), #  ColdADC 4
    (626,1794,287,292), #  LArASIC 1
    (1333,1793,287,292), #LArASIC 2
    (2349,1791,287,292), #LArASIC 3
    (3063,1788,287,292), #LArASIC 4
]

## ----------------------------------------------------##


########################################################################

def read_barcode(image, position, barcode_type):
    x, y, w, h = position
    cropped_image = image[y:y+h, x:x+w]

    if barcode_type == 'QR':
        qreader = QReader()
        try:
            data = qreader.detect_and_decode(image=cropped_image)
            if data:

                return data[0] if isinstance(data, tuple) else data
            else:
                return "QR code not detected!"
        except Exception as e:
            print(f"Error decoding QR code: {e}")
            return "QR code not detected!"
            # Save the QR code image to a file
        cv2.imwrite(f'cropped/QR_code.png', cropped_image)

    elif barcode_type == 'DM':
        dm_image = Image.fromarray(cropped_image)  # Convert to PIL Image format
        results = decode_dm(dm_image)
        if results:
            return results[0].data.decode('utf-8')
        else:
            return "Data Matrix not detected!"

        cv2.imwrite(f'cropped/DM_code.png', cropped_image)

    else:
        return "Invalid barcode type specified!"

########################################################################


def save_barcode_image(image, position, barcode_type, directory_name):
    x, y, w, h = position
    cropped_image = image[y:y+h, x:x+w]

    if barcode_type == 'QR':
        cv2.imwrite(f'{directory_name}/QR_code.png', cropped_image)
    elif barcode_type == 'DM':
        cv2.imwrite(f'{directory_name}/DM_code.png', cropped_image)
    else:
        return "Invalid barcode type specified!"


####################################################################

def sanitize_filename(filename):
     # Replace slashes with underscores first to avoid directory paths
    filename = filename.replace('/', '_')
    # Replace any character that is not alphanumeric, an underscore, or a dot with an underscore
    invalid_chars = '<>:"/\\|?*'
    return "".join([c if c.isalnum() or c in ['_', '.'] else '_' for c in filename if c not in invalid_chars])

####################################################################

def process_chips(image_path, chip_coordinates, directory_name, file_suffix, barcode_content, date_str):

    # Read the image:
    image = cv2.imread(image_path)

    # save a copy of the original image
    cv2.imwrite(f'{directory_name}/{image_path}', image)

    # Creating the file name:
    result_filename = os.path.join(directory_name, f"{file_suffix}_results.txt")

    print(f"-------------- STARTING SERIAL NUMBER RECOGNITION --------------")
    print(f"------------------- FOR [{file_suffix}] SIDE ---------------------\n\n\n")

    with open(result_filename, 'w', encoding='utf-8') as file:

        file.write(f"FEMB SN: {barcode_content}\n\n{date_str}\n\n")

        for i, (x, y, w, h) in enumerate(chip_coordinates):

            ## Crop the image
            chip_image = image[y:y+h, x:x+w]

            print(f'Processing Chip #{i} [{file_suffix}]...')

            # Rotate the chip:
            rotated_chip = cv2.rotate(chip_image, cv2.ROTATE_90_CLOCKWISE)

            ## Save the processed chip image to a file
            chip_image_path = os.path.join(directory_name, f'{file_suffix}_chip_{i}.png')
            cv2.imwrite(chip_image_path, rotated_chip)


            # Perform OCR
            ocr_result = perform_ocr_minicpm(chip_image_path)

            # Apply correction before printing and saving
            corrected_ocr_result = correct_ocr(ocr_result, chip_number=i, side=file_suffix)

            # Writing original OCR result to file (single line per chip):
            file.write(f"* Chip {i} ({file_suffix}):\n")
            file.write(f"Original OCR result: ")
            file.write(ocr_result)

            # Giving the corrected result a nice format to print in terminal
            formatted_ocr_result = corrected_ocr_result.replace(" ", "\n")
            print(f"OCR results: \n\n{formatted_ocr_result}")

            # Validate the OCR result:
            validate_ocr_result(corrected_ocr_result, chip_number=i, side=file_suffix)

            file.write(f"\nFormatted OCR result:\n")
            # Writing validated OCR result to file:
            file.write(formatted_ocr_result)

            print(f"\n\nOCR result saved to {directory_name}")
            print("***********************************************************************")

            file.write("\n\n")

############################################################################################

def count_chips(result_filename):

    with open(result_filename, 'r', encoding='utf-8') as file:
        content = file.read()
    return content.count('*')

############################################################################################

def extract_date_from_filename(filename):
    match = re.search(r'--(\d{2}-\d{2}-\d{4})', filename)
    return match.group(1) if match else "Unknown date"

############################################################################################



def correct_ocr(ocr_result, chip_number, side):
    # Define expected spaces based on side and chip number
    if side == "front":
        if chip_number in [0, 1]:       # COLDATA 1 and 2 on the front side
            max_spaces = 3
        elif chip_number in [2, 3, 4, 5]:  # ColdADC 1-4 on the front side
            max_spaces = 3
        elif chip_number in [6, 7, 8, 9]:  # LArASIC 1-4 on the front side
            max_spaces = 5
        else:
            print(f"Warning: Chip number {chip_number} invalid for front side.")
            return ocr_result
    elif side == "back":
        if chip_number in [0, 1, 2, 3]:    # ColdADC 1-4 on the back side
            max_spaces = 3
        elif chip_number in [4, 5, 6, 7]:  # LArASIC 1-4 on the back side
            max_spaces = 5
        else:
            print(f"Warning: Chip number {chip_number} invalid for back side.")
            return ocr_result
    else:
        print("Warning: Invalid side specified.")
        return ocr_result

    # Count spaces in the OCR result
    space_count = ocr_result.count(" ")


    # Automatically replace specific incorrect variants of "ColdADC" for specified chips
    if (side == "front" and chip_number in [2, 3, 4, 5]) or (side == "back" and chip_number in [0, 1, 2, 3]):
        ocr_result = re.sub(r"\b(Col dADC|Co1 dADC|Cold ADC|Co1d ADC|CoI dADC)\b", "ColdADC", ocr_result)
    #if (side == "front" and chip_number in [6, 7, 8, 9]) or (side == "back" and chip_number in [4, 5, 6, 7]):
    #    ocr_result = re.sub(r"\b(BNl.)\b", "BNL ", ocr_result)

    # Correcting Serial Number impurities: Remove "-" or "." from serial numbers for specified chips
    lines = ocr_result.replace(" ", "\n").split("\n")

    if side == "front":
        # Serial numbers for front chips 0, 1, 2-5, and 6-9
        if chip_number in [0, 1] or chip_number in [2, 3, 4, 5]:  # line 3
            serial_number_line_index = 2
        elif chip_number in [6, 7, 8, 9]:  # line 6
            serial_number_line_index = 5
    elif side == "back":
        if chip_number in [0, 1, 2, 3]:  # line 3
            serial_number_line_index = 2
        elif chip_number in [4, 5, 6, 7]:  # line 6
            serial_number_line_index = 5

    # Apply the correction if we are in the specified range and line exists
    if serial_number_line_index < len(lines):
        if side == "front" and chip_number in [0, 1, 2, 3, 4, 5] or side == "back" and chip_number in [0, 1, 2, 3]:
            # Remove any impurities in the serial number for these specific chips
            lines[serial_number_line_index] = re.sub(r"[-.']", "", lines[serial_number_line_index])

    #return ocr_result
    # Reconstruct the corrected OCR result by replacing newlines with spaces
    corrected_result = " ".join(lines)
    return corrected_result

############################################################################################



def validate_ocr_result(ocr_result, chip_number, side):

    # Correct OCR result for extra or missing spaces
    corrected_ocr_result = correct_ocr(ocr_result, chip_number, side)


    # Define regex patterns based on the chip number and side
    patterns = {
        "front": {
            "COLDATA": re.compile(r"^(COLDATA|colddata|ColdData|CO1DATA)\s+([A-Za-z0-9]+\.[A-Za-z0-9]+)\s+(\d{5})\s+(\d{4})$"),
            "ColdADC": re.compile(r"^(ColdADC|coldadc|Coldadc|Co1dADC|ColADC|CoIdADC)\s+([A-Za-z0-9]+\.[A-Za-z0-9]+)\s+(\d{5})\s+(\d{4})$"),
            "LArASIC": re.compile(r"^BNL\s+LArASIC\s+Version\s+([A-Z0-9]+)\s+(\d{2}/\d{2})\s+(\d{3}-\d{5})$")
        },
        "back": {
            "ColdADC": re.compile(r"^(ColdADC|coldadc|Coldadc|Co1dADC|ColADC|CoIdADC)\s+([A-Za-z0-9]+\.[A-Za-z0-9]+)\s+(\d{5})\s+(\d{4})$"),
            "LArASIC": re.compile(r"^BNL\s+LArASIC\s+Version\s+([A-Z0-9]+)\s+(\d{2}/\d{2})\s+(\d{3}-\d{5})$")
        }
    }
        # TO DO: Include "BNL.", "Version."

    # Determine chip type based on chip number and side
    if side == "front":
        if chip_number in [0, 1]:
            pattern = patterns["front"]["COLDATA"]
        elif chip_number in [2, 3, 4, 5]:
            pattern = patterns["front"]["ColdADC"]
        elif chip_number in [6, 7, 8, 9]:
            pattern = patterns["front"]["LArASIC"]
        else:
            print("Warning: Invalid chip number for front side")
            return

    elif side == "back":
        if chip_number in [0, 1, 2, 3]:
            pattern = patterns["back"]["ColdADC"]
        elif chip_number in [4, 5, 6, 7]:
            pattern = patterns["back"]["LArASIC"]
        else:
            print("Warning: Invalid chip number for back side")
            return
    else:
        print("Warning: Invalid side specified")
        return

    # Validate OCR result
    match = pattern.match(corrected_ocr_result) #was ocr_result
    if not match:
        print("(!) WARNING: check OCR result")

    # Validate the serial number format
    if side == "front" and chip_number in [6, 7, 8, 9] or side == "back" and chip_number in [4, 5, 6, 7]:
        components = corrected_ocr_result.split()
        if components:
            serial_number = components[-1]  # Expected to be the last component for LArASIC
            if not re.match(r"^\d{3}-\d{5}$", serial_number):
                print("(!) ERROR: Serial Number needs correction!")


############################################################################################



def save_reduced_image(image_path, directory_name, suffix, max_dimension=1600):

    image = cv2.imread(image_path)
    h, w = image.shape[:2]

    # Calculate the scaling factor to maintain aspect ratio
    if max(h, w) > max_dimension:
        scale_factor = max_dimension / max(h, w)
        new_size = (int(w * scale_factor), int(h * scale_factor))
        resized_image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    else:
        resized_image = image  # No resizing if already smaller than max_dimension

    # Save the resized image
    reduced_image_path = os.path.join(directory_name, f"{suffix}_reduced.png")
    cv2.imwrite(reduced_image_path, resized_image)
    #print(f"Reduced-size image saved as {reduced_image_path}")


############################################################################################



def main_process(image_path_front, image_path_back):

    image_front = cv2.imread(image_path_front)

    # identify the QR code from the board
    barcode_content = read_barcode(image_front, qr_position if barcode_type == 'QR' else dm_position, barcode_type)
    date_str = extract_date_from_filename(image_path_front)

    # create a new directory ...
    sanitized_name = sanitize_filename(barcode_content)
    directory_name = os.path.join(os.getcwd(), "results", sanitized_name)

    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

    # save the QR code image to this directory ...
    save_barcode_image(image_front, qr_position if barcode_type == 'QR' else dm_position, barcode_type, directory_name)

    # Save reduced-size copies of the front and back images to pload to HWDB later:
    save_reduced_image(image_path_front, directory_name, "FEMB_FRONT")
    save_reduced_image(image_path_back, directory_name, "FEMB_BACK")

    # Front processing with front-specific OCR cleaning
    process_chips(image_path_front, chip_coordinates_front, directory_name, "front",barcode_content, date_str)

    # Back processing with back-specific OCR cleaning, same directory
    process_chips(image_path_back, chip_coordinates_back, directory_name, "back",barcode_content, date_str)

    # Post-processing OCR results:

    front_result_file = os.path.join(directory_name, "front_results.txt")
    back_result_file = os.path.join(directory_name, "back_results.txt")

    front_chip_count = count_chips(front_result_file)
    back_chip_count = count_chips(back_result_file)

    print(f"Number of chips processed on the front side: {front_chip_count}")
    print(f"Number of chips processed on the back side: {back_chip_count}")


# Configuration:

image_path_front = 'images/FEMB_FRONT_21--06-06-2024.png'
image_path_back = 'images/FEMB_BACK_21--06-06-2024.png'

#Let's crop and read some chips!
main_process(image_path_front, image_path_back)


print("FEMB Processing complete!")
