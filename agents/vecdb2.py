from llama_index.core import Document
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.indices.vector_store.retrievers import (
    VectorIndexRetriever,
)
import nest_asyncio
import pandas as pd
import string
from llama_index.embeddings.cohere import CohereEmbedding



class VecDB:
    def __init__(
        self,
        cohere_api_key: str,
        persist_directory="./vec_db",
    ) -> None:

        self.cohere_api_key = cohere_api_key
        self.persist_directory = persist_directory

        self.retriever: None | VectorIndexRetriever = None

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

    def vectorize_db(
        self,
        data: pd.DataFrame,
        product_id_col: str,
        product_doc_info_cols: list[str],
    ) -> None:

        clean_data = pd.DataFrame()
        clean_data['id'] = data[product_id_col]
        clean_data['doc_text'] = product_doc_info_cols[0] + \
            ":" + data[product_doc_info_cols[0]]
        for i in range(len(product_doc_info_cols)-1):
            cur_doc_col = product_doc_info_cols[i+1]
            clean_data['doc_text'] += cur_doc_col + ":" + data[cur_doc_col]

        clean_data['doc_text'] = clean_data['doc_text'].apply(self.clean_text)

        self.docs = []
        for doc in clean_data.to_dict('records'):
            self.docs.append(
                Document(
                    doc_id=doc['id'],
                    text=doc['doc_text']
                )
            )

        nest_asyncio.apply()

        embed_model = CohereEmbedding(
            cohere_api_key=self.cohere_api_key,
            input_type="search_document"
        )

        index = VectorStoreIndex.from_documents(
            documents=self.docs,
            embed_model=embed_model,
            insert_batch=100,
            use_async=True,
            show_progress=True,
        )

        index.storage_context.persist(
            persist_dir=self.persist_directory
        )

        print("VecDB Storing Done.")

    def load_vecdb(self):

        from llama_index.postprocessor.cohere_rerank import CohereRerank

        storage_context = StorageContext.from_defaults(
            persist_dir=self.persist_directory)

        embed_model = CohereEmbedding(
            cohere_api_key=self.cohere_api_key,
            input_type="search_query"
        )

        index = load_index_from_storage(
            storage_context=storage_context,
            embed_model=embed_model
        )  # type: ignore

        self.postprocessor = CohereRerank(
            top_n=2,
            model="rerank-english-v3.0",
            api_key=self.cohere_api_key
        )

        self.retriever = index.as_retriever(  # type: ignore
            similarity_top_k=10,
        )

        print("VecDB Loading Done.")

    def query(self, text: str):
        if self.retriever is None:
            self.load_vecdb()

        text = self.clean_text(text)
        nodes = self.retriever.retrieve(text)  # type: ignore
        nodes = self.postprocessor.postprocess_nodes(
            nodes=nodes,
            query_str=text
        )
        return nodes


class VecdbChatRAG(VecDB):
    def __init__(self, cohere_api_key, persist_directory="./vec_db") -> None:
        super().__init__(cohere_api_key, persist_directory)

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
