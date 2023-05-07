from langchain.document_loaders import UnstructuredFileLoader
from langchain.chains.question_answering import load_qa_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Pinecone
from langchain.embeddings import CohereEmbeddings
from langchain.llms import Cohere
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv
import pinecone

class pdfreaderclass:
    def __init__(self, index_name):
        self.index_name = index_name
        
        load_dotenv()
        self.COHERE_API_KEY = os.getenv('COHERE_API_KEY')
        pinecone.init(
            api_key=os.getenv('PINECONE_API_KEY'),
            environment=os.getenv('PINECONE_ENVIRONMENT')
            )
        self.pinecone_index = pinecone.Index(index_name)
        self.namespaceDict = {}
        self.currentNamespace = None
        
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
        self.chain = load_qa_chain(llm=Cohere(model="command-xlarge-nightly", temperature=0, cohere_api_key=self.COHERE_API_KEY), chain_type="stuff", memory=self.memory, prompt=self.prompt_template)
        
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
        Pinecone.from_texts([t.page_content for t in texts], embedding=embeddings, index_name=self.index_name, namespace=namespace)

        # Get parition of vector database
        docsearch_namespace = Pinecone.from_existing_index(self.index_name, embedding=embeddings, namespace=namespace)
        
        self.namespaceDict.update({namespace : docsearch_namespace})
        self.currentNamespace = docsearch_namespace
            
    def clearPDFs(self):
        # Clear out data folder
        for file in os.scandir("data/"):
            os.remove(file.path)
        return("PDF clear successful!")
    
    def clearNamespace(self,parition_name = "default"):
        # Clear out vector parition
        try:
            self.namespaceDict.pop(parition_name)
        except KeyError as error:
            return ("Error: Please recheck Namespace name. To see a list of namespace names: !listNamespaces")
        self.pinecone_index.delete(deleteAll=True, namespace=parition_name)
        return ("Namespace clear successful!")
    
    def search_docs(self,query):
        # Search for similar chunks
        docs = self.currentNamespace.similarity_search(query, include_metadata=True)
        return docs

    def ask(self,user_input):
        # User sends in query and cohere returns a response
        docs = self.search_docs(user_input)
        answer = self.chain({"input_documents": docs, "human_input": user_input}, return_only_outputs=True)
        return answer