import os
import json
import random
import sys 

current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(current_file_dir) 

if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

from src.pdf_scraper import extract_text_from_pdf 
from src.question_parser import parse_ela_questions 
from src.user_progress import load_completed_questions, save_completed_questions 


def get_ela_questions_file_path():
    current_dir = os.path.dirname(os.path.abspath(__file__)) # Ensure absolute path
    file_path = os.path.join(current_dir, '..', 'data', 'processed_questions', 'ela_questions.json')
    return os.path.abspath(file_path)

def ensure_questions_parsed():
    processed_questions_path = get_ela_questions_file_path()
    
    if os.path.exists(processed_questions_path):
        print("Loading pre-parsed questions...")
        with open(processed_questions_path, 'r', encoding='utf-8') as f:
            all_questions = json.load(f)
        print(f"Loaded {len(all_questions)} questions.")
    else:
        print("Pre-parsed questions not found. Starting PDF scraping and parsing...")
        current_dir = os.path.dirname(os.path.abspath(__file__)) # Ensure absolute path
        pdf_file_path = os.path.join(current_dir, '..', 'data', 'raw_pdfs', 'SAT Suite Question Bank ELA - Results.pdf')
        pdf_file_path = os.path.abspath(pdf_file_path)

        if not os.path.exists(pdf_file_path):
            print(f"Error: Raw PDF not found at {pdf_file_path}. Please place 'SAT Suite Question Bank ELA - Results.pdf' in the raw_pdfs folder.")
            return []

        full_text = extract_text_from_pdf(pdf_file_path)
        if not full_text:
            print("Failed to extract text from PDF. Cannot parse questions.")
            return []

        all_questions = parse_ela_questions(full_text)
        
        os.makedirs(os.path.dirname(processed_questions_path), exist_ok=True)
        with open(processed_questions_path, 'w', encoding='utf-8') as f:
            json.dump(all_questions, f, indent=2, ensure_ascii=False)
        print(f"Parsed {len(all_questions)} questions and saved to {processed_questions_path}")

    return all_questions

def run_ela_test():
    all_questions = ensure_questions_parsed()
    if not all_questions:
        print("No questions available to run the test.")
        return

    completed_question_ids = set(load_completed_questions())
    
    available_questions = [q for q in all_questions if q['id'] not in completed_question_ids]

    if not available_questions:
        print("Congratulations! You have completed all available questions.")
        return

    print(f"\nWelcome to the SAT ELA Test Practice!")
    print(f"You have {len(available_questions)} uncompleted questions available.")

    while True:
        try:
            num_questions_str = input(f"How many questions do you want for this ELA test (1-{len(available_questions)})? ")
            num_questions = int(num_questions_str)
            if 1 <= num_questions <= len(available_questions):
                break
            else:
                print(f"Please enter a number between 1 and {len(available_questions)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    random.shuffle(available_questions)
    session_questions = available_questions[:num_questions]
    
    newly_completed_ids = []
    
    print("\n--- Starting Test ---")
    for i, question in enumerate(session_questions):
        print(f"\nQuestion {i + 1} of {len(session_questions)} (ID: {question['id']})")
        print(f"Domain: {question['domain']} | Skill: {question['skill']} | Difficulty: {question['difficulty']}")
        print("\n" + question['question_text'])
        for choice_key, choice_text in question['choices'].items():
            print(f"{choice_key}. {choice_text}")
        
        user_answer = input("Your answer (A, B, C, D): ").strip().upper()
        
        while user_answer not in ['A', 'B', 'C', 'D']:
            print("Invalid choice. Please enter A, B, C, or D.")
            user_answer = input("Your answer (A, B, C, D): ").strip().upper()
            
        print(f"\nYour answer: {user_answer}")
        print(f"Correct answer: {question['correct_answer']}")
        
        if user_answer == question['correct_answer']:
            print("Result: Correct!")
        else:
            print("Result: Incorrect.")
        
        # Removed explanation display
        # print("\nExplanation:")
        # print(question['explanation'])
        
        newly_completed_ids.append(question['id'])

        if i < len(session_questions) - 1:
            input("\nPress Enter to continue to the next question...")

    updated_completed_ids = list(completed_question_ids.union(set(newly_completed_ids)))
    save_completed_questions(updated_completed_ids)
    
    print("\n--- Test Complete ---")
    print("Your progress has been saved.")
    print(f"You completed {len(newly_completed_ids)} questions in this session.")
    print(f"Total questions completed: {len(updated_completed_ids)}.")

if __name__ == "__main__":
    run_ela_test()
