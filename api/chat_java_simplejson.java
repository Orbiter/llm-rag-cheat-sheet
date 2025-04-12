import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpRequest.BodyPublishers;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class chat_java_simplejson {
    public static void main(String[] args) throws Exception {
        var payload = Map.of(
            "model", "llama3.2",
            "temperature", 0.1,
            "max_tokens", 1024,
            "messages", List.of(
                Map.of("role", "system", "content", "You are a helpful assistant."),
                Map.of("role", "user", "content", "Hello, how are you?")
            ),
            "stream", false
        );
        String jsonPayload = SimpleJson.json2string(payload);
        var client = HttpClient.newHttpClient();
        var request = HttpRequest.newBuilder()
            .uri(URI.create("http://localhost:11434/v1/chat/completions"))
            .header("Content-Type", "application/json")
            .POST(BodyPublishers.ofString(jsonPayload))
            .build();
        var response = client.send(request, HttpResponse.BodyHandlers.ofString());
        System.out.println(SimpleJson.format(response.body()));
    }

    private static class SimpleJson {
        public static String json2string(Object obj) {
            if (obj == null) return "null";
            if (obj instanceof String) return "\"" + ((String)obj).replace("\"", "\\\"") + "\"";
            if (obj instanceof Number || obj instanceof Boolean) return obj.toString();
            if (obj instanceof Map) {
                var sb = new StringBuilder("{");
                var first = true;
                for (var entry : ((Map<?,?>)obj).entrySet()) {
                    if (!first) sb.append(",");
                    sb.append(json2string(entry.getKey())).append(":").append(json2string(entry.getValue()));
                    first = false;
                }
                return sb.append("}").toString();
            }
            if (obj instanceof List) {
                var sb = new StringBuilder("[");
                var first = true;
                for (var item : (List<?>)obj) {
                    if (!first) sb.append(",");
                    sb.append(json2string(item));
                    first = false;
                }
                return sb.append("]").toString();
            }
            return "\"" + obj.toString().replace("\"", "\\\"") + "\"";
        }

        public static String format(String json) {
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
}
