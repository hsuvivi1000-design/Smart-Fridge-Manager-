import json
import chromadb
import os
from chromadb.utils import embedding_functions

def build_vector_db():
    data_file = 'recipes_data.json'
    db_path = './chroma_db'
    
    if not os.path.exists(data_file):
        print(f"找不到 {data_file}，請先執行 scraper.py 抓取資料。")
        return
        
    with open(data_file, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
        
    if not recipes:
        print("食譜資料為空，無法建立資料庫。")
        return
        
    print("正在初始化 ChromaDB...")
    # Initialize ChromaDB client with persistence
    client = chromadb.PersistentClient(path=db_path)
    
    # We use the default sentence transformer model for embeddings
    # which is `all-MiniLM-L6-v2`. It's small, fast and works decently for general semantics.
    # In a production environment for Chinese, a multilingual model like `paraphrase-multilingual-MiniLM-L12-v2` is better,
    # but for this demo, the default or explicitly setting a multilingual one is fine.
    # We will explicitly use a multilingual model for better Chinese support.
    print("載入 Embedding 模型 (這可能需要一點時間下載模型)...")
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    # Create or get collection
    collection_name = "recipes"
    try:
        # Try to delete if exists to recreate for demo purposes
        client.delete_collection(name=collection_name)
    except:
        pass
        
    collection = client.create_collection(
        name=collection_name, 
        embedding_function=sentence_transformer_ef
    )
    
    documents = []
    metadatas = []
    ids = []
    
    print(f"開始處理 {len(recipes)} 筆食譜並寫入資料庫...")
    
    for i, recipe in enumerate(recipes):
        # We create a document string that represents the recipe's ingredients for semantic matching
        title = recipe.get('title', '')
        ingredients = ", ".join(recipe.get('ingredients', []))
        
        # The searchable text
        document = f"食譜名稱: {title}. 所需食材: {ingredients}."
        
        # Store the actual recipe details in metadata so we can retrieve them easily
        metadata = {
            "title": title,
            "url": recipe.get('url', ''),
            "ingredients": json.dumps(recipe.get('ingredients', []), ensure_ascii=False),
            "steps": json.dumps(recipe.get('steps', []), ensure_ascii=False),
            "nutrition": json.dumps(recipe.get('nutrition', {}), ensure_ascii=False)
        }
        
        documents.append(document)
        metadatas.append(metadata)
        ids.append(f"recipe_{i}")
        
    # Add to ChromaDB in batches
    batch_size = 50
    for i in range(0, len(documents), batch_size):
        collection.add(
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
            ids=ids[i:i+batch_size]
        )
        
    print(f"成功將 {len(recipes)} 筆食譜存入 Vector DB (位於 {db_path})！")

if __name__ == "__main__":
    build_vector_db()
