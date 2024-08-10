Telegram Forwarder
Description
Telegram Forwarder is a Python script designed to automate the process of forwarding messages from specified source chats to destination channels on Telegram. This script leverages the Telethon library to interact with the Telegram API, allowing users to perform various tasks such as listing chats, forwarding messages, filtering messages based on keywords, and cleaning messages by removing specified patterns.

Key Features
Connection and Authorization: The script connects to Telegram and authorizes the user if not already authorized. This ensures that the script can interact with the Telegram API on behalf of the user.

Listing Chats: The script can list all chats associated with the user's account and save them to a file. This feature is useful for getting an overview of the user's chats and their respective IDs.

Forwarding Messages: The script can forward messages from specified source chats to destination channels. Users can specify the source chat IDs, destination channel IDs, and keywords to filter messages.

Keyword Filtering: The script allows users to filter messages based on keywords. Only messages containing the specified keywords will be forwarded to the destination channels.

Message Cleaning: The script can clean messages by removing specified patterns. This feature is useful for removing unwanted content from messages before forwarding them.

Requirements
Python 3.7 or higher: The script is written in Python and requires Python 3.7 or higher to run.

Telethon Library: The script uses the Telethon library to interact with the Telegram API. You can install the Telethon library using pip:


pip install telethon
Setup
Credentials File: Create a credentials.txt file with your Telegram API ID, API Hash, and phone number, each on a new line:


API_ID
API_HASH
PHONE_NUMBER
Patterns File: Create a patterns_to_remove.txt file with patterns to remove from messages, each pattern on a new line.

Usage
Run the script using Python:


python telegram_forwarder.py
You will be prompted to choose an option:

List Chats: Lists all chats and saves them to a file named chats_of_PHONE_NUMBER.txt.
Forward Messages: Forwards messages from source chats to destination channels. You will be prompted to enter the source chat IDs, destination channel IDs, and keywords (optional).
Functions
TelegramForwarder Class
__init__(api_id, api_hash, phone_number): Initializes the TelegramForwarder with the given API ID, API Hash, and phone number.
load_patterns(): Loads patterns to remove from the patterns_to_remove.txt file.
connect_and_authorize(): Connects to Telegram and authorizes the user if not already authorized.
list_chats(): Lists all chats and saves them to a file.
forward_messages_to_channels(source_chat_ids, destination_channel_ids, keywords): Forwards messages from source chats to destination channels based on keywords.
clean_message(message_text): Cleans the message text by removing specified patterns.
Helper Functions
read_credentials(): Reads the API ID, API Hash, and phone number from the credentials.txt file.
write_credentials(api_id, api_hash, phone_number): Writes the API ID, API Hash, and phone number to the credentials.txt file.
Notes
The script uses the Telethon library's sync version for simplicity.
The script uses asyncio for asynchronous operations.
The script assumes that the credentials.txt and patterns_to_remove.txt files are in the same directory as the script.
The script saves the list of chats to a file named chats_of_PHONE_NUMBER.txt, where PHONE_NUMBER is the user's phone number.
License
This project is licensed under the MIT License. See the LICENSE file for details.

Acknowledgments
Thanks to the Telethon library for providing a simple and efficient way to interact with Telegram.
Author
joyal george

Contact
hunterz1389@gmail.com
