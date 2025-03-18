import streamlit as st
from google.genai.types import Content, Part, ContentListUnion, GenerateContentResponse
from agents.sales_agent import SalesAgent
from product_card import ProductCard
from agents.response_formatter import ResponseFormatter
from time import sleep
import re


class ChatHandler:
    def __init__(
        self,
        gemini_api_key: str,
        cohere_api_key: str,
    ) -> None:

        self.agent = SalesAgent(
            gemini_api_key=gemini_api_key,
            cohere_api_key=cohere_api_key,
        )
        self.chat_hist = []

        self.arabic_wrapper = '<div style="direction: rtl; text-align: right; padding-right: 15px;">{}</div>'

    @staticmethod
    def is_arabic(text):
        """Check if the given text contains Arabic characters."""
        arabic_pattern = re.compile(
            "[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")
        return bool(arabic_pattern.search(text))

    def render_user_msg(self, msg: Content | str):

        if isinstance(msg, Content):
            msg = msg.parts[0].text  # type: ignore

        if self.is_arabic(msg):
            msg = self.arabic_wrapper.format(msg)

        with st.chat_message('user', avatar='pics/user_avatar.png'):
            st.markdown(msg, unsafe_allow_html=True)

    def render_ai_msg(
            self,
            msg: ResponseFormatter,
            i: int | None = None
    ):

        with st.chat_message('ai', avatar="pics/banque_misr_avatar_logo.jpg"):

            if msg is None:
                st.error("There are something wrong. try again later.")

            conversational_response = msg.conversational_response

            if msg.conversation_langues == 'ar':
                conversational_response = self.arabic_wrapper.format(
                    f'{conversational_response}<br><br>')

            st.markdown(conversational_response, unsafe_allow_html=True)

            if msg.user_search_query is not None and i is not None and msg.recommended_products is None:
                with st.expander("Search In Database with..."):
                    st.write(msg.user_search_query)

                    rag_results = self.chat_hist[i+1].text
                    with st.container(border=True):
                        st.write(rag_results)

                msg = self.chat_hist[i+2].parsed

                if msg.conversation_langues == 'ar':
                    conversational_response = self.arabic_wrapper.format(
                        msg.conversational_response)

                st.markdown(conversational_response,
                            unsafe_allow_html=True)

                i += 2

            if msg.recommended_products is not None:

                rec_prods_title = "<h3>Recommended Products</h3>"
                if msg.conversation_langues == 'ar':
                    rec_prods_title = "<h3>" + "المنتاجات المقترحة" + "</h3>"

                self.stream_markdown(
                    rec_prods_title, st.empty(), msg.conversation_langues)

                cols = st.columns(2)

                for pro_i, prod in enumerate(msg.recommended_products):
                    with cols[pro_i]:
                        ProductCard(
                            name=prod.product_name,
                            description=prod.product_description,
                            lang=prod.product_info_lang,
                            is_stream=False
                        )

        return i or 0

    def render_chat(self):
        self.chat_hist = self.agent.get_chat_hist()
        chat_len = len(self.chat_hist)

        i = 0
        while i < chat_len:
            msg = self.chat_hist[i]

            if isinstance(msg, Content):
                self.render_user_msg(msg)

            elif isinstance(msg, GenerateContentResponse):
                i = self.render_ai_msg(msg.parsed, i)  # type: ignore

            i += 1

    def stream_markdown(self, text: str, parent, lang) -> None:

        if lang == 'ar':
            text = self.arabic_wrapper.format(text)

        rendered_text = ''
        for chr in text:
            rendered_text += chr
            parent.markdown(rendered_text, unsafe_allow_html=True)
            sleep(.001)

    def handle_prompt(self, prompt: str):

        self.render_user_msg(msg=prompt)

        with st.chat_message('ai', avatar="pics/banque_misr_avatar_logo.jpg"):

            with st.spinner("Thinking...", show_time=True):
                response: ResponseFormatter = self.agent.generate_response(
                    prompt)

            if response is None:
                st.error("There Are something wrong, PLease Try Again Later.")

            self.stream_markdown(
                response.conversational_response,
                parent=st.empty(),
                lang=response.conversation_langues
            )

            if response.user_search_query is not None:
                with st.expander("Search In Database with...", expanded=True):

                    st.write(response.user_search_query)

                    with st.spinner("Searching In VecDB"):
                        rag_results, response = self.agent.rag_on(
                            response.user_search_query
                        )
                    with st.container(border=True):
                        st.write(rag_results)

                self.stream_markdown(
                    response.conversational_response,
                    parent=st.empty(),
                    lang=response.conversation_langues)

            if response.recommended_products is not None:

                rec_prods_title = "<h3>Recommended Products</h3>"
                if response.conversation_langues == 'ar':
                    rec_prods_title = "<h3>" + "المنتاجات المقترحة" + "</h3>"

                self.stream_markdown(
                    rec_prods_title, st.empty(), response.conversation_langues)

                cols = st.columns(2)

                num_products = len(response.recommended_products)

                # Initialize the index for the while loop
                index = 0

                # Use a while loop to iterate over the products
                while index < num_products:
                    # Calculate the index for display based on the language
                    if response.conversation_langues == 'ar':
                        display_index = num_products - index - 1
                    else:
                        display_index = index

                    # Get the product at the current index
                    prod = response.recommended_products[index]

                    # Display the product using the calculated display index
                    with cols[display_index]:
                        ProductCard(
                            name=prod.product_name,
                            description=prod.product_description,
                            lang=prod.product_info_lang,
                            is_stream=True
                        )

                    # Increment the index
                    index += 1

            if response.followup_questions is not None:
                st.pills(
                    "Followup Questions",
                    key="followup_question",
                    options=response.followup_questions,  # type: ignore
                )

    def track_hist(self):
        self.chat_hist = self.agent.get_chat_hist()

        cln_chat_hist = []
        for msg in self.chat_hist:

            if isinstance(msg, Content):
                cln_chat_hist.append(
                    dict(
                        role='user',
                        content=msg.parts[0].text  # type: ignore
                    )
                )

            elif isinstance(msg, Part):
                cln_chat_hist.append(
                    dict(
                        role='rag',
                        content=msg.text
                    )
                )

            elif isinstance(msg, GenerateContentResponse):
                cln_chat_hist.append(
                    dict(
                        role='ai',
                        content=msg.parsed.model_dump()  # type: ignore
                    )
                )

        st.sidebar.write(cln_chat_hist)
