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


def extract_referee_names(match):
    """Extract referee names from a match object."""
    referee_names = []
    for referee in match.get('domaruppdraglista', []):
        referee_name = referee.get('personnamn', '') or referee.get('namn', '')
        if referee_name:
            referee_names.append(referee_name)
    return referee_names


# Example match JSON structure for reference:
"""
{
    "__type": "Svenskfotboll.Fogis.Web.FogisMobilDomarKlient.MatchJSON",
    "value": "000024032",
    "label": "000024032: IK Kongahälla - Motala AIF FK (Div 2 Norra Götaland, herr 2025), 2025-04-26 14:00",
    "matchid": 6169105,
    "matchnr": "000024032",
    "lag1namn": "IK Kongahälla",
    "lag2namn": "Motala AIF FK",
    "speldatum": "2025-04-26",
    "avsparkstid": "14:00",
    "domaruppdraglista": [
        {
            "domaruppdragid": 6847166,
            "domarrollnamn": "Huvuddomare",
            "personnamn": "Bartek Svaberg",
            "namn": "Bartek Svaberg"
        },
        {
            "domaruppdragid": 6847167,
            "domarrollnamn": "Assisterande 1",
            "personnamn": "Aleksander Gavrilovic",
            "namn": "Aleksander Gavrilovic"
        },
        {
            "domaruppdragid": 6847168,
            "domarrollnamn": "Assisterande 2",
            "personnamn": "Zakaria Hersi",
            "namn": "Zakaria Hersi"
        }
    ]
}
"""


def save_description_to_file(description_text, match_id):
    """Save description text to a temporary file."""
    description_filename = f"whatsapp_group_description_match_{match_id}.txt"
    temp_description_filepath = f"/tmp/{description_filename}"
    try:
        with open(temp_description_filepath, 'w', encoding='utf-8') as description_file:
            description_file.write(description_text)
        logging.info(f"  Description text saved to temporary file: {temp_description_filepath}")
        return temp_description_filepath
    except Exception as save_error:
        logging.error(f"  Error saving description text to {temp_description_filepath}: {save_error}")
        logging.debug(f"  File saving FAILED with error for: {temp_description_filepath}")
        return None


def create_and_save_avatar(match_id, team1_id, team2_id):
    """Create and save avatar image for a match."""
    avatar_service_url = "http://whatsapp-avatar-service:5002/create_avatar"
    team_ids_payload = {
        "team1_id": str(team1_id),
        "team2_id": str(team2_id)
    }
    logging.info(f"Calling whatsapp-avatar-service to create avatar for match {match_id}...")
    try:
        avatar_response = requests.post(avatar_service_url, json=team_ids_payload, stream=True)
        avatar_response.raise_for_status()

        if avatar_response.headers['Content-Type'] == 'image/png':
            avatar_image_data = avatar_response.content
            logging.debug(f"  Avatar image data length: {len(avatar_image_data)} bytes")
            avatar_filename = f"whatsapp_group_avatar_match_{match_id}.png"
            temp_avatar_filepath = f"/tmp/{avatar_filename}"

            try:
                with open(temp_avatar_filepath, 'wb') as avatar_file:
                    avatar_file.write(avatar_image_data)
                logging.info(f"  Avatar image downloaded and saved to: {temp_avatar_filepath}")
                logging.debug(f"  File saving completed WITHOUT errors for: {temp_avatar_filepath}")
                return temp_avatar_filepath, avatar_filename
            except Exception as save_error:
                logging.error(f"  Error saving avatar image to {temp_avatar_filepath}: {save_error}")
                logging.debug(f"  File saving FAILED with error for: {temp_avatar_filepath}")
                return None, None
        else:
            logging.error(
                f"  Unexpected Content-Type from whatsapp-avatar-service: {avatar_response.headers['Content-Type']}")
            logging.error(f"  Response content: {avatar_response.text[:100]}...")
            return None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"  Error calling whatsapp-avatar-service: {e}")
        return None, None


def upload_to_gdrive(file_path, file_name, folder_path, mime_type):
    """Upload a file to Google Drive."""
    gdrive_service_base_url = "http://google-drive-service:5000"
    gdrive_upload_url = f"{gdrive_service_base_url}/upload_file"

    try:
        with open(file_path, 'rb') as file_obj:
            files = {'file': (file_name, file_obj, mime_type)}
            data = {'folder_path': folder_path}
            response = requests.post(gdrive_upload_url, files=files, data=data)
            response.raise_for_status()
            result = response.json()
            if result.get('status') == 'success':
                file_url = result.get('file_url')
                logging.info(f"  File uploaded to Google Drive. URL: {file_url}")
                return file_url
            else:
                logging.error(
                    f"  Google Drive upload FAILED. Status: {result.get('status')}, Message: {result.get('message')}")
                return None
    except requests.exceptions.RequestException as e:
        logging.error(f"  Request error uploading to Google Drive: {e}")
        return None
    except Exception as e:
        logging.error(f"  Error uploading to Google Drive: {e}")
        return None


def save_group_info_to_file(match_data, match_id):
    """Save group name and referee names to a file."""
    team1_name = match_data.get('lag1namn', 'Team 1')
    team2_name = match_data.get('lag2namn', 'Team 2')
    group_name = f"{team1_name} - {team2_name}"

    # Get match details
    match_date = match_data.get('speldatum', '')
    match_time = match_data.get('avsparkstid', '')
    match_number = match_data.get('matchnr', '')
    competition = match_data.get('tavlingnamn', '')
    venue = match_data.get('anlaggningnamn', '')

    # Create content
    group_info_content = f"Group Name: {group_name}\n"
    group_info_content += f"Match: {match_number}\n"
    group_info_content += f"Competition: {competition}\n"
    group_info_content += f"Date & Time: {match_date} {match_time}\n"
    group_info_content += f"Venue: {venue}\n\n"

    # Add referee information with roles
    group_info_content += "Referees:\n"
    for referee in match_data.get('domaruppdraglista', []):
        name = referee.get('personnamn', '') or referee.get('namn', '')
        role = referee.get('domarrollnamn', '')
        if name:
            group_info_content += f"- {name} ({role})\n"

    group_info_filename = f"whatsapp_group_info_match_{match_id}.txt"
    temp_group_info_filepath = f"/tmp/{group_info_filename}"

    try:
        with open(temp_group_info_filepath, 'w', encoding='utf-8') as group_info_file:
            group_info_file.write(group_info_content)
        logging.info(f"  Group info saved to temporary file: {temp_group_info_filepath}")
        return temp_group_info_filepath, group_info_filename
    except Exception as save_error:
        logging.error(f"  Error saving group info to {temp_group_info_filepath}: {save_error}")
        logging.debug(f"  File saving FAILED with error for: {temp_group_info_filepath}")
        return None, None


def process_match(match_data, match_id_param, is_new=True):
    """Process a match (new or modified)."""
    # Log match details
    action_type = "New" if is_new else "Modified"
    logging.info(
        f"  - {action_type} Match ID: {match_id_param}, Teams: {match_data['lag1namn']} vs {match_data['lag2namn']}, Date: {match_data['speldatum']}, Time: {match_data['avsparkstid']}")

    # If modified, we can get the previous match data from the global previous_matches dictionary
    if not is_new:
        prev_match_data = previous_matches.get(match_id_param)
        if prev_match_data:
            modified_fields = []
            if prev_match_data['tid'] != match_data['tid']:
                modified_fields.append(
                    f"Date/Time changed from {prev_match_data['tidsangivelse']} to {match_data['tidsangivelse']}")
            if prev_match_data['lag1lagid'] != match_data['lag1lagid']:
                modified_fields.append(
                    f"Home Team changed from ID {prev_match_data['lag1lagid']} to {match_data['lag1lagid']}")
            if prev_match_data['lag2lagid'] != match_data['lag2lagid']:
                modified_fields.append(
                    f"Away Team changed from ID {prev_match_data['lag2lagid']} to {match_data['lag2lagid']}")
            if prev_match_data['anlaggningid'] != match_data['anlaggningid']:
                modified_fields.append(
                    f"Venue changed from ID {prev_match_data['anlaggningid']} to {match_data['anlaggningid']}")

            # Check referee changes
            prev_match_referees = prev_match_data.get('domaruppdraglista', [])
            curr_match_referees = match_data.get('domaruppdraglista', [])
            if len(prev_match_referees) != len(curr_match_referees):
                modified_fields.append(f"Referee team assignments changed (number of referees changed)")
            else:
                # Check if any referee has changed
                prev_match_ref_ids = {ref.get('domarid') for ref in prev_match_referees}
                curr_match_ref_ids = {ref.get('domarid') for ref in curr_match_referees}
                if prev_match_ref_ids != curr_match_ref_ids:
                    modified_fields.append(f"Referee team assignments changed (different referees)")

            for field_change in modified_fields:
                logging.info(f"    - {field_change}")

    # Check number of referees. Skip WhatsApp actions if only one or zero referees
    domaruppdraglista = match_data.get('domaruppdraglista', [])
    if len(domaruppdraglista) < 2:
        logging.info(f"  Match ID {match_id_param} has less than 2 referees. Skipping WhatsApp group creation/update.")
        return

    # Generate WhatsApp group description
    description_text = create_group_description.generate_whatsapp_description(match_data)
    logging.info(f"  Generated WhatsApp group description:\n{description_text}")

    # Save description to temporary file
    temp_description_filepath = save_description_to_file(description_text, match_id_param)
    if not temp_description_filepath:
        return  # Skip if saving failed

    # Save group info (group name and referee names) to temporary file
    temp_group_info_filepath, group_info_filename = save_group_info_to_file(match_data, match_id_param)
    if not temp_group_info_filepath:
        return  # Skip if saving failed

    # Extract referee names
    referee_names_list = extract_referee_names(match_data)
    logging.info(f"  Extracted referee names: {referee_names_list}")

    # Format match date for folder structure
    match_date_formatted = match_data.get('speldatum', '')  # Keep original format with hyphens (YYYY-MM-DD)
    safe_label = f"{match_id_param}_{match_data['lag1namn'].replace(' ', '_')}_{match_data['lag2namn'].replace(' ', '_')}"
    logging.info(f"  Formatted match date: {match_date_formatted}, Safe label: {safe_label}")

    # Create and save avatar
    temp_avatar_filepath, avatar_filename = create_and_save_avatar(
        match_id_param,
        match_data.get('lag1foreningid'),
        match_data.get('lag2foreningid')
    )
    if not temp_avatar_filepath:
        return  # Skip if avatar creation failed

    # Google Drive folder path
    gdrive_folder_path = f"WhatsApp_Group_Assets/{match_date_formatted}/Match_{safe_label}"

    # Upload description file to Google Drive
    description_filename_gd = f"whatsapp_group_description_match_{match_id_param}.txt"
    description_url = upload_to_gdrive(
        temp_description_filepath,
        description_filename_gd,
        gdrive_folder_path,
        'text/plain'
    )

    # Upload group info file to Google Drive
    group_info_url = upload_to_gdrive(
        temp_group_info_filepath,
        group_info_filename,
        gdrive_folder_path,
        'text/plain'
    )

    # Upload avatar file to Google Drive
    avatar_url = upload_to_gdrive(
        temp_avatar_filepath,
        avatar_filename,
        gdrive_folder_path,
        'image/png'
    )

    # Here you could add code to create or update WhatsApp groups
    # For example, call a WhatsApp service to create/update groups

    return description_url, group_info_url, avatar_url


# Main execution block
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
    current_matches_list_response = api_client.fetch_matches_list()
    logging.debug(f"Type of current_matches_list_response from API Client: {type(current_matches_list_response)}")
    current_matches_list_raw_json_string = json.dumps(current_matches_list_response, ensure_ascii=False)
    current_matches_list = current_matches_list_response

    logging.info(f"Fetched current matches list: {len(current_matches_list)} matches.")

    if not current_matches_list:
        logging.warning(
            "Could not fetch current matches list from API or unexpected response. Exiting change detection.")
        logging.info("process_matches.py execution finished prematurely due to API fetch failure.")
        logging.info("\n--- Container will now stay running indefinitely (for testing) ---")
        while True:
            time.sleep(60)
        exit()

    # Convert BOTH previous and current match lists to dictionaries for comparison
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

    # Process new matches
    if new_match_ids:
        logging.info(f"Detected NEW matches: {len(new_match_ids)}")
        for current_match_id in new_match_ids:
            new_match_data = current_matches[current_match_id]
            process_match(new_match_data, current_match_id, is_new=True)
    else:
        logging.info("No new matches detected.")

    # Process removed matches
    if removed_match_ids:
        logging.info(f"Detected REMOVED matches: {len(removed_match_ids)}")
        for removed_match_id in removed_match_ids:
            removed_match_data = previous_matches[removed_match_id]
            logging.info(
                f"  - Removed Match ID: {removed_match_id}, Teams: {removed_match_data['lag1namn']} vs {removed_match_data['lag2namn']}, Date: {removed_match_data['speldatum']}, Time: {removed_match_data['avsparkstid']}")
            # Here you could add code to handle removed matches
    else:
        logging.info("No removed matches detected.")

    # Process modified matches
    if common_match_ids:
        logging.info(f"Detected {len(common_match_ids)} COMMON matches. Checking for modifications...")
        modified_count = 0
        for common_match_id in common_match_ids:
            prev_match_data = previous_matches[common_match_id]
            curr_match_data = current_matches[common_match_id]

            # Check if match has been modified
            is_modified = (
                    prev_match_data['tid'] != curr_match_data['tid'] or
                    prev_match_data['lag1lagid'] != curr_match_data['lag1lagid'] or
                    prev_match_data['lag2lagid'] != curr_match_data['lag2lagid'] or
                    prev_match_data['anlaggningid'] != curr_match_data['anlaggningid']
            )

            # Check if referee team has changed
            prev_match_referees = prev_match_data.get('domaruppdraglista', [])
            curr_match_referees = curr_match_data.get('domaruppdraglista', [])
            if len(prev_match_referees) != len(curr_match_referees):
                is_modified = True
            else:
                prev_match_ref_ids = {ref.get('domarid') for ref in prev_match_referees}
                curr_match_ref_ids = {ref.get('domarid') for ref in curr_match_referees}
                if prev_match_ref_ids != curr_match_ref_ids:
                    is_modified = True

            if is_modified:
                modified_count += 1
                process_match(curr_match_data, common_match_id, is_new=False)

        logging.info(f"Found {modified_count} modified matches out of {len(common_match_ids)} common matches.")
    else:
        logging.info("No common matches found between previous and current lists.")

    logging.info("\n--- Match Comparison and Change Detection Finished ---")

    # Save current matches as RAW JSON STRING to volume
    save_current_matches_raw_json(current_matches_list_raw_json_string)
    logging.info("Current matches saved as raw JSON for future comparison.")

    logging.info("\nprocess_matches.py execution finished.")

    logging.info("\n--- Container will now stay running indefinitely (for testing) ---")
    while True:
        time.sleep(60)
