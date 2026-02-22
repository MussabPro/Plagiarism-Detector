"""
Text processing utilities.
Functions for text cleaning, tokenization, and preprocessing for plagiarism detection.
"""
from nltk.tokenize import word_tokenize
import os
import re
import nltk
from typing import List, Set

# Force NLTK to use /tmp on Vercel (only writable directory in serverless)
nltk.data.path.insert(0, "/tmp/nltk_data")

# Ensure NLTK data is downloaded at import time
for _pkg in ("punkt", "punkt_tab"):
    try:
        nltk.data.find(f"tokenizers/{_pkg}")
    except LookupError:
        try:
            nltk.download(_pkg, download_dir="/tmp/nltk_data", quiet=True)
        except Exception:
            # Gracefully degrade if download fails (e.g. no network on Vercel)
            pass


def tokenize_text(text: str) -> List[str]:
    """
    Tokenize text into words using NLTK.

    Args:
        text: Text to tokenize

    Returns:
        List of tokens (words)
    """
    try:
        tokens = word_tokenize(text.lower())
        return tokens
    except Exception:
        # Fallback to simple splitting if NLTK fails
        return text.lower().split()


def remove_references(text: str) -> str:
    """
    Remove reference sections from text using regex patterns.

    Args:
        text: Text potentially containing references

    Returns:
        Text with references removed
    """
    # Remove "References" section and everything after
    text = re.sub(
        r'\bReferences?\b.*$',
        '',
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Remove "Bibliography" section and everything after
    text = re.sub(
        r'\bBibliography\b.*$',
        '',
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Remove "Works Cited" section and everything after
    text = re.sub(
        r'\bWorks\s+Cited\b.*$',
        '',
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Remove inline citations like [1], (Smith, 2020), etc.
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\(\w+,?\s*\d{4}\)', '', text)
    text = re.sub(r'\(\w+\s+et\s+al\.,?\s*\d{4}\)', '', text)

    return text.strip()


def remove_quotes(text: str) -> str:
    """
    Remove quoted text from document.

    Args:
        text: Text potentially containing quotes

    Returns:
        Text with quotes removed
    """
    # Remove text in double quotes
    text = re.sub(r'"[^"]*"', '', text)

    # Remove text in single quotes (but be careful with contractions)
    text = re.sub(r"'([^']{10,})'", '', text)

    # Remove block quotes (lines starting with >)
    text = re.sub(r'^>.*$', '', text, flags=re.MULTILINE)

    return text.strip()


def preprocess_document(
    text: str,
    remove_refs: bool = False,
    remove_quotes_flag: bool = False
) -> str:
    """
    Preprocess document for plagiarism detection.

    Args:
        text: Raw document text
        remove_refs: Whether to remove references
        remove_quotes_flag: Whether to remove quotes

    Returns:
        Preprocessed text
    """
    # Remove references if requested
    if remove_refs:
        text = remove_references(text)

    # Remove quotes if requested
    if remove_quotes_flag:
        text = remove_quotes(text)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?;:\-]', '', text)

    return text.strip()


def get_word_set(text: str) -> Set[str]:
    """
    Get set of unique words from text.
    Used for Jaccard similarity calculation.

    Args:
        text: Text to process

    Returns:
        Set of unique lowercased words
    """
    tokens = tokenize_text(text)
    # Filter out very short tokens and punctuation
    return {token for token in tokens if len(token) > 2 and token.isalnum()}


def extract_sentences(text: str) -> List[str]:
    """
    Extract sentences from text.

    Args:
        text: Text to extract sentences from

    Returns:
        List of sentences
    """
    # Simple sentence splitting on common punctuation
    sentences = re.split(r'[.!?]+', text)
    # Filter empty sentences and strip whitespace
    return [s.strip() for s in sentences if s.strip()]


def clean_text(text: str) -> str:
    """
    Clean text by removing URLs, emails, and excessive punctuation.

    Args:
        text: Text to clean

    Returns:
        Cleaned text
    """
    # Remove URLs
    text = re.sub(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)

    # Remove excessive punctuation
    text = re.sub(r'([!?.]){2,}', r'\1', text)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def get_n_grams(tokens: List[str], n: int = 3) -> List[tuple]:
    """
    Generate n-grams from tokens.

    Args:
        tokens: List of tokens
        n: Size of n-grams

    Returns:
        List of n-gram tuples
    """
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


def normalize_text(text: str) -> str:
    """
    Normalize text to lowercase and remove excess whitespace.

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
