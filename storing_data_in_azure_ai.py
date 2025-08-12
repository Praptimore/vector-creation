# --------------------------------------------------------------
# This script creates an Azure Cognitive Search index that supports vector search
# and uploads documents (with image/text vectors) to that index.
# --------------------------------------------------------------

import os
import json
from dotenv import load_dotenv
import requests

# Azure SDK imports
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)
# --------------------------------------------------------------
# 1. Load API keys and environment variables
# --------------------------------------------------------------
load_dotenv()

endpoint = os.getenv("SEARCH_ENDPOINT")  # Azure Search endpoint
admin_key = os.getenv("SEARCH_KEY")      # Azure Search Admin Key
index_name = "images-index1"             # Name of the search index
json_path = "km_mapped_output/km_image_text.json"  # Path to JSON with image & vectors
api_version = "2023-11-01"

headers = {
    "Content-Type": "application/json",
    "api-key": admin_key
}

# --------------------------------------------------------------
# 2. Function: Create the Azure Search Index
# --------------------------------------------------------------
def create_index():
    print("Creating vector search index...")

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="description", type=SearchFieldDataType.String),
        SearchField(
            name="vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=512,
            vector_search_profile_name="default-vector-profile"  # updated property
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="default-vector-config"
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="default-vector-profile",
                algorithm_configuration_name="default-vector-config"
            )
        ]
    )

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search
    )

    index_client = SearchIndexClient(endpoint, AzureKeyCredential(admin_key))

    try:
        index_client.delete_index(index_name)
        print(f"Deleted existing index '{index_name}'.")
    except Exception:
        pass

    try:
        index_client.create_index(index)
        print(f"✅ Index '{index_name}' created successfully!")
    except Exception as e:
        print(f"❌ Failed to create index: {e}")

# --------------------------------------------------------------
# 3. Function: Upload JSON documents with vectors to the index
# --------------------------------------------------------------
def upload_documents():
    print(f"Uploading documents from {json_path}...")

    # Load data from JSON
    with open(json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    documents = []

    # Process each entry
    for doc_id, content in raw_data.items():
        if "vector" in content and isinstance(content["vector"], list):
            if len(content["vector"]) != 512:
                print(f"⚠ Skipping {doc_id}: Invalid vector length ({len(content['vector'])})")
                continue
            try:
                doc = {
                    "id": str(doc_id),
                    "description": content.get("text", ""),
                    "vector": [float(x) for x in content["vector"]]
                }
                documents.append(doc)
            except Exception as e:
                print(f"Error processing {doc_id}: {e}")

    if not documents:
        print("❌ No valid documents found to upload.")
        return

    print("Sample document:\n", json.dumps(documents[0], indent=2))
    print(f"Uploading {len(documents)} documents...")

    # Prepare API request for bulk upload
    upload_url = f"{endpoint}/indexes/{index_name}/docs/index?api-version={api_version}"
    actions = [{"@search.action": "upload", **doc} for doc in documents]
    payload = {"value": actions}

    response = requests.post(upload_url, headers=headers, json=payload)

    # Show status
    print("Upload status:", response.status_code)
    try:
        print("Response JSON:", response.json())
    except Exception:
        print("Response Text:", response.text)

# --------------------------------------------------------------
# 4. Run script
# --------------------------------------------------------------
if __name__ == "__main__":
    create_index()
    upload_documents()
