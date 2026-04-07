"""
Chunker module for the internal knowledge base system.
Splits ParsedDocument content into overlapping token-based chunks using langchain-text-splitters.
"""
from __future__ import annotations

import uuid

import tiktoken
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.core.schemas import Chunk, ParsedDocument


class Chunker:
    """Splits a ParsedDocument into token-bounded Chunks using semantic splitting."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self._enc = tiktoken.get_encoding(encoding_name)
        
        # Headers to split on for Markdown
        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]

    def chunk(
        self,
        doc: ParsedDocument,
        max_tokens: int = 512,
        overlap: int = 50,
    ) -> list[Chunk]:
        """
        Split *doc* into Chunks using semantic strategies based on file type.
        """
        content = doc.content
        if not content or not content.strip():
            return []

        if doc.file_type in ("md", "markdown"):
            return self._chunk_markdown(doc, max_tokens, overlap)
        elif doc.file_type in ("xlsx", "xls"):
            return self._chunk_excel(doc, max_tokens, overlap)
        else:
            return self._chunk_text(doc, max_tokens, overlap)

    def _chunk_markdown(self, doc: ParsedDocument, max_tokens: int, overlap: int) -> list[Chunk]:
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False
        )
        md_header_splits = markdown_splitter.split_text(doc.content)
        
        # Secondary split for large sections under a single header
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=max_tokens,
            chunk_overlap=overlap,
            encoding_name="cl100k_base"
        )
        splits = text_splitter.split_documents(md_header_splits)
        
        chunks = []
        for i, split in enumerate(splits):
            # Include headers in the content for better context
            header_context = " > ".join([f"{v}" for k, v in split.metadata.items() if k.startswith("Header")])
            final_content = f"[{header_context}]\n{split.page_content}" if header_context else split.page_content
            
            tokens = self._enc.encode(final_content)
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc.doc_id,
                    content=final_content,
                    token_count=len(tokens),
                    position=i,
                )
            )
        return chunks

    def _chunk_text(self, doc: ParsedDocument, max_tokens: int, overlap: int) -> list[Chunk]:
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=max_tokens,
            chunk_overlap=overlap,
            encoding_name="cl100k_base",
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )
        
        splits = text_splitter.split_text(doc.content)
        
        chunks = []
        for i, text in enumerate(splits):
            tokens = self._enc.encode(text)
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc.doc_id,
                    content=text,
                    token_count=len(tokens),
                    position=i,
                )
            )
        return chunks

    def _chunk_excel(self, doc: ParsedDocument, max_tokens: int, overlap: int) -> list[Chunk]:
        # For Excel, paragraphs are already formatted as "[表格: Sheet1]\n列1: 值1\n..."
        # We want to keep each row (paragraph) intact if possible, so we prioritize \n\n
        # over \n.
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=max_tokens,
            chunk_overlap=overlap,
            encoding_name="cl100k_base",
            separators=["\n\n", "\n"] # Only split by block or line, never mid-sentence
        )
        
        splits = text_splitter.split_text(doc.content)
        
        chunks = []
        for i, text in enumerate(splits):
            tokens = self._enc.encode(text)
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc.doc_id,
                    content=text,
                    token_count=len(tokens),
                    position=i,
                )
            )
        return chunks
