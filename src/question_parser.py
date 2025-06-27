import re
import json
import os
import sys
import time # For timing

# Add the parent directory (satELA) to the Python path
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(current_script_dir) # This is 'satELA'
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

from src.pdf_scraper import extract_text_from_pdf

def clean_text(text):
    # Normalize Windows newlines to Unix
    text = re.sub(r'\r\n', '\n', text)
    # Remove form feed characters (page breaks) - typically represented as \f
    text = text.replace('\f', '')
    # Remove any general page headers like "--- PAGE \d+ ---" if present (though pdfminer might not add them)
    text = re.sub(r'--- PAGE \d+ ---', '', text)
    # Remove the "ID: <ID> Answer" line which often appears before the rationale and disrupts splitting
    # This line should be handled carefully; for now, let's keep it simple and remove known disruptive patterns.
    # Removed global removal of "ID: <ID> Answer" as it's better handled during block processing.
    # Replace non-breaking spaces with regular spaces
    text = text.replace('\xa0', ' ')
    # Reduce multiple newlines to at most two for paragraph separation
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Replace multiple spaces/tabs with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip() # Remove leading/trailing whitespace
    return text

def parse_ela_questions(full_pdf_text):
    start_parse_time = time.time()
    questions_data = []
    
    print("Cleaning text...")
    cleaned_text = clean_text(full_pdf_text)
    print(f"Text cleaning complete. Length: {len(cleaned_text)} characters.")
    
    # New strategy: Split into blocks by looking for "Question ID"
    # This regex is meant to reliably split the document into distinct question segments.
    # It accounts for "Question ID" appearing at the start of a line, potentially with leading whitespace.
    # Use re.split to get blocks directly based on the "Question ID" pattern
    # The ( ) around the pattern make sure the delimiter (including the ID) is included in the result list
    question_blocks_raw_split = re.split(r'(Question ID ([0-9a-fA-F]{8,}))', cleaned_text, flags=re.MULTILINE)
    
    # The split result will be: ['', 'Question ID <id1>', '<content1>', 'Question ID <id2>', '<content2>', ...]
    # We need to pair the ID with its content.
    
    raw_question_blocks = []
    # Skip the first empty string if it exists
    start_index = 1 if not question_blocks_raw_split[0] else 0 

    for i in range(start_index, len(question_blocks_raw_split) - 1, 3): # Iterate by 3s: ID_match_group, ID, content
        if i + 2 < len(question_blocks_raw_split):
            full_match_str = question_blocks_raw_split[i] # e.g., "Question ID 12345678"
            question_id = question_blocks_raw_split[i+1] # e.g., "12345678"
            content = question_blocks_raw_split[i+2]
            raw_question_blocks.append((question_id, content.strip()))

    print(f"Found {len(raw_question_blocks)} potential question blocks after initial split.")

    successfully_parsed_count = 0

    for i, (question_id, raw_block_content) in enumerate(raw_question_blocks):
        block_start_time = time.time()
        
        # Initialize defaults for each question at the start of the loop
        assessment = "N/A"
        test = "N/A"
        domain = "N/A"
        skill = "N/A"
        difficulty = "N/A"
        
        question_text = ""
        choices = {"A": "", "B": "", "C": "", "D": ""}
        correct_answer_choice = "N/A"
        explanation = ""
        
        content_for_parsing = raw_block_content # The content that regexes will search

        # --- Parse Metadata (Assessment, Test, Domain, Skill, Difficulty) ---
        # Adjusted metadata pattern: removed ID from pattern itself and fixed difficulty
        metadata_pattern = re.compile(
            r'Assessment\s*\n([^\n]+)\s*\n+'  # Assessment (Group 1)
            r'Test\s*\n([^\n]+)\s*\n+'       # Test (Group 2)
            r'Domain\s*\n([^\n]+(?:(?:\s*and\s*|\s*)\n[^\n]+)?)\s*\n+' # Domain (Group 3)
            r'Skill\s*\n([^\n]+)\s*\n+'      # Skill (Group 4)
            r'Difficulty\s*\n([^\n]+)\s*\n+',   # Difficulty (Group 5) - Fixed "Difficulty"
            re.DOTALL
        )
        
        meta_match = metadata_pattern.match(content_for_parsing)
        
        if meta_match:
            assessment = (meta_match.group(1) or '').strip()
            test = (meta_match.group(2) or '').strip()
            domain = (meta_match.group(3) or '').replace('\n', ' ').strip()
            skill = (meta_match.group(4) or '').strip()
            difficulty = (meta_match.group(5) or '').strip() 
            
            # Remove the matched metadata from the content for further parsing
            content_for_parsing = content_for_parsing[meta_match.end():].strip()
        # else: pass (defaults remain 'N/A')

        # Clean potential "ID: <ID> Answer" line if it's still present at the beginning of content_for_parsing
        content_for_parsing = re.sub(r'^ID:\s*[0-9a-fA-F]{8,}\s*Answer\s*\n*', '', content_for_parsing, 1, re.MULTILINE).strip()


        # --- Determine Question Text and the Section Containing Choices/Answer ---
        # Find the very first marker (A., B., C., D., or Correct Answer:)
        first_marker_in_content_pattern = re.compile(r'(A\.\s*|B\.\s*|C\.\s*|D\.\s*|Correct Answer:)', re.DOTALL)
        first_marker_match = first_marker_in_content_pattern.search(content_for_parsing)
        
        choices_and_answer_section_raw = ""
        if first_marker_match:
            question_text_raw = content_for_parsing[:first_marker_match.start()].strip()
            choices_and_answer_section_raw = content_for_parsing[first_marker_match.start():].strip()
        else:
            # If no choices/answer markers found, the entire content is just question text.
            question_text_raw = content_for_parsing.strip()
            choices_and_answer_section_raw = ""

        # --- Refine Question Text: Remove common prompts if they are at the end ---
        ela_prompts_raw = [
            r'Which choice most logically completes the text\??',
            r'Which quotation from .*? most effectively illustrates the claim\??',
            r'Which choice best states the main idea of the text\??',
            r'Which choice best describes data from the graph that support .*? conclusion\??',
            r'Which choice most effectively uses data from the graph to complete the .*?\??',
            r'Which finding, if true, would most directly support .*? claim\??',
            r'Which statement, if true, would most strongly support the claim in the underlined sentence\??',
            r'According to the text, .*?\??',
            r'Based on the text, .*?\??',
            r'Which choice best describes the function of the underlined (portion|sentence) in the text as a whole\??',
            r'Which choice best describes a difference in how the authors of Text 1 and Text 2 view .*?\??',
            r'Which choice best describes a similarity in how the authors of Text 1 and Text 2 view .*?\??',
            r'Based on the texts, how would the author of Text 2 most likely respond to the (underlined claim|assertion|assessment) .*?\??',
            r'Which question does the text most directly attempt to answer\??',
            r'What does the text most strongly suggest about .*?\??',
            r'Which choice best describes the overall structure of the text\??',
            r'Which choice completes the text with the most logical and precise word or phrase\??',
            r'As used in the text, what does the word ‚Äú.*?‚Äù most nearly mean\??',
            r'Which choice completes the text so that it conforms to the conventions of Standard English\??',
            r'Which choice best describes data from the graph that (support|illustrate) .*? conclusion\??',
            r'Which choice most effectively uses relevant information from the notes to accomplish this goal\??',
            r'Which choice most effectively uses relevant information from the notes to (introduce|emphasize) .*?\??',
            r'Which choice completes the text with the most logical transition\??',
            r'Which choice best describes data from the table that support .*? conclusion\??', 
            r'Which choice best states the main idea of the passage\??', 
            r'Which choice provides the best evidence for the answer to the previous question\??', 
            r'Which choice offers an accurate interpretation of the data in the graph\??',
            r'Which choice best describes the primary purpose of the text\??',
            r'Which choice most strongly supports the claim that .*?\??',
            r'Which choice provides the best evidence for the answer to the previous question\??', # Appears frequently
            r'Which choice most effectively uses information from the notes to accomplish this goal\??',
            r'The primary purpose of the text is to', # Common phrase ending a question
            r'Which choice completes the text with the most logical and precise word or phrase\?',
        ]
        
        prompt_remover_pattern = re.compile(r'(\n+\s*(?:' + '|'.join(ela_prompts_raw) + r'))\s*$', re.DOTALL | re.IGNORECASE)
        question_text = re.sub(prompt_remover_pattern, '', question_text_raw).strip()
        
        # --- Parse Choices (A, B, C, D) using explicit markers and slicing ---
        # Find the very first actual choice marker (A., B., C., or D.)
        first_actual_choice_marker_pattern = re.compile(r'(A\.\s*|B\.\s*|C\.\s*|D\.\s*)', re.DOTALL)
        first_actual_choice_match = first_actual_choice_marker_pattern.search(choices_and_answer_section_raw)

        choices_only_section = ""
        if first_actual_choice_match:
            # Start parsing choices from where the first actual choice marker was found
            choices_only_section = choices_and_answer_section_raw[first_actual_choice_match.start():].strip()
        else:
            # If no A., B., C., D. markers found, then there are no choices.
            # In this case, choices_only_section remains empty, and the content will be treated as rationale.
            choices_only_section = ""

        # Split the choices_only_section by choice markers and "Correct Answer:"
        # Use re.split with a pattern that captures the delimiters
        choice_split_parts = re.split(r'(A\.\s*|B\.\s*|C\.\s*|D\.\s*|Correct Answer:)', choices_only_section, flags=re.MULTILINE)
        
        current_choice_key = None
        remainder_for_answer_rationale = ""
        
        for part in choice_split_parts:
            part = part.strip()
            if not part:
                continue

            if part.startswith('A.'):
                current_choice_key = 'A'
            elif part.startswith('B.'):
                current_choice_key = 'B'
            elif part.startswith('C.'):
                current_choice_key = 'C'
            elif part.startswith('D.'):
                current_choice_key = 'D'
            elif part == 'Correct Answer:':
                current_choice_key = 'CORRECT_ANSWER_MARKER'
                # The rest of the content from here on is for correct answer and explanation
                remainder_for_answer_rationale = choices_only_section[choices_only_section.find('Correct Answer:'):].strip()
                break # Stop processing choices, move to answer/rationale extraction
            else:
                # This is the content for the current_choice_key
                if current_choice_key and current_choice_key in ['A', 'B', 'C', 'D']:
                    choices[current_choice_key] += (" " if choices[current_choice_key] else "") + part.strip()
        
        # --- Extract Correct Answer and Rationale ---
        # Adjusted for the "Rationale" to be optional and to correctly capture the end of the rationale.
        answer_rationale_pattern = re.compile(
            r'Correct Answer:\s*([A-D])\s*\n+' # Group 1: Correct Answer letter
            r'(?:Rationale\s*\n+(.*?))?' # Optional Group 2: Explanation (non-greedy, captures everything until end or next pattern)
            r'(?:\s*Question Difficulty:\s*(Hard|Medium|Easy))?', # Optional Group 3: Final Difficulty 
            re.DOTALL
        )
        
        ar_match = answer_rationale_pattern.search(remainder_for_answer_rationale)
        
        if ar_match:
            correct_answer_choice = (ar_match.group(1) or 'N/A').strip()
            explanation = (ar_match.group(2) or '').strip()

            if ar_match.group(3): # If difficulty found at end of rationale
                difficulty = ar_match.group(3).strip()
        
        # Filter out questions that don't have essential data after parsing
        # Check if question text is not empty and correct_answer is found
        # We allow choices to be potentially empty if they weren't properly parsed, but still attempt to include them.
        if (question_id and question_text and correct_answer_choice in ['A', 'B', 'C', 'D']):
            
            questions_data.append({
                "id": question_id,
                "assessment": assessment,
                "test": test,
                "domain": domain,
                "skill": skill,
                "difficulty": difficulty,
                "question_text": question_text,
                "choices": choices,
                "correct_answer": correct_answer_choice,
                "explanation": explanation
            })
            successfully_parsed_count += 1
        else:
            print(f"SKIPPING INCOMPLETE QUESTION: ID={question_id if question_id else 'UNKNOWN'} (Block {i+1}/{len(raw_question_blocks)})")
            print(f"  Q Text: {bool(question_text)}, Correct Answer: {correct_answer_choice}")
            # print(f"  Raw block content start:\n{raw_block_content[:500]}...") # Uncomment for very deep debug

        # Print time for every 10 blocks or if it takes too long
        if (i + 1) % 10 == 0 or (time.time() - block_start_time > 0.5): # Print every 10 blocks or if a single block takes > 0.5 sec
             print(f"Processed block {i+1}/{len(raw_question_blocks)} (ID: {question_id}). Time: {time.time() - block_start_time:.4f} seconds.")


    total_parse_time = time.time() - start_parse_time
    print(f"\n--- Parsing Summary ---")
    print(f"Total parsing (regex matching) time: {total_parse_time:.2f} seconds.")
    print(f"Successfully parsed {successfully_parsed_count} out of {len(raw_question_blocks)} potential blocks.")
    return questions_data

if __name__ == "__main__":
    current_dir = os.path.dirname(__file__)
    pdf_file_path = os.path.join(current_dir, '..', 'data', 'raw_pdfs', 'SAT Suite Question Bank ELA - Results.pdf')
    pdf_file_path = os.path.abspath(pdf_file_path)
    
    output_json_path = os.path.join(current_dir, '..', 'data', 'processed_questions', 'ela_questions.json')
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)

    print(f"Loading PDF text from: {pdf_file_path} using pdfminer.six")
    full_text = extract_text_from_pdf(pdf_file_path) # Uses the new pdfminer.six scraper

    if full_text:
        print("Starting parsing...")
        parsed_questions = parse_ela_questions(full_text)
        print(f"\nParsing complete. Found {len(parsed_questions)} questions.")

        if parsed_questions:
            print("\n--- First Parsed Question (JSON Output) ---")
            print(json.dumps(parsed_questions[0], indent=2))
            print("\n--- End of First Parsed Question ---")

            try:
                with open(output_json_path, 'w', encoding='utf-8') as f:
                    json.dump(parsed_questions, f, indent=2, ensure_ascii=False)
                print(f"\nParsed questions saved to: {output_json_path}")
            except Exception as e:
                print(f"Error saving parsed questions to JSON: {e}")
        else:
            print("No questions were parsed. This might indicate an issue with the regex patterns or PDF extraction.")
    else:
        print("Could not load PDF text, cannot parse questions.")