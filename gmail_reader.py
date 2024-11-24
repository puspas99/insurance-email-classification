from pathlib import Path
from gmail_service import init_gmail_service, get_latest_unread_email_inbox,mark_email_as_read, is_email_spam,get_attachments_as_dict,mark_email_as_unread,send_email
from file_operation import delete_all_files_in_folder

import json
# Create the Gmail API service
class GmailReader:
    def __init__(self):
        self._service = init_gmail_service('token.json')

    def read_latest_unread_email(self):
        final_email = {}
        latest_email = get_latest_unread_email_inbox(self._service)
        download_dir = Path('./downloads')

        if latest_email:
            msg_id = latest_email['msg_id']
            print("Mail Recieved: " + latest_email['sender'])
            is_spam = is_email_spam(self._service, msg_id)
            if is_spam:
                print("This email is marked as spam. No further actions. Request the sender to mark as NOT SPAM.")
            else:
                attachments_base64 = get_attachments_as_dict(self._service, msg_id)

                # Prepare the final JSON structure
                final_json = {
                    "msg_id": msg_id,
                    "replay": latest_email['replay'],
                    "email_body": latest_email['body'],
                    "email_subject": latest_email['subject'],
                    "email_from": latest_email['sender'],
                    "email_date": latest_email['date'],
                    "attachments": attachments_base64 if attachments_base64 else {}
                }

                print("Customer subject: " + latest_email['subject'])

                # Mark email as read
                result = mark_email_as_read(self._service, msg_id)
                if result:
                    print("Email marked as read successfully,msg_id=",msg_id)
                else:
                    print("Failed to mark the email as read.")
                final_email = final_json
            # Clean up downloaded files
            delete_all_files_in_folder(download_dir)
        else:
            print("No unread emails found in INBOX.")
        return final_email

    def send_plan_mail(self, subject, body, attachments):
        send_email(self._service, 'ninjasminds@gmail.com', subject, body, attachments=attachments)

    def replay(self, msg_id, to, subject, body):
        send_email(self._service, to, subject, body, message_id=msg_id)
   
    def mark_email_as_unread(self, msg_id):
        mark_email_as_unread(self._service, message_id=msg_id)   