import json
import os

def get_user_progress_file_path():
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, '..', 'user_data', 'completed_questions.json')
    return os.path.abspath(file_path)

def load_completed_questions():
    filename = get_user_progress_file_path()
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(item) for item in data]
            else:
                print(f"Warning: Data in {filename} is not a list. Returning empty list.")
                return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filename}: {e}. Returning empty list.")
        return []
    except IOError as e:
        print(f"Error loading completed questions from file {filename}: {e}. Returning empty list.")
        return []

def save_completed_questions(question_ids):
    filename = get_user_progress_file_path()
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(list(set(question_ids)), f, indent=2, ensure_ascii=False)
        print(f"Successfully saved {len(set(question_ids))} completed question IDs to {filename}")
    except IOError as e:
        print(f"Error saving completed questions to file {filename}: {e}")

if __name__ == "__main__":
    print("Testing user_progress.py...")
    test_q_ids = ["q1", "q2", "q3", "q1"]
    save_completed_questions(test_q_ids)

    loaded_ids = load_completed_questions()
    print("Loaded IDs:", loaded_ids)

    loaded_ids.append("q4")
    save_completed_questions(loaded_ids)
    print("Reloaded IDs after adding q4:", load_completed_questions())