from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.chains.question_answering import load_qa_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Pinecone
from langchain_cohere import CohereEmbeddings
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_cohere import ChatCohere

class pdfreaderclass:
    def __init__(self, index_name):
        # loading api keys
        load_dotenv()
        
        self.COHERE_API_KEY = os.getenv('COHERE_API_KEY')
        pc = Pinecone(api_key = os.getenv('PINECONE_API_KEY'))
        
        # setting up variables
        self.index_name = index_name
        self.pinecone_index = pc.Index(index_name)
        self.embeddings = CohereEmbeddings(model="embed-english-v3.0", cohere_api_key=self.COHERE_API_KEY)
        
        # loading namespaces from index
        self.namespaceDict = {namespace: PineconeVectorStore.from_existing_index(self.index_name, embedding=self.embeddings, namespace=namespace) for namespace in list(self.pinecone_index.describe_index_stats().get("namespaces", {}).keys())}
        self.currentNamespace = None
        
        self.template = """You are an AI assistant for answering questions about the documents you have uploaded.
            You are given the following extracted parts of a long document and a question. Provide a straightforward answer.
            At the end of your answer, provide the sources used for your answer such as the page number and the name of the document. You can only reference the documents provided.
            If you don't know the answer, just say "Hmm, I'm not sure." Don't try to make up an answer.
            =========
            {context}
            =========
            {chat_history}
            User: {human_input}
            AI Assistant:
            """
        # Set up the promptbn 
        self.prompt_template = PromptTemplate(input_variables=["human_input", "context", "chat_history"], template=self.template)
        
        # Bot remembers 8 (k) conversation turns back
        self.memory = ConversationBufferWindowMemory(k=8, return_messages=True, memory_key="chat_history",input_key="human_input", ai_prefix="AI Assistant")
        self.chain = load_qa_chain(llm=ChatCohere(model="command-xlarge-nightly", temperature=0, cohere_api_key=self.COHERE_API_KEY), chain_type="stuff", memory=self.memory, prompt=self.prompt_template)
        
    def setCurrentNamespace(self, namespace):
        self.currentNamespace = self.namespaceDict[namespace]
        
    def loadPDF(self,filename, namespace = "default"):        
        # PDF to vectors
        # Load in pdf file and split text into chunks
        loader = UnstructuredFileLoader(f"./data/{filename}")
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=[
                "\n\n",
                "\n",
                " ",
                ".",
                ",",
                "\u200b",  # Zero-width space
                "\uff0c",  # Fullwidth comma
                "\u3001",  # Ideographic comma
                "\uff0e",  # Fullwidth full stop
                "\u3002",  # Ideographic full stop
                ""
            ])
        texts = text_splitter.split_documents(docs)

        # Text embeddings and store the vector results in Pinecone vector database
        print(texts)
        PineconeVectorStore.from_texts([t.page_content for t in texts], 
                                       embedding=self.embeddings, 
                                       index_name=self.index_name, 
                                       namespace=namespace,
                                       metadatas=[{"source": filename, "page": str(i)} for i in range(len(texts))], embeddings_chunk_size=1000, batch_size=64)
        
        # Get parition of vector database
        docsearch_namespace = PineconeVectorStore.from_existing_index(self.index_name, embedding=self.embeddings, namespace=namespace)
        
        self.namespaceDict.update({namespace : docsearch_namespace})
        self.currentNamespace = docsearch_namespace
        
    def clearPDFs(self):
        # Clear out data folder
        for file in os.scandir("data/"):
            os.remove(file.path)
        return("PDF clear successful!")
    
    def loadPDFs(self):
        #loadPDFs that are currently in the data folder
        count = 0
        try:
            for file in os.scandir("data/"):
                self.loadPDF(file.path[len("data/"):])
                count += 1
                print(f"uploaded {file.path[len('data/'):]}")
            return(f"Connecting QueryQuack!\nTotal {count} files preloaded into 'default' namespace")
        except Exception as e:
            return (f"Error: {e}")
        
    def clearNamespace(self,parition_name = "default"):
        # Clear out vector parition
        try:
            self.namespaceDict.pop(parition_name)   
        except KeyError as err:
            return("Error: Please recheck Namespace name. To see a list of namespace names: !listNamespaces")
        finally:
            self.pinecone_index.delete(deleteAll=True, namespace=parition_name)
        return ("Namespace clear successful!")
    
    def search_docs(self,query):
        # Search for similar chunks
        docs = self.currentNamespace.max_marginal_relevance_search(query)
        return docs

    def ask(self,user_input):
        # User sends in query and cohere returns a response
        docs = self.search_docs(user_input)
        answer = self.chain.invoke({"input_documents": docs, "human_input": user_input}, return_only_outputs=True)
        return answer

        