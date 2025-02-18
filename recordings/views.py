from django.http import JsonResponse
import logging
from .services.api_service import fetch_and_download_call_recordings

# Configure logging
logger = logging.getLogger(__name__)

def list_recordings(request):
    """
    Fetch and return all call recordings.
    """
    try:
        # Fetch call recordings (without specific object_id)
        recordings = fetch_and_download_call_recordings()
        
        if not recordings:
            return JsonResponse({"success": True, "message": "No recordings found"}, status=200)

        return JsonResponse({"success": True, "data": recordings}, status=200)
    except Exception as e:
        logger.error(f"Error fetching recordings: {str(e)}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)

def get_recording(request, object_id):
    """
    Fetch and return a specific call recording's metadata.
    """
    try:
        if not object_id:
            return JsonResponse({"success": False, "error": "Missing object_id"}, status=400)

        # Pass object_id to fetch a specific recording
        recording = fetch_and_download_call_recordings(object_id)

        if not recording:
            return JsonResponse({"success": False, "error": "Recording not found"}, status=404)

        return JsonResponse({"success": True, "data": recording}, status=200)
    except Exception as e:
        logger.error(f"Error fetching recording {object_id}: {str(e)}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
