import os
import json
import base64
from anthropic import Anthropic

class ClaudeRequestClient:
    def __init__(self, api_key: str):
        self._client = Anthropic(api_key=api_key)
        self._tools = [
            {
                "name": "action_plan",
                "description": "Create an action plan for one department",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "adminMailSubject": {
                            "type": "string",
                            "description": "A Subject to admin mail"
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
            }
        ]
        self._system = open('Insurance-email-context.txt','r').read()

    def interact_with_claude(self, prompt, attachments=[]):
        try:
            # Send message to Claude
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

            message_params = {
                "model": "claude-3-5-sonnet-20240620",  # You can change the model as needed
                "max_tokens": 1000,
                "system": self._system,
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                "tools": self._tools,
                "tool_choice": {
                    "type": "tool",
                    "name": "action_plan"
                }
            }
            message = self._client.messages.create(**message_params)
            # Return the text of Claude's response
            return message
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def clasify_email(self, name, date, subject, body, attachments=[]):
        prompt = """
            Name: %s
            Date: %s
            Subject: %s
            Body: %s
        """%(name, date, subject, body)
        response = self.interact_with_claude(prompt, attachments)
        tool_blocks = [
            {
                "name": block.name,
                "input": block.input
            } for block in response.content
            if hasattr(block, 'type') and block.type == 'tool_use'
        ]
        resp = tool_blocks[0]["input"]
        print('Admin subject : ' + resp["adminMailSubject"])
        print('Customer Reply : ' + resp["customerReply"])
       # print('Customer action plan : ' + resp["customerBody"])
        return resp
    