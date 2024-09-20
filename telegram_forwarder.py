import time
import asyncio
import logging
import re
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
import json
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
import os
from telethon import functions
from telethon.tl.types import MessageEntityTextUrl
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator, ValidationError

class TelegramForwarder:
    def __init__(self, api_id, api_hash, phone_number, language='en'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.language = language
        self.client = TelegramClient('session_' + phone_number, api_id, api_hash)
        self.logger = logging.getLogger(__name__)

    async def list_chats(self):
        await self.client.connect()

        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input(self.translate('Enter the code: ', self.language)))

        # Get a list of all the dialogs (chats)
        dialogs = await self.client.get_dialogs()
        chats_file = open(f"chats_of_{self.phone_number}.txt", "w")
        # Print information about each chat
        for dialog in dialogs:
            print(f"Chat ID: {dialog.id}, Title: {dialog.title}")
            chats_file.write(f"Chat ID: {dialog.id}, Title: {dialog.title} \n")
          

        print(self.translate('List of groups printed successfully!', self.language))

    async def forward_messages_to_channels(self, forward_rules):
        await self.client.connect()

        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input(self.translate('Enter the code: ', self.language)))

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
                        self.logger.error(f"Error forwarding message: {str(e)}", exc_info=True)

        @self.client.on(events.MessageEdited())
        async def edit_handler(event):
            for rule in forward_rules:
                if event.chat_id == rule['source_chat_id'] and rule.get('forward_edits', False):
                    try:
                        if self._should_forward(event.message, rule):
                            await self._forward_message(event.message, rule, is_edit=True)
                    except Exception as e:
                        self.logger.error(f"Error forwarding edited message: {str(e)}", exc_info=True)

        self.logger.info(self.translate("Listening for new messages...", self.language))
        await self.client.run_until_disconnected()

    def _should_forward(self, message, rule):
        # Existing conditions
        basic_conditions = super()._should_forward(message, rule)
        
        # New date/time filter
        if 'time_range' in rule:
            message_time = message.date.time()
            start_time = datetime.strptime(rule['time_range']['start'], "%H:%M").time()
            end_time = datetime.strptime(rule['time_range']['end'], "%H:%M").time()
            time_condition = start_time <= message_time <= end_time
        else:
            time_condition = True
        
        return basic_conditions and time_condition

    async def _forward_message(self, message, rule, is_edit=False):
        for dest_channel in rule['destination_channels']:
            scheduled_time = self._get_scheduled_time(rule)
            prefix = rule.get('prefix', '')
            suffix = rule.get('suffix', '')
            
            # Process the message text
            processed_text = self._process_message_text(message.text, rule)
            forwarded_text = f"{prefix}{processed_text}{suffix}"

            # Generate preview
            preview = self._generate_preview(forwarded_text, message)
            print("\n" + self.translate("Message Preview:", self.language))
            print(preview)

            # Ask for confirmation
            confirm = input(self.translate("Send this message? (y/n): ", self.language)).lower().strip()
            if confirm != 'y':
                print(self.translate("Message sending cancelled.", self.language))
                continue

            try:
                if scheduled_time:
                    await self.client.send_message(dest_channel, forwarded_text, schedule=scheduled_time)
                    self.logger.info(f"Message scheduled for {scheduled_time} to channel {dest_channel}")
                else:
                    if rule.get('include_media', True) and message.media:
                        await self.client.send_file(dest_channel, message.media, caption=forwarded_text)
                    else:
                        await self.client.send_message(dest_channel, forwarded_text)
                    
                    action = "forwarded" if not is_edit else "edit forwarded"
                    self.logger.info(f"Message {action}: {message.id} to channel {dest_channel}")
            except Exception as e:
                self.logger.error(f"Failed to forward message {message.id}: {str(e)}", exc_info=True)

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

    def _generate_preview(self, text, original_message):
        preview = text

        # Add formatting indicators
        if original_message.entities:
            for entity in original_message.entities:
                if isinstance(entity, MessageEntityTextUrl):
                    start = entity.offset
                    end = entity.offset + entity.length
                    url = entity.url
                    preview = preview[:start] + f"[{preview[start:end]}]({url})" + preview[end:]
                elif type(entity).__name__ == 'MessageEntityBold':
                    start = entity.offset
                    end = entity.offset + entity.length
                    preview = preview[:start] + f"**{preview[start:end]}**" + preview[end:]
                elif type(entity).__name__ == 'MessageEntityItalic':
                    start = entity.offset
                    end = entity.offset + entity.length
                    preview = preview[:start] + f"*{preview[start:end]}*" + preview[end:]
                # Add more formatting types as needed

        # Add media indicator if present
        if original_message.media:
            preview = "[Media Attachment]\n" + preview

        return preview

    async def view_scheduled_messages(self):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            self.logger.error(self.translate("User not authorized. Please run the forwarder first.", self.language))
            return

        for rule in self.forward_rules:
            for dest_channel in rule['destination_channels']:
                try:
                    channel = await self.client.get_entity(dest_channel)
                    scheduled = await self.client(functions.messages.GetScheduledHistoryRequest(
                        peer=channel,
                        hash=0
                    ))
                    if scheduled.messages:
                        print(f"\nScheduled messages for channel {dest_channel}:")
                        for msg in scheduled.messages:
                            print(f"ID: {msg.id}, Scheduled for: {msg.date}, Text: {msg.message[:50]}...")
                    else:
                        print(f"\nNo scheduled messages for channel {dest_channel}")
                except Exception as e:
                    self.logger.error(f"Error fetching scheduled messages for channel {dest_channel}: {str(e)}")

    async def delete_scheduled_message(self, channel_id, message_id):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            self.logger.error(self.translate("User not authorized. Please run the forwarder first.", self.language))
            return

        try:
            channel = await self.client.get_entity(channel_id)
            await self.client(functions.messages.DeleteScheduledMessagesRequest(
                peer=channel,
                id=[message_id]
            ))
            print(f"Successfully deleted scheduled message {message_id} from channel {channel_id}")
        except Exception as e:
            self.logger.error(f"Error deleting scheduled message {message_id} from channel {channel_id}: {str(e)}")

    def translate(self, text, language='en'):
        translations = {
            'en': {
                'Enter the code: ': 'Enter the code: ',
                'List of groups printed successfully!': 'List of groups printed successfully!',
                'Listening for new messages...': 'Listening for new messages...',
                'Message Preview:': 'Message Preview:',
                'Send this message? (y/n): ': 'Send this message? (y/n): ',
                'Message sending cancelled.': 'Message sending cancelled.',
                'User not authorized. Please run the forwarder first.': 'User not authorized. Please run the forwarder first.',
            },
            'es': {
                'Enter the code: ': 'Ingrese el código: ',
                'List of groups printed successfully!': '¡Lista de grupos impresa con éxito!',
                'Listening for new messages...': 'Escuchando nuevos mensajes...',
                'Message Preview:': 'Vista previa del mensaje:',
                'Send this message? (y/n): ': '¿Enviar este mensaje? (s/n): ',
                'Message sending cancelled.': 'Envío de mensaje cancelado.',
                'User not authorized. Please run the forwarder first.': 'Usuario no autorizado. Por favor, ejecute el reenviador primero.',
            },
            # Add more languages as needed
        }
        return translations.get(language, translations['en']).get(text, text)

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
    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    os.makedirs(logs_dir, exist_ok=True)

    # Set up logging
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Main log file
    main_log_file = os.path.join(logs_dir, 'telegram_forwarder.log')
    file_handler = RotatingFileHandler(main_log_file, maxBytes=5*1024*1024, backupCount=5)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Error log file
    error_log_file = os.path.join(logs_dir, 'error.log')
    error_file_handler = RotatingFileHandler(error_log_file, maxBytes=5*1024*1024, backupCount=5)
    error_file_handler.setFormatter(log_formatter)
    error_file_handler.setLevel(logging.ERROR)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)

    # Get the root logger and add handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_file_handler)
    root_logger.addHandler(console_handler)

    logger = logging.getLogger(__name__)
    logger.info("Starting Telegram Forwarder")

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

    # Define styles for prompt_toolkit
    style = Style.from_dict({
        'prompt': '#ansigreen bold',
        'title': '#ansiblue underline',
    })

    # Language selection
    language_completer = WordCompleter(['1', '2', 'English', 'Español'])
    print(style_text("Select language / Seleccione el idioma:", 'title'))
    print("1. English")
    print("2. Español")
    language_choice = prompt("Enter choice / Ingrese opción: ", completer=language_completer, style=style)
    language = 'en' if language_choice in ['1', 'English'] else 'es'

    forwarder = TelegramForwarder(api_id, api_hash, phone_number, language)
    
    while True:
        print("\n" + style_text(forwarder.translate("Choose an option:", language), 'title'))
        options = [
            "1. " + forwarder.translate("List Chats", language),
            "2. " + forwarder.translate("Forward Messages", language),
            "3. " + forwarder.translate("Edit Forwarding Rules", language),
            "4. " + forwarder.translate("View Scheduled Messages", language),
            "5. " + forwarder.translate("Delete Scheduled Message", language),
            "6. " + forwarder.translate("Exit", language)
        ]
        for option in options:
            print(option)
        
        option_completer = WordCompleter([str(i) for i in range(1, 7)])
        choice = prompt(
            forwarder.translate("Enter your choice: ", language),
            completer=option_completer,
            style=style
        )
        
        if choice == "1":
            await forwarder.list_chats()
        elif choice == "2":
            forward_rules = config.get('forward_rules', [])
            if not forward_rules:
                print(forwarder.translate("No forwarding rules found. Please add rules first.", language))
            else:
                await forwarder.forward_messages_to_channels(forward_rules)
        elif choice == "3":
            edit_forwarding_rules(config, language, forwarder)
        elif choice == "4":
            await forwarder.view_scheduled_messages()
        elif choice == "5":
            channel_id = int(prompt(forwarder.translate("Enter the channel ID: ", language), style=style))
            message_id = int(prompt(forwarder.translate("Enter the message ID to delete: ", language), style=style))
            await forwarder.delete_scheduled_message(channel_id, message_id)
        elif choice == "6":
            print(forwarder.translate("Exiting...", language))
            break
        else:
            print(forwarder.translate("Invalid choice. Please try again.", language))

def style_text(text, style_name):
    return f"[{style_name}]{text}[/{style_name}]"

def edit_forwarding_rules(config, language, forwarder):
    forward_rules = config.get('forward_rules', [])
    while True:
        print("\n" + style_text(forwarder.translate("Current Forwarding Rules:", language), 'title'))
        for i, rule in enumerate(forward_rules):
            print(f"{i+1}. {rule['source_chat_id']} -> {rule['destination_channels']}")
        
        print("\n" + style_text(forwarder.translate("Options:", language), 'title'))
        options = [
            "1. " + forwarder.translate("Add new rule", language),
            "2. " + forwarder.translate("Edit existing rule", language),
            "3. " + forwarder.translate("Delete rule", language),
            "4. " + forwarder.translate("Save and exit", language)
        ]
        for option in options:
            print(option)
        
        option_completer = WordCompleter([str(i) for i in range(1, 5)])
        choice = prompt(
            forwarder.translate("Enter your choice: ", language),
            completer=option_completer,
            style=style
        )
        
        if choice == "1":
            new_rule = create_new_rule(language, forwarder)
            forward_rules.append(new_rule)
        elif choice == "2":
            rule_index = int(prompt(forwarder.translate("Enter the rule number to edit: ", language), style=style)) - 1
            if 0 <= rule_index < len(forward_rules):
                forward_rules[rule_index] = edit_rule(forward_rules[rule_index], language, forwarder)
            else:
                print(forwarder.translate("Invalid rule number", language))
        elif choice == "3":
            rule_index = int(prompt(forwarder.translate("Enter the rule number to delete: ", language), style=style)) - 1
            if 0 <= rule_index < len(forward_rules):
                del forward_rules[rule_index]
            else:
                print(forwarder.translate("Invalid rule number", language))
        elif choice == "4":
            break
        else:
            print(forwarder.translate("Invalid choice", language))
    
    config['forward_rules'] = forward_rules
    save_config(config)

def create_new_rule(language, forwarder):
    rule = {}
    rule['source_chat_id'] = int(prompt(forwarder.translate("Enter source chat ID: ", language), style=style))
    rule['destination_channels'] = [int(x.strip()) for x in prompt(forwarder.translate("Enter destination channel IDs (comma-separated): ", language), style=style).split(',')]
    rule['keywords'] = prompt(forwarder.translate("Enter keywords (comma-separated, or leave blank): ", language), style=style).split(',')
    rule['regex_pattern'] = prompt(forwarder.translate("Enter regex pattern (or leave blank): ", language), style=style).strip() or None
    rule['include_media'] = prompt(forwarder.translate("Include media? (y/n): ", language), style=style).lower() == 'y'
    rule['forward_edits'] = prompt(forwarder.translate("Forward edited messages? (y/n): ", language), style=style).lower() == 'y'
    rule['schedule'] = prompt(forwarder.translate("Enter schedule time (HH:MM) or leave blank: ", language), style=style).strip() or None
    rule['prefix'] = prompt(forwarder.translate("Enter message prefix (or leave blank): ", language), style=style)
    rule['suffix'] = prompt(forwarder.translate("Enter message suffix (or leave blank): ", language), style=style)
    rule['remove_links'] = prompt(forwarder.translate("Remove links from messages? (y/n): ", language), style=style).lower() == 'y'
    time_range = prompt(forwarder.translate("Enter time range for forwarding (HH:MM-HH:MM) or leave blank: ", language), style=style).strip()
    if time_range:
        start, end = time_range.split('-')
        rule['time_range'] = {'start': start.strip(), 'end': end.strip()}
    return rule

def edit_rule(rule, language, forwarder):
    style = Style.from_dict({
        'prompt': '#ansigreen bold',
    })
    
    print(forwarder.translate("Leave blank to keep current value", language))
    new_source = prompt(f"{forwarder.translate('Source chat ID', language)} [{rule['source_chat_id']}]: ", style=style)
    rule['source_chat_id'] = int(new_source) if new_source else rule['source_chat_id']
    
    new_dest = prompt(f"{forwarder.translate('Destination channel IDs', language)} {rule['destination_channels']}: ", style=style)
    rule['destination_channels'] = [int(x.strip()) for x in new_dest.split(',')] if new_dest else rule['destination_channels']
    
    new_keywords = prompt(f"{forwarder.translate('Keywords', language)} {rule['keywords']}: ", style=style)
    rule['keywords'] = new_keywords.split(',') if new_keywords else rule['keywords']
    
    new_regex = prompt(f"{forwarder.translate('Regex pattern', language)} [{rule.get('regex_pattern', '')}]: ", style=style)
    rule['regex_pattern'] = new_regex if new_regex else rule.get('regex_pattern')
    
    new_include_media = prompt(f"{forwarder.translate('Include media? (y/n)', language)} [{'y' if rule['include_media'] else 'n'}]: ", style=style)
    rule['include_media'] = new_include_media.lower() == 'y' if new_include_media else rule['include_media']
    
    new_forward_edits = prompt(f"{forwarder.translate('Forward edited messages? (y/n)', language)} [{'y' if rule.get('forward_edits', False) else 'n'}]: ", style=style)
    rule['forward_edits'] = new_forward_edits.lower() == 'y' if new_forward_edits else rule.get('forward_edits', False)
    
    new_schedule = prompt(f"{forwarder.translate('Schedule time', language)} [{rule.get('schedule', '')}]: ", style=style)
    rule['schedule'] = new_schedule if new_schedule else rule.get('schedule')
    
    new_prefix = prompt(f"{forwarder.translate('Message prefix', language)} [{rule.get('prefix', '')}]: ", style=style)
    rule['prefix'] = new_prefix if new_prefix else rule.get('prefix', '')
    
    new_suffix = prompt(f"{forwarder.translate('Message suffix', language)} [{rule.get('suffix', '')}]: ", style=style)
    rule['suffix'] = new_suffix if new_suffix else rule.get('suffix', '')
    
    new_remove_links = prompt(f"{forwarder.translate('Remove links from messages? (y/n)', language)} [{'y' if rule.get('remove_links', False) else 'n'}]: ", style=style)
    rule['remove_links'] = new_remove_links.lower() == 'y' if new_remove_links else rule.get('remove_links', False)
    
    new_time_range = prompt(f"{forwarder.translate('Time range for forwarding', language)} [{rule.get('time_range', {}).get('start', '')}-{rule.get('time_range', {}).get('end', '')}]: ", style=style)
    if new_time_range:
        start, end = new_time_range.split('-')
        rule['time_range'] = {'start': start.strip(), 'end': end.strip()}
    elif not new_time_range:
        rule.pop('time_range', None)
    
    return rule

# Start the event loop and run the main function
if __name__ == "__main__":
    asyncio.run(main())

