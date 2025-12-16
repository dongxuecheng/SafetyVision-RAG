#!/usr/bin/env python3
"""
Quick test script for RAG QA system
"""

import asyncio
import httpx


async def test_qa_api():
    """Test QA API endpoint"""

    base_url = "http://localhost:8080"

    # Test questions
    questions = [
        "什么是高处作业？",
        "安全帽的使用要求是什么？",
        "施工现场消防安全注意事项",
    ]

    print("🧪 Testing RAG QA System API\n")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test health endpoint
        try:
            response = await client.get(f"{base_url}/api/qa/health")
            print(f"\n✅ Health Check: {response.json()}")
        except Exception as e:
            print(f"\n❌ Health Check Failed: {e}")
            return

        # Test QA endpoint
        for i, question in enumerate(questions, 1):
            print(f"\n{'=' * 60}")
            print(f"Question {i}: {question}")
            print("-" * 60)

            try:
                response = await client.post(
                    f"{base_url}/api/qa/ask", json={"question": question}, timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    print(f"\n📝 Answer:\n{result['answer']}\n")

                    if result["has_relevant_sources"]:
                        print(f"📚 Sources ({len(result['sources'])} found):")
                        for idx, source in enumerate(result["sources"][:3], 1):
                            print(
                                f"  {idx}. {source['filename']} - Score: {source['score']:.3f}"
                            )
                    else:
                        print("ℹ️  No relevant sources found")
                else:
                    print(f"❌ Error: Status {response.status_code}")
                    print(response.text)

            except Exception as e:
                print(f"❌ Request Failed: {e}")

            await asyncio.sleep(1)  # Rate limiting

    print("\n" + "=" * 60)
    print("✅ Test completed!\n")


if __name__ == "__main__":
    print(
        """
╔══════════════════════════════════════════════════════╗
║        RAG QA System - Quick Test Script            ║
╚══════════════════════════════════════════════════════╝

Prerequisites:
1. FastAPI service is running: docker compose up -d
2. Knowledge documents are uploaded to QA collection
3. Service is accessible at http://localhost:8080

Starting tests...
    """
    )

    asyncio.run(test_qa_api())
