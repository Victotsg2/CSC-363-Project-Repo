from flask import Flask, render_template, request, send_file
from langchain_openai import ChatOpenAI
from docx import Document 
from docx2pdf import convert
import PyPDF2
import io
import os

app = Flask(__name__)

def read_resume_file(file):
    """Read content from uploaded resume file"""
    if file.filename.endswith('.txt') or file.filename.endswith('.md'):
        return file.read().decode('utf-8')
    elif file.filename.endswith('.docx'):
        doc = Document(file)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    elif file.filename.endswith('.pdf'):
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""
    else:
        return ""

@app.route('/', methods=['GET', 'POST'])
def index():
    generated_resume = None
    error = None

    if request.method == 'POST':
        try:
            job_description = request.form.get('jobDescription', '')
            base_resume = ""

            # Handle resume upload
            if 'resume' in request.files:
                file = request.files['resume']
                if file.filename:
                    base_resume = read_resume_file(file)

            if job_description:
                # Initialize GPT4All with the mini model
                llm = ChatOpenAI(model="gpt-4o-mini")

                # Create prompt based on whether a resume was uploaded
                if base_resume:
                    prompt = f"""Create a professional resume in markdown format based on this job description and existing resume:

Job Description:
{job_description}

Existing Resume:
{base_resume}

Instructions:
- Use the existing resume as a base but modify it to better match the job requirements
- Format the output in proper markdown
- Include relevant sections (Summary, Skills, Experience, Education)
- Keep it to one page
- Make it professional and well-organized
- Maintain truthful information from the original resume
"""
                else:
                    prompt = f"""Create a professional resume in markdown format based on this job description:

Job Description:
{job_description}

Instructions:
- Format the resume in proper markdown
- Include relevant sections (Summary, Skills, Experience, Education)
- Create content that matches the job requirements
- Keep it to one page
- Make it professional and well-organized
- Use realistic but fictional details
"""
                # Generate resume
                response = llm.invoke(prompt)
                generated_resume = str(response) if response else ""

                # Save as Markdown
                with open("resume.md", "w", encoding='utf-8') as f:
                    f.write(generated_resume)

                # Create Word document
                doc = Document()
                lines = generated_resume.split('\n')
                for line in lines:
                    if line.startswith('# '):
                        doc.add_heading(line[2:], level=1)
                    elif line.startswith('## '):
                        doc.add_heading(line[3:], level=2)
                    elif line.startswith('### '):
                        doc.add_heading(line[4:], level=3)
                    elif line.startswith('- '):
                        doc.add_paragraph(line[2:], style='List Bullet')
                    else:
                        doc.add_paragraph(line)

                doc.save("resume.docx")

                # Convert to PDF
                try:
                    convert("resume.docx", "resume.pdf")
                except Exception as e:
                    print(f"Error converting to PDF: {e}")

        except Exception as e:
            error = str(e)
            print(f"Error: {e}")

    return render_template('index.html', 
                         generated_resume=generated_resume, 
                         error=error)

@app.route('/download/<format>')
def download_file(format):
    if format in ['pdf', 'docx', 'md']:
        filename = f"resume.{format}"
        if os.path.exists(filename):
            return send_file(filename, as_attachment=True)
    return "File not found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port, debug=True)
