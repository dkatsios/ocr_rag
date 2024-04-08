import os
from dotenv import load_dotenv
from pinecone import Pinecone, PodSpec
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.schema.document import Document
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains.question_answering import load_qa_chain

from .structures import QueryResponse
from .misc import translate

load_dotenv()
UUID_KEY = "uuid"
UUID_ENG_KEY = "uuid_eng"


class EmbeddingHandler:
    def __init__(self, cfg: dict):
        self._configure(cfg)

    def create_embeddings(self, uuid: str, text: str, do_translate: bool = False):
        docs = self.text_splitter.split_text(text)
        uuid_key = UUID_ENG_KEY if do_translate else UUID_KEY
        metadatas = [{uuid_key: uuid} for _ in docs]
        PineconeVectorStore.from_texts(
            docs,
            self.embeddings_model,
            index_name=self.cfg["pinecone"]["index_name"],
            metadatas=metadatas,
        )

    def get_response_with_rag(
        self, uuid: str, query: str, do_translate: bool = True
    ) -> QueryResponse:
        uuid = uuid.replace(" ", "")
        uuids = uuid.split(",")
        q_docs = self._get_relative_docs(uuids, query)
        if do_translate:
            query_eng = translate(query, os.environ.get("OPENAI_API_KEY"))
            q_docs_eng = self._get_relative_docs(uuids, query_eng, do_translate=True)
            q_docs.extend(q_docs_eng)
        llm = ChatOpenAI(temperature=0, openai_api_key=os.environ.get("OPENAI_API_KEY"))
        chain = load_qa_chain(llm, chain_type="stuff")
        response = chain.invoke({"input_documents": q_docs, "question": query})
        response["input_documents"] = [dict(d) for d in response["input_documents"]]
        response = QueryResponse(**response)
        return response

    def remove_embeddings(self, uuid: str):
        vectorstore = PineconeVectorStore(
            index_name=self.cfg["pinecone"]["index_name"],
            embedding=self.embeddings_model,
        )
        vectorstore.delete(filter={UUID_KEY: uuid})
        vectorstore.delete(filter={UUID_ENG_KEY: uuid})

    def get_index_stats(self):
        return self.index.describe_index_stats()

    def empty_index(self):
        self.index.delete(delete_all=True)

    def _configure(self, cfg: dict):
        self.cfg = cfg
        self._create_pc(cfg["pinecone"])
        self._create_splitter(cfg["splitter"])
        self._create_embedding_model(cfg["pinecone"])

    def _create_pc(self, cfg: dict):
        self.pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
        self.index = self._create_pc_index(cfg["index_name"])

    def _create_splitter(self, cfg: dict):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=cfg["chunk_size"],
            chunk_overlap=cfg["chunk_overlap"],
            separators=cfg["separators"],
        )

    def _create_embedding_model(self, cfg: dict):
        self.embeddings_model = OpenAIEmbeddings(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            model=cfg["model_name"],
        )

    def _get_relative_docs(
        self, uuids: list[str], query: str, do_translate: bool = False
    ) -> list[str]:
        vectorstore = PineconeVectorStore(
            index_name=self.cfg["pinecone"]["index_name"],
            embedding=self.embeddings_model,
        )

        uuid_key = UUID_ENG_KEY if do_translate else UUID_KEY
        q_docs = vectorstore.similarity_search(
            query,
            k=self.cfg["pinecone"]["top_k"],
            filter={uuid_key: {"$in": uuids}},
        )
        return q_docs

    def _create_pc_index(self, index_name: str):
        if index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=index_name,
                dimension=self.cfg["pinecone"]["dimension"],
                metric=self.cfg["pinecone"]["metric"],
                spec=PodSpec(
                    environment=os.environ.get("PINECONE_API_ENV"),
                    pod_type=self.cfg["pinecone"]["pod_type"],
                ),
            )
        index = self.pc.Index(index_name)
        return index
