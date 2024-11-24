from anthropic import Anthropic
import re
from typing import Dict, List, Optional
import base64

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
                "text": "These are the attachments in thie email"
            })
        else:
            content.append({
                "type": "text",
                "text": "Not find any attachments in the email"
            })

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

        email_content = """
            Name: %s
            Date: %s
            Subject: %s
            Body: %s
        """%(name, date, subject, body)

        try:
            message = self._client.messages.create(
                model="claude-3-5-sonnet-20240620",
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
            # Extract and format response
           # message.tool_calls[0].function.arguments if message.tool_calls else None
            return resp if resp else None
            
        except Exception as e:
            print(f"Error processing email: {e}")
            return None

