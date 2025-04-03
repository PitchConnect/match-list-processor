import json
import os
import requests
import abc
import time
import logging
import create_group_description

DATA_FOLDER = "/data"
PREVIOUS_MATCHES_JSON_FILE = os.path.join(DATA_FOLDER, "previous_matches.json")  # File to store RAW JSON


class ApiClientInterface(abc.ABC):
    """
    Abstract interface for API clients.
    """

    @abc.abstractmethod
    def fetch_matches_list(self):
        """
        Fetches a list of matches.
        """
        pass


class DockerNetworkApiClient(ApiClientInterface):
    """
    API client implementation that communicates with the fogis-api-client-service
    container over the Docker network using HTTP.
    """

    def fetch_matches_list(self):
        """
        Fetches the list of matches from the API client service.
        """
        url = 'http://fogis-api-client-service:8080/matches'
        logging.info(f"Fetching matches list from: {url}...")
        try:
            result = requests.get(url)
            result.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            logging.info(f"API Client Container Response (Matches List Test - Status Code: {result.status_code})")
            response_data = result.json()  # Parse JSON here
            logging.debug(f"API Response Type for matches list: {type(response_data)}")  # Log response type
            return response_data  # Return parsed JSON (list or dict)
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching matches list from {url}: {e}")
            return []


def load_previous_matches_raw_json():
    """
    Loads the previous match list from JSON file as RAW JSON STRING.
    Returns None if file not found or error, indicating fresh start.
    """
    try:
        with open(PREVIOUS_MATCHES_JSON_FILE, 'r', encoding='utf-8') as f:
            raw_json_string = f.read()  # Load as RAW JSON STRING
            logging.debug(f"Loaded previous matches JSON from {PREVIOUS_MATCHES_JSON_FILE} (raw string).")
            return raw_json_string  # Return RAW JSON STRING
    except FileNotFoundError:
        logging.info(f"Previous matches JSON file not found at {PREVIOUS_MATCHES_JSON_FILE}. Starting fresh.")
        return None  # Indicate no previous data
    except Exception as e:
        logging.error(f"Error loading previous matches JSON from {PREVIOUS_MATCHES_JSON_FILE}: {e}. Starting fresh.")
        return None  # Indicate no previous data


def parse_raw_json_to_list(raw_json_string):
    """
    Parses the raw JSON string into a Python list of matches.
    Returns an empty list if parsing fails or raw_json_string is None.
    """
    if not raw_json_string:
        return []  # Return empty list if no raw JSON
    try:
        previous_matches_list = json.loads(raw_json_string)  # Parse JSON string to list
        logging.debug(
            f"Parsed raw JSON to list of matches (count: {len(previous_matches_list)}) - first 3 match IDs: {[match['matchid'] for match in previous_matches_list[:3]] if previous_matches_list else []}")  # Log first 3 match IDs
        return previous_matches_list  # Return LIST of matches
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON string: {e}. Starting fresh with empty data.")
        return []  # Return empty list on parsing error


def save_current_matches_raw_json(raw_json_string):
    """
    Saves the current match list as RAW JSON STRING to file.
    """
    os.makedirs(DATA_FOLDER, exist_ok=True)
    try:
        logging.debug(
            f"Saving current matches as raw JSON string (first 50 chars): {raw_json_string[:50]}...")  # Log first part of JSON string
        with open(PREVIOUS_MATCHES_JSON_FILE, 'w', encoding='utf-8') as f:
            f.write(raw_json_string)  # Save the RAW JSON STRING
        logging.info(f"Current matches saved to {PREVIOUS_MATCHES_JSON_FILE} as raw JSON.")
    except Exception as e:
        logging.error(f"Error saving current matches as raw JSON to {PREVIOUS_MATCHES_JSON_FILE}: {e}")


def extract_referee_names(match_details):
    """
    Extracts a list of referee names from match details.
    """
    referee_names = []
    domaruppdraglista = match_details.get('domaruppdraglista', [])
    for uppdrag in domaruppdraglista:
        referee_name = uppdrag.get('personnamn')
        if referee_name:
            referee_names.append(referee_name)
    return referee_names


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Starting process_matches.py...")

    # Load previous matches RAW JSON from volume
    raw_previous_matches_json = load_previous_matches_raw_json()

    # Parse raw JSON to list (or get empty list if no previous data or parsing error)
    previous_matches_list = parse_raw_json_to_list(raw_previous_matches_json)
    logging.info(f"Loaded and parsed previous matches data: {len(previous_matches_list)} matches (from raw JSON).")

    # Instantiate API client and fetch current matches list
    api_client = DockerNetworkApiClient()
    logging.info("\n--- Fetching Current Matches List ---")
    current_matches_list_response = api_client.fetch_matches_list()  # Get response (parsed JSON - list or dict)
    logging.debug(
        f"Type of current_matches_list_response from API Client: {type(current_matches_list_response)}")  # Log the type of the response
    current_matches_list_raw_json_string = json.dumps(current_matches_list_response,
                                                      ensure_ascii=False)  # Convert to JSON string for saving
    current_matches_list = current_matches_list_response  # Use the parsed JSON directly as list

    logging.info(f"Fetched current matches list: {len(current_matches_list)} matches.")

    if not current_matches_list:
        logging.warning(
            "Could not fetch current matches list from API or unexpected response. Exiting change detection.")
        logging.info("process_matches.py execution finished prematurely due to API fetch failure.")
        logging.info("\n--- Container will now stay running indefinitely (for testing) ---")
        while True:
            time.sleep(60)
        exit()

    # --- Convert BOTH previous and current match lists to dictionaries for comparison ---
    previous_matches = {int(match['matchid']): match for match in previous_matches_list}
    current_matches = {int(match['matchid']): match for match in current_matches_list}
    logging.debug(f"Keys of current_matches dictionary: {list(current_matches.keys())}")
    logging.debug(f"Keys of previous_matches dictionary: {list(previous_matches.keys())}")

    logging.info("\n--- Starting Match Comparison and Change Detection ---")

    previous_match_ids = set(previous_matches.keys())
    current_match_ids = set(current_matches.keys())

    new_match_ids = current_match_ids - previous_match_ids
    removed_match_ids = previous_match_ids - current_match_ids
    common_match_ids = current_match_ids.intersection(previous_match_ids)

    if new_match_ids:
        logging.info(f"Detected NEW matches: {len(new_match_ids)}")
        for match_id in new_match_ids:
            new_match = current_matches[match_id]
            logging.info(
                f"  - New Match ID: {match_id}, Teams: {new_match['lag1namn']} vs {new_match['lag2namn']}, Date: {new_match['speldatum']}, Time: {new_match['avsparkstid']}")

            # --- Check number of referees. Skip WhatsApp actions if only one or zero referees ---
            domaruppdraglista = new_match.get('domaruppdraglista', [])
            if len(domaruppdraglista) < 2:
                logging.info(f"  Match ID {match_id} has less than 2 referees. Skipping WhatsApp group creation.")
                continue  # Skip to the next match

            # --- Generate WhatsApp group description ---
            description_text = create_group_description.generate_whatsapp_description(new_match)
            logging.info(f"  Generated WhatsApp group description:\n{description_text}")

            # --- Save description to temporary file ---
            description_filename = f"whatsapp_group_description_match_{match_id}.txt"
            temp_description_filepath = f"/tmp/{description_filename}"
            try:
                with open(temp_description_filepath, 'w', encoding='utf-8') as description_file:
                    description_file.write(description_text)
                logging.info(f"  Description text saved to temporary file: {temp_description_filepath}")
            except Exception as save_error:
                logging.error(f"  Error saving description text to {temp_description_filepath}: {save_error}")
                logging.debug(f"  File saving FAILED with error for: {temp_description_filepath}")
                continue  # Skip to next match if we can't save the description file

            # --- Extract Referee Names ---
            referee_names_list = extract_referee_names(new_match)
            logging.info(f"  Extracted referee names: {referee_names_list}")

            # --- Format match date for folder structure ---
            match_date_formatted = new_match.get('speldatum', '')  # Keep original format with hyphens (YYYY-MM-DD)
            safe_label = f"{match_id}_{new_match['lag1namn'].replace(' ', '_')}_{new_match['lag2namn'].replace(' ', '_')}"
            logging.info(f"  Formatted match date: {match_date_formatted}, Safe label: {safe_label}")

            avatar_service_url = "http://whatsapp-avatar-service:5002/create_avatar"  # <--- Use your service URL
            team_ids_payload = {
                "team1_id": str(new_match.get('lag1foreningid')),  # Extract team 1 ID, convert to string
                "team2_id": str(new_match.get('lag2foreningid'))  # Extract team 2 ID, convert to string
            }
            logging.info(f"Calling whatsapp-avatar-service to create avatar for match {match_id}...")
            try:
                avatar_response = requests.post(avatar_service_url, json=team_ids_payload,
                                                stream=True)  # stream=True for image data
                avatar_response.raise_for_status()  # Raise HTTPError for bad responses

                if avatar_response.headers['Content-Type'] == 'image/png':  # Check content type is image/png
                    avatar_image_data = avatar_response.content  # Get image binary data
                    logging.debug(f"  Avatar image data length: {len(avatar_image_data)} bytes")
                    avatar_filename = f"whatsapp_group_avatar_match_{match_id}.png"  # Consistent filename
                    temp_avatar_filepath = f"/tmp/{avatar_filename}"  # Temporary file path in /tmp

                    try:
                        with open(temp_avatar_filepath, 'wb') as avatar_file:
                            avatar_file.write(avatar_image_data)
                        logging.info(f"  Avatar image downloaded and saved to: {temp_avatar_filepath}")
                        logging.debug(f"  File saving completed WITHOUT errors for: {temp_avatar_filepath}")
                    except Exception as save_error:
                        logging.error(f"  Error saving avatar image to {temp_avatar_filepath}: {save_error}")
                        logging.debug(f"  File saving FAILED with error for: {temp_avatar_filepath}")

                    logging.debug(f"  Contents of /tmp folder AFTER avatar save attempt: {os.listdir('/tmp')}")

                    # --- Google Drive Folder Path ---
                    gdrive_folder_path = f"WhatsApp_Group_Assets/{match_date_formatted}/Match_{safe_label}"  # Google Drive folder path

                    # --- Test connection to Google Drive service before attempting operations ---
                    gdrive_service_base_url = "http://google-drive-service:5000"  # Use internal port 5000 for container-to-container communication
                    logging.info(f"Testing connection to Google Drive service at {gdrive_service_base_url}...")
                    try:
                        # Try a simple GET request to check if service is reachable
                        test_response = requests.get(f"{gdrive_service_base_url}/health", timeout=5)
                        logging.info(f"Google Drive service connection test result: Status {test_response.status_code}")
                    except requests.exceptions.RequestException as e:
                        logging.error(f"Google Drive service connection test failed: {e}")
                        logging.warning("Will skip Google Drive operations due to connection issues")
                        # Continue with other processing without Google Drive operations
                        continue  # Skip to next match

                    # --- Google Drive Upload - Description Text File ---
                    gdrive_upload_url = f"{gdrive_service_base_url}/upload_file"  # Google Drive Service URL - upload file endpoint
                    description_filename_gd = f"whatsapp_group_description_match_{match_id}.txt"  # Filename in Google Drive
                    temp_description_filepath = f"/tmp/{description_filename_gd}"  # Temp file path (already created)

                    # Note: Removed the folder creation code block as folders are created automatically when needed

                    logging.info(
                        f"Uploading WhatsApp group description to Google Drive folder: '{gdrive_folder_path}'...")
                    try:
                        with open(temp_description_filepath,
                                  'rb') as description_file_gd:  # Open temp description file
                            files_gd = {'file': (
                            description_filename_gd, description_file_gd, 'text/plain')}  # File info for upload
                            data_gd = {'folder_path': gdrive_folder_path}  # Folder path data
                            gd_description_response = requests.post(gdrive_upload_url, files=files_gd,
                                                                    data=data_gd)  # HTTP POST to google-drive-service
                            gd_description_response.raise_for_status()  # Raise HTTPError for bad responses
                            gd_description_upload_result = gd_description_response.json()  # Parse JSON response
                            if gd_description_upload_result.get('status') == 'success':
                                description_file_url = gd_description_upload_result.get('file_url')
                                logging.info(f"  Description uploaded to Google Drive. URL: {description_file_url}")
                            else:
                                logging.error(
                                    f"  Google Drive upload FAILED for description. Status: {gd_description_upload_result.get('status')}, Message: {gd_description_upload_result.get('message')}")
                    except requests.exceptions.RequestException as e_gd_upload_desc:
                        logging.error(f"  Request error uploading description to Google Drive: {e_gd_upload_desc}")

                    # --- Google Drive Upload - Avatar Image File ---
                    avatar_filename_gd = avatar_filename  # Use the same filename as before
                    temp_avatar_filepath = f"/tmp/{avatar_filename_gd}"  # Same path as before

                    logging.info(
                        f"Uploading WhatsApp group avatar to Google Drive folder: '{gdrive_folder_path}'...")
                    try:
                        with open(temp_avatar_filepath, 'rb') as avatar_file_gd:  # Open temp avatar image file
                            files_gd_avatar = {
                                'file': (avatar_filename_gd, avatar_file_gd, 'image/png')}  # File info for upload
                            data_gd_avatar = {'folder_path': gdrive_folder_path}  # Folder path data
                            gd_avatar_response = requests.post(gdrive_upload_url, files=files_gd_avatar,
                                                               data=data_gd_avatar)  # HTTP POST to google-drive-service
                            gd_avatar_response.raise_for_status()  # Raise HTTPError for bad responses
                            gd_avatar_upload_result = gd_avatar_response.json()  # Parse JSON response
                            if gd_avatar_upload_result.get('status') == 'success':
                                avatar_file_url = gd_avatar_upload_result.get('file_url')
                                logging.info(f"  Avatar uploaded to Google Drive. URL: {avatar_file_url}")
                            else:
                                logging.error(
                                    f"  Google Drive upload FAILED for avatar. Status: {gd_avatar_upload_result.get('status')}, Message: {gd_avatar_upload_result.get('message')}")
                    except requests.exceptions.RequestException as e_gd_upload_avatar:
                        logging.error(f"  Request error uploading avatar to Google Drive: {e_gd_upload_avatar}")


                else:
                    logging.error(
                        f"  Unexpected Content-Type from whatsapp-avatar-service: {avatar_response.headers['Content-Type']}")
                    logging.error(
                        f"  Response content: {avatar_response.text[:100]}...")  # Log first part of response text

            except requests.exceptions.RequestException as e:
                logging.error(f"  Error calling whatsapp-avatar-service: {e}")

    if removed_match_ids:
        logging.info(f"Detected REMOVED matches: {len(removed_match_ids)}")
        for match_id in removed_match_ids:
            removed_match = previous_matches[match_id]
            logging.info(
                f"  - Removed Match ID: {match_id}, Teams: {removed_match['lag1namn']} vs {removed_match['lag2namn']}, Date: {removed_match['speldatum']}, Time: {removed_match['avsparkstid']}")

    if common_match_ids:
        logging.info(f"Detected {len(common_match_ids)} COMMON matches. Checking for modifications...")
        for match_id in common_match_ids:
            previous_match = previous_matches[match_id]
            current_match = current_matches[match_id]
            modified_fields = []

            if previous_match['tid'] != current_match['tid']:
                modified_fields.append(
                    f"Date/Time changed from {previous_match['tidsangivelse']} to {current_match['tidsangivelse']}")  # Using tidsangivelse for combined date and time string
            if previous_match['lag1lagid'] != current_match['lag1lagid']:
                modified_fields.append(
                    f"Home Team changed from ID {previous_match['lag1lagid']} to {current_match['lag1lagid']}")
            if previous_match['lag2lagid'] != current_match['lag2lagid']:
                modified_fields.append(
                    f"Away Team changed from ID {previous_match['lag2lagid']} to {current_match['lag2lagid']}")
            if previous_match['anlaggningid'] != current_match['anlaggningid']:
                modified_fields.append(
                    f"Venue changed from ID {previous_match['anlaggningid']} to {current_match['anlaggningid']}")

                # --- Check Referee Team Changes - Modified Matches ---
                previous_referees = previous_match['domaruppdraglista']
                current_referees = current_match['domaruppdraglista']
                if len(previous_referees) != len(current_referees):
                    modified_fields.append(f"Referee team assignments changed (number of referees changed)")

                if modified_fields:  # If any modifications are detected for a COMMON match
                    logging.info(
                        f"  - Modified Match ID: {match_id}, Teams: {current_match['lag1namn']} vs {current_match['lag2namn']}")
                    for field_change in modified_fields:
                        logging.info(f"    - {field_change}")

                    # --- Check number of referees for MODIFIED match. Skip WhatsApp actions if only one or zero referees ---
                    domaruppdraglista_current = current_match.get('domaruppdraglista',
                                                                  [])  # Use current match's referee list
                    if len(domaruppdraglista_current) < 2:
                        logging.info(
                            f"  Modified Match ID {match_id} now has less than 2 referees. Skipping WhatsApp group actions (or potential group update).")
                        continue  # Skip WhatsApp actions for this MODIFIED match

                    # --- Generate WhatsApp group description for MODIFIED match ---
                    description_text = create_group_description.generate_whatsapp_description(
                        current_match)  # Use current_match details
                    logging.info(f"  Generated WhatsApp group description (for modified match):\n{description_text}")

                    # --- Extract Referee Names for MODIFIED match ---
                    referee_names_list = extract_referee_names(current_match)  # Use current_match details
                    logging.info(f"  Extracted referee names (for modified match): {referee_names_list}")

                    # --- (Future: Call whatsapp-avatar-service, google-drive-service, etc. for MODIFIED match will go here) ---

    else:
        logging.info("No common matches found between previous and current lists.")

    logging.info("\n--- Match Comparison and Change Detection Finished ---")

    # Save current matches as RAW JSON STRING to volume
    save_current_matches_raw_json(current_matches_list_raw_json_string)  # Save RAW JSON string
    logging.info("Current matches saved as raw JSON for future comparison.")

    logging.info("\nprocess_matches.py execution finished.")

    logging.info("\n--- Container will now stay running indefinitely (for testing) ---")
    while True:
        time.sleep(60)
