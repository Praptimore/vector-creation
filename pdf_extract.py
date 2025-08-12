# ---------------------------------------------------------
# This script extracts specific pages from a PDF file
# and saves them into a new PDF file.
# Useful for testing or when you only need certain pages.
# ---------------------------------------------------------

from PyPDF2 import PdfReader, PdfWriter  # Library to read and write PDF files

# ---------------------------------------------------------
# 1. File paths - where to read from and where to save
# ---------------------------------------------------------
input_pdf_path = "StandardCatalogofWorldCoins1801_1900.pdf"       # The original PDF file
output_pdf_path = "testing.pdf"  # The new PDF file with selected pages

# ---------------------------------------------------------
# 2. Open the PDF for reading
# ---------------------------------------------------------
reader = PdfReader(input_pdf_path)  # Load the original PDF
writer = PdfWriter()                # Create a new empty PDF

# ---------------------------------------------------------
# 3. Decide which pages to extract
# ---------------------------------------------------------
start_page = 687 # Page numbers start from 0 in programming, but here we use human numbering
end_page = start_page + 1  # This will extract 40 pages (from page 32 to page 71 in human terms)

# ---------------------------------------------------------
# 4. Loop through the selected pages and add them to new PDF
# ---------------------------------------------------------
for page_num in range(start_page, end_page):
    if page_num < len(reader.pages):  # Ensure we don't go beyond the total pages
        writer.add_page(reader.pages[page_num])  # Add this page to the new PDF

# ---------------------------------------------------------
# 5. Save the new PDF file
# ---------------------------------------------------------
with open(output_pdf_path, "wb") as output_pdf:
    writer.write(output_pdf)

print(f"✅ Extracted pages saved to: {output_pdf_path}")
