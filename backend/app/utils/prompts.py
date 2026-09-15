import os
import tempfile
import whisper

from dotenv import load_dotenv
from pytube import YouTube

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import DocArrayInMemorySearch
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


# Load API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# LLM
model = ChatOpenAI(
    openai_api_key=OPENAI_API_KEY,
    model="gpt-3.5-turbo"
)


# Prompt
prompt = ChatPromptTemplate.from_template("""
Answer the question based on the context below.
If you can't answer, reply "I don't know".

Context: {context}

Question: {question}
""")


# YouTube video
YOUTUBE_VIDEO = "https://www.youtube.com/watch?v=cdiD-9MMpb0"


# Download audio
youtube = YouTube(YOUTUBE_VIDEO)
audio = youtube.streams.filter(only_audio=True).first()


# Whisper transcription
whisper_model = whisper.load_model("base")

with tempfile.TemporaryDirectory() as tmpdir:
    file = audio.download(output_path=tmpdir)

    transcription = whisper_model.transcribe(
        file,
        fp16=False
    )["text"].strip()


# Save transcription
with open("transcription.txt", "w") as f:
    f.write(transcription)


# Load transcription
loader = TextLoader("transcription.txt")
text_documents = loader.load()


# Split into chunks
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=20
)

documents = splitter.split_documents(text_documents)


# Create embeddings
embeddings = OpenAIEmbeddings()


# Vector store
vectorstore = DocArrayInMemorySearch.from_documents(
    documents,
    embeddings
)


# Retriever
retriever = vectorstore.as_retriever()


# RAG chain
chain = (
    {
        "context": retriever,
        "question": RunnablePassthrough()
    }
    | prompt
    | model
    | StrOutputParser()
)


# Ask question
question = input("Ask a question: ")

answer = chain.invoke(question)

print("\nAnswer:")
print(answer)
