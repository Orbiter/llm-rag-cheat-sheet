import sys
import time
import json
import queue
import urllib3
import argparse
import threading
import http.client
import concurrent.futures
from urllib.parse import urlparse

POISON_OUTPUT_TOKEN = "***POISON_OUTPUT_TOKEN***" # token to indicate end of output in output_queue
SYSTEM_PROMPT = "You are Simple-Shell-Chat. Behave silly and funny but give true, proper answers. If possible, use friendly emojies."

endpoint = "http://localhost:11434"
model = "llama3.2:latest"
input_lines = []
context = [{"role": "system", "content": SYSTEM_PROMPT}]

def request_response(method, api_url, body=None):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    headers = {'Accept': 'application/json'}
    if body:
        encoded_body = json.dumps(body).encode('utf-8')
        headers.update({'Content-Type': 'application/json', 'Content-Length': str(len(encoded_body))})

    api_url = urlparse(api_url)
    conn = http.client.HTTPSConnection(api_url.netloc) if api_url.scheme == "https" else http.client.HTTPConnection(api_url.netloc)
    conn.request(method, api_url.path, body=encoded_body if body else None, headers=headers)
    response = conn.getresponse()

    if response.status == 301:
        new_url = response.getheader('Location')
        conn.close()
        return request_response(method, new_url if new_url.startswith("http") else f"{api_url.scheme}://{api_url.netloc}{new_url}", body)

    return response, conn

# compute responses
def console(prompt):
    global context, model

    # parse and execute the prompt
    if prompt == '': # ignore empty lines / respond with empty lines (gives batch outputs a better structure)
        print("")
        return

    if prompt == 'clear':
        context = [{"role": "system", "content": SYSTEM_PROMPT}]
        print("Cleared session context")
        print("")
        return

    if prompt == 'ollama ls':
        print("Available models:")
        try:
            response, conn = request_response("GET", f"{endpoint}/api/tags", None)
            if response.status != 200: raise Exception(f"Unexpected status code: {response.status}")
            data = json.loads(response.read())
            conn.close()
            for entry in data['models']: print(f"{entry['model']}")
            print("")
        except Exception as e:
            print(f"Error fetching models from endpoint {endpoint}: {e}")
        return
    
    if prompt == 'ollama ps':
        print("Running models:")
        response, conn = request_response("GET", f"{endpoint}/api/ps", None)
        data = json.loads(response.read())
        conn.close()
        for entry in data['models']: print(f"{entry['model']} {entry['details']['parameter_size']} {entry['details']['quantization_level']}")
        print("")
        return
    
    if prompt == 'model':
        print(f"Current model is '{model}'")
        print("")
        return

    if prompt.startswith('model '):
        tokens = prompt.split()
        if len(tokens) == 2:
            model = tokens[1].strip()
        elif len(tokens) == 3 and tokens[1].strip() == "run":
            model = tokens[2].strip()
        else:
            print("Error switching to a model: wrong syntax")
        return

    # chat with model
    context.append({"role": "user", "content": prompt})
    body = {
        "top_p": 0.7, "stream": True, "messages": context, "presence_penalty": 0.3, "frequency_penalty": 0.7,
        "max_tokens": 8192, "max_completion_tokens": 8192, "temperature": 0.0, "model": model,
        "keep_alive": "24h", "response_format": { "type": "text" },
        "stop": ["[/INST]", "<|im_end|>", "<|end_of_turn|>", "<|eot_id|>", "<|end_header_id|>", "<EOS_TOKEN>", "</s>", "<|end|>"]
    }
    
    response, conn = request_response("POST", endpoint + "/v1/chat/completions", body)
    answer = ""
    for line in response:
        t = line.decode('utf-8').strip()
        if not t or len(t) < 6: continue
        if "data: [DONE]" in t or '"finish_reason":"stop"' in t:
            conn.close()
            print("\n")
            context.append({"role": "assistant", "content": answer})
            return 

        t = t[6:] # remove "data: "
        if not t: continue

        try:
            t = json.loads(t)
            token = t.get('choices', [{}])[0].get('delta', {}).get('content', '')
            print(token, end="", flush=True)
            answer += token
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response from the API: {e}, t: {t}")
        
def main():
    global endpoint, model
    parser = argparse.ArgumentParser(description='Simple Shell Chat')
    parser.add_argument('--model', type=str, required=False, default=model, help='An additional parameter for the command')
    parser.add_argument('--api', type=str, required=False, default=endpoint, help="Specify backend OpenAI API endpoints (i.e. ollama); can be used multiple times")

    args = parser.parse_args()
    endpoint = args.api
    model = args.model
    multi_line = False

    # run the shell
    while True:
        # read user input
        print("... " if multi_line else ">>> ", end="") # the prompt is not placed in the output_queue!
        sys.stdout.flush()
        command_line = input()
        command_line = command_line.replace('\\', '/') # fix mistakes in input
        
        # handle termination
        if command_line == 'bye': break

        # pass user input to terminal
        if command_line == '"""':
            if multi_line:
                multi_line = False
                console("\n".join(input_lines))
                continue

            multi_line = True
            input_lines = []
            continue
        
        if multi_line:
            input_lines.append(command_line)
            continue

        console(command_line)

if __name__ == "__main__":
    main()
