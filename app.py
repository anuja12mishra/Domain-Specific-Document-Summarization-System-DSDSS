import os
from dotenv import load_dotenv;
load_dotenv()
import gradio as gr
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
import sqlite3
from datetime import datetime, timezone
import cohere

# ----- Database Setup -----
def init_db():
    conn = sqlite3.connect("feedback.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            doc_id TEXT,
            domain TEXT,
            rating INTEGER,
            comment TEXT,
            summary TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ----- Cohere Setup -----
COHERE_API_KEY= os.getenv("COHERE_API_KEY")

co = cohere.Client(COHERE_API_KEY)  # Replace with your actual Cohere API key

# ----- Text Extraction -----
def extract_text_from_file(file):
    """Extract text from PDF or DOCX."""
    text = ""
    file_path = file.name if hasattr(file, "name") else file
    filename = file_path.lower()

    try:
        if filename.endswith(".pdf"):
            text = extract_pdf_text(file_path)
        elif filename.endswith(".docx"):
            doc = Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        print("❌ Error extracting text:", e)

    print("✅ Extracted text length:", len(text))
    return text.strip()

# ----- Updated Cohere Chat API Summarizer -----
def summarize_text(domain, text):
    """Summarize text using the latest Cohere 'command-a' model."""
    if not text:
        return "No text found in document."

    prompt = (
        f"You are an expert summarizer in the {domain} field.\n\n"
        f"Summarize the following text in a concise, professional manner suitable for experts in {domain}:\n\n"
        f"{text[:3500]}"
    )

    try:
        response = co.chat(
            model="command-a-03-2025",  # You can also try: command-a-reasoning-08-2025
            message=prompt
        )
        summary = response.text
    except Exception as e:
        print("❌ Error from Cohere Chat API:", e)
        summary = "Error: Could not generate summary."

    return summary.strip()


# ----- Generate Summary and Compute Metrics -----
def generate_summary(file, domain):
    if not file:
        return "", 0, 0, 0, ""
    text = extract_text_from_file(file)
    summary = summarize_text(domain, text)

    summary_len = len(summary)
    ratio = summary_len / len(text) if len(text) > 0 else 0
    coherence_score = 0.85 if summary_len > 0 else 0  # Placeholder for now
    doc_id = f"doc_{abs(hash(file.name))}"

    print(f"📝 Generated summary for {file.name}, length: {summary_len}")
    return summary, summary_len, ratio, coherence_score, doc_id

# ----- Feedback Saving -----
def save_feedback(doc_id, domain, rating, comment, summary_text):
    conn = sqlite3.connect("feedback.db")
    cur = conn.cursor()
    timestamp = datetime.now(timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO feedback (doc_id, domain, rating, comment, summary, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (doc_id, domain, rating, comment, summary_text, timestamp))
    conn.commit()
    conn.close()
    print(f"💾 Feedback saved for {doc_id} (Rating: {rating})")
    return "Feedback saved successfully!" if rating > 0 else "No rating provided"

# ----- Gradio Interface -----
with gr.Blocks(title="Domain-tuned Document Summarizer") as demo:
    gr.Markdown("## 🧠 Domain-tuned Document Summarizer (with SME Feedback & Grafana Metrics)")

    with gr.Row():
        file = gr.File(label="📄 Upload PDF / DOCX")
        domain = gr.Dropdown(["Legal", "Medical", "Finance", "Technical"], label="Domain", value="Legal")

    gen_btn = gr.Button("🚀 Generate Domain Summary")

    with gr.Row():
        doc_id = gr.Textbox(label="🆔 Doc ID", interactive=False)
        summary = gr.Textbox(label="📝 Summary", lines=10)
        summary_len = gr.Number(label="Summary Length (chars)")
        ratio = gr.Number(label="Summary/Doc Length Ratio")
        coherence = gr.Number(label="Coherence Score")

    gen_btn.click(
        generate_summary,
        inputs=[file, domain],
        outputs=[summary, summary_len, ratio, coherence, doc_id]
    )

    gr.Markdown("### 🗣️ SME Feedback Section")
    with gr.Row():
        rating = gr.Slider(0, 5, value=0, step=1, label="⭐ Star Rating (0 = no rating)")
        comment = gr.Textbox(label="💬 Comment")

    save_btn = gr.Button("💾 Save Feedback")
    status = gr.Textbox(label="Status", interactive=False)

    save_btn.click(
        save_feedback,
        inputs=[doc_id, domain, rating, comment, summary],
        outputs=[status]
    )

# Launch the app (set share=True for public access)
demo.launch(share=False)
