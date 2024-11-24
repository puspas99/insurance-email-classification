import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from goolge_apis import create_service


def init_gmail_service(client_file, api_name='gmail', api_version='v1', scopes=['https://mail.google.com/']):
    return create_service(client_file, api_name, api_version, scopes)


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


def get_email_messages(service, user_id='me', label_ids=None, folder_name='INBOX', max_results=5):
    messages = []
    next_page_token = None

    if folder_name:
        label_results = service.users().labels().list(userId=user_id).execute()
        labels = label_results.get('labels', [])
        folder_label_id = next((label['id'] for label in labels if label['name'].lower() == folder_name.lower()), None)
        if folder_label_id:
            if label_ids:
                label_ids.append(folder_label_id)
            else:
                label_ids = [folder_label_id]
        else:
            raise ValueError(f"Folder '{folder_name}' not found.")

    while True:
        result = service.users().messages().list(
            userId=user_id,
            labelIds=label_ids,
            maxResults=min(500, max_results - len(messages)) if max_results else 500,
            pageToken=next_page_token
        ).execute()

        messages.extend(result.get('messages', []))

        next_page_token = result.get('nextPageToken')

        if not next_page_token or (max_results and len(messages) >= max_results):
            break

    return messages[:max_results] if max_results else messages


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


def search_emails(service, query, user_id='me', max_results=5):
    messages = []
    next_page_token = None

    while True:
        result = service.users().messages().list(
            userId=user_id,
            q=query,
            maxResults=min(500, max_results - len(messages)) if max_results else 500,
            pageToken=next_page_token
        ).execute()

        messages.extend(result.get('messages', []))

        next_page_token = result.get('nextPageToken')

        if not next_page_token or (max_results and len(messages) >= max_results):
            break

    return messages[:max_results] if max_results else messages


def search_email_conversations(service, query, user_id='me', max_results=5):
    conversations = []
    next_page_token = None

    while True:
        result = service.users().threads().list(
            userId=user_id,
            q=query,
            maxResults=min(500, max_results - len(conversations)) if max_results else 500,
            pageToken=next_page_token
        ).execute()

        conversations.extend(result.get('threads', []))

        next_page_token = result.get('nextPageToken')

        if not next_page_token or (max_results and len(conversations) >= max_results):
            break

    return conversations[:max_results] if max_results else conversations


def download_attachments_message(service, msg_id, target_dir):
    message = service.users().messages().get(userId='me', id=msg_id).execute()
    for part in message['payload']['parts']:
        if part['filename']:
            att_id = part['body']['attachmentId']
            att = service.users().messages().attachments().get(userId='me', messageId=msg_id, id=att_id).execute()
            data = att['data']
            file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
            file_path = os.path.join(target_dir, part['filename'])
            print('Saving attachment to: ', file_path)
            with open(file_path, 'wb') as f:
                f.write(file_data)

def download_attachments_thread(service, msg_id, target_dir):
    thread = service.users().threads().get(userId='me', id=msg_id).execute()
    for message in thread['messages']:
        for part in message['payload']['parts']:
            if part['filename']:
                att_id = part['body']['attachmentId']
                att = service.users().messages().attachments().get(userId='me', messageId=message['id'],
                                                                   id=att_id).execute()
                data = att['data']
                file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                file_path = os.path.join(target_dir, part['filename'])
                print('Saving attachment to: ', file_path)
                with open(file_path, 'wb') as f:
                    f.write(file_data)


def create_label(service, name, label_list_visibility='labelShow', message_list_visibility='show'):
    label = {
        'name': name,
        'labelListVisibility': label_list_visibility,
        'messageListVisibility': message_list_visibility
    }
    created_label = service.users().labels().create(userId='me', body=label).execute()
    return created_label


def list_labels(service):
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    return labels


def get_label_details(service, label_id):
    return service.users().labels().get(userId='me', id=label_id).execute()


def modify_label(service, label_id, **updates):
    label = service.users().labels().get(userId='me', id=label_id).execute()
    for key, value in updates.items():
        label[key] = value
    updated_label = service.users().labels().update(userId='me', id=label_id, body=label).execute()
    return updated_label


def delete_label(service, label_id):
    service.users().labels().delete(userId='me', id=label_id).execute()


def map_label_name_to_id(service, label_name):
    labels = list_labels(service)
    label = next((label for label in labels if label['name'] == label_name), None)
    return label['id'] if label else None


def trash_email(service, user_id, message_id):
    service.users().messages().trash(userId=user_id, id=message_id).execute()


def batch_trash_emails(service, user_id, message_ids):
    batch = service.new_batch_http_request()
    for message_id in message_ids:
        batch.add(service.users().messages().trash(userId=user_id, id=message_id))
    batch.execute()


def permanently_delete_email(service, user_id, message_id):
    service.users().messages().delete(userId=user_id, id=message_id).execute()


def untrash_email(service, user_id, message_id):
    service.users().messages().untrash(userId=user_id, id=message_id).execute()


def batch_untrash_emails(service, user_id, message_ids):
    batch = service.new_batch_http_request()
    for message_id in message_ids:
        batch.add(service.users().messages().untrash(userId=user_id, id=message_id))
    batch.execute()


def empty_trash(service):
    page_token = None
    total_deleted = 0

    while True:
        response = service.users().messages().list(
            userId='me',
            q='in:trash',
            pageToken=page_token,
            maxResults=500
        ).execute()

        messages = response.get('messages', [])
        if not messages:
            break

        batch = service.new_batch_http_request()
        for message in messages:
            batch.add(service.users().messages().delete(userId='me', id=message['id']))
        batch.execute()

        total_deleted += len(messages)

        page_token = response.get('nextPageToken')
        if not page_token:
            break

    return total_deleted


def modify_email_labels(service, user_id, message_id, add_labels=None, remove_labels=None):
    def batch_labels(labels, batch_size=100):
        return [labels[i:i + batch_size] for i in range(0, len(labels), batch_size)]

    if add_labels:
        for batch in batch_labels(add_labels):
            service.users().messages().modify(
                userId=user_id,
                id=message_id,
                body={'addLabelIds': batch}
            ).execute()

    if remove_labels:
        for batch in batch_labels(remove_labels):
            service.users().messages().modify(
                userId=user_id,
                id=message_id,
                body={'removeLabelIds': batch}
            ).execute()


def list_draft_email_messages(service, user_id='me', max_results=5):
    drafts = []
    next_page_token = None

    while True:
        result = service.users().drafts().list(
            userId=user_id,
            maxResults=min(500, max_results - len(drafts)) if max_results else 500,
            pageToken=next_page_token
        ).execute()

        drafts.extend(result.get('drafts', []))

        next_page_token = result.get('nextPageToken')

        if not next_page_token or (max_results and len(drafts) >= max_results):
            break

    return drafts[:max_results] if max_results else drafts


def create_draft_email(service, to, subject, body, body_type='plain', attachment_paths=None):
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject

    if body_type.lower() not in ['plain', 'html']:
        raise ValueError("body_type must be either 'plain' or 'html'")

    message.attach(MIMEText(body, body_type.lower()))

    if attachment_paths:
        for attachment_path in attachment_paths:
            if os.path.exists(attachment_path):
                filename = os.path.basename(attachment_path)

                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())

                encoders.encode_base64(part)

                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {filename}",
                )

                message.attach(part)
            else:
                raise FileNotFoundError(f"File not found - {attachment_path}")

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    draft = service.users().drafts().create(
        userId='me',
        body={'message': {'raw': raw_message}}
    ).execute()

    return draft


def get_draft_email_message_details(service, draft_id, format='full'):
    draft_detail = service.users().drafts().get(userId='me', id=draft_id, format=format).execute()
    draft_id = draft_detail['id']
    draft_message = draft_detail['message']
    draft_payload = draft_message['payload']
    headers = draft_payload.get('headers', [])
    subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No subject')

    subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), None)
    if not subject:
        subject = draft_detail.get('subject', 'No subject')

    sender = next((header['value'] for header in headers if header['name'] == 'From'), 'No sender')
    recipients = next((header['value'] for header in headers if header['name'] == 'To'), 'No recipients')
    snippet = draft_message.get('snippet', 'No snippet')
    has_attachments = any(part.get('filename') for part in draft_payload.get('parts', []) if part.get('filename'))
    date = next((header['value'] for header in headers if header['name'] == 'Date'), 'No date')
    star = draft_message.get('labelIds', []).count('STARRED') > 0
    label = ', '.join(draft_message.get('labelIds', []))

    body = '<Text body not available>'
    if 'parts' in draft_payload:
        for part in draft_payload['parts']:
            if part['mimeType'] == 'multipart/alternative':
                for subpart in part['parts']:
                    if subpart['mimeType'] == 'text/plain' and 'data' in subpart['body']:
                        body = base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8')
                        break
            elif part['mimeType'] == 'text/plain' and 'data' in part['body']:
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                break

    return {
        'subject': subject,
        'sender': sender,
        'recipients': recipients,
        'body': body,
        'snippet': snippet,
        'has_attachments': has_attachments,
        'date': date,
        'star': star,
        'label': label
    }


def send_draft_email(service, draft_id):
    draft = service.users().drafts().send(userId='me', body={'id': draft_id}).execute()
    return draft


def delete_draft_email(service, draft_id):
    service.users().drafts().delete(userId='me', id=draft_id).execute()


def is_thread_parent(service, msg_id):
    try:
        message = service.users().messages().get(userId='me', id=msg_id).execute()
        thread_id = message['threadId']
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        first_message_in_thread = thread['messages'][0]
        return msg_id == first_message_in_thread['id']
    except Exception as e:
        return False


def get_message_and_replies(service, message_id):
    message = service.users().messages().get(userId='me', id=message_id, format='minimal').execute()
    thread_id = message['threadId']
    thread = service.users().threads().get(userId='me', id=thread_id).execute()

    processed_messages = []
    for msg in thread['messages']:
        subject = next((header['value'] for header in msg['payload']['headers'] if header['name'].lower() == 'subject'),
                       'No Subject')
        from_header = next(
            (header['value'] for header in msg['payload']['headers'] if header['name'].lower() == 'from'),
            'Unknown Sender')
        date = next((header['value'] for header in msg['payload']['headers'] if header['name'].lower() == 'date'),
                    'Unknown Date')

        content = _extract_body(msg['payload'])

        processed_messages.append({
            'id': msg['id'],
            'subject': subject,
            'from': from_header,
            'date': date,
            'body': content
        })

    return processed_messages

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


def get_email_attachments_info(service, msg_id, user_id='me'):

    try:
        # Retrieve the email message
        message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()
        payload = message['payload']
        parts = payload.get('parts', [])

        attachments_info = []

        # Traverse through the parts to find attachments
        for part in parts:
            if part.get('filename') and part['body'].get('attachmentId'):
                attachments_info.append({
                    'filename': part['filename'],
                    'attachmentId': part['body']['attachmentId']
                })

        return attachments_info

    except Exception as e:
        print(f"An error occurred while fetching attachments: {e}")
        return []


def download_attachments_message_base64(service, msg_id, target_dir):

    try:
        # Fetch the message details
        message = service.users().messages().get(userId='me', id=msg_id).execute()
        attachments_base64 = {}

        for part in message.get('payload', {}).get('parts', []):
            if part.get('filename'):  # Check if there is a filename
                att_id = part['body'].get('attachmentId')
                if not att_id:
                    continue

                # Fetch the attachment
                att = service.users().messages().attachments().get(userId='me', messageId=msg_id, id=att_id).execute()
                data = att['data']
                file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))

                # Save the file to the target directory
                file_path = os.path.join(target_dir, part['filename'])
                print('Saving attachment to:', file_path)
                with open(file_path, 'wb') as f:
                    f.write(file_data)

                # Add base64-encoded data to the dictionary
                attachments_base64[part['filename']] = data

        return attachments_base64

    except Exception as e:
        print(f"An error occurred while downloading attachments: {e}")
        return {}




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
                # Add to the dictionary (filename as key, base64 content as value)
                #attachments_dict.[part['filename']] = data
        return attachments_dict

    except Exception as e:
        print(f"An error occurred while retrieving attachments: {e}")
        return []


def encode_to_base64(data):
    return base64.b64encode(data.encode('utf-8')).decode('utf-8')
