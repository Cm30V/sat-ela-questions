# satELA/src/pdf_scraper.py

import sys
import os
from pdfminer.high_level import extract_text as extract_text_pdfminer # Import pdfminer.six

# Add the parent directory (satELA) to the Python path
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(current_script_dir) # This is 'satELA'
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using pdfminer.six.

    Args:
        pdf_path (str): The full path to the PDF file.

    Returns:
        str: The extracted text from the PDF, or an empty string if an error occurs.
    """
    text = ""
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return ""
    try:
        # pdfminer.high_level.extract_text is a convenient function
        # It handles opening, parsing, and closing the PDF
        text = extract_text_pdfminer(pdf_path)
        return text
    except Exception as e:
        print(f"An error occurred while extracting text from {pdf_path} using pdfminer.six: {e}")
        return ""

if __name__ == "__main__":
    current_dir = os.path.dirname(__file__)
    pdf_file_path = os.path.join(current_dir, '..', 'data', 'raw_pdfs', 'SAT Suite Question Bank ELA - Results.pdf')
    pdf_file_path = os.path.abspath(pdf_file_path)

    print(f"Attempting to extract text from: {pdf_file_path} using pdfminer.six")
    extracted_content = extract_text_from_pdf(pdf_file_path)

    if extracted_content:
        print("\n--- First 2000 Characters of Extracted Text (pdfminer.six) ---")
        print(extracted_content[:2000]) # Increased snippet size for better view
        print("\n--- End of Snippet ---")
        
        # Save the full extracted text to a file for debugging
        output_txt_path = os.path.join(project_root_dir, 'extracted_full_text_for_debugging.txt')
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(extracted_content)
        print(f"\nFull extracted text saved to: {output_txt_path}")
    else:
        print("No text was extracted or an error occurred.")

