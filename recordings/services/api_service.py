import requests
import base64
import time
import logging
import os
import zipfile
import openai
import re
from django.conf import settings

# Set up logging
logger = logging.getLogger(__name__)

EXTRACTED_FILES_DIR = "extracted_files"  # Folder where extracted files should be stored

def get_access_token():
    """Fetch an access token from 8x8 API using client credentials."""
    try:
        url = "https://api.8x8.com/oauth/v2/token"
        credentials = f"{settings.CLIENT_ID}:{settings.SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {"grant_type": "client_credentials"}
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()

        access_token = response.json().get("access_token")
        print(f"Access Token: {access_token}")  # Print access token for debugging
        return access_token
    except Exception as e:
        logger.error(f"Error fetching access token: {e}", exc_info=True)
        raise

def get_my_regions(token):
    """Retrieve available regions for the 8x8 account."""
    try:
        url = f"https://api.8x8.com/storage/{settings.REGION}/v3/regions"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        regions = response.json()
        print(f"Regions: {regions}")  # Print regions for debugging
        return regions
    except Exception as e:
        logger.error(f"Error fetching regions: {e}", exc_info=True)
        raise

def find_objects(token, region, filter_query):
    """Find objects in a specific region."""
    try:
        url = f"https://api.8x8.com/storage/{region}/v3/objects"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        params = {"filter": filter_query}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        print(f"Objects Found: {response.json()}")  # Print found objects for debugging
        return response.json()
    except Exception as e:
        logger.error(f"Error finding objects: {e}", exc_info=True)
        raise

def create_bulk_download(token, region, object_ids):
    """Create a bulk download job."""
    try:
        url = f"https://api.8x8.com/storage/{region}/v3/bulk/download/start"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        response = requests.post(url, headers=headers, json=object_ids)
        response.raise_for_status()

        zip_name = response.json().get("zipName")
        print(f"Bulk Download Zip Name: {zip_name}")  # Print ZIP name for debugging
        return response.json()
    except Exception as e:
        logger.error(f"Error creating bulk download: {e}", exc_info=True)
        raise

def check_download_status(token, region, zip_name):
    """Check the status of a bulk download job."""
    try:
        url = f"https://api.8x8.com/storage/{region}/v3/bulk/download/status/{zip_name}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        print(f"Download Status: {response.json()}")  # Print download status for debugging
        return response.json()
    except Exception as e:
        logger.error(f"Error checking download status: {e}", exc_info=True)
        raise

def download_zip_file(token, region, zip_name):
    """Download a completed bulk download ZIP file and save it."""
    try:
        url = f"https://api.8x8.com/storage/{region}/v3/bulk/download/{zip_name}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()

        zip_path = os.path.join(os.getcwd(), zip_name)

        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Downloaded Zip File: {zip_path}")  # Print zip file path for debugging
        return zip_path
    except Exception as e:
        logger.error(f"Error downloading zip file: {e}", exc_info=True)
        raise

def extract_zip_file(zip_path):
    """Extract the downloaded ZIP file and rename MP3 and WAV files."""
    try:
        zip_name = os.path.splitext(os.path.basename(zip_path))[0]
        extract_path = os.path.join(EXTRACTED_FILES_DIR, zip_name)

        os.makedirs(extract_path, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)

        rename_audio_files(extract_path)  # Call function to rename files

        print(f"Extracted Files Path: {extract_path}")  # Print extracted files path for debugging
        return extract_path
    except Exception as e:
        logger.error(f"Error extracting zip file: {e}", exc_info=True)
        raise

def rename_audio_files(extract_path):
    """Rename MP3 and WAV files to keep only the phone number."""
    for file in os.listdir(extract_path):
        if file.endswith(".mp3") or file.endswith(".wav"):
            old_path = os.path.join(extract_path, file)

            # Extract phone number using regex pattern
            match = re.search(r"\+(\d+)", file)
            if match:
                phone_number = f"+{match.group(1)}{os.path.splitext(file)[1]}"  # Keep the file extension (.mp3 or .wav)
                new_path = os.path.join(extract_path, phone_number)
                
                os.rename(old_path, new_path)
                print(f"Renamed: {file} -> {phone_number}")  # Print renamed file for debugging

# def transcribe_audio(file_path):
#     """Transcribe an MP3 file using OpenAI Whisper API."""
#     try:
#         openai.api_key = settings.OPENAI_API_KEY  
#         with open(file_path, "rb") as audio_file:
#             response = openai.Audio.transcribe("whisper-1", audio_file)
        
#         transcript = response.get("text", "")
#         print(f"Transcript for {file_path}: {transcript}")  # Print transcript for debugging
#         return transcript
#     except Exception as e:
#         logger.error(f"Error transcribing audio: {e}", exc_info=True)
#         raise

# def analyze_feedback(transcript):
#     """Analyze call transcript and provide AI-driven feedback."""
#     try:
#         prompt = f"""
#         Analyze the following customer service call transcript and provide feedback:
#         - Identify areas where the agent could improve.
#         - Was the agent polite, clear, and helpful?
#         - Were the customer's concerns properly addressed?
#         - Any suggestions to improve customer comfort?

#         Transcript:
#         {transcript}
#         """
#         response = openai.ChatCompletion.create(
#             model="gpt-4",
#             messages=[{"role": "system", "content": "You are an AI call feedback analyzer."},
#                       {"role": "user", "content": prompt}]
#         )
#         feedback = response["choices"][0]["message"]["content"]
#         print(f"Feedback: {feedback}")  # Print feedback for debugging
#         return feedback
#     except Exception as e:
#         logger.error(f"Error analyzing feedback: {e}", exc_info=True)
#         raise
import requests

def upload_mp3_and_feedback_to_bitrix24(mp3_path, phone_number, feedback):
    """Upload the MP3 file and feedback to Bitrix24 lead based on phone number."""
    try:
        # Extract last 4 digits from phone number
        last_four_digits = phone_number[-4:]

        # Search for leads using the last 4 digits
        search_url = f"{settings.BITRIX24_API_URL}/crm.lead.list.json"
        search_params = {"filter[PHONE]": last_four_digits}
        search_response = requests.get(search_url, params=search_params)
        search_response.raise_for_status()
        
        leads = search_response.json().get("result", [])
        if not leads:
            print(f"No lead found for phone number ending with {last_four_digits}")
            return

        lead_id = leads[0]["ID"]
        print(f"Lead ID found: {lead_id}")

        #  Upload MP3 File to Bitrix24
        upload_url = f"{settings.BITRIX24_API_URL}/disk.storage.uploadfile.json"
        with open(mp3_path, "rb") as file_data:
            files = {"file": file_data}
            response = requests.post(upload_url, files=files)
            response.raise_for_status()
            file_url = response.json().get('result', {}).get('file', {}).get('url', '')
            print(f"File uploaded successfully. File URL: {file_url}")

        # Attach the file to the lead using the file URL
        update_url = f"{settings.BITRIX24_API_URL}/crm.lead.update.json"
        data = {
            "ID": lead_id,
            "UF_CRM_123456": file_url  # Use the correct custom field ID to store the file URL
        }
        update_response = requests.post(update_url, data=data)
        update_response.raise_for_status()
        print(f"Successfully updated lead {lead_id} with MP3 file")

        # Add AI Feedback as a Comment
        # comment_url = f"{settings.BITRIX24_API_URL}/crm.timeline.comment.add.json"
        # comment_data = {
        #     "fields": {
        #         "ENTITY_ID": lead_id,
        #         "ENTITY_TYPE": "lead",
        #         "COMMENT": feedback
        #     }
        # }
        # comment_response = requests.post(comment_url, json=comment_data)
        # comment_response.raise_for_status()
        # print(f"Successfully uploaded feedback to lead {lead_id}")

    except Exception as e:
        print(f"Error uploading data to Bitrix24: {e}")
        raise

def fetch_and_download_call_recordings(object_id=None):
    """Fetch, download, extract, transcribe, and analyze call recordings."""
    try:
        token = get_access_token()
        regions = get_my_regions(token)

        for region in regions:
            filter_query = f"type==callcenterrecording,objectState==AVAILABLE" if not object_id else f"id=={object_id}"
            response = find_objects(token, region, filter_query)

            content = response.get("content", [])
            if content:
                object_ids = [obj["id"] for obj in content]
                bulk_download_response = create_bulk_download(token, region, object_ids)
                zip_name = bulk_download_response.get("zipName")

                for _ in range(20):
                    if check_download_status(token, region, zip_name).get("status") == "DONE":
                        break
                    time.sleep(15)

                zip_path = download_zip_file(token, region, zip_name)
                extract_path = extract_zip_file(zip_path)

                for file in os.listdir(extract_path):
                    if file.endswith(".mp3") or file.endswith(".wav"):
                        file_path = os.path.join(extract_path, file)
                        # transcript = transcribe_audio(file_path)
                        # feedback = analyze_feedback(transcript)
                        # print(f"Feedback for {file}: \n{feedback}")

                        # # Upload MP3 and feedback to Bitrix24
                        phone_number_from_filename = file.split(".")[0]  # Extract phone number from filename
                        upload_mp3_and_feedback_to_bitrix24(file_path, phone_number_from_filename) #feedback)

        return {"message": "Processing complete"}
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise
