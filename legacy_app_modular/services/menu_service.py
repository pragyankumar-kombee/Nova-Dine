import PyPDF2
import io
import json
import os
from typing import Dict, List, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from config.settings import settings

class MenuExtractionService:
    def __init__(self):
        # Use Groq if available, fallback to settings
        groq_api_key = os.getenv('GROQ_API_KEY') or settings.groq_api_key
        self.model = ChatGroq(
            temperature=0,
            model_name="llama3-70b-8192",
            groq_api_key=groq_api_key
        )
        
        # Use HuggingFace for embeddings (Open source and reliable)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Disable Chroma telemetry to avoid capture() error
        os.environ['ANONYMIZED_TELEMETRY'] = 'False'
        
        self.vector_store = Chroma(
            persist_directory=settings.vector_db_path or "./chroma_db",
            embedding_function=self.embeddings
        )
    
    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text from uploaded PDF menu"""
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    
    def extract_dishes_and_ingredients(self, menu_text: str) -> Dict[str, Any]:
        """Use Groq to extract dishes and ingredients from menu"""
        prompt_path = os.path.join('config', 'prompts', 'ingredient_extractor_prompt.txt')
        if not os.path.exists(prompt_path):
            # Inline fallback prompt if file missing
            prompt_template = "Extract dishes and ingredients from: {menu_text}. Return JSON format."
        else:
            with open(prompt_path, 'r') as f:
                prompt_template = f.read()
        
        prompt = prompt_template.replace("{menu_text}", menu_text[:4000]) # Limit context
        
        try:
            response = self.model.invoke([HumanMessage(content=prompt)])
            result_text = response.content
            
            # Find JSON part in response
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                return {"dishes": []}
        except Exception as e:
            print(f"Error calling Groq: {e}")
            return {"dishes": []}
    
    def store_menu_in_vector_db(self, user_id: int, menu_data: Dict[str, Any]):
        """Store extracted menu data in vector database"""
        documents = []
        metadatas = []
        
        for dish in menu_data.get('dishes', []):
            dish_text = f"Dish: {dish['dish_name']}\nIngredients: {', '.join(dish['ingredients'])}"
            documents.append(dish_text)
            metadatas.append({
                "user_id": user_id,
                "dish_name": dish['dish_name'],
                "type": "menu_item"
            })
        
        if documents:
            self.vector_store.add_texts(
                texts=documents,
                metadatas=metadatas
            )
        
        return len(documents)