from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.chains.question_answering import load_qa_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Pinecone
from langchain_cohere import CohereEmbeddings
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
import time
from langchain_pinecone import PineconeVectorStore
from langchain_cohere import ChatCohere

class pdfreaderclass:
    def __init__(self, index_name):
        self.index_name = index_name
        
        load_dotenv()
        self.COHERE_API_KEY = os.getenv('COHERE_API_KEY')
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        if index_name not in pc.list_indexes().names():
            pc.create_index(
                name=index_name,
                dimension=2,
                metric="cosine",
                spec=ServerlessSpec(
                cloud='aws', 
                region='us-east-1'
                ) 
            ) 
            while not pc.describe_index(index_name).status["ready"]:
                time.sleep(1)

        embeddings = CohereEmbeddings(model="multilingual-22-12", cohere_api_key=self.COHERE_API_KEY)
        self.pinecone_index = pc.Index(index_name)
        docsearchNamespace = PineconeVectorStore.from_existing_index(self.index_name, embedding=embeddings, namespace="default")
        self.namespaceDict = {"default": docsearchNamespace}
        self.currentNamespace = docsearchNamespace
        
        self.template = """You are an AI assistant for answering questions about the Document you have uploaded.
            You are given the following extracted parts of a long document and a question. Provide a conversational answer.
            At the end of your answer, provide the sources used for your answer such as the page number and the name of the document.
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
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        texts = text_splitter.split_documents(docs)

        # Text embeddings and store the vector results in Pinecone vector database
        embeddings = CohereEmbeddings(model="multilingual-22-12", cohere_api_key=self.COHERE_API_KEY)
        PineconeVectorStore.from_texts([t.page_content for t in texts], embedding=embeddings, index_name=self.index_name, namespace=namespace)
        
        # Get parition of vector database
        docsearch_namespace = PineconeVectorStore.from_existing_index(self.index_name, embedding=embeddings, namespace=namespace)
        
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
        embeddings = CohereEmbeddings(model="multilingual-22-12", cohere_api_key=self.COHERE_API_KEY)
        
        found_docs = self.currentNamespace.max_marginal_relevance_search(query, k=2, fetch_k=10)
        for i, doc in enumerate(found_docs):
            print(f"{i + 1}.", doc.page_content, "\n")


        







    def ask(self,user_input):
        # User sends in query and cohere returns a response
        docs = self.search_docs(user_input)
        answer = self.chain({"input_documents": docs, "human_input": user_input}, return_only_outputs=True)
        return answer

        