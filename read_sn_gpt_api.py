# This program crops all chips from the input picture
# based on chips coordinates. Then it converts the image into a base64 string
# for ChatGPT to do OCR.

# Code reads EITHER QR codes or Data Matrices.
# Code processes both FRONT and BACK chip readings.

import cv2
import numpy as np
from PIL import Image
import re
import os

from openai import OpenAI
#import openai
import base64
import io

from pylibdmtx.pylibdmtx import decode as decode_dm
from qreader import QReader

# Open the image file and encode it as a base64 string
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")



# Configuration variable: 'QR' or 'DM' (Data Matrix)
barcode_type = 'DM'


# Define the positions for QR and DM
qr_position = (1048, 1497, 142, 142)
#dm_position = (1050, 1516, 164, 160) # pictures 01-08
dm_position = (1056, 1510, 164, 172) # pictires 09-25

# Define the coordinates and sizes for each chip



##-------- Positions for pictures 09-25 ----------##
chip_coordinates_front = [#For chip's region of interest only:
    (963, 400, 300, 488),  # coordinates and size for COLDATA 1
    (2695, 396, 300, 488), # COLDATA 2
    (663,1160,196,292), #  ColdADC 1
    (1372,1155,196,292), #  ColdADC 2
    (2394,1157,196,292), #  ColdADC 3
    (3106,1157,196,292), #  ColdADC 4
    (669,1805,196,260), #  LArASIC 1
    (1377,1805,196,260), #LArASIC 2
    (2394,1805,196,260), #LArASIC 3
    (3111,1805,196,260), #LArASIC 4
]

chip_coordinates_back = [
    (669, 1165, 196, 292),  # coordinates and size for ColdADC 1
    (1377, 1158, 196, 292), # ColdADC 2
    (2398,1158,196,292), #  ColdADC 3
    (3105,1154,196,292), #  ColdADC 4
    (677,1800,196,260), #  LArASIC 1
    (1385,1816,196,260), #LArASIC 2
    (2401,1807,196,260), #LArASIC 3
    (3114,1807,196,260), #LArASIC 4
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

    ## Set the API key and model name
    MODEL="gpt-4o"
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "<your api key>"))
    

    file = open(result_filename, 'w', encoding='utf-8')

    file.write(f"{barcode_content}\n\n{date_str}\n\n")

    all_ocr_results = []
    for i, (x, y, w, h) in enumerate(chip_coordinates):

        ## Crop the image
        chip_image = image[y:y+h, x:x+w]

        print(f'Processing {i}th chip')

        # Rotate the chip:
        rotated_chip = cv2.rotate(chip_image, cv2.ROTATE_90_CLOCKWISE)

        ## Save the processed chip image to a file
        chip_image_path = os.path.join(directory_name, f'{file_suffix}_chip_{i}.png')
        cv2.imwrite(chip_image_path, rotated_chip)

        image_cv = cv2.imread(chip_image_path, cv2.IMREAD_ANYDEPTH)


        # Resize the image to make the text more clear
        #resized_image = cv2.resize(image_cv, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        resized_image = cv2.resize(image_cv, (100, 100))  # Resize to a smaller size if possible


        pil_image = Image.fromarray(resized_image)
        buffered = io.BytesIO()
        pil_image.save(buffered, format="PNG", optimize=True, quality=75)  # Adjust quality for compression
        processed_base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')


        #base64_image = encode_image(IMAGE_PATH)

        file.write(f"* Chip {i} ({file_suffix}):\n")

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                        {"role": "system", "content": "You are a helpful assistant. Help me with an Optical Character Recognition (OCR) task."},
                        {"role": "user", "content": [
                        {"type": "text", "text": "Can you provide a manual transcription of the visible text from this image?"},
                        {"type": "image_url", "image_url": {
#                       "url": f"data:image/png;base64,{base64_image}"}
                        "url": f"data:image/png;base64,{processed_base64_image}"}
                        }
                        ]}
                    ],
            temperature=0.0,
        )


        file.write(response.choices[0].message.content)


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

def main_process(image_path_front, image_path_back):

    image_front = cv2.imread(image_path_front)

    # identify the QR code from the board
    barcode_content = read_barcode(image_front, qr_position if barcode_type == 'QR' else dm_position, barcode_type)
    date_str = extract_date_from_filename(image_path_front)

    # create a new directory ...
    sanitized_name = sanitize_filename(barcode_content)
    directory_name = os.path.join(os.getcwd(), sanitized_name)

    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

    # save the QR code image to this directory ...
    save_barcode_image(image_front, qr_position if barcode_type == 'QR' else dm_position, barcode_type, directory_name)

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

image_path_front = '/home/karla/Documents/CE-QC/QC_camera/text_recognition/Images/femb_batch_5_new_boards/FEMB_FRONT_01--06-06-2024.png'
image_path_back = '/home/karla/Documents/CE-QC/QC_camera/text_recognition/Images/femb_batch_5_new_boards/FEMB_BACK_01--06-06-2024.png'

#Let's crop and read some chips!
main_process(image_path_front, image_path_back)
