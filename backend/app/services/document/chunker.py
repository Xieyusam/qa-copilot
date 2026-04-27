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

    def chunk_with_config(
        self,
        doc: ParsedDocument,
        config,
    ) -> list[Chunk]:
        """
        Split *doc* into Chunks using config-driven strategy selection.

        Args:
            doc: ParsedDocument to chunk
            config: KbChunkingConfig object with chunking_strategy, max_tokens, overlap, strategy_overrides
        """
        if not doc.content or not doc.content.strip():
            return []

        # 1. Check strategy_overrides for file_type specific strategy
        if config.strategy_overrides and doc.file_type in config.strategy_overrides:
            strategy = config.strategy_overrides[doc.file_type]
        else:
            # 2. Fall back to config's default chunking_strategy
            strategy = config.chunking_strategy

        max_tokens = config.max_tokens
        overlap = config.overlap

        # Route to appropriate strategy
        if strategy == "semantic" and hasattr(self, "_chunk_semantic"):
            return self._chunk_semantic(doc, max_tokens, overlap)
        elif strategy == "sentence":
            return self._chunk_sentence(doc, max_tokens, overlap)
        elif strategy == "sliding_window":
            return self._chunk_sliding_window(doc, max_tokens, overlap)
        elif strategy == "markdown":
            return self._chunk_markdown(doc, max_tokens, overlap)
        elif strategy in ("xlsx", "excel"):
            return self._chunk_excel(doc, max_tokens, overlap)
        elif strategy == "recursive_text":
            return self._chunk_text(doc, max_tokens, overlap)
        else:
            # Default fallback
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

    def _chunk_sentence(self, doc: ParsedDocument, max_tokens: int, overlap: int) -> list[Chunk]:
        """按句子切分，使用正则检测句子边界。"""
        import re
        # 句子结束符：中文句号、英文句号、问号、感叹号
        sentence_pattern = r"(?<=[。！？.?!])\s+"
        sentences = re.split(sentence_pattern, doc.content)

        chunks = []
        current_chunk = []
        current_tokens = 0
        position = 0

        for sentence in sentences:
            if not sentence.strip():
                continue
            sentence_tokens = len(self._enc.encode(sentence))

            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                # 输出当前 chunk
                chunk_text = "".join(current_chunk)
                chunks.append(
                    Chunk(
                        chunk_id=str(uuid.uuid4()),
                        doc_id=doc.doc_id,
                        content=chunk_text,
                        token_count=current_tokens,
                        position=position,
                    )
                )
                position += 1

                # 处理重叠
                if overlap > 0:
                    # 将最后一个句子作为重叠的一部分
                    overlap_tokens = 0
                    overlap_sentences = []
                    for s in reversed(current_chunk):
                        s_tokens = len(self._enc.encode(s))
                        if overlap_tokens + s_tokens <= overlap:
                            overlap_sentences.insert(0, s)
                            overlap_tokens += s_tokens
                        else:
                            break
                    current_chunk = overlap_sentences
                    current_tokens = overlap_tokens
                else:
                    current_chunk = []
                    current_tokens = 0

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # 处理最后一个 chunk
        if current_chunk:
            chunk_text = "".join(current_chunk)
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc.doc_id,
                    content=chunk_text,
                    token_count=current_tokens,
                    position=position,
                )
            )

        return chunks

    def _chunk_sliding_window(self, doc: ParsedDocument, max_tokens: int, overlap: int) -> list[Chunk]:
        """固定 token 数 + 重叠滑动窗口切分。"""
        if not doc.content:
            return []

        all_tokens = self._enc.encode(doc.content)
        total_tokens = len(all_tokens)

        if total_tokens == 0:
            return []

        chunks = []
        position = 0
        start = 0

        while start < total_tokens:
            end = min(start + max_tokens, total_tokens)
            window_tokens = all_tokens[start:end]
            window_text = self._enc.decode(window_tokens)

            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc.doc_id,
                    content=window_text,
                    token_count=len(window_tokens),
                    position=position,
                )
            )
            position += 1

            # 滑动窗口步长 = max_tokens - overlap
            step = max_tokens - overlap
            if step <= 0:
                # 避免无限循环
                break
            start += step

        return chunks

    def _chunk_semantic(self, doc: ParsedDocument, max_tokens: int, overlap: int) -> list[Chunk]:
        """
        基于 Embedder 计算 embedding 相似度检测语义边界切分。

        逻辑：
        1. 用标点将文本拆分为候选句子
        2. 将连续句子合并为候选 chunk（不超过 max_tokens）
        3. 对每个 chunk 调用 Embedder.embed([chunk]) 获取向量
        4. 计算连续 chunk 之间的余弦相似度
        5. 当相似度突然下降 > 阈值（如 0.3）时，断开作为新的语义段落
        6. overlap：保留上一个 chunk 的最后 1-2 个句子到下一个 chunk
        """
        import re
        from app.services.retrieval.embedder import Embedder

        embedder = Embedder()
        sentence_pattern = r"(?<=[。！？.?!])\s+"
        sentences = re.split(sentence_pattern, doc.content)

        chunks = []
        current_chunk: list[str] = []
        current_tokens = 0
        prev_embedding: list[float] | None = None
        position = 0
        SIMILARITY_THRESHOLD = 0.7  # 相似度低于此值认为进入新主题

        for sentence in sentences:
            if not sentence.strip():
                continue
            sentence_tokens = len(self._enc.encode(sentence))

            # 如果单个句子超过 max_tokens，直接切分（用滑动窗口处理）
            if sentence_tokens > max_tokens:
                if current_chunk:
                    chunk_text = "".join(current_chunk)
                    chunk_emb = embedder.embed([chunk_text])[0]
                    chunks.append(self._make_chunk(doc, current_chunk, position, chunk_emb))
                    position += 1
                    prev_embedding = chunk_emb
                    # 语义边界处不使用 overlap，直接清空
                    current_chunk = []
                    current_tokens = 0

                # 对超长句子按滑动窗口切分
                sub_chunks = self._chunk_sliding_window(
                    ParsedDocument(doc_id=doc.doc_id, file_type=doc.file_type, content=sentence),
                    max_tokens,
                    overlap
                )
                for sub in sub_chunks:
                    sub.position = position
                    position += 1
                chunks.extend(sub_chunks)
                prev_embedding = None
                current_chunk = []
                current_tokens = 0
                continue

            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                chunk_text = "".join(current_chunk)
                chunk_emb = embedder.embed([chunk_text])[0]

                # 语义边界检测
                is_semantic_break = False
                if prev_embedding is not None:
                    similarity = self._cosine_similarity(prev_embedding, chunk_emb)
                    is_semantic_break = similarity < SIMILARITY_THRESHOLD

                chunks.append(self._make_chunk(doc, current_chunk, position, chunk_emb))
                position += 1
                prev_embedding = chunk_emb

                if is_semantic_break:
                    # 语义边界处不使用 overlap，直接开始新 chunk
                    current_chunk = []
                    current_tokens = 0
                else:
                    # 普通边界：保留 overlap
                    current_chunk, current_tokens = self._apply_overlap_sentences(current_chunk, overlap)
                    if not current_chunk:
                        continue

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        if current_chunk:
            chunk_text = "".join(current_chunk)
            chunk_emb = embedder.embed([chunk_text])[0]
            chunks.append(self._make_chunk(doc, current_chunk, position, chunk_emb))

        return chunks

    def _apply_overlap_sentences(self, current_chunk: list[str], overlap: int) -> tuple[list[str], int]:
        """将 current_chunk 的最后几个句子作为 overlap 返回。"""
        if overlap <= 0 or not current_chunk:
            return [], 0
        overlap_tokens = 0
        overlap_sentences = []
        for s in reversed(current_chunk):
            s_tokens = len(self._enc.encode(s))
            if overlap_tokens + s_tokens <= overlap:
                overlap_sentences.insert(0, s)
                overlap_tokens += s_tokens
            else:
                break
        overlap_text = "".join(overlap_sentences)
        return overlap_sentences, overlap_tokens

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """计算两个向量的余弦相似度。"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b + 1e-8)

    def _make_chunk(
        self,
        doc: ParsedDocument,
        texts: list[str],
        position: int,
        embedding: list[float] | None = None,
    ) -> Chunk:
        """辅助方法：从文本列表创建 Chunk。"""
        content = "".join(texts)
        tokens = self._enc.encode(content)
        return Chunk(
            chunk_id=str(uuid.uuid4()),
            doc_id=doc.doc_id,
            content=content,
            token_count=len(tokens),
            position=position,
        )
