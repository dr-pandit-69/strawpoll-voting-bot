import requests
import re
import time
import random
import json
from datetime import datetime

# Load voting details from JSON file
def load_vote_details(file_path='vote_details.json'):
    with open(file_path, 'r') as file:
        return json.load(file)

# Get CSRF token and vote count from file
def get_csrf_token_and_vote_count(session, url, csrf_token_regex, vote_count_file):
    response = session.get(url)
    if response.status_code != 200:
        raise ValueError("Failed to fetch the page, status code:", response.status_code)
    
    csrf_token_match = re.search(csrf_token_regex, response.text)
    if not csrf_token_match:
        raise ValueError("CSRF token not found in the response")
    
    try:
        with open(vote_count_file, 'r') as file:
            lines = file.readlines()
            vote_count = int(lines[-1].split(' ')[0]) if lines else 0
    except FileNotFoundError:
        vote_count = 0
    
    return csrf_token_match.group(1), vote_count

# Send vote and handle errors/retries
def send_vote(url, csrf_token, session, vote_data, max_retries=3):
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'X-CSRF-Token': csrf_token,
        'Origin': 'https://strawpoll.com',
        'Referer': 'https://strawpoll.com/',
        'User-Agent': session.headers['User-Agent']
    }
    
    for retry in range(max_retries):
        try:
            response = session.post(url, json=vote_data, headers=headers)
            if response.status_code == 200:
                response_json = response.json()
                message = response_json.get('message')
                error_message = response_json.get('error', {}).get('message')
                
                if message:
                    print(f"Vote successfully submitted! Message: {message}")
                    return True
                elif error_message:
                    print(f"Vote failed. Error message: {error_message}")
                    return False if "already participated" in error_message.lower() else False
                else:
                    print("Unexpected response format")
                    return False
            else:
                print(f"Failed to submit vote: {response.status_code} - {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            if retry < max_retries - 1:
                print(f"Retrying in 5 seconds (attempt {retry + 1}/{max_retries})...")
                time.sleep(5)
            else:
                print("Max retries exceeded. Giving up.")
                return False

# Update vote count in file with a timestamp
def update_vote_count(count, vote_count_file):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(vote_count_file, 'a') as file:
        file.write(f"{count} Given to Sombir Sangwan at {timestamp}\n")

# Wait for a random time between specified range
def random_wait(wait_time_range):
    wait_time = random.randint(wait_time_range[0], wait_time_range[1])
    print(f"Waiting for {wait_time} seconds...")
    time.sleep(wait_time)

# Main function to orchestrate voting process
def main():
    vote_details = load_vote_details()  # Load details from JSON
    
    with requests.Session() as session:
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        csrf_token, vote_count = get_csrf_token_and_vote_count(
            session, vote_details["url"], 
            vote_details["csrf_token_regex"], vote_details["vote_count_file"]
        )
        
        for _ in range(vote_details["max_votes"]):  # Number of votes to cast
            if send_vote(
                vote_details["vote_url"], csrf_token, session, 
                vote_details["vote_data"], vote_details["retry_attempts"]
            ):
                vote_count += 1
                update_vote_count(vote_count, vote_details["vote_count_file"])
            random_wait(vote_details["wait_time_range"])
            session.cookies.clear()  # Clear cookies after each vote

if __name__ == "__main__":
    main()
