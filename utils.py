
from io import BytesIO
from PyPDF2 import PdfReader
from docx import Document
from googlesearch import search
import re
import nltk
from http.client import RemoteDisconnected

nltk.download('punkt')


class PlagiarismDetectionService:

    @staticmethod
    def find_plagiarism_sources(text):
        plagiarism_sources = []

        # Use Google search to find potential sources
        try:
            for result in search(text, num=5, stop=5, pause=2):
                plagiarism_sources.append(result)
        except RemoteDisconnected:
            plagiarism_sources.append("Not copied from any extrenl source.")
            # Handle the exception (e.g., wait for some time and retry)

        return plagiarism_sources

    @staticmethod
    def check_plagiarism(file_data1, file_data2, filename1, filename2, exclude_references=False, exclude_quotes=False):
        content1 = convert_file_data_to_text(
            file_data1, filename1, exclude_references, exclude_quotes)
        content2 = convert_file_data_to_text(
            file_data2, filename2, exclude_references, exclude_quotes)

        tokens1 = nltk.word_tokenize(content1)
        tokens2 = nltk.word_tokenize(content2)

        common_words = set(tokens1) & set(tokens2)
        similarity_percentage = (
            len(common_words) / len(set(tokens1 + tokens2))) * 100

        plagiarism_sources = PlagiarismDetectionService.find_plagiarism_sources(
            content1)

        return similarity_percentage, plagiarism_sources


def exclude_references_logic(text):
    # Example: Remove text within square brackets, assuming they are citations
    return re.sub(r'\[[^\]]*\]', '', text)


def exclude_quotes_logic(text):
    # Example: Remove text within double quotation marks
    return re.sub(r'"[^"]*"', '', text)


def convert_file_data_to_text(file_data, filename, exclude_references=False, exclude_quotes=False):
    # Check file type and convert to plain text
    if filename.endswith('.txt'):
        text = file_data.decode('utf-8')
    elif filename.endswith('.pdf'):
        text = extract_text_from_pdf(file_data)
    elif filename.endswith('.docx'):
        text = extract_text_from_docx(file_data)

    if exclude_references:
        text = exclude_references_logic(text)
    if exclude_quotes:
        text = exclude_quotes_logic(text)

    return text


def extract_text_from_pdf(file_data):
    pdf_reader = PdfReader(BytesIO(file_data))
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        text += pdf_reader.pages[page_num].extract_text()
    return text


def extract_text_from_docx(file_data):
    document = Document(BytesIO(file_data))
    text = ""
    for paragraph in document.paragraphs:
        text += paragraph.text + "\n"
    return text
