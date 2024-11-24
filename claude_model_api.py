from anthropic import Anthropic
from typing import Dict, List, Optional
import base64
from pdf_to_image import convert_pdf_to_images

class InsuranceEmailClasifier:
    def __init__(self,  api_key: str):
        self._client = Anthropic(api_key=api_key)
        self._system = open('Insurance-email-context.txt','r').read()

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

    def createAttachment(self, type, mediaType, data):
        if "text" in type:
            return [{
                "type": "text",
                "text": data.decode('UTF-8')
            }]
        
        if "application/pdf" in mediaType:
            images = convert_pdf_to_images(data)
            content = []
            for i in images:
                ic = self.createAttachment('image', 'image/png', i)
                content.extend(ic)
            return content

        b64 = base64.b64encode(data).decode('utf-8')
        source = {
            "type": "base64",
            "media_type": mediaType,
            "data": b64
        }
        
        return [{
            "type": type,
            "source": source
        }]

    def construct_content(self, email_content: str, attachments:List[Dict] = None) -> str :
        """Create content"""

        prompt = f"""Analyze this insurance-related email and catagories:

            Email Content:
            {email_content}

        """

        content = [
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        
        if attachments:
            content.append({
                "type": "text",
                "text": "These are the attachments in the email."
            })
        else:
            content.append({
                "type": "text",
                "text": "Not find attachments in the email"
            })
        
        for att in attachments:
                type = att["type"]
                mediaType = att["mediaType"]
                attachContent = self.createAttachment(type, mediaType, att["data"])
                content.extend(attachContent)
                
        print('Content Size: ', len(content))
        return content
    
    def process_email(self, name, date, subject, body, attachments: List[Dict] = None):
        """Process email and generate responses"""

        email_content = """
            Name: %s
            Date: %s
            Subject: %s
            Body: %s
        """%(name, date, subject, body)

        try:
            message = self._client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=self._system,
                messages=[{
                    "role": "user",
                    "content": self.construct_content(email_content, attachments)
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
            return resp if resp else None
            
        except Exception as e:
            print(f"Error processing email: {e}")
            return None

