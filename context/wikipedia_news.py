import difflib
import mwclient
from langchain_ollama import ChatOllama
from datetime import datetime, timedelta

def wikipedia_news(page_title, weeks):
    page = mwclient.Site('en.wikipedia.org').pages[page_title]
    prev_content, lines = None, []
    for rev in page.revisions(start=datetime.now() - timedelta(weeks=weeks), dir='newer', prop='content'):
        current_content = rev.get('*', '')
        if prev_content:
            diff_lines = difflib.unified_diff(prev_content.splitlines(), current_content.splitlines(), lineterm='')
            lines.extend(line for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
        prev_content = current_content
    return lines

def analyst(news):
    llm = ChatOllama(model = "gemma3:4b", temperature = 0.1, num_predict = 1024)
    messages = [
        ("system",  "You are a news assistant and a financial analyst. Summarize and analyse the text from the user input. The user reports company news. " +
                    "Make sections about the following topics: what happened, is this good or bad for the company, what is the possible impact on the stock price."),
        ("human", news),
    ]
    return llm.invoke(messages).content

companies = ["Tesla, Inc.", "Apple Inc.", "Microsoft Corporation", "Amazon.com, Inc.", "Alphabet Inc.", "Facebook, Inc.",
             "NVIDIA Corporation", "PayPal Holdings, Inc.", "Netflix, Inc.", "Adobe Inc.", "Salesforce.com, Inc.", "Intel Corporation",
             "Cisco Systems, Inc.", "Oracle Corporation", "IBM", "Qualcomm Inc.", "Zoom Video Communications, Inc.", "Spotify Technology S.A.",
             "Snap Inc.", "Twitter, Inc.", "Uber Technologies, Inc.", "Lyft, Inc.", "Airbnb, Inc.", "DoorDash, Inc.",
             "Palantir Technologies Inc.", "Snowflake Inc.", "Roblox Corporation", "Coinbase Global, Inc.", "Unity Software Inc.",
             "C3.ai, Inc.", "UiPath Inc.", "Asana, Inc.", "Slack Technologies, Inc.", "Atlassian Corporation Plc"]
news = '\n'.join(wikipedia_news("Tesla, Inc.", 1))
#print(news)
print(analyst(news))
