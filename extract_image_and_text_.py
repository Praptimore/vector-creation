import fitz  # PyMuPDF
import os
import json
import re

# ========== CONFIGURATION ==========
pdf_path = "KrauseGuide1601_1700.pdf"  # Your large PDF
output_folder = "KrauseGuide_Output"
images_folder = os.path.join(output_folder, "images")
json_path = os.path.join(output_folder, "km_image_text.json")

# PDF split chunk size
chunk_size = 80

# Tolerances for matching image and text horizontally and vertically
horizontal_tolerance = 50  # points tolerance for horizontal alignment
vertical_tolerance = -2    # allow small overlap vertically

# Regex pattern for KM number IDs in text
id_pattern = r"(KM#\s*\d+(?:-\d+)?(?:\.\d+)?)"

# Make sure folders exist
os.makedirs(images_folder, exist_ok=True)

# ================== FUNCTIONS ==================

def process_pages(doc, start_page, end_page, data, image_index):
    """
    Process a range of pages and update the data dictionary.
    Returns updated data dictionary and image index.
    """
    for page_num in range(start_page, min(end_page, len(doc))):
        page = doc[page_num]

        # Step 1: Extract all image info
        image_info = []
        for img in page.get_images(full=True):
            xref = img[0]
            rects = page.get_image_rects(xref)
            for r in rects:
                bbox = (r.x0, r.y0, r.x1, r.y1)
                center = ((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
                image_info.append({
                    "xref": xref,
                    "bbox": bbox,
                    "center": center
                })

        if not image_info:
            continue  # No images on this page

        # Step 2: Extract KM IDs in text
        text_blocks = page.get_text("dict")["blocks"]
        id_entries = []
        for block in text_blocks:
            if block['type'] != 0:  # Only text blocks
                continue
            block_text = " ".join(span['text'] for line in block['lines'] for span in line['spans']).strip()
            matches = re.findall(id_pattern, block_text)
            if matches:
                bbox = block['bbox']
                for match_id in matches:
                    id_entries.append({
                        "id": match_id.strip(),
                        "text": block_text,
                        "bbox": bbox
                    })

        if not id_entries:
            continue  # No KM text

        # Step 3: Match images to closest KM text
        for img_obj in image_info:
            img_x0, img_y0, img_x1, img_y1 = img_obj["bbox"]
            xref = img_obj["xref"]
            closest_id = None
            min_dist = float("inf")

            for ent in id_entries:
                ent_x0, ent_y0, ent_x1, ent_y1 = ent["bbox"]
                ent_center_x = (ent_x0 + ent_x1) / 2
                ent_top = ent_y0

                # Text must be below image
                if ent_top <= img_y1 + vertical_tolerance:
                    continue

                # Check horizontal alignment
                if ent_center_x < img_x0 - horizontal_tolerance or ent_center_x > img_x1 + horizontal_tolerance:
                    continue

                dist = ent_top - img_y1
                if dist < min_dist:
                    min_dist = dist
                    closest_id = ent

            # Save matched image and data
            if closest_id:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]
                filename = f"img_{image_index}.{ext}"
                img_path = os.path.join(images_folder, filename)
                with open(img_path, "wb") as f:
                    f.write(image_bytes)

                data[image_index] = {
                    "image": filename,
                    "page": page_num,
                    "unique_number": closest_id["id"],
                    "text": closest_id["text"]
                }
                image_index += 1

    return data, image_index


# ================== MAIN SCRIPT ==================
if __name__ == "__main__":
    # Load existing JSON if available
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    # Start image index correctly (continue from existing data)
    image_index = max(data.keys(), default=-1) + 1 if data else 0

    # Open PDF
    doc = fitz.open(pdf_path)

    total_pages = len(doc)
    print(f" Total pages: {total_pages}")

    # Process in chunks
    for start in range(0, total_pages, chunk_size):
        end = start + chunk_size
        print(f" Processing pages {start} to {min(end, total_pages)-1}")
        data, image_index = process_pages(doc, start, end, data, image_index)

        # Save intermediate JSON (checkpoint)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f" Saved progress after pages {start}-{end-1}")

    print(f"\n Completed. Total images mapped: {len(data)}")
    print(f" JSON output saved to {json_path}")
