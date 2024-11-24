from anthropic import Anthropic
import re
from typing import Dict, List, Optional
import base64

class InsuranceEmailClasifier:
    def __init__(self,  api_key: str):
        self._client = Anthropic(api_key=api_key)
        self._system = """You are an insurance support manager. Your task is to:
1. Analyze email content and catagories the request being made by the policyholder.
Once the email is categorized, the you should be able to suggest appropriate actions (e.g., create a claim record, 
schedule a policy review, provide premium payment details, etc.) for customer as well as insurance company departments 
to complete the task
2. Check for attachment discrepancies
3. Generate appropriate responses
4. Create action plans for admin with detailed description or points for each department that needed to complete the request"""

        self._tools = [{
            "name": "action_plan",
            "description": "Generate customer reply and admin actions for insurance email",
             "input_schema": {
                    "type": "object",
                    "properties": {
                        "adminMailSubject": {
                            "type": "string",
                            "description": "A Subject to admin mail that tells the primary catagory of policyholder request"
                        },
                        "adminMailBody": {
                            "type": "string",
                            "description": "Proper instructions for the admin to guide related departments"
                        },
                        "customerReply": {
                            "type": "string",
                            "description": "A reply with around 20 - 50 words. Provide proper instruction to customer if needed"
                        }
                    },
                    "required": ["adminMailSubject", "adminMailBody", "customerReply"]
                }
        }]
        

    def check_attachment_mention(self, email_body: str) -> bool:
        """Check if email mentions attachments"""
        attachment_keywords = [
            r'attach',
            r'PFA',
            r'added document',
            r'added file',
            r'sending file',
            r'enclosed',
            r'attached document',
            r'included file',
            r'sending.*document',
            r'document.*attached'
        ]
        pattern = '|'.join(attachment_keywords)
        return bool(re.search(pattern, email_body, re.IGNORECASE))
    
    def construct_prompt(self, email_content: str,mentioned_attachments:str,has_actual_attachments:bool) -> str:
        """ creating claude prompt """
        prompt = f"""Analyze this insurance-related email and catagories:

Email Content:
{email_content}

Context:
- Attachments mentioned in email: {"Yes" if mentioned_attachments else "No"}
- Actually attached files: {"Yes" if has_actual_attachments else "No"}

{
"If attachments are mentioned but not included, ensure both responses address this:"
if mentioned_attachments and not has_actual_attachments
else ""
}

Generate two responses:

1. ADMIN ACTIONS:
- Prepare a detailed description or points for each department that needed to complete the policyholder email.
- Don't confuse by refering more departments or duplicate department.
- List missing documents (if any)
- Add some policy holder detail if needed
- Add attacahment document details if needed
- Specify next steps if required timeline of action
- Attach the incident Id created for customer for their request 
- Add professional closing on admin mail

2. CUSTOMER REPLY:
- Create a incident Id and Acknowledge their request
- {"Politely notify about missing attachments" if mentioned_attachments and not has_actual_attachments else ""}
- Provide clear next steps 
- Include website, portal and app details if needed or mentioned by you
- Include contact number: 1-800-555-4000
- Add professional closing


Keep customer reply under 100 words."""

        return prompt
    def construct_content(self, prompt: str,attachments:List[Dict] = None) -> str :
        """Create content"""
        content = [
                {
                    "type": "text",
                    "text": prompt
                }
            ]

        for att in attachments:
                if "text" in att["type"]:
                    content.append({
                        "type": "text",
                        "text": att["data"].decode('UTF-8')
                    })
                elif "application/pdf" in att["mediaType"]: 
                    b64 = base64.b64encode(att["data"]).decode('utf-8') 
                    source = {
                        "type": "document",
                        "media_type": att["mediaType"],
                        "data": b64
                    }
                else:
                    b64 = base64.b64encode(att["data"]).decode('utf-8')
                    source = {
                        "type": "base64",
                        "media_type": att["mediaType"],
                        "data": b64 
                    }
                    
                    content.append({
                        "type": att["type"],
                        "source": source
                    })
        return content
    
    def process_email(self, name, date, subject, body, attachments: List[Dict] = None):
        """Process email and generate responses"""

        mentioned_attachments = self.check_attachment_mention(body)
        has_actual_attachments = bool(attachments and len(attachments) > 0)
        email_content = """
            Name: %s
            Date: %s
            Subject: %s
            Body: %s
        """%(name, date, subject, body)

        prompt=self.construct_prompt(email_content,mentioned_attachments,has_actual_attachments)
        try:
            message = self._client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1000,
                system=self._system,
                messages=[{
                    "role": "user",
                    "content": self.construct_content(prompt,attachments)
                }],
                tools=self._tools,
                tool_choice={"type": "tool", "name": "action_plan"}
            )
            tool_blocks = [
            {
                "name": block.name,
                "input": block.input
            } for block in message.content
            if hasattr(block, 'type') and block.type == 'tool_use'
        ]
            resp = tool_blocks[0]["input"]
            print('Admin subject : ' + resp["adminMailSubject"])
            print('Customer Reply : ' + resp["customerReply"])
            # Extract and format response
           # message.tool_calls[0].function.arguments if message.tool_calls else None
            return resp if resp else None
            
        except Exception as e:
            print(f"Error processing email: {e}")
            return None

