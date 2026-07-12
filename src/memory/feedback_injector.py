import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
FEEDBACK_FILE = BASE_DIR / "agent_memory" / "human_feedback.jsonl"

def get_relevant_feedback(setup_type: str = None) -> str:
    """
    Reads the human feedback file and returns a formatted string of lessons learned
    for the specific setup_type. If setup_type is None, it returns all feedback.
    """
    if not FEEDBACK_FILE.exists():
        return ""
        
    lessons = []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    # If setup_type is provided, filter by it. Allow if setup is unknown.
                    if setup_type and data.get("fabio_setup") != setup_type:
                        continue
                        
                    date = data.get("date", "Unknown Date")
                    text = data.get("feedback_text", "").strip()
                    if text:
                        lessons.append(f"- [{date}] {text}")
                except json.JSONDecodeError:
                    continue
                    
        if not lessons:
            return ""
            
        header = f"\n\n--- CRITICAL HUMAN FEEDBACK LESSONS FOR {setup_type.upper() if setup_type else 'TRADING'} ---\n"
        header += "The human operator has previously corrected the agent's behavior. You MUST follow these rules strictly:\n"
        return header + "\n".join(lessons) + "\n--------------------------------------------------\n"
        
    except Exception as e:
        print(f"Error loading human feedback: {e}")
        return ""
