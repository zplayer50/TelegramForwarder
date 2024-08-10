import re
import asyncio
from telethon.sync import TelegramClient

class TelegramForwarder:
    def __init__(self, api_id, api_hash, phone_number):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = TelegramClient('session_' + phone_number, api_id, api_hash)
        self.patterns_to_remove = self.load_patterns()

    def load_patterns(self):
        try:
            with open("patterns_to_remove.txt", "r") as file:
                return [line.strip() for line in file.readlines()]
        except FileNotFoundError:
            print("Patterns file not found. No patterns will be removed.")
            return []

    async def connect_and_authorize(self):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))

    async def list_chats(self):
        await self.connect_and_authorize()

        dialogs = await self.client.get_dialogs()
        with open(f"chats_of_{self.phone_number}.txt", "w") as chats_file:
            for dialog in dialogs:
                print(f"Chat ID: {dialog.id}, Title: {dialog.title}")
                chats_file.write(f"Chat ID: {dialog.id}, Title: {dialog.title} \n")

        print("List of groups printed successfully!")

    async def forward_messages_to_channels(self, source_chat_ids, destination_channel_ids, keywords):
        await self.connect_and_authorize()

        last_message_ids = {chat_id: (await self.client.get_messages(chat_id, limit=1))[0].id for chat_id in source_chat_ids}

        while True:
            print("Checking for messages and forwarding them...")
            for chat_id in source_chat_ids:
                last_message_id = last_message_ids[chat_id]
                messages = await self.client.get_messages(chat_id, min_id=last_message_id, limit=None)

                for message in reversed(messages):
                    if keywords and message.text:
                        if any(keyword in message.text.lower() for keyword in keywords):
                            cleaned_message = self.clean_message(message.text)
                            for destination_channel_id in destination_channel_ids:
                                await self.client.send_message(destination_channel_id, cleaned_message)
                            print("Message forwarded")
                    elif message.text:
                        cleaned_message = self.clean_message(message.text)
                        for destination_channel_id in destination_channel_ids:
                            await self.client.send_message(destination_channel_id, cleaned_message)
                        print("Message forwarded")

                    last_message_ids[chat_id] = max(last_message_ids[chat_id], message.id)

            await asyncio.sleep(5)

    def clean_message(self, message_text):
        cleaned_message = message_text
        for pattern in self.patterns_to_remove:
            cleaned_message = re.sub(pattern, "", cleaned_message)
        return cleaned_message

def read_credentials():
    try:
        with open("credentials.txt", "r") as file:
            lines = file.readlines()
            return lines[0].strip(), lines[1].strip(), lines[2].strip()
    except FileNotFoundError:
        print("Credentials file not found.")
        return None, None, None

def write_credentials(api_id, api_hash, phone_number):
    with open("credentials.txt", "w") as file:
        file.write(api_id + "\n")
        file.write(api_hash + "\n")
        file.write(phone_number + "\n")

async def main():
    api_id, api_hash, phone_number = read_credentials()

    if not all([api_id, api_hash, phone_number]):
        api_id = input("Enter your API ID: ")
        api_hash = input("Enter your API Hash: ")
        phone_number = input("Enter your phone number: ")
        write_credentials(api_id, api_hash, phone_number)

    forwarder = TelegramForwarder(api_id, api_hash, phone_number)

    print("Choose an option:")
    print("1. List Chats")
    print("2. Forward Messages")

    choice = input("Enter your choice: ")

    if choice == "1":
        await forwarder.list_chats()
    elif choice == "2":
        source_chat_ids = list(map(int, input("Enter the source chat IDs (comma separated): ").split(",")))
        destination_channel_ids = list(map(int, input("Enter the destination chat IDs (comma separated): ").split(",")))
        keywords = input("Enter keywords (comma separated if multiple, or leave blank): ").split(",")

        await forwarder.forward_messages_to_channels(source_chat_ids, destination_channel_ids, keywords)
    else:
        print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())
