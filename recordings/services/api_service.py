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

def transcribe_audio(file_path):
    """Transcribe an MP3 file using OpenAI Whisper API."""
    try:
        openai.api_key = settings.OPENAI_API_KEY  
        with open(file_path, "rb") as audio_file:
            response = openai.Audio.transcribe("whisper-1", audio_file)
        
        transcript = response.get("text", "")
        print(f"Transcript for {file_path}: {transcript}")
        return transcript
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        raise

def analyze_feedback(transcript):
    """Analyze call transcript for feedback including sentiment analysis."""
    try:
        sentiment_prompt = f"""
        Analyze the sentiment of this call transcript. 
        Rate it as Positive, Neutral, or Negative and provide reasoning.
        
        Transcript:
        {transcript}
        """

        sentiment_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a sentiment analysis expert."},
                      {"role": "user", "content": sentiment_prompt}]
        )

        sentiment = sentiment_response["choices"][0]["message"]["content"]
        print(f"Sentiment Analysis: {sentiment}")

        feedback_prompt = f"""
        Provide detailed feedback on this customer service call transcript:
        - Identify areas where the agent could improve.
        - Was the agent polite, clear, and helpful?
        - Were the customer's concerns properly addressed?
        - Suggestions to improve customer experience.

        Transcript:
        {transcript}
        """

        feedback_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are an AI call feedback analyzer."},
                      {"role": "user", "content": feedback_prompt}]
        )

        feedback = feedback_response["choices"][0]["message"]["content"]
        print(f"Feedback: {feedback}")

        return f"Sentiment: {sentiment}\n\nFeedback:\n{feedback}"
    except Exception as e:
        print(f"Error analyzing feedback: {e}")
        raise
import requests
from django.conf import settings

def get_storage_id():
    """Retrieve Bitrix24 Storage ID"""
    storage_url = f"{settings.BITRIX24_API_URL}/disk.storage.get.json"
    response = requests.get(storage_url, params={"id": 1})  # Default storage ID is usually 1
    response.raise_for_status()
    
    storage_id = response.json().get("result", {}).get("ID")
    print(f"✅ Retrieved Storage ID: {storage_id}")  # Debugging output
    
    return storage_id



def get_folder_id():
    """Retrieves a valid folder ID where MP3 files should be uploaded."""
    try:
        response = requests.get(f"{settings.BITRIX24_API_URL}/disk.storage.get.json", params={"id": 1})  # Assuming storage ID is 1
        response.raise_for_status()
        result = response.json()
        
        if "result" in result and "ID" in result["result"]:
            folder_id = result["result"]["ID"]
            print(f"✅ Folder ID retrieved: {folder_id}")
            return folder_id
        else:
            print("❌ Failed to retrieve folder ID:", result)
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error retrieving folder ID: {e}")
        return None

def upload_mp3(mp3_path):
    """Uploads an MP3 file to Bitrix24 Disk folder."""
    try:
        folder_id = get_folder_id()
        if not folder_id:
            print("❌ No valid folder found for uploading.")
            return None

        # 1️⃣ Request an Upload URL from Bitrix24
        upload_url_request = f"{settings.BITRIX24_API_URL}/disk.folder.uploadfile.json"
        params = {"id": folder_id}  # Uploading to a folder
        response = requests.post(upload_url_request, json=params)
        response.raise_for_status()

        upload_info = response.json()
        if "result" not in upload_info or "uploadUrl" not in upload_info["result"]:
            print("❌ Failed to get upload URL:", upload_info)
            return None

        upload_url = upload_info["result"]["uploadUrl"]
        print(f"✅ Upload URL received: {upload_url}")

        # 2️⃣ Upload the MP3 File
        with open(mp3_path, "rb") as file_data:
            files = {"file": ("recording.mp3", file_data, "audio/mpeg")}
            upload_response = requests.post(upload_url, files=files)
            upload_response.raise_for_status()

            upload_result = upload_response.json()
            if "result" not in upload_result or "ID" not in upload_result["result"]:
                print("❌ File upload failed:", upload_result)
                return None

            file_id = upload_result["result"]["ID"]
            print(f"✅ File uploaded successfully! File ID: {file_id}")
            return file_id

    except requests.exceptions.RequestException as e:
        print(f"❌ Error uploading file: {e}")
        return None
    
def attach_file_to_lead(lead_id, file_id):
    """Attach uploaded file to a lead"""
    update_url = f"{settings.BITRIX24_API_URL}/crm.lead.update.json"
    params = {
        "id": lead_id,
        "fields": {
            "UF_CRM_123456": file_id  # Replace with actual custom field ID in Bitrix24
        }
    }

    response = requests.post(update_url, json=params)
    response.raise_for_status()
    return response.json()

def upload_mp3_and_feedback_to_bitrix24(mp3_path, phone_number): #, feedback):
    """Find lead, upload MP3, and attach to lead in Bitrix24"""
    try:
        # 1️⃣ Search for Lead by Phone Number
        search_url = f"{settings.BITRIX24_API_URL}/crm.lead.list.json"
        search_params = {"filter": {"PHONE": phone_number}, "select": ["ID"]}

        search_response = requests.post(search_url, json=search_params)
        search_response.raise_for_status()
        
        leads = search_response.json().get("result", [])
        if not leads:
            print(f"❌ No lead found for phone number: {phone_number}")
            return
        
        lead_id = leads[0]["ID"]
        print(f"✅ Lead found: {lead_id}")

        # 2️⃣ Upload MP3 File
        file_id = upload_mp3(mp3_path)
        if not file_id:
            print("❌ MP3 Upload Failed")
            return

        # 3️⃣ Attach File to Lead
        attach_file_to_lead(lead_id, file_id)
        print(f"✅ Successfully attached MP3 file to lead {lead_id}")

        # 4️⃣ Add AI Feedback as a Comment
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
        # print(f"✅ Successfully uploaded feedback to lead {lead_id}")

    except requests.exceptions.RequestException as e:
        print("❌ Error uploading data to Bitrix24:", e)
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

                rename_audio_files(extract_path)  # Rename files before processing

                for file in os.listdir(extract_path):
                    if file.endswith(".mp3") or file.endswith(".wav"):
                        file_path = os.path.join(extract_path, file)
                        # transcript = transcribe_audio(file_path)
                        # feedback = analyze_feedback(transcript)
                        phone_number_from_filename = file.split(".")[0]  # Extract phone number from filename
                        upload_mp3_and_feedback_to_bitrix24(file_path, phone_number_from_filename)#, feedback)

        return {"message": "Processing complete"}
    except Exception as e:
        print(f"Error: {e}")
        raise