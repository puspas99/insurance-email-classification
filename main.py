import time
import os
from claude_model_api import InsuranceEmailClasifier
from gmail_reader import GmailReader

g = GmailReader()

insuranceClassifier=InsuranceEmailClasifier(os.getenv('CLAUDE_API_KEY'))
print('Started mail polling')
while True:
    email = g.read_latest_unread_email()
    if email:
        print(f'Sending to AI, Email_from = {email["email_from"]}, Email_date = {email["email_date"]}, '
      f'Email_subject = {email["email_subject"]}, Email_body = {email["email_body"]}')
        #prompt claude
        resp=insuranceClassifier.process_email(email['email_from'], email['email_date'], email['email_subject'], email['email_body'],email["attachments"])
        if resp:
            print('Admin subject : ' + resp["adminMailSubject"])
            print('Customer Reply : ' + resp["customerReply"])
             #user reply
            g.replay(email['replay'], email['email_from'], email['email_subject'], resp["customerReply"])
             #admin
            g.send_plan_mail(resp["adminMailSubject"], resp["adminMailBody"], email["attachments"])
        else:
          print("InsuranceClassifier experiencied error while analysis the email content, for email_form = ",email["email_from"])
          g.mark_email_as_unread(email['msg_id'])
        print("Done")
    time.sleep(1)