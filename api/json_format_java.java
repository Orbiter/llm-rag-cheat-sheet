import java.net.URI;
import java.net.http.*;
import java.net.http.HttpRequest.BodyPublishers;
import java.util.*;

public class json_format_java {
    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        Map<String, Object> format = new java.util.LinkedHashMap<>();
        format.put("title", "Translation");
        format.put("type", "object");
        format.put("properties", new java.util.LinkedHashMap<>(Map.of(
            "english", Map.of("type", "string"),
            "german", Map.of("type", "string"),
            "spanish", Map.of("type", "string"),
            "italian", Map.of("type", "string")
        )));
        format.put("required", List.of("german", "spanish"));
        List<?> messages = List.of(
            Map.of("role", "system", "content", "Translate the user sentence."),
            Map.of("role", "user", "content", "I love programming.")
        );
        Map<String, ?>  payload = Map.of(
            "model", "llama3.2", "temperature", 0.1, "max_tokens", 1024,
            "messages", messages, "stream", false, "format", format
        );
        String jsonPayload = SimpleJson.json2string(payload);
        var client = HttpClient.newHttpClient();
        var request = HttpRequest.newBuilder()
            .uri(URI.create("http://localhost:11434/api/chat"))
            .header("Content-Type", "application/json")
            .POST(BodyPublishers.ofString(jsonPayload))
            .build();
        var response = client.send(request, HttpResponse.BodyHandlers.ofString());
        String jsonstring = response.body();
        Map<String,?> json = SimpleJson.toMap(jsonstring);
        Map<String,?> message = (Map<String,?>) json.get("message");
        Map<String, ?> content = SimpleJson.toMap((String) message.get("content"));
        System.out.println(SimpleJson.format(SimpleJson.json2string(content)));
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

        public static Map<String,?> toMap(String json) {
            Map<String, Object> map = new HashMap<>();
            json = json.trim();
            String content = json.substring(1, json.length() - 1).trim(); // cut off the outer braces
            if (content.isEmpty()) return map;
            String[] pairs = splitTokens(content, ',');
            for (String pair : pairs) {
                String[] kv = splitTokens(pair, ':');
                if (kv.length != 2) throw new IllegalArgumentException("Invalid key-value pair: " + pair);
                String key = parseString(kv[0].trim());
                Object value = parseValue(kv[1].trim());
                map.put(key, value);
            }
            return map;
        }
    
        public static List<?> toArray(String json) {
            List<Object> list = new ArrayList<>();
            json = json.trim();
            String content = json.substring(1, json.length() - 1).trim();
            if (content.isEmpty()) return list;            
            String[] elements = splitTokens(content, ',');
            for (String element : elements) {
                list.add(parseValue(element.trim()));
            }
            return list;
        }

        private static Object parseValue(String value) {
            if (value.startsWith("\"")) return parseString(value);
            if (value.startsWith("{")) return toMap(value);
            if (value.startsWith("[")) return toArray(value);
            if (value.equals("true")) return true;
            if (value.equals("false")) return false;
            if (value.equals("null")) return null;
            try {
                if (value.contains(".")) return Double.parseDouble(value);
                return Long.parseLong(value);
            } catch (NumberFormatException e) {
                throw new IllegalArgumentException("Invalid value: " + value);
            }
        }
        
        private static String parseString(String str) {
            str = str.trim();
            return str.substring(1, str.length() - 1).replace("\\\"", "\"").replace("\\\\", "\\");
        }
        
        private static String[] splitTokens(String input, char delimiter) {
            List<String> tokens = new ArrayList<>();
            int depth = 0;
            int start = 0;
            boolean inQuotes = false;
            for (int i = 0; i < input.length(); i++) {
                char c = input.charAt(i);
                if (c == '\"') inQuotes = !inQuotes;
                if (c == '{' || c == '[') depth++;
                if (c == '}' || c == ']') depth--;
                if (!inQuotes && c == delimiter && depth == 0) {
                    tokens.add(input.substring(start, i).trim());
                    start = i + 1;
                }
            }
            tokens.add(input.substring(start).trim());
            return tokens.toArray(new String[0]);
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
