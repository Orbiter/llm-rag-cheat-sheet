import difflib
import mwclient
from langchain_ollama import ChatOllama
from datetime import datetime, timedelta

def wikipedia_news(page_title, weeks):
    page = mwclient.Site('de.wikipedia.org').pages[page_title]
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
        ("system",  "Du bist ein Nachrichten-Assistent. Fasse die folgenden Nachrichten zusammen:"),
        ("human", news),
    ]
    return llm.invoke(messages).content

news = '\n'.join(wikipedia_news("Olaf_Scholz", 8))
print(news)
print(analyst(news))
