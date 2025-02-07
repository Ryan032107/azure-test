import os
import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class TTS_Transcription:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.client = OpenAI(api_key=self.api_key)

    def text_to_speech(self, input_text,output_path):
        response = self.client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input= input_text
        )

        response.stream_to_file(output_path)

    def transcribe_audio(self, file_path):
        with open(file_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return response.text
