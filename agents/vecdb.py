from llama_index.core import Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.indices.vector_store.retrievers import (
    VectorIndexRetriever,
)
import nest_asyncio
import pandas as pd
from tqdm.notebook import tqdm
from concurrent.futures import ThreadPoolExecutor
import string


class VecDB:
    def __init__(
        self,
        embedding_model="all-MiniLM-L6-v2",
        persist_directory="./vec_db",
    ) -> None:

        self.embedding_model = embedding_model
        self.persist_directory = persist_directory

        self.retriever: None | VectorIndexRetriever = None
        self.embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

    @staticmethod
    def clean_text(text: str) -> str:
        clean_text_str = ''
        text = text.replace('\n', ' ').lower().strip()
        text_len = len(text)

        def is_valid_char(
            char) -> bool: return char in (string.ascii_lowercase + string.digits) or char in string.whitespace or char in '’\''

        for i, char in enumerate(text):

            in_range = i in range(1, len(text))
            is_char_valid = is_valid_char(char)

            is_prev_num = text[i-1] in string.digits
            is_prev_valid = is_valid_char(text[i-1])
            is_prev_space = text[i-1] == ' '

            if is_char_valid:
                is_char_num = char in string.digits
                is_char_alpha = char in string.ascii_lowercase
                is_prev_char = text[i-1] in string.ascii_lowercase

                if in_range and not is_prev_space:
                    if text[i-1] in '.-,' and is_char_num:
                        pass

                    elif (is_prev_num and is_char_alpha) | \
                        (is_char_num and is_prev_char) | \
                            (not is_prev_valid):
                        clean_text_str += ' '

                clean_text_str += char

            else:
                is_next_num = text[min(i+1, text_len-1)] in string.digits

                if char in '.-,':

                    if in_range:
                        if is_prev_num and is_next_num:
                            clean_text_str += char
                            continue

                if not is_prev_space and not is_prev_valid:
                    clean_text_str += char
                    continue

                clean_text_str += ' ' + char

        return clean_text_str.replace('  ', ' ').replace(" _ ", ' ')

    def split_into_chunks(self, data_recs, chunk_size):
        for i in range(0, len(data_recs), chunk_size):
            yield data_recs[i: i+chunk_size]

    def process_chunk(self, chunk):
        chunk_docs = []
        for prod in tqdm(chunk, desc="Embedding Chunk", position=1):
            chunk_docs.append(
                Document(
                    doc_id=prod['id'],
                    text=prod['doc_text'],
                    embedding=self.embed_model.get_text_embedding(
                        prod['doc_text'])
                )
            )
        return chunk_docs

    def vectorize_db(
        self,
        data: pd.DataFrame,
        product_id_col: str,
        product_doc_info_cols: list[str],
        chunk_size=20,
        max_workers=4
    ) -> None:

        clean_data = pd.DataFrame()
        clean_data['id'] = data[product_id_col]
        clean_data['doc_text'] = product_doc_info_cols[0] + \
            ":" + data[product_doc_info_cols[0]]
        for i in range(len(product_doc_info_cols)-1):
            cur_doc_col = product_doc_info_cols[i+1]
            clean_data['doc_text'] += cur_doc_col + ":" + data[cur_doc_col]

        clean_data['doc_text'] = clean_data['doc_text'].apply(self.clean_text)

        data_recs = clean_data.to_dict('records')

        data_chunks = list(self.split_into_chunks(data_recs, chunk_size))

        self.docs = []

        with ThreadPoolExecutor(
            max_workers=max_workers
        ) as executor:
            chunks_docs = list(
                tqdm(
                    executor.map(self.process_chunk, data_chunks),
                    position=0,
                    total=len(data_chunks),
                    desc="Embedding Texts"
                )
            )
        for chunk_docs in chunks_docs:
            self.docs .extend(chunk_docs)

        nest_asyncio.apply()

        index = VectorStoreIndex.from_documents(
            documents=self.docs,
            embed_model=self.embed_model,
            insert_batch=30,
            use_async=True,
            show_progress=True,
        )

        index.storage_context.persist(
            persist_dir=self.persist_directory
        )

        self.retriever = index.as_retriever()  # type: ignore

        print("VecDB Storing Done.")

    def load_vecdb(self):
        storage_context = StorageContext.from_defaults(
            persist_dir=self.persist_directory)

        embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

        index = load_index_from_storage(
            storage_context=storage_context,
            embed_model=embed_model
        )  # type: ignore

        self.retriever = index.as_retriever()  # type: ignore

        print("VecDB Loading Done.")

    def query(self, text: str):
        if self.retriever is None:
            self.load_vecdb()

        return self.retriever.retrieve(self.clean_text(text))  # type: ignore


class VecdbChatRAG(VecDB):
    def __init__(self, embedding_model="all-MiniLM-L6-v2", persist_directory="./vec_db") -> None:
        super().__init__(embedding_model, persist_directory)

        self.retrieved_node_ids = set()

    def query(self, text: str):  # type: ignore

        nodes = super().query(text)

        i = 0
        ret_prods = ''
        for node in nodes:
            node_id = node.node.node_id

            if node_id in self.retrieved_node_ids:
                continue

            self.retrieved_node_ids.add(node_id)

            prod_text = node.text
            ret_prods += f'{(i:=i+1)}. {prod_text}\n'

        rag_str_result = f'Search Results Based on user Query: {text[:(min(len(text)-1, 100))]}...\n'

        if ret_prods:
            rag_str_result += ret_prods

        else:
            rag_str_result += " - All Retrieved Docs, In Chat History."

        return rag_str_result
