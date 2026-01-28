# AtomHumanizer

AtomHumanizer is an advanced AI text humanization tool designed to rewrite AI-generated content (from ChatGPT, Claude, Gemini, etc.) to bypass AI detectors and sound more natural. It mimics the writing style of a "tired student" (Atom Mode) or simply improves flow and readability.

## Features

- **Humanize Text**: Rewrite AI text to bypass detectors like Turnitin, GPTZero, and Originality.ai.
- **AI Writer**: Generate new content from scratch with a specific topic.
- **AI Check**: Analyze text for AI probability (simulated core scoring).
- **Chat Interface**: interactive chat to edit and refine the result (e.g., "Make paragraph 2 shorter").
- **Auto Revise**: Automatically improve the humanization score with one click.
- **File Support**: Upload `.txt`, `.md`, `.docx`, `.pptx` files directly.
- **Multi-Provider Support**:
  - Google Gemini (Free Tier supported)
  - Ollama (Local LLMs)
  - OpenRouter (Access to Claude 3.5 Sonnet, GPT-4o, etc.)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/aToom13/Humanizer.git
   cd Humanizer
   ```

2. **Install dependencies:**
   It is recommended to use a virtual environment.
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python run.py
   ```

4. **Access the UI:**
   Open your browser and navigate to `http://localhost:5000`.

## Configuration

### API Keys
AtomHumanizer requires an LLM provider to function. You can configure this in the **Settings** (gear icon) of the web interface.
- **Google Gemini**: Get a free API key from [Google AI Studio](https://aistudio.google.com/).
- **OpenRouter**: Get a key from [OpenRouter](https://openrouter.ai/).
- **Ollama**: Ensure Ollama is running locally (default: `http://localhost:11434`).

### Environment Variables
For production deployment, set the `SECRET_KEY` environment variable to a secure random string.
```bash
export SECRET_KEY='your-secure-secret-key'
```

## Usage

1. **Paste Text**: Copy your AI-generated text into the input box.
2. **Select Mode**: Choose "Humanizer" to rewrite or "AI Writer" to generate.
3. **Process**: Click the main action button.
4. **Refine**: Use the chat box to request specific changes (e.g., "Add more slang").
5. **Download**: Save your result as TXT, DOCX, or MD.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
