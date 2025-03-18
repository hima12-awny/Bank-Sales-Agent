import streamlit as st
from typing import Literal
from time import sleep
import uuid


class ProductCard:
    def __init__(
        self,
        name: str,
        description: str,
        lang: Literal["en", 'ar'] = 'en',
        is_stream=True
    ) -> None:

        name = f'<h3>{name}</h3>'

        if lang == 'ar':
            # For Arabic, use RTL direction
            wrapper = '<div style="direction: rtl; text-align: right;  padding-right: 15px;">{}</div>'

            name = wrapper.format(name)

            description = wrapper.format(description)

        with st.container(border=True, key=str(uuid.uuid4())):

            if is_stream:
                self.stream_markdown(name, st.empty())
                self.stream_markdown(description, st.empty())
            else:
                st.markdown(name, unsafe_allow_html=True)
                st.markdown(description, unsafe_allow_html=True)

            details = 'Details...' if lang == 'en' else 'تفاصل...'
            st.markdown(
                f"""
                <a href="https://example.com" target="_blank" style="text-decoration: none; direction: {'rtl' if lang == 'ar' else 'ltr'};">
                <div style="
                    padding: 0.4em 1em;
                    color: white;
                    background-color: #262C33FF;
                    border-radius: 10px;
                    text-align: center;
                    width: 100%;
                    box-sizing: border-box;
                    margin-bottom: 15px;
                ">
                    {details}
                </div>
            </a>
            """,
                unsafe_allow_html=True
            )

    def stream_markdown(self, text, parent):

        rendered_text = ''
        for chr in text:
            rendered_text += chr
            # Wrap the text in appropriate direction div
            parent.markdown(rendered_text, unsafe_allow_html=True)
            sleep(.001)

