import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpRequest.BodyPublishers;
import java.util.Map;

public class chat_java_formatteronly { // requires Java 15+ for text blocks
    public static void main(String[] args) throws Exception {
        String jsonPayload = """
            {
                "model": "llama3.2",
                "temperature": 0.1,
                "max_tokens": 1024,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, how are you?"}
                ],
                "stream": false
            }
            """;
        var client = HttpClient.newHttpClient();
        var request = HttpRequest.newBuilder()
            .uri(URI.create("http://localhost:11434/v1/chat/completions"))
            .header("Content-Type", "application/json")
            .POST(BodyPublishers.ofString(jsonPayload))
            .build();
        var response = client.send(request, HttpResponse.BodyHandlers.ofString());
        System.out.println(formatJson(response.body()));
    }

    private static String formatJson(String json) {
        int i = 0;
        var r = new StringBuilder();
        for (char c : json.toCharArray()) {
            if (c == '{' || c == '[') r.append(c).append("\n").append("  ".repeat(++i));
            else if (c == '}' || c == ']') r.append("\n").append("  ".repeat(--i)).append(c);
            else if (c == ',') r.append(c).append("\n").append("  ".repeat(i));
            else r.append(c);
        }
        return r.toString();
    }
}