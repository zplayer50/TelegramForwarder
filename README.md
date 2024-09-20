# Telegram Autoforwarder

Telegram Autoforwarder is a powerful Python script that allows you to automatically forward messages between Telegram chats based on customizable rules. It supports multiple forwarding rules, advanced filtering options, and various message processing features.

## Features

- Forward messages from multiple source chats to multiple destination chats
- Filter messages based on keywords and regular expressions
- Schedule message forwarding
- Forward edited messages
- Add custom prefix and suffix to forwarded messages
- Remove links from forwarded messages
- Support for media forwarding
- Easy-to-use command-line interface for managing forwarding rules
- Configuration storage using JSON for persistent settings

## Requirements

- Python 3.7+
- Telethon library
- Other dependencies listed in `requirements.txt`

## Setup

1. Clone the repository:

   ```bash
   git https://github.com/zplayer50/TelegramForwarder.git
   cd Telegram-Autoforwarder
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Obtain Telegram API credentials:

   - Go to https://my.telegram.org/apps and create a new application
   - Note down the API ID and API Hash

## Usage

1. Run the script:

   ```bash
   python TelegramForwarder.py
   ```

2. On first run, enter your Telegram API ID, API Hash, and phone number when prompted

3. Choose from the following options:
   - List Chats: View all available chats and their IDs
   - Forward Messages: Start the forwarding process based on configured rules
   - Edit Forwarding Rules: Add, modify, or delete forwarding rules

## Configuring Forwarding Rules

Each forwarding rule can include the following options:

- Source chat ID
- Destination channel IDs (multiple allowed)
- Keywords for filtering
- Regular expression pattern for advanced filtering
- Include media option
- Forward edited messages option
- Scheduling option
- Custom prefix and suffix for forwarded messages
- Link removal option

## Notes

- Keep your API credentials secure and do not share them publicly
- Ensure you have the necessary permissions in both source and destination chats
- Be mindful of Telegram's rate limits to avoid getting your account banned

## License

This project is licensed under the MIT License.


Acknowledgments
Thanks to the Telethon library for providing a simple and efficient way to interact with Telegram.
Author
joyal george

Contact
hunterz1389@gmail.com
