# This program crops all chips from the input picture
# based on chips coordinates. Then it converts the images into a Black
# and White format to be analized for text recognition.

# Code reads EITHER QR codes or Data Matrices.
# Code is user-interactive, so the user can correct bad readings.
# Code processes both FRONT and BACK chip readings.

import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import os


# Import libraries for both QR and Data Matrix decoding
from pylibdmtx.pylibdmtx import decode as decode_dm
from qreader import QReader


# Configuration variable: 'QR' or 'DM' (Data Matrix)
barcode_type = 'QR'  # Change this to 'QR' if decoding QR codes

# Define the positions for QR and DM
qr_position = (1048, 1497, 142, 142)
dm_position = (1058, 1520, 152, 152)

# Define the coordinates and sizes for each chip
chip_coordinates_front = [#For chip's region of interest only:
    (976, 406, 282, 436),  # coordinates and size for COLDATA 1
    (2720, 404, 282, 436), # COLDATA 2
    (676,1148,162,281), #  ColdADC 1
    (1393,1147,162,281), #  ColdADC 2
    (2423,1148,162,281), #  ColdADC 3
    (3145,1154,162,281), #  ColdADC 4
    (673,1828,172,192), #  LArASIC 1
    (1389,1830,172,192), #LArASIC 2
    (2417,1833,172,192), #LArASIC 3
    (3139,1833,172,192), #LArASIC 4
]

chip_coordinates_back = [
    (677, 1154, 168, 284),  # coordinates and size for ColdADC 1
    (1389, 1151, 168, 284), # ColdADC 2
    (2419,1149,168,284), #  ColdADC 3
    (3140,1152,168,284), #  ColdADC 4
    (675,1836,180,192), #  LArASIC 1
    (1388,1833,180,192), #LArASIC 2
    (2415,1834,180,192), #LArASIC 3
    (3139,1832,180,192), #LArASIC 4
]

########################################################################

def clean_ocr_text_front(chip_index, ocr_text):
    lines = ocr_text.strip().split('\n')
    cleaned_lines = []
    corrections_detected = False

    # Determine the expected number of lines and the minimum characters per line
    if chip_index in [0, 1]:
        min_chars = 4
        expected_lines = 4
        valid_char_pattern = r'[^A-Z0-9.]'
    elif chip_index in [2, 3, 4, 5]:
        min_chars = 4
        expected_lines = 4
        valid_char_pattern = r'[^A-Za-z0-9.]'
    elif chip_index in [6, 7, 8, 9]:
        min_chars = 3
        expected_lines = 5
        valid_char_pattern = r'[^A-Za-z0-9/-_ ]'
    else:
        min_chars = 3
        expected_lines = 4  # Default case, can be adjusted
        valid_char_pattern = r'[^A-Za-z0-9./-_]'


    # Filter and clean lines based on the defined patterns and rules
    for line in lines:
        cleaned_line = re.sub(valid_char_pattern, '', line)

        # Specific fix for the last line of chips 6-9:
        # Replace '7' with '-' only if it appears at the fourth position
        if chip_index in [6, 7, 8, 9] and lines.index(line) == len(lines) - 1:
            if len(cleaned_line) > 3 and cleaned_line[3] == '7':  # Check if the fourth character is '7'
                cleaned_line = cleaned_line[:3] + '-' + cleaned_line[4:]  # Replace '7' with '-'


        if len(cleaned_line) >= min_chars:
            cleaned_lines.append(cleaned_line)
            if cleaned_line != line:
                corrections_detected = True
        else:
            corrections_detected = True  # Any line not meeting the criteria is flagged

    # Ensure the number of lines meets the expected count
    if len(cleaned_lines) != expected_lines:
        corrections_detected = True  # Not enough lines or too many lines also triggers a correction flag

    return '\n'.join(cleaned_lines), corrections_detected


####################################################################

def clean_ocr_text_back(chip_index, ocr_text):
    lines = ocr_text.strip().split('\n')
    cleaned_lines = []
    corrections_detected = False

    # Determine the expected number of lines and the minimum characters per line
    if  chip_index in [0, 1, 2, 3]:
        min_chars = 4
        expected_lines = 4
        valid_char_pattern = r'[^A-Za-z0-9.]'
    elif chip_index in [4, 5, 6, 7]:
        min_chars = 3
        expected_lines = 5
        valid_char_pattern = r'[^A-Za-z0-9/-_ ]'
    else:
        min_chars = 4
        expected_lines = 4  # Default case, can be adjusted
        valid_char_pattern = r'[^A-Za-z0-9./-_]'


    # Filter and clean lines based on the defined patterns and rules
    for line in lines:
        cleaned_line = re.sub(valid_char_pattern, '', line)

        # Specific fix for the last line of chips 4-7:
        # Replace '7' with '-' only if it appears at the fourth position
        if chip_index in [4, 5, 6, 7] and lines.index(line) == len(lines) - 1:
            if len(cleaned_line) > 3 and cleaned_line[3] == '1':  # Check if the fourth character is '1'
                cleaned_line = cleaned_line[:3] + '-' + cleaned_line[4:]  # Replace '7' with '-'


        if len(cleaned_line) >= min_chars:
            cleaned_lines.append(cleaned_line)
            if cleaned_line != line:
                corrections_detected = True
        else:
            corrections_detected = True  # Any line not meeting the criteria is flagged

    # Ensure the number of lines meets the expected count
    if len(cleaned_lines) != expected_lines:
        corrections_detected = True  # Not enough lines or too many lines also triggers a correction flag

    return '\n'.join(cleaned_lines), corrections_detected


####################################################################

def read_barcode(image, position, barcode_type):
    x, y, w, h = position
    cropped_image = image[y:y+h, x:x+w]

    if barcode_type == 'QR':
        qreader = QReader()
        try:
            data = qreader.detect_and_decode(image=cropped_image)
            if data:
                #return data
                # Extract the first element of the tuple if that's the expected format
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


####################################################################

def sanitize_filename(filename):
     # Replace slashes with underscores first to avoid directory paths
    filename = filename.replace('/', '_')
    # Replace any character that is not alphanumeric, an underscore, or a dot with an underscore
    invalid_chars = '<>:"/\\|?*'
    return "".join([c if c.isalnum() or c in ['_', '.'] else '_' for c in filename if c not in invalid_chars])



####################################################################

def process_chips(image_path, chip_coordinates, directory_name, file_suffix, clean_ocr_text):

    # Read the image:
    image = cv2.imread(image_path)

    # Convert the whole image to grayscale:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Creating the file name:
    #result_filename = os.path.join(directory_name, f"{directory_name}_{file_suffix}_results.txt")
    result_filename = os.path.join(directory_name, f"{file_suffix}_results.txt")



    all_ocr_results = []
    for i, (x, y, w, h) in enumerate(chip_coordinates):

        ## Crop the image using the coordinates and sizes
        chip_image = gray[y:y+h, x:x+w]

        ## Convert chip image to binary (black and white)
        ## Otsu's thresholding automatically calculates an optimal threshold value
        _, bw_chip = cv2.threshold(chip_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Rotate the chip:
        rotated_chip = cv2.rotate(bw_chip, cv2.ROTATE_90_CLOCKWISE)

        ## Use pytesseract to do OCR on the processed chip image
        text = pytesseract.image_to_string(rotated_chip, config='--psm 6')

        ## Clean and record OCR results
        clean_text, _ = clean_ocr_text(i, text)
        all_ocr_results.append((i, clean_text.split('\n')))

        ## Save the processed chip image to a file
        chip_image_path = os.path.join(directory_name, f'chip_{i}_{file_suffix}.png')
        cv2.imwrite(chip_image_path, rotated_chip)

    # Print all OCR results for user review
    print(f"\n\n\n\n\n------- OCR RESULTS FOR **{file_suffix.upper()}** OF THE BOARD -------\n")
    for chip_idx, lines in all_ocr_results:
        print(f"\n**** Chip {chip_idx}:")
        for line_idx, line in enumerate(lines):
            print(f"  * Line {line_idx + 1}: {line}")
    print("\n\n******************************************\n")
    print(F"OCR for **{file_suffix.upper()}** done. Please carefully inspect the results to determine if any of the chips needs corrections.\n")
    print("******************************************\n\n")


    print(F"* If NO corrections are needed, just type X and press ENTER to exit.\n* If corrections are needed, follow the instructions: \n ")

    print("     We need to save the chip numbers for correction.\n     Please input the chip number you want to correct and press ENTER. \n     -> FRONT side has chips 0-9. \n     -> BACK side has chips 0-7.\n     -> Type X and press ENTER when you are done entering chip numbers.\n ")


    # Ask user which chips to correct
    chips_to_correct = []
    while True:
        chip_index = input("Enter chip number to correct and then press ENTER. Type X and press ENTER to finish.\n ").strip().upper()
        if chip_index == 'X':
            break
        if chip_index.isdigit() and int(chip_index) in range(len(all_ocr_results)):
            chips_to_correct.append(int(chip_index))
        else:
            print("Invalid chip number. Please enter a valid number (0-9) or type X and then ENTER to finish.")

    # If corrections are needed
    if chips_to_correct:
        print("\n\n***** CORRECTING CHIPS *****\n")
        with open(result_filename, 'w', encoding='utf-8') as file:
            for chip_idx, lines in all_ocr_results:
                if chip_idx in chips_to_correct:
                    print(f"\n---OCR readings for Chip {chip_idx}:")
                    for line_idx, line in enumerate(lines):
                        print(f"  - Line {line_idx + 1}: {line}")
                        correction_query = input("Would you like to correct this line? (Y/N): ").strip().upper()
                        if correction_query == 'Y':
                            corrected_line = input("\nPlease write the correct reading and press ENTER when done: ").strip()
                            lines[line_idx] = corrected_line  # Replace the line with corrected input
                # Write results to file
                file.write(f"* Chip {chip_idx}:\n")
                for line in lines:
                    file.write(f"{line}\n")
                file.write("\n\n")
        print(f"\n\nAll {file_suffix.upper()} results have been saved successfully in {directory_name}.")

    else:
        with open(result_filename, 'w', encoding='utf-8') as file:
            for chip_idx, lines in all_ocr_results:
                file.write(f"* Chip {chip_idx} ({file_suffix}):\n")
                for line in lines:
                    file.write(f"{line}\n")
                file.write("\n\n")
        print(f"\n\nNo corrections made. As-is results file for {file_suffix.upper()} side has been saved. Exiting.")
    return

    # Print final corrected results
    print("\n\nFinal corrected OCR results:")
    for chip_idx, lines in all_ocr_results:
        print(f"\n****Final results for Chip {chip_idx} ({file_suffix}):")
        for line_idx, line in enumerate(lines):
            print(f"{line}")


####################################################################


def main_process(image_path_front, image_path_back):

    image_front = cv2.imread(image_path_front)

    barcode_content = read_barcode(image_front, qr_position if barcode_type == 'QR' else dm_position, barcode_type)

    sanitized_name = sanitize_filename(barcode_content)

    directory_name = os.path.join(os.getcwd(), sanitized_name)

    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

    # Front processing with front-specific OCR cleaning
    process_chips(image_path_front, chip_coordinates_front, directory_name, "front", clean_ocr_text_front)

    # Back processing with back-specific OCR cleaning, same directory
    process_chips(image_path_back, chip_coordinates_back, directory_name, "back", clean_ocr_text_back)

# Configuration:

image_path_front = '/home/karla/Documents/CE-QC/QC_camera/text_recognition/Images/FEMB_2PBars_10PL_88PF_1s.png'

image_path_back = '/home/karla/Documents/CE-QC/QC_camera/text_recognition/Images/FEMB_BACK_2PBars_10PL_88PF_1s.png'

#Let's crop and read some chips!
main_process(image_path_front, image_path_back)


