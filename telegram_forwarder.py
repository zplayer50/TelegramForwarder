import time
import asyncio
import logging
import re
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
import json
from datetime import datetime, timedelta

class TelegramForwarder:
    def __init__(self, api_id, api_hash, phone_number):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = TelegramClient('session_' + phone_number, api_id, api_hash)
        self.logger = logging.getLogger(__name__)

    async def list_chats(self):
        await self.client.connect()

        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))

        # Get a list of all the dialogs (chats)
        dialogs = await self.client.get_dialogs()
        chats_file = open(f"chats_of_{self.phone_number}.txt", "w")
        # Print information about each chat
        for dialog in dialogs:
            print(f"Chat ID: {dialog.id}, Title: {dialog.title}")
            chats_file.write(f"Chat ID: {dialog.id}, Title: {dialog.title} \n")
          

        print("List of groups printed successfully!")

    async def forward_messages_to_channels(self, forward_rules):
        await self.client.connect()

        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))

        @self.client.on(events.NewMessage())
        async def handler(event):
            for rule in forward_rules:
                if event.chat_id == rule['source_chat_id']:
                    try:
                        if self._should_forward(event.message, rule):
                            await self._forward_message(event.message, rule)
                    except FloodWaitError as e:
                        self.logger.warning(f"Rate limit hit. Waiting for {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        self.logger.error(f"Error forwarding message: {str(e)}")

        @self.client.on(events.MessageEdited())
        async def edit_handler(event):
            for rule in forward_rules:
                if event.chat_id == rule['source_chat_id'] and rule.get('forward_edits', False):
                    try:
                        if self._should_forward(event.message, rule):
                            await self._forward_message(event.message, rule, is_edit=True)
                    except Exception as e:
                        self.logger.error(f"Error forwarding edited message: {str(e)}")

        self.logger.info("Listening for new messages...")
        await self.client.run_until_disconnected()

    def _should_forward(self, message, rule):
        if not rule['keywords'] and not rule.get('regex_pattern'):
            return True
        text_match = message.text and any(keyword.lower() in message.text.lower() for keyword in rule['keywords'])
        regex_match = rule.get('regex_pattern') and re.search(rule['regex_pattern'], message.text or '')
        return text_match or regex_match

    async def _forward_message(self, message, rule, is_edit=False):
        for dest_channel in rule['destination_channels']:
            scheduled_time = self._get_scheduled_time(rule)
            prefix = rule.get('prefix', '')
            suffix = rule.get('suffix', '')
            
            # Process the message text
            processed_text = self._process_message_text(message.text, rule)
            forwarded_text = f"{prefix}{processed_text}{suffix}"

            if scheduled_time:
                await self.client.send_message(dest_channel, forwarded_text, schedule=scheduled_time)
                self.logger.info(f"Message scheduled for {scheduled_time}")
            else:
                if rule.get('include_media', True) and message.media:
                    await self.client.send_file(dest_channel, message.media, caption=forwarded_text)
                else:
                    await self.client.send_message(dest_channel, forwarded_text)
                
                action = "forwarded" if not is_edit else "edit forwarded"
                self.logger.info(f"Message {action}: {message.id} to {dest_channel}")

    def _process_message_text(self, text, rule):
        if rule.get('remove_links', False):
            # Remove URLs from the text
            text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Add more text processing options here if needed
        
        return text.strip()

    def _get_scheduled_time(self, rule):
        if rule.get('schedule'):
            now = datetime.now()
            schedule_time = datetime.strptime(rule['schedule'], "%H:%M").time()
            scheduled_datetime = datetime.combine(now.date(), schedule_time)
            if scheduled_datetime <= now:
                scheduled_datetime += timedelta(days=1)
            return scheduled_datetime
        return None

# Function to read credentials from file
def read_credentials():
    try:
        with open("credentials.txt", "r") as file:
            lines = file.readlines()
            api_id = lines[0].strip()
            api_hash = lines[1].strip()
            phone_number = lines[2].strip()
            return api_id, api_hash, phone_number
    except FileNotFoundError:
        print("Credentials file not found.")
        return None, None, None

# Function to write credentials to file
def write_credentials(api_id, api_hash, phone_number):
    with open("credentials.txt", "w") as file:
        file.write(api_id + "\n")
        file.write(api_hash + "\n")
        file.write(phone_number + "\n")

def load_config():
    try:
        with open("config.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_config(config):
    with open("config.json", "w") as file:
        json.dump(config, file, indent=2)

async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    config = load_config()

    # Attempt to read credentials from file
    api_id, api_hash, phone_number = read_credentials()

    # If credentials not found in file, prompt the user to input them
    if api_id is None or api_hash is None or phone_number is None:
        api_id = input("Enter your API ID: ")
        api_hash = input("Enter your API Hash: ")
        phone_number = input("Enter your phone number: ")
        # Write credentials to file for future use
        write_credentials(api_id, api_hash, phone_number)

    forwarder = TelegramForwarder(api_id, api_hash, phone_number)
    
    print("Choose an option:")
    print("1. List Chats")
    print("2. Forward Messages")
    print("3. Edit Forwarding Rules")
    
    choice = input("Enter your choice: ")
    
    if choice == "1":
        await forwarder.list_chats()
    elif choice == "2":
        forward_rules = config.get('forward_rules', [])
        if not forward_rules:
            print("No forwarding rules found. Please add rules first.")
        else:
            await forwarder.forward_messages_to_channels(forward_rules)
    elif choice == "3":
        edit_forwarding_rules(config)
    else:
        logger.error("Invalid choice")

def edit_forwarding_rules(config):
    forward_rules = config.get('forward_rules', [])
    while True:
        print("\nCurrent Forwarding Rules:")
        for i, rule in enumerate(forward_rules):
            print(f"{i+1}. {rule['source_chat_id']} -> {rule['destination_channels']}")
        
        print("\nOptions:")
        print("1. Add new rule")
        print("2. Edit existing rule")
        print("3. Delete rule")
        print("4. Save and exit")
        
        choice = input("Enter your choice: ")
        
        if choice == "1":
            new_rule = create_new_rule()
            forward_rules.append(new_rule)
        elif choice == "2":
            rule_index = int(input("Enter the rule number to edit: ")) - 1
            if 0 <= rule_index < len(forward_rules):
                forward_rules[rule_index] = edit_rule(forward_rules[rule_index])
            else:
                print("Invalid rule number")
        elif choice == "3":
            rule_index = int(input("Enter the rule number to delete: ")) - 1
            if 0 <= rule_index < len(forward_rules):
                del forward_rules[rule_index]
            else:
                print("Invalid rule number")
        elif choice == "4":
            break
        else:
            print("Invalid choice")
    
    config['forward_rules'] = forward_rules
    save_config(config)

def create_new_rule():
    rule = {}
    rule['source_chat_id'] = int(input("Enter source chat ID: "))
    rule['destination_channels'] = [int(x.strip()) for x in input("Enter destination channel IDs (comma-separated): ").split(',')]
    rule['keywords'] = input("Enter keywords (comma-separated, or leave blank): ").split(',')
    rule['regex_pattern'] = input("Enter regex pattern (or leave blank): ").strip() or None
    rule['include_media'] = input("Include media? (y/n): ").lower() == 'y'
    rule['forward_edits'] = input("Forward edited messages? (y/n): ").lower() == 'y'
    rule['schedule'] = input("Enter schedule time (HH:MM) or leave blank: ").strip() or None
    rule['prefix'] = input("Enter message prefix (or leave blank): ")
    rule['suffix'] = input("Enter message suffix (or leave blank): ")
    rule['remove_links'] = input("Remove links from messages? (y/n): ").lower() == 'y'
    return rule

def edit_rule(rule):
    print("Leave blank to keep current value")
    new_source = input(f"Source chat ID [{rule['source_chat_id']}]: ")
    rule['source_chat_id'] = int(new_source) if new_source else rule['source_chat_id']
    
    new_dest = input(f"Destination channel IDs {rule['destination_channels']}: ")
    rule['destination_channels'] = [int(x.strip()) for x in new_dest.split(',')] if new_dest else rule['destination_channels']
    
    new_keywords = input(f"Keywords {rule['keywords']}: ")
    rule['keywords'] = new_keywords.split(',') if new_keywords else rule['keywords']
    
    new_regex = input(f"Regex pattern [{rule.get('regex_pattern', '')}]: ")
    rule['regex_pattern'] = new_regex if new_regex else rule.get('regex_pattern')
    
    new_include_media = input(f"Include media? (y/n) [{'y' if rule['include_media'] else 'n'}]: ")
    rule['include_media'] = new_include_media.lower() == 'y' if new_include_media else rule['include_media']
    
    new_forward_edits = input(f"Forward edited messages? (y/n) [{'y' if rule.get('forward_edits', False) else 'n'}]: ")
    rule['forward_edits'] = new_forward_edits.lower() == 'y' if new_forward_edits else rule.get('forward_edits', False)
    
    new_schedule = input(f"Schedule time [{rule.get('schedule', '')}]: ")
    rule['schedule'] = new_schedule if new_schedule else rule.get('schedule')
    
    new_prefix = input(f"Message prefix [{rule.get('prefix', '')}]: ")
    rule['prefix'] = new_prefix if new_prefix else rule.get('prefix', '')
    
    new_suffix = input(f"Message suffix [{rule.get('suffix', '')}]: ")
    rule['suffix'] = new_suffix if new_suffix else rule.get('suffix', '')
    
    new_remove_links = input(f"Remove links from messages? (y/n) [{'y' if rule.get('remove_links', False) else 'n'}]: ")
    rule['remove_links'] = new_remove_links.lower() == 'y' if new_remove_links else rule.get('remove_links', False)
    
    return rule

# Start the event loop and run the main function
if __name__ == "__main__":
    asyncio.run(main())
