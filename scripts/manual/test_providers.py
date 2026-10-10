"""
Test script for LLM and embedding providers.
This script tests both Ollama and vLLM providers to verify they're working correctly.
"""
import os
import time
import argparse
from pprint import pprint

from app.integrations.providers import get_llm_provider, get_embedding_provider
from app.core.logger import logger

def test_llm_provider(provider_type):
    """Test text generation with the specified LLM provider"""
    print(f"\n{'='*30}")
    print(f"Testing {provider_type.upper()} LLM Provider")
    print(f"{'='*30}")
    
    try:
        # Get provider instance
        start = time.time()
        provider = get_llm_provider(provider_type=provider_type)
        print(f"✓ Provider instantiated ({time.time() - start:.2f}s)")
        
        # Get model info
        start = time.time()
        model_info = provider.get_model_info()
        print(f"✓ Model info retrieved ({time.time() - start:.2f}s)")
        print(f"  Model: {model_info.get('name')}")
        
        # Test text generation
        prompt = "Explain what an embedding is in 3 sentences."
        print(f"\nGenerating text with prompt: '{prompt}'")
        start = time.time()
        response = provider.generate_text(prompt=prompt, max_tokens=200, temperature=0.7)
        generation_time = time.time() - start
        print(f"\nResponse ({generation_time:.2f}s):")
        print(f"{response}")
        
        return True
    except Exception as e:
        print(f"✗ Error testing {provider_type} LLM provider: {e}")
        return False

def test_embedding_provider(provider_type):
    """Test embedding generation with the specified embedding provider"""
    print(f"\n{'='*30}")
    print(f"Testing {provider_type.upper()} Embedding Provider")
    print(f"{'='*30}")
    
    try:
        # Get provider instance
        start = time.time()
        provider = get_embedding_provider(provider_type=provider_type)
        print(f"✓ Provider instantiated ({time.time() - start:.2f}s)")
        
        # Get model info
        start = time.time()
        model_info = provider.get_model_info()
        print(f"✓ Model info retrieved ({time.time() - start:.2f}s)")
        print(f"  Model: {model_info.get('name')}")
        if 'embedding_dimensions' in model_info:
            print(f"  Dimensions: {model_info.get('embedding_dimensions')}")
        
        # Test embedding - single text
        text = "This is a test sentence to embed."
        print(f"\nGenerating embedding for: '{text}'")
        start = time.time()
        embedding = provider.get_embedding(text)
        embedding_time = time.time() - start
        
        # Print some statistics about the embedding
        embedding_len = len(embedding) if embedding else 0
        print(f"\nEmbedding generated ({embedding_time:.2f}s):")
        print(f"  Dimensions: {embedding_len}")
        if embedding_len > 0:
            print(f"  First 5 values: {embedding[:5]}")
        
        # Test batch embedding
        texts = ["First test sentence.", "Second test sentence.", "Third test sentence."]
        print(f"\nGenerating batch embeddings for {len(texts)} texts")
        start = time.time()
        embeddings = provider.get_embedding(texts)
        batch_time = time.time() - start
        
        print(f"\nBatch embeddings generated ({batch_time:.2f}s):")
        print(f"  Number of embeddings: {len(embeddings)}")
        if embeddings and len(embeddings) > 0:
            print(f"  Dimensions of first embedding: {len(embeddings[0])}")
        
        return True
    except Exception as e:
        print(f"✗ Error testing {provider_type} embedding provider: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test LLM and embedding providers")
    parser.add_argument("--provider", choices=["ollama", "vllm", "both"], default="both",
                        help="Which provider to test (ollama, vllm, or both)")
    parser.add_argument("--test-type", choices=["llm", "embedding", "both"], default="both",
                        help="Which functionality to test (llm, embedding, or both)")
    args = parser.parse_args()
    
    providers_to_test = []
    if args.provider == "both":
        providers_to_test = ["ollama", "vllm"]
    else:
        providers_to_test = [args.provider]
    
    results = {}
    
    for provider in providers_to_test:
        print(f"\n\n{'#'*50}")
        print(f"# Testing {provider.upper()} Provider")
        print(f"{'#'*50}")
        
        if args.test_type in ["llm", "both"]:
            results[f"{provider}_llm"] = test_llm_provider(provider)
            
        if args.test_type in ["embedding", "both"]:
            results[f"{provider}_embedding"] = test_embedding_provider(provider)
    
    # Print summary
    print(f"\n\n{'#'*50}")
    print("# Test Results Summary")
    print(f"{'#'*50}")
    
    for test, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test}: {status}")

if __name__ == "__main__":
    main()
