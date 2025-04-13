import json
import http.client

def verifier(proposition: str, compute_confidence: bool = True, binary: bool = True) -> bool:
    true_tokens = ["true", "True", "TRUE", "1", "Proven", "⊤", "T"]
    false_tokens = ["false", "False", "FALSE", "0", "Disproven", "⊥", "F"]
    undecided_tokens = ["maybe", "Maybe", "unknown", "Unknown", "undecided", "open", "undefined"]
    token_binary_options = [token for pair in zip(true_tokens, false_tokens) for token in pair]
    token_trinary_options = [token for pair in zip(true_tokens, false_tokens, undecided_tokens) for token in pair]
    schema = {
        "title": "Classifier", "type": "object",
        "properties": {
            "truth": {"type": "literal", "enum": token_binary_options if binary else token_trinary_options}
        },
        "required": ["truth"]
    }
    if compute_confidence:
        schema["properties"]["confidence"] = {"type": "number", "minimum": 0, "maximum": 100}
        schema["required"].append("confidence")
    system_message_undecided_direction = "- Clearly undecided (respond with undecided)\n"
    system_message_confidence_direction = "- confidence: a number between 0 and 100 that indicates your confidence in the truth of the proposition.\n"
    messages = [
        {"role": "system",
         "content": (
             "You are a truth classifier. Analyze the user's proposition and determine if it is: \n"
             "- Clearly true (respond with true)\n"
             "- Clearly false (respond with false)\n"
             "- Most likely true (respond with true)\n"
             "- Most likely false (respond with false)\n"
             + ("" if binary else system_message_undecided_direction)
             + "\nRespond with a JSON object containing your decision. "
             + ("Two values are" if compute_confidence else "One value is")
             + " expected in the JSON object:\n"
             "- truth: a string that is either 'true' or 'false'\n"
             + (system_message_confidence_direction if compute_confidence else "")
         )},
        {"role": "user",
         "content": proposition},
    ]
    data = {
        "model": "llama3.2", "temperature": 0.1, "max_tokens": 1024,
        "messages": messages, "stream": False, 
        "response_format": {
            "type": "json_schema",
            "json_schema": {"strict": True, "schema": schema}
        }
    }
    conn = http.client.HTTPConnection("localhost", 11434)
    conn.request("POST", "/v1/chat/completions", json.dumps(data), {"Content-Type": "application/json"})
    response = json.loads(conn.getresponse().read().decode())
    content = json.loads(response.get("choices", [{}])[0].get("message", {}).get("content", "").strip())
    conn.close()
    truth = content.get("truth", "false")
    if isinstance(truth, (int, float)): truth = str(truth)
    if truth.startswith("'"): truth = truth[1:]
    if truth.endswith("'"): truth = truth[:-1]
    truth_decision = truth in true_tokens
    if not binary and truth in undecided_tokens: truth_decision = None
    confidence = content.get("confidence", 0.5) if compute_confidence else 1.0
    if confidence > 1: confidence = confidence / 100 # some models return confidence in percentage
    return truth_decision, confidence

propositions = [
    ("5 > 3", True),
    ("1 == 2", False),
    ("This is a good day.", None),
    ("The sun rises in the east", True),
    ("Earth is flat", False),
    ("Water boils at 100°C", True),
    ("All men are equal", False),
    ("All men are created equal", True),
    ("Pigeons are robots", False),
    ("The moon is made of cheese", False),
    ("Cats are better than dogs", None),
    ("Dogs are better than cats", None),
    ("The earth revolves around the sun", True),
    ("The sun revolves around the earth", False),
    ("The earth is the center of the universe", False),
    ("The universe is expanding", True),
    ("The speed of light is constant", True),
    ("Gravity is a force that attracts two bodies towards each other", True),
    ("The Riemann Hypothesis is true", None),
    ("The Goldbach Conjecture is true", None),
    ("The Twin Prime Conjecture is true", None),
    ("P vs NP is true", None),
    ("The Halting Problem is undecidable", True),
    ("Gödel's Incompleteness Theorem is true", True),
]

# test the verifier function
correct = 0
for proposition, true_truth in propositions:
    computed_truth, confidence = verifier(proposition, True, False)
    if computed_truth != true_truth:
        print(f"Error: {proposition} -> {computed_truth}, confidence {confidence} (expected: {true_truth})")
    else:
        if confidence < 0.5:
            print(f"Warning - too low confidence: {proposition} -> {computed_truth}, confidence {confidence} (expected {true_truth})")
        else:
            correct += 1

print(f"Correct: {correct} / {len(propositions)}")


