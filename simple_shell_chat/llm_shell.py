import sys
import time
import json
import queue
import random
import urllib3
import argparse
import threading
import http.client
import concurrent.futures
from urllib.parse import urlparse


POISON_OUTPUT_TOKEN = "***POISON_OUTPUT_TOKEN***" # token to indicate end of output in output_queue
SYSTEM_PROMPT = "Be very helpful."

def request_response_base(method, api_url, body=None, key=None):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    encoded_body = json.dumps(body).encode('utf-8') if body else None
    headers = {'Accept': 'application/json'}
    if encoded_body:
        headers['Content-Type'] = 'application/json'
        headers['Content-Length'] = str(len(encoded_body))
    if key: headers['Authorization'] = 'Bearer ' + key
    api_url = urlparse(api_url)
    if api_url.scheme == "https":
        conn = http.client.HTTPSConnection(api_url.netloc)
    else:
        conn = http.client.HTTPConnection(api_url.netloc)
    conn.request(method, api_url.path, body=encoded_body, headers=headers)
    response = conn.getresponse()
    return response, conn

def request_response(method, api_url, body=None, key=None):
    response, conn = request_response_base(method, api_url, body, key)
    status_code = response.status

    if status_code == 301:
        new_path = response.getheader('Location')
        conn.close()
        api_url_parsed = urlparse(api_url)
        new_url = new_path if new_path.startswith("http") else f"{api_url_parsed.scheme}://{api_url_parsed.netloc}{new_path}"
        response, conn = request_response("GET", f"{new_url}", body, key)
        status_code = response.status
    
    return response, conn

def ollama_list(endpoint):
    response, conn = request_response("GET", f"{endpoint}/api/tags", None, None)
    status_code = response.status
    if status_code != 200:
        raise Exception(f"Unexpected status code: {status_code}")
    data = json.loads(response.read())
    conn.close()
    models_dict = {
        entry['model']: {
            'parameter_size': float(entry['details']['parameter_size'][:-1]),
            'quantization_level': entry['details']['quantization_level'][1:2]
        }
        for entry in data['models']
    }

    return models_dict

def ollama_ps(endpoint):
    response, conn = request_response("GET", f"{endpoint}/api/ps", None, None)
    data = json.loads(response.read())
    conn.close()
    models_dict = {
        entry['model']: {
            'parameter_size': float(entry['details']['parameter_size'][:-1]),
            'quantization_level': entry['details']['quantization_level'][1:2]
        }
        for entry in data['models']
    }
    return models_dict


def chat(endpoint, output_queue, model, context, prompt='Hello World', stream = False, temperature=0.0, max_tokens=8192, response_format=None):
    context.append({"role": "user", "content": prompt})
    body = {
        "top_p": 0.7,
        "stream": stream,
        "messages": context,
        "presence_penalty": 0.3,
        "frequency_penalty": 0.7,
        "max_tokens": max_tokens,
        "max_completion_tokens": max_tokens,
        "temperature": temperature,
        "model": model,
        "response_format": { "type": "text" },
        "stop": ["[/INST]", "<|im_end|>", "<|end_of_turn|>", "<|eot_id|>", "<|end_header_id|>", "<EOS_TOKEN>", "</s>", "<|end|>"]
    }
    if response_format:
        if not "json" in prompt.lower(): body["messages"][-1]["content"] += "\n return a json object as response"
        body["response_format"] = {"type": "json_schema", "json_schema": {"schema": response_format}}
    
    t_0 = time.time()
    response, conn = request_response("POST", endpoint + "/v1/chat/completions", body, None)
    POISON_PILL = "data: [DONE]"
    if stream:
        total_tokens = 0
        for line in response:
            t = line.decode('utf-8').strip()
            if not t or len(t) < 6: continue
            if POISON_PILL in t or '"finish_reason":"stop"' in t:
                conn.close()
                if output_queue: output_queue.put("\n\n")
                t_1 = time.time()
                token_per_second = total_tokens / (t_1 - t_0)
                return total_tokens, token_per_second

            t = t[6:] # remove "data: "
            if not t: continue

            try:
                t = json.loads(t)
                token = t.get('choices', [{}])[0].get('delta', {}).get('content', '')
                if output_queue: output_queue.put(token)
                total_tokens += 1
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse JSON response from the API: {e}, t: {t}")
        # if we reach here, the stream was closed
        return total_tokens, token_per_second
    else:
        data = response.read()
        conn.close()

        try:
            data = json.loads(data)
            usage = data.get('usage', {})
            total_tokens = usage.get('total_tokens', 0)
            t_1 = time.time()
            token_per_second = total_tokens / (t_1 - t_0)
            choices = data.get('choices', [])
            if not choices: raise Exception("No response from the API: " + str(data))
            message = choices[0].get('message', {})
            answer = message.get('content', '')
            if output_queue:
                for line in answer.split('\n'):
                    output_queue.put(f"{line}\n")
                    time.sleep(0.1)
            context.append({"role": "assistant", "content": answer})
            return total_tokens, token_per_second
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response from the API: {e}")

# initialize status: this is a dictionary that holds the current state of the console
def initialize_status(endpoint, preferred_model, output_queue):
    return {
        "endpoint": endpoint, # endpoint url stub
        "model": preferred_model,
        "context": [{"role": "system", "content": SYSTEM_PROMPT}],
        "multi_line": False,
        "input_lines": [],
        "output_queue": output_queue
    }

# queue printer which prints all items in the queue until the poison token is found
def queue_printer(output_queue):
    while True:
        item = output_queue.get()
        if item == POISON_OUTPUT_TOKEN:
            break
        print(item, end="")
        sys.stdout.flush()

# compute responses
def console(status, prompt):
    output_queue = status["output_queue"]

    # parse and execute the prompt
    if prompt == '': # ignore empty lines / respond with empty lines (gives batch outputs a better structure)
        output_queue.put("\n")
        return

    if prompt == '/clear':
        status["context"] = {"role": "system", "content": SYSTEM_PROMPT}
        output_queue.put("Cleared session context\n")
        output_queue.put("\n")
        return

    if prompt == '/ollama ls':
        output_queue.put("Available models:\n")
        models_acc_dict = {}
        model_max_len = 0
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(ollama_list, endpoint): endpoint for endpoint in status["endpoints"]}
            for future in concurrent.futures.as_completed(futures):
                endpoint = futures[future]
                try:
                    models_dict = future.result()
                    for model, attr in models_dict.items():
                        model_max_len = max(model_max_len, len(model))
                        if model not in models_acc_dict:
                            models_acc_dict[model] = 1
                        else:
                            models_acc_dict[model] += 1
                except Exception as e:
                    output_queue.put(f"Error fetching models from endpoint {endpoint['api_base']}: {e}\n")
        output_queue.put(f"Model Name {' '*(model_max_len-22)} # of Endpoints\n")
        output_queue.put(f"{'-'*(model_max_len+4)}\n")
        for (model, count) in models_acc_dict.items():
            output_queue.put(f"{model} {' '*(model_max_len-len(model))} {count}\n")
        output_queue.put("\n")
        return
    
    if prompt == '/ollama ps':
        output_queue.put("Running models:\n")
        models_acc_dict = {}
        endpoint = status["endpoint"]
        models_dict = ollama_ps(endpoint)
        for (model, attr) in models_dict.items():
            models_acc_dict[model] = endpoint["api_base"]
        for (model, endpoint) in models_acc_dict.items():
            output_queue.put(f"{model} {endpoint}\n")
        output_queue.put("\n")
        return
    
    if prompt == '/model':
        output_queue.put(f"Current model is '{status['endpoint']['model']}'\n")
        output_queue.put("\n")
        return

    if prompt.startswith('/model '):
        try:
            token = prompt.split(' ')
            if len(token) < 3:
                model_name = token[1].strip()
            elif token[1].strip() == "run":
                model_name = token[2].strip()
            else:
                output_queue.put(f"Error switching to a model: wrong syntax")
                output_queue.put("\n")
                return
            
            # search for any endpoint that has the model. If found, the model can be selected
            endpoint = status["endpoint"]
            try:
                models_dict = ollama_list(endpoint)
                if model_name in models_dict:
                    status["model"] = model_name
                    output_queue.put(f"Switched to model '{model_name}'\n")
                    output_queue.put("\n")
                    return
            except Exception as e:
                pass
            
            output_queue.put(f"A model with name '{model_name}' does not exist\n")
            output_queue.put("\n")
            return
        except Exception as e:
            output_queue.put(f"Error switching model: {e}\n")
            output_queue.put("\n")
            return

    endpoint = status["endpoint"]
    chat(endpoint, output_queue, status["model"], status["context"], prompt=prompt, stream=True)

# process commands line by line, handles multi-line inputs
def terminal(status, command_line):
    if command_line == '"""':
        if status["multi_line"]:
            status["multi_line"] = False
            console(status, "\n".join(status["input_lines"]))
            return

        status["multi_line"] = True
        status["input_lines"] = []
        return
    
    if status["multi_line"]:
        status["input_lines"].append(command_line)
        return

    console(status, command_line)

def main():
    parser = argparse.ArgumentParser(description='AI Command Line Tools')
    parser.add_argument('model', nargs='?', default='llama3.2:latest', help='An additional parameter for the command')
    parser.add_argument('--api', action='append', help="Specify backend OpenAI API endpoints (i.e. ollama); can be used multiple times")

    args = parser.parse_args()
    
    # initialize output queue and status
    output_queue = queue.Queue()
    output_queue_thread = threading.Thread(target=queue_printer, args=(output_queue,), daemon=True)
    output_queue_thread.start()
    endpoint = args.api if args.api else "http://localhost:11434"
    status = initialize_status(endpoint, args.model, output_queue)

    # run the shell
    while True:
        # read user input
        while not output_queue.empty(): time.sleep(0.1) # wait until the output queue is empty
        print("... " if status["multi_line"] else ">>> ", end="") # the prompt is not placed in the output_queue!
        sys.stdout.flush()
        user_input = input()
        user_input = user_input.replace('\\', '/') # fix mistakes in input
        
        # handle termination
        if user_input == '/bye': break

        # pass user input to terminal
        terminal(status, user_input)

    # wait for output queue to finish
    output_queue.put(POISON_OUTPUT_TOKEN)
    output_queue_thread.join()

if __name__ == "__main__":
    main()
