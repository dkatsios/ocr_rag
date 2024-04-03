# from enum import Enum
from pydantic import BaseModel


# class ErrorCodes(Enum):
#     NO_SESSION_FOUND = "NO_SESSION_FOUND", "No session found"
#     NO_BOT_EXISTS = "NO_BOT_EXISTS", "No bot exists. Create a bot first."
#     INVALID_BOT = "INVALID_BOT", "The bot is not valid. Create a valid bot."
    
#     def __init__(self, code, message):
#         self.code = code
#         self.message = message


class UploadedFile(BaseModel):
    path: str


# class Prompt(BaseModel):
#     user_input: str


# class Snippet(BaseModel):
#     index: int = -1
#     code: str = ""
