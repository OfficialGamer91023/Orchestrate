import json
from app.services.router import route_messages
from app.services.data_loader import data_loader

def main():
    data_loader.load()
    golden = []
    for _, row in data_loader.sample_messages.iterrows():
        if row.get("action"):
            golden.append({
                "message_id": row["message_id"],
                "action": row["action"],
                "text": row.get("message_text", "")
            })
    
    gold_map = {g["message_id"]: g for g in golden}
    
    # We will route the sample messages
    results = route_messages(data_loader.sample_messages)
    
    misclassified = []
    for r in results:
        msg_id = r["message_id"]
        pred_action = r["action"]
        if msg_id in gold_map:
            gold_action = gold_map[msg_id]["action"]
            if pred_action != gold_action:
                misclassified.append({
                    "message_id": msg_id,
                    "text": gold_map[msg_id]["text"],
                    "predicted": pred_action,
                    "golden": gold_action,
                    "reasoning": r.get("reason", "")
                })
                
    print(f"Total misclassified: {len(misclassified)}")
    for m in misclassified:
        print(json.dumps(m, indent=2))

if __name__ == "__main__":
    main()
