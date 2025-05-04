import json, http.client

HOST, PORT, MODEL = "localhost", 11434, "llama3.2"
CLASSES = ["comm_email", "summarization", "data_analysis", "other"]

def class_block(business_class):
    return (business_class, {"type":"object","properties":{
        "why":{"type":"string"}, "likelihood":{"type":"number","minimum":0,"maximum":1}
    },"required":["why","likelihood"],"additionalProperties": False})

FORMAT = {
    "title": "Prompt Classification", "type": "object",
    "properties": dict([*map(class_block, CLASSES)] + [
        ("final_why", {"type": "string"}),
        ("top_class", {"type": "string", "enum": CLASSES}),
        ("final_likelihood", {"type": "number", "minimum": 0, "maximum": 1}),
        ("other_label", {"type": "string"})
    ]),
    "required": CLASSES + ["final_why", "top_class", "final_likelihood", "other_label"],
    "additionalProperties": False
}

#print("format = " + json.dumps(FORMAT, indent=2, sort_keys=False))

SYSTEM_PROMPT = (
  f"You classify prompts into: {', '.join(CLASSES)}.\n"
  "- For each class, output: why (1 sentence), likelihood in [0,1]. Sum ≈ 1.\n"
  "- Set final_why: one short sentence explaining which class fits best overall considering all 'why'.\n"
  "- Set top_class = your ultimate choice after considering all reasons.\n"
  "- Set final_likelihood = the likelihood that top_class is correct, in [0,1].\n"
  "- If none of the listed classes fits well (e.g., all likelihoods < 0.5), choose 'other' and set other_label to a short snake_case tag for the proposed class."
)

def classify_prompt(user_prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {"role":"system","content": SYSTEM_PROMPT},
            {"role":"user","content": f"Classify this prompt:\n\n{user_prompt}"}
        ],
        "temperature": 0.0, "top_p": 1, "max_tokens": 1024, 
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "PromptClassification", "schema": FORMAT, "strict": True}
        }
    }
    conn = http.client.HTTPConnection(HOST, PORT)
    try:
        conn.request("POST", "/v1/chat/completions", json.dumps(payload), {"Content-Type": "application/json"})
        data = json.loads(conn.getresponse().read().decode())
        print(json.dumps(json.loads(data["choices"][0]["message"]["content"]), indent=2, sort_keys=False))
    finally:
        conn.close()

if __name__ == "__main__":
    for p in [
        "Write a polite follow-up email to a supplier about a delayed shipment.",
        "Summarize the attached Q3 operations report in 5 bullets.",
        "From this CSV of weekly sales by region, identify trends and anomalies.",
        "Write a catchy LinkedIn post announcing our company’s participation in the Green Tech Expo." # -> should fill other_label
    ]: classify_prompt(p)
