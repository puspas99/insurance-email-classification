import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from goolge_apis import create_service


def init_gmail_service(client_file, api_name='gmail', api_version='v1', scopes=['https://mail.google.com/']):
    return create_service(client_file, api_name, api_version, scopes)

def send_email(service, to, subject, body, body_type='plain', attachments=[], message_id=None):
   # Create a MIME message
    message = MIMEMultipart()
    message['to'] = to
    if subject:
        message['Subject'] = subject
    message.attach(MIMEText(body, body_type))

    for att in attachments:
        filename = att["name"]
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(att["data"])
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        message.attach(part)
     # Add the In-Reply-To and References headers to make sure Gmail threads the reply properly
    if message_id:
        message.add_header('In-Reply-To', message_id)
        message.add_header('References', message_id)

    if body_type.lower() not in ['plain', 'html']:
        raise ValueError("body_type must be either 'plain' or 'html'")

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    sent_message = service.users().messages().send(
        userId='me',
        body={'raw': raw_message}
    ).execute()

    return sent_message


def get_latest_unread_email_inbox(service, user_id='me'):

    # Search for unread emails in the INBOX with a limit of 1
    result = service.users().messages().list(
        userId=user_id,
        q="is:unread",  # Query for unread emails
        labelIds=["INBOX"],  # Only from INBOX
        maxResults=1  # Fetch the most recent unread email
    ).execute()

    messages = result.get('messages', [])
    if not messages:
        return None  # No unread emails found

    # Fetch details of the first unread email
    msg_id = messages[0]['id']
    latest_unread_email = get_email_message_details(service, msg_id)
    return latest_unread_email

def get_email_message_details(service, msg_id):
    message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    payload = message['payload']
    headers = payload.get('headers', [])

    subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), None)
    if not subject:
        subject = message.get('subject', '')

    replay = next((header['value'] for header in headers if header['name'] == 'Message-ID'), 'No Msg Id')
    sender = next((header['value'] for header in headers if header['name'] == 'From'), 'No sender')
    recipients = next((header['value'] for header in headers if header['name'] == 'To'), 'No recipients')
    snippet = message.get('snippet', 'No snippet')
    has_attachments = any(part.get('filename') for part in payload.get('parts', []) if part.get('filename'))
    date = next((header['value'] for header in headers if header['name'] == 'Date'), 'No date')
    star = message.get('labelIds', []).count('STARRED') > 0
    label = ', '.join(message.get('labelIds', []))

    body = _extract_body(payload)

    return {
        'subject': subject,
        'sender': sender,
        'recipients': recipients,
        'body': body,
        'snippet': snippet,
        'has_attachments': has_attachments,
        'date': date,
        'star': star,
        'label': label,
        'replay': replay,
        'msg_id':msg_id
    }
def _extract_body(payload):
    body = '<Text body not available>'
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'multipart/alternative':
                for subpart in part['parts']:
                    if subpart['mimeType'] == 'text/plain' and 'data' in subpart['body']:
                        body = base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8')
                        break
            elif part['mimeType'] == 'text/plain' and 'data' in part['body']:
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                break
    elif 'body' in payload and 'data' in payload['body']:
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    return body

def mark_email_as_read(service, message_id, user_id='me'):

    try:
        result = service.users().messages().modify(
            userId=user_id,
            id=message_id,
            body={
                'removeLabelIds': ['UNREAD'],
                'addLabelIds': []  # No labels are added
            }
        ).execute()
        return result
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def is_email_spam(service, message_id, user_id='me'):

    try:
        message = service.users().messages().get(userId=user_id, id=message_id, format='metadata').execute()
        label_ids = message.get('labelIds', [])
        return 'SPAM' in label_ids
    except Exception as e:
        print(f"An error occurred while checking if the email is spam: {e}")
        return False

def  get_attachments_as_dict(service, msg_id):

    try:
        # Fetch the email message
        message = service.users().messages().get(userId='me', id=msg_id).execute()
        attachments_dict = []

        # Loop through message parts
        for part in message.get('payload', {}).get('parts', []):
            if part.get('filename'):  # If the part is an attachment
                att_id = part['body'].get('attachmentId')
                mimeType = part['mimeType']
                name = part['filename']
                if not att_id:
                    continue
                # Fetch the attachment data
                att = service.users().messages().attachments().get(userId='me', messageId=msg_id, id=att_id).execute()
                data = att.get('data')
                attachments_dict.append({
                    "name": name,
                    "mediaType": mimeType,
                    "type": mimeType.split('/')[0],
                    "data": base64.urlsafe_b64decode(data.encode('UTF-8')),
                    "id": att_id
                })
        return attachments_dict

    except Exception as e:
        print(f"An error occurred while retrieving attachments: {e}")
        return []


def mark_email_as_unread(service, message_id):
    user_id = 'me'
    try:
         # Get the current labels of the message
        message = service.users().messages().get(userId='me', id=message_id).execute()
        current_labels = message.get('labelIds', [])
        if 'UNREAD' not in current_labels:
            result = service.users().messages().modify(
                userId=user_id,
                id=message_id,
                body={
                    'addLabelIds': ['UNREAD'],
                    'removeLabelIds': []
                }
            ).execute()

            print("Successfully marked as unread")
        else:
            print("Message is already marked as unread")
            return True
 
    except Exception as e:
        print(f"An error occurred: {e}")
        return False