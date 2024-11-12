# DUNE-sn-rec
Implementation of text recognition techniques for use in DUNE Cold Electronics, to read out serial numbers from chips on our FEMBs (WIB's coming soon!). Chip location is purely based on position.

1) "read_sn_gpt_api.py" performs OCR based on an OpenAI GPT-4o API Key. When running "read_sn_gpt_api.py", please do so with "FEMB_FRONT_01--06-06-2024.png" and "FEMB_BACK_01--06-06-2024.png" images.
2) "crop_chips_FEMB.py" performs OCR based on OpenBMB MiniCPM-V-2_6 (https://huggingface.co/openbmb/MiniCPM-V-2_6). We will use this version for the SN recognition from now on (November 2024). 
3) "produce_json.py" loops over all OCR results in "results" to produce the corresponding .JSON files that will be used to create records in HWDB.
4) "upload_FEMBs.py" will send such records to HWDB using a set of CURL commands.
