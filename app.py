import streamlit as st


# Page configuration
st.set_page_config(
    page_title="Sales Agent Chatbot - Bank Misr",
    page_icon="💬",
    layout="wide"
)


st.html(
    """
    <style>
        /* Import font */
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@200..1000&family=Roboto+Slab:wght@100..900&display=swap');

        /* Apply the font */
        body {
           font-family: "Cairo", sans-serif;
            font-optical-sizing: 30px;
            font-weight: 500;
            font-style: normal;
            }
    </style>
"""
)


cols = st.columns([1, 8], gap='small', vertical_alignment='center')

with cols[0]:
    st.image('pics/banque_misr_main_logo.png', width=200)

with cols[1]:

    st.title("Sales Agent Chatbot - Bank Misr Products")
    st.markdown(
        "Chat with our AI sales assistant to get information about our products and services.")


with st.sidebar.container(border=True):
    st.subheader("Set APIs Keys:")

    GEMINI_API_KEY = st.text_input(
        label="Gemini Api Key",
        type='password',
    )

    COHER_API_KEY = st.text_input(
        label="Coher Api Key",
        type='password',
    )

    if st.columns([1, 1, 1])[2].button(
        'Set',
        disabled=not (GEMINI_API_KEY and COHER_API_KEY),
        use_container_width=True,
        type='primary'
    ):
        with st.spinner("Loading Sales Agent..."):
            from chat_ui_handler import ChatHandler

            st.session_state.ui_agent = ChatHandler(
                gemini_api_key=GEMINI_API_KEY,
                cohere_api_key=COHER_API_KEY
            )
        st.success("You Can now Chat")


if "ui_agent" not in st.session_state:
    st.warning(
        "You Should Set Gemini and Cohere API Keys first to Chat with The Agent.")
    st.stop()

st.session_state.ui_agent.render_chat()

if prompt := st.chat_input("Type your message here..."):

    st.session_state.ui_agent.handle_prompt(
        prompt=prompt
    )


fuq = st.session_state.get("followup_question")

if fuq:
    st.session_state.ui_agent.handle_prompt(
        prompt=fuq
    )

# st.session_state.ui_agent.track_hist()
