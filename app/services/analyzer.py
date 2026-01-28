import json
import logging
from app.services.providers import LLMFactory, ANALYZER_PROMPT

logger = logging.getLogger(__name__)

class Analyzer:
    def analyze(self, text, provider_name='gemini', api_key=None, model='gemini-3-flash-preview', **kwargs):
        if not text:
            return {"error": "No text provided"}

        prompt = ANALYZER_PROMPT.replace('{text}', text)
        
        # Use simple provider for analysis (default to Gemini/configured one)
        # Verify if api_key is passed, otherwise might fail if not in env var (though FE passes it)
        try:
            # We need a non-streaming response for easier parsing, or we accumulate the stream
            provider = LLMFactory.get_provider(provider_name)
            
            # Reusing generate_stream but consuming it all
            full_response = ""
            stream = provider.generate_stream(prompt=prompt, api_key=api_key, model=model, **kwargs)
            
            for chunk in stream:
                if chunk:
                    if chunk.startswith("Error:"):
                        logger.error(f"Provider Stream Error: {chunk}")
                        full_response += chunk # Append so we can see it in raw response log
                    else:
                        full_response += chunk
            
            # Clean response (remove markdown code blocks if any)
            full_response = full_response.strip()
            logger.info(f"Analyzer Raw Response: {full_response[:200]}...") # Log first 200 chars

            if not full_response:
                raise ValueError("Empty response from LLM provider")

            if full_response.startswith('```json'):
                full_response = full_response[7:-3]
            elif full_response.startswith('```'):
                full_response = full_response[3:-3]
            
            # Additional cleanup for safety
            full_response = full_response.strip()
                
            data = json.loads(full_response)
            return data

        except Exception as e:
            logger.error(f"LLM Analysis failed: {e}")
            # Fallback to simple mock or error
            return {
                "ai_score": 0,
                "reasons": [f"Analysis failed: {str(e)}"],
                "sentence_analysis": []
            }
