from flask import Blueprint, request, jsonify, Response, stream_with_context, send_file
from app.utils.rate_limit import rate_limit
from app.services.providers import LLMFactory, HUMANIZER_PROMPT, WRITER_PROMPT, REVISION_PROMPT
from app.services.analyzer import Analyzer
from app.services.file_handler import FileHandler
import logging
import json

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/humanize', methods=['POST'])
@rate_limit(max_requests=10, window=60)
def humanize():
    data = request.json
    text = data.get('text', '')
    provider_name = data.get('provider', 'gemini')
    api_key = data.get('apiKey', '')
    model = data.get('model', 'gemini-3-flash-preview')
    
    logger.info(f"Humanize request: provider={provider_name}, model={model}, text_len={len(text)}")
    
    if not text or not api_key:
        logger.warning("Missing text or API key in humanize request")
        return jsonify({"error": "Missing text or API key"}), 400
    
    # Append text to the instructions
    prompt = f"{HUMANIZER_PROMPT}\n\nINPUT TEXT TO REWRITE:\n{text}"
    
    def generate():
        try:
            provider = LLMFactory.get_provider(provider_name)
            
            # Pass extra data for specific providers (like Ollama)
            stream = provider.generate_stream(
                prompt=prompt, 
                api_key=api_key, 
                model=model, 
                base_url=data.get('ollamaUrl'), 
                ollamaModel=data.get('ollamaModel')
            )
            
            for chunk in stream:
                if chunk:
                    # Format as valid SSE
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Humanize error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@api_bp.route('/write', methods=['POST'])
@rate_limit(max_requests=10, window=60)
def write():
    data = request.json
    topic = data.get('topic', '')
    provider_name = data.get('provider', 'gemini')
    api_key = data.get('apiKey', '')
    model = data.get('model', 'gemini-3-flash-preview')
    
    logger.info(f"Write request: provider={provider_name}, model={model}, topic_len={len(topic)}")

    if not topic or not api_key:
        return jsonify({"error": "Missing topic or API key"}), 400
    
    # Append topic to the instructions
    prompt = f"{WRITER_PROMPT}\n\nTOPIC TO WRITE ABOUT:\n{topic}"
    
    def generate():
        try:
            provider = LLMFactory.get_provider(provider_name)
            stream = provider.generate_stream(
                prompt=prompt, 
                api_key=api_key, 
                model=model,
                base_url=data.get('ollamaUrl'), 
                ollamaModel=data.get('ollamaModel')
            )
            
            for chunk in stream:
                if chunk:
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Write error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@api_bp.route('/edit', methods=['POST'])
@rate_limit(max_requests=20, window=60)
def edit_text():
    """Simple text editing endpoint - takes instruction and text, returns only modified text."""
    data = request.json
    instruction = data.get('instruction', '')
    text = data.get('text', '')
    full_text = data.get('fullText', '')  # Optional: full document for context
    provider_name = data.get('provider', 'gemini')
    api_key = data.get('apiKey', '')
    model = data.get('model', 'gemini-3-flash-preview')
    
    logger.info(f"Edit request: instruction={instruction[:50]}..., text_len={len(text)}")
    
    if not text or not api_key:
        return jsonify({"error": "Missing text or API key"}), 400
    
    # Build a focused edit prompt
    if full_text:
        # Chat-based editing: modify specific part of full document
        prompt = f"""GÖREV: Aşağıdaki TAM METİN içinde sadece belirtilen kısmı TALİMAT'a göre değiştir.

TALİMAT: {instruction}

TAM METİN:
{full_text}

ÇOK ÖNEMLİ KURALLAR:
1. Sadece talimatla ilgili paragraf/cümleleri değiştir
2. Diğer tüm paragrafları ve cümleleri KESİNLİKLE değiştirme, AYNEN koru
3. Metnin TAMAMINI döndür (değişen + değişmeyenler birlikte)
4. Hiçbir açıklama, giriş veya sonuç ekleme
5. "İşte düzenlenmiş metin:" gibi ifadeler YAZMA

Düzenlenmiş tam metin:"""
    else:
        # Selection-based editing: only modify selected text
        prompt = f"""GÖREV: Aşağıdaki metni verilen talimata göre değiştir ve SADECE değiştirilmiş metni döndür.

TALİMAT: {instruction if instruction else "Daha doğal ve akıcı yeniden yaz"}

METİN: {text}

KURALLAR:
- SADECE düzenlenmiş metni döndür
- Açıklama ekleme
- Giriş cümlesi yazma
- "İşte" gibi ifadeler kullanma

ÇIKTI:"""
    
    def generate():
        try:
            provider = LLMFactory.get_provider(provider_name)
            stream = provider.generate_stream(
                prompt=prompt, 
                api_key=api_key, 
                model=model,
                base_url=data.get('ollamaUrl'), 
                ollamaModel=data.get('ollamaModel')
            )
            
            for chunk in stream:
                if chunk:
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Edit error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@api_bp.route('/chat', methods=['POST'])
@rate_limit(max_requests=30, window=60)
def chat_about_text():
    """Chat endpoint - can answer questions about the text or modify it."""
    data = request.json
    message = data.get('message', '')
    text = data.get('text', '')
    provider_name = data.get('provider', 'gemini')
    api_key = data.get('apiKey', '')
    model = data.get('model', 'gemini-3-flash-preview')
    
    logger.info(f"Chat request: message={message[:50]}...")
    
    if not message or not api_key:
        return jsonify({"error": "Missing message or API key"}), 400
    
    # Detect if this is a question or an edit command
    question_keywords = ['ne', 'nedir', 'nasıl', 'neden', 'kim', 'hangi', 'kaç', 'anlatıyor', 'açıkla', 'özetle', 'anlat', '?']
    is_question = any(kw in message.lower() for kw in question_keywords)
    
    if is_question:
        # This is a question - answer it
        prompt = f"""METİN:
{text}

KULLANICI SORUSU: {message}

Bu metin hakkındaki soruyu kısa ve öz bir şekilde cevapla. Türkçe yaz."""
        return_type = 'answer'
    else:
        # This is an edit command - modify the text
        prompt = f"""GÖREV: Aşağıdaki metni verilen talimata göre düzenle.

TALİMAT: {message}

METİN:
{text}

ÇOK ÖNEMLİ KURALLAR:
1. Sadece talimatla ilgili paragraf/cümleleri değiştir
2. Diğer tüm paragrafları ve cümleleri KESİNLİKLE değiştirme, AYNEN koru
3. Metnin TAMAMINI döndür (değişen + değişmeyenler birlikte)
4. Hiçbir açıklama, giriş veya sonuç ekleme

Düzenlenmiş tam metin:"""
        return_type = 'edit'
    
    def generate():
        try:
            provider = LLMFactory.get_provider(provider_name)
            stream = provider.generate_stream(
                prompt=prompt, 
                api_key=api_key, 
                model=model,
                base_url=data.get('ollamaUrl'), 
                ollamaModel=data.get('ollamaModel')
            )
            
            # Send the type first
            yield f"data: {json.dumps({'type': return_type})}\n\n"
            
            for chunk in stream:
                if chunk:
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Chat error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@api_bp.route('/check', methods=['POST'])
@rate_limit(max_requests=20, window=60)
def check_ai():
    data = request.json
    text = data.get('text', '')
    provider_name = data.get('provider', 'gemini')
    api_key = data.get('apiKey', '')
    model = data.get('model', 'gemini-3-flash-preview')

    if not text:
        return jsonify({"error": "Missing text"}), 400
    
    analyzer = Analyzer()
    result = analyzer.analyze(
        text, 
        provider_name=provider_name, 
        api_key=api_key, 
        model=model,
        base_url=data.get('ollamaUrl'),
        ollamaModel=data.get('ollamaModel')
    )
    
    return jsonify(result)

@api_bp.route('/auto-revise', methods=['POST'])
@rate_limit(max_requests=20, window=60)
def auto_revise():
    """Auto-revise endpoint: Check AI score, revise if needed, repeat until target score."""
    data = request.json
    text = data.get('text', '')
    provider_name = data.get('provider', 'gemini')
    api_key = data.get('apiKey', '')
    model = data.get('model', 'gemini-3-flash-preview')
    target_score = data.get('targetScore', 15)
    max_iterations = data.get('maxIterations', 3)
    
    logger.info(f"Auto-revise request: target={target_score}, max_iter={max_iterations}")
    
    if not text or not api_key:
        return jsonify({"error": "Missing text or API key"}), 400
    
    analyzer = Analyzer()
    provider = LLMFactory.get_provider(provider_name)
    
    iterations = []
    current_text = text
    
    for i in range(max_iterations):
        # Step 1: Analyze current text
        analysis = analyzer.analyze(
            current_text,
            provider_name=provider_name,
            api_key=api_key,
            model=model,
            base_url=data.get('ollamaUrl'),
            ollamaModel=data.get('ollamaModel')
        )
        
        current_score = analysis.get('ai_score', 0)
        iterations.append({
            "iteration": i + 1,
            "score": current_score,
            "feedback": analysis.get('overall_feedback', '')
        })
        
        logger.info(f"Auto-revise iteration {i+1}: score={current_score}")
        
        # Step 2: If score is acceptable, stop
        if current_score <= target_score:
            break
        
        # Step 3: Create feedback string from sentence analysis
        feedback_lines = []
        for item in analysis.get('sentence_analysis', []):
            if item.get('score', 0) > 30:  # Only include problematic sentences
                feedback_lines.append(f"- Sentence: \"{item['sentence']}\" | Reason: {item['reason']}")
        
        feedback_str = "\n".join(feedback_lines) if feedback_lines else analysis.get('overall_feedback', 'General improvement needed.')
        
        # Step 4: Create revision prompt and call LLM
        revision_prompt = REVISION_PROMPT.replace('{original_text}', current_text).replace('{feedback}', feedback_str)
        
        revised_text = ""
        stream = provider.generate_stream(
            prompt=revision_prompt,
            api_key=api_key,
            model=model,
            base_url=data.get('ollamaUrl'),
            ollamaModel=data.get('ollamaModel')
        )
        
        for chunk in stream:
            if chunk and not chunk.startswith("Error:"):
                revised_text += chunk
        
        current_text = revised_text.strip()
    
    return jsonify({
        "final_text": current_text,
        "final_score": iterations[-1]['score'] if iterations else 0,
        "iterations": iterations
    })

@api_bp.route('/upload', methods=['POST'])
@rate_limit(max_requests=20, window=60)
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and FileHandler.allowed_file(file.filename):
        try:
            content = FileHandler.parse_file(file)
            return jsonify({"text": content})
        except Exception as e:
            logger.error(f"File upload error: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
            
    return jsonify({"error": "Invalid file type"}), 400

@api_bp.route('/download', methods=['POST'])
@rate_limit(max_requests=20, window=60)
def download_file():
    data = request.json
    text = data.get('text', '')
    format_type = data.get('format', 'txt')
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    try:
        if format_type == 'docx':
            file_stream = FileHandler.create_docx(text)
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            filename = 'humanized_text.docx'
        else: # txt or md
            file_stream = FileHandler.create_txt(text)
            mimetype = 'text/plain'
            filename = f'humanized_text.{format_type}'
            
        return send_file(
            file_stream,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Download error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

