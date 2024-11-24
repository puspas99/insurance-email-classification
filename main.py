import time
import os
from claude_model_api import InsuranceEmailClasifier
#ClaudeRequestClient
from gmail_reader import GmailReader

g = GmailReader()
#claude = ClaudeRequestClient(os.getenv('CLAUDE_API_KEY'))
claude=InsuranceEmailClasifier(os.getenv('CLAUDE_API_KEY'))
print('Started mail polling')
while True:
    email = g.read_latest_unread_email()
    if email:
        print(f'Sending to AI, Email_from = {email["email_from"]}, Email_date = {email["email_date"]}, '
      f'Email_subject = {email["email_subject"]}, Email_body = {email["email_body"]}')
        
        #prompt claude
       
        resp=claude.process_email(email['email_from'], email['email_date'], email['email_subject'], email['email_body'],email["attachments"])
        print(resp)
        #resp = claude.clasify_email(email['email_from'], email['email_date'], email['email_subject'], email['email_body'], email["attachments"])
        
        #user reply
        g.replay(email['replay'], email['email_from'], email['email_subject'], resp["customerReply"])

        #admin
        g.send_plan_mail(resp["adminMailSubject"], resp["adminMailBody"], email["attachments"])
        print("Done")
    time.sleep(1)