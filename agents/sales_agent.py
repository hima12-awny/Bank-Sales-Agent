from google import genai
from google.genai.types import Content, Part, ContentListUnion
from typing import Optional, Union
from pydantic import Field
from agents.sys_prompt import sys_prompt
from agents.response_formatter import ResponseFormatter
from agents.vecdb2 import VecdbChatRAG


class UserContent(Content):
    """Contains the multi-part content of a user message."""

    role: Optional[str] = Field(
        default="user",
        description="The producer of the content. Fixed as 'user' for user messages."
    )  # type: ignore

    def __init__(self, text: Union[str, list[str]], **kwargs):
        # Handle both single string and list of strings
        if isinstance(text, str):
            parts = [Part(text=text)]
        elif isinstance(text, list):
            parts = [Part(text=t) for t in text]
        else:
            raise ValueError("text must be either a string or list of strings")

        super().__init__(parts=parts, **kwargs)



class SalesAgent:
    def __init__(
        self,
        gemini_api_key: str,
        cohere_api_key: str,
        model_name: str = 'gemini-2.0-flash-001',
        sys_prompt: str = sys_prompt
    ):

        self.client = genai.Client(api_key=gemini_api_key)
        self.model = self.client.models.generate_content

        self.vecdb = VecdbChatRAG(
            cohere_api_key=cohere_api_key
        )

        self.contents = []

        self.all_model_config = dict(
            model=model_name,
            config={
                'response_mime_type': 'application/json',
                'response_schema': ResponseFormatter,
                "system_instruction": sys_prompt,
                "temperature": 0
            })

    def generate_response(self, text: str) -> ResponseFormatter:

        self.contents.append(UserContent(text=text))  # type: ignore

        return self.invoke()

    def invoke(self) -> ResponseFormatter:

        response = self.model(
            contents=self.contents,
            **self.all_model_config  # type: ignore
        )

        self.contents.append(response)

        return response.parsed  # type: ignore

    def rag_on(self, user_search_query: str):

        rag_results_context = self.vecdb.query(
            text=user_search_query
        )

        self.contents.append(
            Part(text=rag_results_context)
        )

        return rag_results_context, self.invoke()

    def get_chat_hist(self):
        return self.contents
