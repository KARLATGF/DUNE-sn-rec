# This program iterates over all FEMB directories
# to find each board's .JSON and .png files to upload them to the HWDB.

# These FEMB pictures and OCR results come from the QC Camera Setup at BNL and its
# MiniCPM-based Serial Number Recognition algorithm (crop_chips_FEMB.py)

# Don't forget to define CURL as: alias CURL='curl --cert Output.pem --pass <phrase>'

import os
import json
import subprocess

# Base directory containing the variable directories (like 00003)
base_dir = '/results'

# URL for the API
post_url = 'https://dbwebapi2.fnal.gov:8443/cdbdev/api/component-types/D08100400001/components'
image_url_template = 'https://dbwebapi2.fnal.gov:8443/cdbdev/api/components/{}/images'

# Iterate over each directory in the base directory
for dir_name in os.listdir(base_dir):
    dir_path = os.path.join(base_dir, dir_name)

    # Only proceed if it's a directory
    if os.path.isdir(dir_path):
        json_file = os.path.join(dir_path, f"{dir_name}.JSON")
        front_image = os.path.join(dir_path, "FEMB_FRONT_reduced.png")
        back_image = os.path.join(dir_path, "FEMB_BACK_reduced.png")

        # Ensure JSON file and both images exist
        if os.path.exists(json_file) and os.path.exists(front_image) and os.path.exists(back_image):
            # First CURL command to send JSON data
            result = subprocess.run(
                ['CURL', '-H', 'Content-Type: application/json', '-X', 'POST', '-d', f'@{json_file}', post_url],
                capture_output=True, text=True
            )

            # Parse the output to get the part_id
            response = json.loads(result.stdout)
            part_id = response.get("part_id")

            if part_id:
                # URLs for uploading images with the obtained part_id
                image_url = image_url_template.format(part_id)

                # CURL command for the front image
                subprocess.run(
                    ['CURL', '-H', 'comments=Front of the FEMB', '-F', f'image=@{front_image}', image_url]
                )

                # CURL command for the back image
                subprocess.run(
                    ['CURL', '-H', 'comments=Back of the FEMB', '-F', f'image=@{back_image}', image_url]
                )
            else:
                print(f"Failed to retrieve part_id for {json_file}")
        else:
            print(f"Required files missing in {dir_path}")
