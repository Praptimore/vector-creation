import os
import json
import torch
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image

# --- Paths ---
json_path = "km_mapped_output/km_image_text.json"
images_folder = "km_mapped_output/images"

# --- Load JSON ---
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# --- Define image transform ---
transform = transforms.Compose([
    transforms.Resize((224, 224)),# Resize image to 224×224 pixels
    transforms.ToTensor(), # Convert to PyTorch tensor
    transforms.Normalize(mean=[0.485, 0.456, 0.406], # Normalize using ImageNet mean & std
                         std=[0.229, 0.224, 0.225])
])

# --- Load pretrained ResNet18 model ---
model = models.resnet18(pretrained=True)
model.eval()  # Set to eval mode
model = torch.nn.Sequential(*list(model.children())[:-1])  # Remove final classifier layer

# --- Generate embeddings ---
for idx, entry in data.items():
    image_path = os.path.join(images_folder, entry["image"])
    
    try:
        img = Image.open(image_path).convert("RGB")
        img_tensor = transform(img).unsqueeze(0)  # Add batch dimension

        with torch.no_grad():
            embedding = model(img_tensor).squeeze().numpy()  # Shape: (512,)
            vector = embedding.tolist()

        # Save vector in JSON
        data[idx]["vector"] = vector

    except Exception as e:
        print(f"⚠️ Failed to process image {entry['image']}: {e}")

# --- Save updated JSON ---
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("✅ Image vectors added to JSON file.")
