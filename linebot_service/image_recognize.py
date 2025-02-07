import base64
import requests
import os
from dotenv import load_dotenv

load_dotenv()

class ImageDescription:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def get_image_description(self, image_path):
        base64_image = self.encode_image(image_path)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": "這張照片是什麼?"
                    },
                    {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                    }
                ]
                }
            ],
            "max_tokens": 300
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

        response_json = response.json()

        # 提取並回傳 content
        if 'choices' in response_json and len(response_json['choices']) > 0:
            return response_json['choices'][0]['message']['content']
        else:
            return "抱歉!無法辨識紹片!"
        
# image_description = ImageDescription()

# # Path to your image
# image_path = r"D:\work\git_RAG\FactoryTech\a.png"

# # Get description of the image
# message_content = image_description.get_image_description(image_path)
# print(message_content)