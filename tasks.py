# app/tasks.py
import os
import json
import fitz  # PyMuPDF
import requests
import uuid
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer
from pydantic import BaseModel, Field
from typing import List

from .celery_worker import celery_app

# --- AI MODEL & DATABASE SETUP ---

print("Loading Sentence Transformer model...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
print("Model loaded.")

# Load the tokenizer for Mistral v0.3. This is needed to format the prompt correctly.
print("Loading Mistral v0.3 tokenizer...")
tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.3")
print("Tokenizer loaded.")

qdrant_host = os.environ.get("QDRANT_HOST", "localhost")
qdrant_client = QdrantClient(host=qdrant_host, port=6333)

# The URL for the new model on Hugging Face Inference API
HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
HF_TOKEN = os.environ.get("HUGGING_FACE_TOKEN")
hf_headers = {"Authorization": f"Bearer {HF_TOKEN}"}

print(f"Loaded Hugging Face Token: {'hf_... ' + HF_TOKEN[-4:] if HF_TOKEN else 'None'}")


try:
    qdrant_client.recreate_collection(
        collection_name="jobs",
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )
    qdrant_client.recreate_collection(
        collection_name="profiles",
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )
    print("Qdrant collections 'jobs' and 'profiles' created.")
except Exception:
    print("Qdrant collections already exist.")


# --- Pydantic Models for Function Calling Structure ---
# These models define the exact structure of the JSON we want back.

class WorkExperience(BaseModel):
    title: str = Field(description="The job title")
    company: str = Field(description="The name of the company")
    duration: str = Field(description="The duration of employment, e.g., '2020-2023'")

class Education(BaseModel):
    degree: str = Field(description="The degree obtained")
    institution: str = Field(description="The name of the institution")

class ResumeDetails(BaseModel):
    skills: List[str] = Field(description="A list of key skills, technologies, and methodologies.")
    work_experience: List[WorkExperience] = Field(description="A list of professional work experiences.")
    education: List[Education] = Field(description="A list of educational qualifications.")


# --- CELERY TASKS ---

@celery_app.task
def parse_resume_task(resume_url):
    """
    Downloads a resume and uses Mistral-v0.3's function calling to parse it.
    """
    print(f"Received task to parse resume at: {resume_url}")
    try:
        response = requests.get(resume_url)
        response.raise_for_status()
        pdf_document = fitz.open(stream=response.content, filetype="pdf")
        resume_text = "".join(page.get_text() for page in pdf_document)

        # 1. Define the conversation and the tool (our Pydantic model)
        messages = [{"role": "user", "content": f"Extract the details from this resume text:\n\n{resume_text[:4000]}"}]
        tools = [{"type": "function", "function": {"name": "extract_resume_details", "description": "Extracts structured information from a resume.", "parameters": ResumeDetails.model_json_schema()}}]

        # 2. Use the tokenizer to create the full prompt string for the API
        # This correctly formats the messages and tools into the special format Mistral expects.
        prompt = tokenizer.apply_chat_template(messages, tools=tools, add_generation_prompt=True, tokenize=False)
        
        # 3. Call the Hugging Face Inference API
        api_payload = {"inputs": prompt, "parameters": {"return_full_text": False}}
        hf_response = requests.post(HF_API_URL, headers=hf_headers, json=api_payload, timeout=90)
        hf_response.raise_for_status()
        
        raw_output = hf_response.json()[0]['generated_text']
        print(f"Finished parsing. Raw LLM output:\n{raw_output}")
        
        # 4. Extract the JSON from the model's function call output
        # The model will output something like: `[TOOL_CALLS]...[{"name": "extract_resume_details", "arguments": {...}}]`
        # We need to parse this string to get the arguments JSON.
        try:
            # Find the start of the JSON arguments
            json_str_start = raw_output.find('{"name":')
            if json_str_start != -1:
                tool_call_json = json.loads(raw_output[json_str_start:])
                arguments = tool_call_json[0]['arguments']
                # Validate with Pydantic
                final_details = ResumeDetails(**arguments)
                return final_details.model_dump_json()
            else:
                 return {"error": "Function call JSON not found in model output."}
        except Exception as e:
            print(f"Error parsing function call JSON: {e}")
            return {"error": "Failed to parse model output.", "raw_output": raw_output}

    except Exception as e:
        print(f"Error processing resume {resume_url}: {e}")
        return {"error": str(e)}

# (The create_embedding_task function is unchanged)
@celery_app.task
def create_embedding_task(collection_name, document_id, text_content):
    print(f"Received task to create embedding for document: {document_id} in collection: {collection_name}")
    try:
        vector = embedding_model.encode(text_content).tolist()
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, document_id))
        qdrant_client.upsert(
            collection_name=collection_name,
            points=[models.PointStruct(id=point_id, vector=vector, payload={"original_id": document_id})],
            wait=True,
        )
        print(f"Finished creating and storing embedding for document: {document_id} with UUID: {point_id}")
        return {"status": "success", "documentId": document_id}
    except Exception as e:
        print(f"Error creating embedding for {document_id}: {e}")
        return {"error": str(e)}