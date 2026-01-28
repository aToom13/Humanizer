import requests
import json
import os
from abc import ABC, abstractmethod

# Path to the prompt file
PROMPT_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'prompt.txt')

def load_prompt():
    try:
        with open(PROMPT_FILE_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading prompt.txt: {e}")
        return ""

# Load the prompt content once
# Load the prompt content once
BASE_PROMPT = load_prompt()

# Context-aware prompts
HUMANIZER_PROMPT = BASE_PROMPT
WRITER_PROMPT = BASE_PROMPT

ANALYZER_PROMPT = """
TASK: You are a ruthless AI Detection Simulator (modeling GPTZero, Turnitin, Originality.ai).
Your job is to catch AI-generated text by spotting specific vocabulary and structural patterns. You must be STRICT.

CRITICAL DETECTION RULES (PENALIZE HEAVILY):

1.  **TIER 1: INSTANT AI GIVEAWAYS (If found, score > 80%):**
    -   *Vocabulary*: "delve", "tapestry", "landscape" (metaphor), "nuance", "multifaceted", "myriad", "plethora", "testament", "underscore", "spearhead", "leverage", "utilize", "facilitate", "comprehensive", "elucidate", "exemplify", "foster", "robust", "seamless", "synergy", "transformative", "crucial", "vital", "pivotal".
    -   *Phrases*: "It is important to note", "In conclusion", "Furthermore", "Moreover", "Additionally", "In today's world", "On the other hand", "It goes without saying".

2.  **TIER 2: STRUCTURAL AI SIGNALS:**
    -   **Low Perplexity**: Text chooses the most predictable words (e.g., "The weather is" -> "nice" instead of "garbage").
    -   **Low Burstiness**: Sentences are all similar length (e.g., 15-20 words). No fragments. No run-ons.
    -   **Neutral/Balanced Tone**: "While X is good, Y is also..." (Hedging).
    -   **Lack of Opinion**: AI avoids "This is stupid" or "I hate this".

3.  **HUMAN POSITIVE SIGNALS (LOWER THE SCORE):**
    -   **Fragments**: "Maybe.", "Not really.", "Simple as that."
    -   **Conversational Fillers**: "Basically,", "Honestly,", "Kind of", "You know".
    -   **Messiness**: Stylistic lowercase ("it's just too much"), missing commas in run-ons.
    -   **Direct Address**: "Picture this", "Think about it".
    -   **Specifics**: "My Ford Fiesta died" instead of "The vehicle malfunctioned".

INPUT TEXT:
{text}

OUTPUT FORMAT:
Return valid raw JSON only.
{
    "ai_score": <float 0-100>,
    "sentence_analysis": [
        {
            "sentence": "<sentence substring>",
            "score": <float 0-100>,
            "reason": "<Ex: 'Found banned word: delve' or 'Robotic transition' or 'Good human fragment'>"
        }
    ],
    "overall_feedback": "<Concise analysis. Mention specific banned words found if any.>"
}
"""

REVISION_PROMPT = f"""
You are THE HUMANIZER. You must REVISE the text below to pass AI detection.

STYLE RULES (From your training):
{BASE_PROMPT}

CRITICAL: The AI Detector flagged specific sentences. You MUST fix them.

ORIGINAL TEXT:
{{original_text}}

AI DETECTOR FEEDBACK (Fix these issues):
{{feedback}}

INSTRUCTIONS:
1. Rewrite ONLY the flagged sentences using the Style Rules.
2. If a banned word is found, replace it with a simple alternative.
3. If the structure is "robotic", add fragments, run-ons, or conversational fillers.
4. Keep the rest of the text intact.
5. Do NOT add any explanations. Return ONLY the revised full text.

OUTPUT:
"""

class LLMProvider(ABC):
    @abstractmethod
    def generate_stream(self, prompt, **kwargs):
        pass

class GeminiProvider(LLMProvider):
    def generate_stream(self, prompt, api_key, model="gemini-3-flash-preview", **kwargs):
        # Using streamGenerateContent (server-sent events style but slightly different in Gemini REST)
        # Gemini REST returns a JSON array stream
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": api_key, "alt": "sse"} # Use SSE mode for easier parsing
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.9,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 8192
            }
        }
        
        with requests.post(url, headers=headers, params=params, json=body, stream=True) as response:
            try:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith('data: '):
                            json_str = decoded_line[6:]
                            try:
                                data = json.loads(json_str)
                                if 'candidates' in data and len(data['candidates']) > 0:
                                    content = data['candidates'][0]['content']['parts'][0]['text']
                                    yield content
                            except Exception:
                                pass
            except Exception as e:
                yield f"Error: {str(e)}"

class OpenRouterProvider(LLMProvider):
    def generate_stream(self, prompt, api_key, model, **kwargs):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://2am-humanizer.com",
            "X-Title": "Atom Humanizer"
        }
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.9,
            "max_tokens": 4096,
            "stream": True # Enable streaming
        }
        
        with requests.post(url, headers=headers, json=body, stream=True) as response:
            try:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith('data: '):
                            if decoded_line == 'data: [DONE]':
                                break
                            json_str = decoded_line[6:]
                            try:
                                data = json.loads(json_str)
                                content = data['choices'][0]['delta'].get('content', '')
                                if content:
                                    yield content
                            except Exception:
                                pass
            except Exception as e:
                yield f"Error: {str(e)}"

class OllamaProvider(LLMProvider):
    def generate_stream(self, prompt, base_url="http://localhost:11434", model="llama2", **kwargs):
        url = f"{base_url}/api/generate"
        body = {
            "model": model,
            "prompt": prompt,
            "stream": True, # Enable streaming
            "options": {"temperature": 0.9}
        }
        
        with requests.post(url, json=body, stream=True) as response:
            try:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            content = data.get('response', '')
                            if content:
                                yield content
                            if data.get('done', False):
                                break
                        except Exception:
                            pass
            except Exception as e:
                yield f"Error: {str(e)}"

class LLMFactory:
    @staticmethod
    def get_provider(provider_name):
        if provider_name == 'gemini':
            return GeminiProvider()
        elif provider_name == 'openrouter':
            return OpenRouterProvider()
        elif provider_name == 'ollama':
            return OllamaProvider()
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
