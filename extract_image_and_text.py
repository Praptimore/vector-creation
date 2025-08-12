# ---------------------------------------------------------
# This script extracts images from a PDF and matches them
# with an identifier (such as "KM# 488", "C# 5-10.5", etc.)
# found in the text below each image.
# It uses bounding boxes and clustering to figure out which
# image goes with which number.
# ---------------------------------------------------------
import fitz  # PyMuPDF – used to read PDF files, extract text, images, and positions
import os    # For creating folders and managing file paths
import json  # To save the extracted data as a structured JSON file
import re    # For finding identifier patterns in text
from sklearn.cluster import KMeans  # For grouping items into columns based on their positions
import numpy as np  # For handling numeric data like coordinates

# ---------------------------------------------------------
# 1. File paths and folder setup.
# ---------------------------------------------------------
pdf_path = "testing.pdf"                       # PDF file to process
output_folder = "final_testing"                # Folder where results will be saved
images_folder = os.path.join(output_folder, "images1")  # Subfolder for extracted images
json_path = os.path.join(output_folder, "km_image_text2.json")  # JSON file for mapping results

# Create folders if they do not exist
os.makedirs(images_folder, exist_ok=True)

# ---------------------------------------------------------
# 2. Pattern to find identifiers (like "KM# 488", "C# 5-10.5", "Y# 6.12", etc.)
# ---------------------------------------------------------
id_pattern = r"([A-Z]+#\s*\d+(?:-\d+)?(?:\.\d+)?)"

# ---------------------------------------------------------
# 3. Open the PDF for processing
# ---------------------------------------------------------
doc = fitz.open(pdf_path)
data = {}              # Dictionary to store final image → identifier mapping
image_index = 0        # Counter to give unique names to extracted images

# ---------------------------------------------------------
# 4. Go through each page in the PDF
# ---------------------------------------------------------
for page_num in range(len(doc)):
    page = doc[page_num]

    # Extract all content blocks (text, image, etc.) along with positions
    text_instances = page.get_text("dict")["blocks"]

    # Get image metadata for this page
    page_images = page.get_images(full=True)

    # ---------------------------------------------------------
    # Step 1: Find all identifier text entries on this page
    # ---------------------------------------------------------
    id_entries = []
    for block in text_instances:
        if block['type'] == 0:  # type 0 = text block
            block_text = ""
            for line in block['lines']:
                for span in line['spans']:
                    block_text += span['text'] + " "

            # Look for pattern in the text
            match = re.search(id_pattern, block_text)
            if match and match.group(1):
                unique_id = match.group(1).strip()
                bbox = block['bbox']  # (x0, y0, x1, y1) position of the text block
                id_entries.append({
                    "id": unique_id,
                    "text": block_text.strip(),
                    "bbox": bbox
                })

    # Skip the page if there are no id entries or no images
    if not id_entries or not page_images:
        continue

    # ---------------------------------------------------------
    # Step 2: Identify image blocks and get their positions
    # ---------------------------------------------------------
    image_blocks = [block for block in text_instances if block["type"] == 1]  # type 1 = image block

    image_coords = []  # Stores x-centers for clustering
    image_info = []    # Stores full image data

    for block in image_blocks:
        bbox = block["bbox"]
        x0, y0, x1, y1 = bbox
        x_center = (x0 + x1) / 2
        y_center = (y0 + y1) / 2

        # Find the image's "xref" (internal reference number in the PDF)
        matching_xref = None
        for img in page_images:
            xref = img[0]
            try:
                rect = page.get_image_rects(xref)[0]
                if abs(rect.x0 - x0) < 2 and abs(rect.y0 - y0) < 2:
                    matching_xref = xref
                    break
            except Exception:
                continue

        if not matching_xref:
            continue

        image_coords.append([x_center])
        image_info.append({
            "xref": matching_xref,
            "center": (x_center, y_center),
            "bbox": bbox
        })

    if not image_info:
        continue

    # ---------------------------------------------------------
    # Step 3: Group images into columns using KMeans clustering
    # ---------------------------------------------------------
    kmeans = KMeans(n_clusters=3, random_state=42)  # Assuming PDF has 3 main vertical columns
    X = np.array(image_coords)
    labels = kmeans.fit_predict(X)

    # Add cluster label to each image
    for i in range(len(image_info)):
        image_info[i]["cluster"] = labels[i]

    # ---------------------------------------------------------
    # Step 4: Match each image to the closest id below it in same column
    # ---------------------------------------------------------
    for img_obj in sorted(image_info, key=lambda x: x["center"][1]):  # Sort top to bottom
        img_cluster = img_obj["cluster"]
        img_y = img_obj["center"][1]
        xref = img_obj["xref"]

        closest_id = None
        min_dist = float("inf")

        for ent in id_entries:
            ent_x_center = (ent["bbox"][0] + ent["bbox"][2]) / 2
            ent_y_center = (ent["bbox"][1] + ent["bbox"][3]) / 2

            # Predict cluster for id based on x-position
            ent_cluster = kmeans.predict([[ent_x_center]])[0]

            # Only match if:
            # 1. id is in same column (cluster)
            # 2. id is below the image on the page
            if ent_cluster == img_cluster and ent_y_center > img_y:
                dist = ent_y_center - img_y
                if dist < min_dist:
                    min_dist = dist
                    closest_id = ent

        # ---------------------------------------------------------
        # Step 5: Save the matched image and its details
        # ---------------------------------------------------------
        if closest_id:
            base_image = doc.extract_image(xref)  # Extract the actual image
            image_bytes = base_image["image"]
            ext = base_image["ext"]  # File extension (png, jpg, etc.)
            filename = f"img_{image_index}.{ext}"
            path = os.path.join(images_folder, filename)

            # Save image to folder
            with open(path, "wb") as f:
                f.write(image_bytes)

            # Save mapping data
            data[image_index] = {
                "image": filename,
                "page": page_num,
                "unique_number": closest_id["id"],
                "text": closest_id["text"]
            }

            image_index += 1

# ---------------------------------------------------------
# 5. Save the final image-to-id mapping as JSON
# ---------------------------------------------------------
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

# ---------------------------------------------------------
# 6. Print completion message
# ---------------------------------------------------------
print(f"✅ Mapping completed using bbox matching + KMeans with below-image logic. "
      f"{image_index} images mapped in {json_path}")
