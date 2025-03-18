from typing import Optional, Literal
from pydantic import BaseModel, Field


class ProductInformation(BaseModel):

    product_name: str = Field(
        description="the product name translated into user language"
    )
    product_description: str = Field(
        description='ONly generate HTML FORMATE Summarization of the product description to convey the customer, generate this in well formatted HTML FORMATE only, Note: Dont Include the product name in the product description'
    )

    product_info_lang: Literal['en', 'ar'] = Field(
        description='the product info langues that llm generate the response with either english(en) or arabic(ar)'
    )


class ResponseFormatter(BaseModel):
    """Format for AI responses including both conversational and search components"""

    conversational_response: str = Field(
        description="AI's response in user langue: professional, empathetic, and context-aware. you can generate tables if user asks to make a comparison over products"
    )

    conversation_langues: Literal['en', 'ar'] = Field(
        description="the conversational langues that llm generate the response with either english(en) or arabic(ar)"
    )

    user_search_query: Optional[str] = Field(
        default=None,
        description="* minimum 30 words Search Query, Generate English Only search query: captures product needs and specifications. make it long as you can so can reach the most product suitable for user, NOTE: Generate it in English ONLY"
    )

    recommended_products: Optional[list[ProductInformation]] = Field(
        default=None,
        description="List of recommended products based on user needs, Max Two ProductInformation containing Summarization product information in the user's preferred language (English or Arabic). Each product includes a name and HTML-formatted description."
    )

    followup_questions: Optional[list[str]] = Field(
        description="Generate a list of follow-up questions that *User* may ask, based on the user prompt and the AI's response."
    )
