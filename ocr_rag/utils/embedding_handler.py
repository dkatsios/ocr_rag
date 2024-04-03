import os
from dotenv import load_dotenv
from pinecone import Pinecone, PodSpec
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.schema.document import Document
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains.question_answering import load_qa_chain
import openai

load_dotenv()


class EmbeddingHandler:
    def __init__(self, cfg: dict):
        self._configure(cfg)

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

    def create_embeddings(self, text):
        # docs = [Document(page_content=x) for x in self.text_splitter.split_text(text)]
        docs = self.text_splitter.split_text(text)
        # doc_embeds = embeddings_model.embed_documents(docs)
        docsearch = PineconeVectorStore.from_texts(
            docs, self.embeddings_model, index_name=self.cfg["pinecone"]["index_name"]
        )
        # doc_embeds = Pinecone.from_texts(
        #     [doc.page_content for doc in docs],
        #     embeddings_model,
        #     index_name=self.cfg["index_name"],
        # )
        # docs = self.text_splitter.split_text(text)
        # print(f"{docs[0]=}")
        # res = openai.embeddings.create(input=docs, model=self.cfg["model_name"])
        # doc_embeds = [r.embedding for r in res.data]
        # print(f"{doc_embeds[0]=}")
        print(f"{docsearch=}")
        return docsearch

    def get_respond_with_rag(self, query: str) -> str:
        q_docs = self._get_relative_docs(query)
        llm = ChatOpenAI(temperature=0, openai_api_key=os.environ.get("OPENAI_API_KEY"))
        chain = load_qa_chain(llm, chain_type="stuff")
        respond = chain.invoke({"input_documents": q_docs, "question": query})
        return respond

    def get_index_stats(self):
        return self.index.describe_index_stats()

    def empty_index(self):
        self.index.delete(delete_all=True)

    def _get_relative_docs(self, query: str) -> list[str]:
        vectorstore = PineconeVectorStore(
            index_name=self.cfg["pinecone"]["index_name"],
            embedding=self.embeddings_model,
        )

        q_docs = vectorstore.similarity_search(query, k=self.cfg["pinecone"]["top_k"])
        return q_docs

    def _create_pc_index(self, index_name: str):
        if index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=index_name,
                dimension=cfg["dimension"],
                metric=cfg["metric"],
                spec=PodSpec(
                    environment=os.environ.get("PINECONE_API_ENV"),
                    pod_type=cfg["pod_type"],
                ),
            )
        index = self.pc.Index(index_name)
        return index
