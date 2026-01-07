"""
Advanced retrieval strategies for RAG

Implements various retrieval techniques following LangChain best practices
"""

import re
from typing import List, Optional, Set
from langchain_core.documents import Document
import cohere
from loguru import logger


class SafetyRetriever:
    """Advanced retriever with multiple strategies"""

    def __init__(self, vector_store, reranker_client: Optional[cohere.ClientV2] = None):
        self.vector_store = vector_store
        self.reranker = reranker_client

    def _number_to_chinese(self, num: int) -> str:
        """Convert Arabic number to Chinese number (1-999)"""
        if num <= 0 or num > 999:
            return ""

        units = ["", "十", "百"]
        digits = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]

        if num < 10:
            return digits[num]
        elif num < 100:
            tens = num // 10
            ones = num % 10
            if tens == 1:
                return "十" + (digits[ones] if ones else "")
            else:
                return digits[tens] + "十" + (digits[ones] if ones else "")
        else:
            hundreds = num // 100
            remainder = num % 100
            result = digits[hundreds] + "百"
            if remainder == 0:
                return result
            elif remainder < 10:
                return result + "零" + digits[remainder]
            else:
                tens = remainder // 10
                ones = remainder % 10
                return result + digits[tens] + "十" + (digits[ones] if ones else "")

    def _extract_keywords(self, query: str) -> dict:
        """
        Extract important keywords from query for text matching
        Focuses on document names, article numbers, standards, technical terms

        Returns:
            dict with keys:
                - doc_names: List of document names from 《》 or recognized patterns
                - article_numbers: List of article numbers (第X条, 5.5.1条, etc.)
                - standards: List of standard codes (GB/T, JB/T, AQ, etc.)
                - terms: List of other technical terms
        """
        result = {
            "doc_names": [],
            "article_numbers": [],
            "standards": [],
            "terms": [],
        }

        # 1. Extract document names in 《》format (highest priority)
        doc_names = re.findall(r"《([^》]+)》", query)

        # 1b. Also try to extract document names without 《》
        # Common patterns: XXX法, XXX条例, XXX规范, XXX规程, XXX办法, XXX标准
        if not doc_names:
            # Match document names ending with 法/条例/规范 etc, followed by boundary
            # Use word boundary or 的/第/是/空白 etc. to avoid over-matching
            doc_pattern = r"([\u4e00-\u9fa5]{2,20}(?:法|条例|规范|规程|办法|标准|细则|守则|准则))(?:的|第|是|\s|$)"
            potential_docs = re.findall(doc_pattern, query)
            # Filter out matches that are too short (less than 4 chars for 法, 6 for others)
            doc_names = []
            for d in potential_docs:
                if d.endswith("法") and len(d) >= 4:
                    doc_names.append(d)
                elif len(d) >= 6:
                    doc_names.append(d)

        result["doc_names"] = doc_names

        # 2. Extract article/section numbers
        # Supports: 第一条, 第二十五条, 第100条, 第5.5.1条, 5.5.1条, etc.
        article_numbers = []
        article_numbers_plain = []  # Plain numbers without 第/条 for searching

        # Pattern 1: 第X条 (Chinese numbers or digits)
        pattern1 = re.findall(r"第[一二三四五六七八九十百千零\d]+条", query)
        article_numbers.extend(pattern1)

        # Convert Arabic numbers to Chinese numbers for better matching
        # e.g., "第32条" -> also search "第三十二条"
        for art in pattern1:
            # Extract the number part
            num_match = re.search(r"第(\d+)条", art)
            if num_match:
                num = int(num_match.group(1))
                chinese_num = self._number_to_chinese(num)
                if chinese_num:
                    article_numbers.append(f"第{chinese_num}条")

        # Pattern 2: 第X.X.X条 or X.X.X条 (numbered sections like 5.5.1条)
        pattern2 = re.findall(r"第?([\d]+(?:\.[\d]+)+)条", query)
        for num in pattern2:
            article_numbers.append(
                f"第{num}条" if not query.startswith(num) else f"{num}条"
            )
            article_numbers_plain.append(num)  # Also store plain number like "5.5.1"

        # Pattern 3: 第X章/节/款/项
        pattern3 = re.findall(r"第[一二三四五六七八九十百千零\d]+[章节款项]", query)
        article_numbers.extend(pattern3)

        result["article_numbers"] = list(set(article_numbers))  # Deduplicate
        result["article_numbers_plain"] = list(
            set(article_numbers_plain)
        )  # Plain numbers for searching

        # 3. Standard codes like JB/T, GB/T, AQ, MT
        standards = re.findall(
            r"[A-Z]{1,3}[/]?[A-Z]?\s*\d+[-—]?\d*", query, re.IGNORECASE
        )
        result["standards"] = standards

        # 4. Remove already extracted content from query for further processing
        remaining_query = query
        for name in doc_names:
            remaining_query = remaining_query.replace(f"《{name}》", "")
            remaining_query = remaining_query.replace(name, "")
        for num in article_numbers:
            remaining_query = remaining_query.replace(num, "")
        for std in standards:
            remaining_query = remaining_query.replace(std, "")

        # Remove common question words
        stop_words = {
            "什么",
            "哪些",
            "如何",
            "怎么",
            "怎样",
            "为什么",
            "是否",
            "能否",
            "可以",
            "应该",
            "的",
            "了",
            "吗",
            "呢",
            "啊",
            "是",
            "有",
            "在",
            "和",
            "与",
            "或",
            "等",
            "按",
            "进行",
            "内容",
            "规定",
            "要求",
            "包括",
            "主要",
            "具体",
        }

        # 5. Chinese technical terms from remaining query
        # First try to extract meaningful 2-4 character terms
        chinese_terms = re.findall(r"[\u4e00-\u9fa5]{2,4}", remaining_query)
        chinese_terms = [
            t for t in chinese_terms if t not in stop_words and len(t) >= 2
        ]

        # Deduplicate while preserving order
        seen = set()
        unique_terms = []
        for t in chinese_terms:
            if t not in seen:
                seen.add(t)
                unique_terms.append(t)

        result["terms"] = unique_terms[:5]  # Limit to top 5

        return result

    def _get_flat_keywords(self, extracted: dict) -> List[str]:
        """Convert extracted keywords dict to flat list for text matching"""
        keywords = []
        # Prioritize document names (use full name for matching)
        keywords.extend(extracted.get("doc_names", []))
        # Add article numbers
        keywords.extend(extracted.get("article_numbers", []))
        # Add standards
        keywords.extend(extracted.get("standards", []))
        # Add other terms
        keywords.extend(extracted.get("terms", []))
        return keywords[:6]  # Limit total keywords

    async def retrieve_with_text_match(
        self,
        query: str,
        extracted_keywords: dict,
        k: int = 50,
    ) -> List[Document]:
        """
        Retrieve documents using text matching with document name filtering

        If document names are specified (《XXX》format), prioritizes those documents.
        Combines with article number and keyword matching for precision.
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import FieldCondition, MatchText, Filter

            from app.core.config import get_settings

            settings = get_settings()
            client = QdrantClient(url=settings.qdrant_url)
            collection_name = self.vector_store.collection_name

            matched_docs = []
            seen_ids: Set[str] = set()

            doc_names = extracted_keywords.get("doc_names", [])
            article_numbers = extracted_keywords.get("article_numbers", [])
            article_numbers_plain = extracted_keywords.get("article_numbers_plain", [])
            standards = extracted_keywords.get("standards", [])
            terms = extracted_keywords.get("terms", [])

            # Combine all article number variants for searching
            all_article_variants = list(set(article_numbers + article_numbers_plain))

            # Strategy 1: If document name is specified, search within that document
            if doc_names:
                for doc_name in doc_names:
                    # Build filter: filename contains doc_name
                    # AND (optionally) content contains article number
                    must_conditions = [
                        FieldCondition(
                            key="metadata.filename", match=MatchText(text=doc_name)
                        )
                    ]

                    # If article number specified, also filter by it (including plain numbers)
                    if all_article_variants:
                        should_conditions = [
                            FieldCondition(
                                key="page_content",
                                match=MatchText(text=article_num),
                            )
                            for article_num in all_article_variants
                        ]
                        # Search with doc name + article number
                        try:
                            results = client.scroll(
                                collection_name=collection_name,
                                scroll_filter=Filter(
                                    must=must_conditions,
                                    should=should_conditions,
                                    min_should={
                                        "conditions": should_conditions,
                                        "min_count": 1,
                                    },
                                ),
                                limit=k,
                                with_payload=True,
                            )
                            for point in results[0]:
                                point_id = str(point.id)
                                if point_id not in seen_ids:
                                    seen_ids.add(point_id)
                                    doc = Document(
                                        page_content=point.payload.get(
                                            "page_content", ""
                                        ),
                                        metadata={
                                            **point.payload.get("metadata", {}),
                                            "score": 0.8,  # High score for doc+article match
                                            "match_type": "doc_article",
                                        },
                                    )
                                    matched_docs.append(doc)
                        except Exception:
                            pass

                    # Also get all chunks from this document (broader match)
                    try:
                        results = client.scroll(
                            collection_name=collection_name,
                            scroll_filter=Filter(must=must_conditions),
                            limit=k // 2,
                            with_payload=True,
                        )
                        for point in results[0]:
                            point_id = str(point.id)
                            if point_id not in seen_ids:
                                seen_ids.add(point_id)
                                doc = Document(
                                    page_content=point.payload.get("page_content", ""),
                                    metadata={
                                        **point.payload.get("metadata", {}),
                                        "score": 0.6,  # Medium score for doc name match
                                        "match_type": "doc_name",
                                    },
                                )
                                matched_docs.append(doc)
                    except Exception:
                        pass

            # Strategy 2: Search by article number alone (if no doc name or as supplement)
            if article_numbers and not doc_names:
                for article_num in article_numbers:
                    try:
                        results = client.scroll(
                            collection_name=collection_name,
                            scroll_filter={
                                "must": [
                                    {
                                        "key": "page_content",
                                        "match": {"text": article_num},
                                    }
                                ]
                            },
                            limit=k // 2,
                            with_payload=True,
                        )
                        for point in results[0]:
                            point_id = str(point.id)
                            if point_id not in seen_ids:
                                seen_ids.add(point_id)
                                doc = Document(
                                    page_content=point.payload.get("page_content", ""),
                                    metadata={
                                        **point.payload.get("metadata", {}),
                                        "score": 0.5,
                                        "match_type": "article_num",
                                    },
                                )
                                matched_docs.append(doc)
                    except Exception:
                        continue

            # Strategy 3: Search by standards (e.g., GB/T, JB/T)
            for standard in standards:
                if len(standard) < 3:
                    continue
                try:
                    results = client.scroll(
                        collection_name=collection_name,
                        scroll_filter={
                            "must": [
                                {"key": "page_content", "match": {"text": standard}}
                            ]
                        },
                        limit=k // 4,
                        with_payload=True,
                    )
                    for point in results[0]:
                        point_id = str(point.id)
                        if point_id not in seen_ids:
                            seen_ids.add(point_id)
                            doc = Document(
                                page_content=point.payload.get("page_content", ""),
                                metadata={
                                    **point.payload.get("metadata", {}),
                                    "score": 0.5,
                                    "match_type": "standard",
                                },
                            )
                            matched_docs.append(doc)
                except Exception:
                    continue

            # Strategy 4: Search by other technical terms
            for term in terms:
                if len(term) < 3:
                    continue
                try:
                    results = client.scroll(
                        collection_name=collection_name,
                        scroll_filter={
                            "must": [{"key": "page_content", "match": {"text": term}}]
                        },
                        limit=k // 4,
                        with_payload=True,
                    )
                    for point in results[0]:
                        point_id = str(point.id)
                        if point_id not in seen_ids:
                            seen_ids.add(point_id)
                            doc = Document(
                                page_content=point.payload.get("page_content", ""),
                                metadata={
                                    **point.payload.get("metadata", {}),
                                    "score": 0.4,
                                    "match_type": "keyword",
                                },
                            )
                            matched_docs.append(doc)
                except Exception:
                    continue

            return matched_docs[:k]
        except Exception as e:
            logger.warning(f"Text match failed: {e}")
            return []

    async def retrieve_with_score(
        self, query: str, k: int = 5, score_threshold: Optional[float] = None
    ) -> List[Document]:
        """
        Retrieve with similarity scores and store them in document metadata

        Optionally filter by minimum score threshold
        """
        # Use similarity_search_with_score to get scores
        if score_threshold:
            results = await self.vector_store.asimilarity_search_with_score(
                query, k=k, score_threshold=score_threshold
            )
        else:
            results = await self.vector_store.asimilarity_search_with_score(query, k=k)

        # Store scores in document metadata
        docs_with_scores = []
        for doc, score in results:
            doc.metadata["score"] = score
            docs_with_scores.append(doc)

        return docs_with_scores

    async def retrieve_with_rerank(
        self,
        query: str,
        k: int = 3,
        fetch_k: int = 30,
        model: str = "/model/bge-reranker-v2-m3",
        rerank_score_threshold: float = 0.3,
    ) -> List[Document]:
        """
        Two-stage retrieval: Similarity (coarse) → Rerank (fine)

        Args:
            query: Query text
            k: Number of final documents to return
            fetch_k: Number of candidates to fetch (should >= k, default 30 for better coverage)
            model: Rerank model name
            rerank_score_threshold: Minimum rerank score to keep documents (default 0.3)

        Returns:
            Reranked top_k documents filtered by score threshold
        """
        # Stage 1: Coarse ranking - retrieve candidates with similarity search
        candidates = await self.retrieve_with_score(query, k=fetch_k)

        if not self.reranker or len(candidates) <= k:
            # No reranker or insufficient candidates, return as-is
            return candidates[:k]

        # Stage 2: Fine ranking - rerank with Rerank model
        try:
            # Extract document content
            documents_text = [doc.page_content for doc in candidates]

            # Import settings for top_n multiplier
            from app.core.config import get_settings

            settings = get_settings()

            # Call Rerank API
            rerank_response = self.reranker.rerank(
                model=model,
                query=query,
                documents=documents_text,
                top_n=k * settings.rerank_top_n_multiplier,
            )

            # Filter by rerank score threshold and reorder
            reranked_docs = []
            for result in rerank_response.results:
                # Only keep documents above threshold
                if (
                    hasattr(result, "relevance_score")
                    and result.relevance_score >= rerank_score_threshold
                ):
                    doc = candidates[result.index]
                    # Store rerank score in metadata for later use
                    doc.metadata["score"] = result.relevance_score
                    reranked_docs.append(doc)
                elif not hasattr(result, "relevance_score"):
                    # Fallback: if no score attribute, keep all (backwards compatibility)
                    reranked_docs.append(candidates[result.index])

            # Return top k from filtered results
            return reranked_docs[:k]

        except Exception as e:
            # Fallback: if rerank fails, return similarity results
            logger.warning(f"Rerank failed: {e}, falling back to similarity")
            return candidates[:k]

    async def retrieve_with_fallback(
        self,
        query: str,
        k: int = 5,
        score_threshold: float = 0.65,
    ) -> List[Document]:
        """
        Hybrid retrieval: Combines vector search + keyword matching + reranking

        This approach solves the semantic gap problem where:
        - Vector search may miss exact technical terms (e.g., "JB/T 8097")
        - Keyword matching captures precise term matches
        - Document name + article number filtering for precise citation queries
        - Reranking combines all for best results

        Args:
            query: Search query
            k: Number of documents to return
            score_threshold: Minimum similarity score for retrieval
        """
        from app.core.config import get_settings

        settings = get_settings()

        # Step 1: Extract structured keywords for text matching
        extracted_keywords = self._extract_keywords(query)

        # Step 2: Get candidates from both methods
        seen_contents = set()
        all_candidates = []

        # 2a: Keyword text matching with document name filtering (PRIORITIZED)
        # This is first because document-specific queries need precise matching
        has_doc_name = bool(extracted_keywords.get("doc_names"))
        has_keywords = (
            has_doc_name
            or extracted_keywords.get("article_numbers")
            or extracted_keywords.get("standards")
            or extracted_keywords.get("terms")  # Also match on general terms
        )
        if has_keywords:
            try:
                keyword_candidates = await self.retrieve_with_text_match(
                    query, extracted_keywords, k=100
                )
                for doc in keyword_candidates:
                    content_hash = hash(doc.page_content[:200])
                    if content_hash not in seen_contents:
                        seen_contents.add(content_hash)
                        all_candidates.append(doc)
            except Exception as e:
                logger.warning(f"Keyword search failed: {e}")

        # 2b: Vector similarity search (supplements keyword matching)
        try:
            fetch_k = k * settings.fetch_k_multiplier
            vector_candidates = await self.retrieve_with_score(query, k=fetch_k)
            for doc in vector_candidates:
                content_hash = hash(doc.page_content[:200])
                if content_hash not in seen_contents:
                    seen_contents.add(content_hash)
                    all_candidates.append(doc)
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")

        if not all_candidates:
            return []

        # Step 3: Rerank combined candidates
        if self.reranker and len(all_candidates) > k:
            try:
                documents_text = [doc.page_content for doc in all_candidates]

                rerank_response = self.reranker.rerank(
                    model="/model/bge-reranker-v2-m3",
                    query=query,
                    documents=documents_text,
                    top_n=k * settings.rerank_top_n_multiplier,
                )

                reranked_docs = []
                doc_article_matches = []  # Separate list for exact doc+article matches

                for result in rerank_response.results:
                    if (
                        hasattr(result, "relevance_score")
                        and result.relevance_score >= settings.rerank_score_threshold
                    ):
                        doc = all_candidates[result.index]
                        doc.metadata["score"] = result.relevance_score

                        # Prioritize doc+article exact matches
                        if doc.metadata.get("match_type") == "doc_article":
                            doc_article_matches.append(doc)
                        else:
                            reranked_docs.append(doc)

                # Put doc+article matches first, then other reranked docs
                final_docs = doc_article_matches + reranked_docs
                return final_docs[:k]

            except Exception as e:
                logger.warning(f"Rerank failed: {e}, using combined candidates")

        # Fallback: return top candidates by original score
        return sorted(
            all_candidates, key=lambda d: d.metadata.get("score", 0), reverse=True
        )[:k]
