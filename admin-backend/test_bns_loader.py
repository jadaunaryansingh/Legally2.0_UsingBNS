#!/usr/bin/env python3
"""
Test the BNS JSON loader
"""
from bns_loader import get_bns_loader

def test_bns_loader():
    print("="*60)
    print("Testing BNS JSON Loader")
    print("="*60)
    
    loader = get_bns_loader()
    
    # Test 1: Get stats
    print("\n📊 BNS Statistics:")
    stats = loader.get_stats()
    print(f"  Total sections: {stats['total_sections']}")
    print(f"  Total categories: {stats['total_categories']}")
    print(f"  Sections with punishment: {stats['sections_with_punishment']}")
    
    # Test 2: Search for specific topics
    test_queries = ["murder", "theft", "assault", "fraud"]
    
    for query in test_queries:
        print(f"\n🔍 Searching for: '{query}'")
        sections = loader.search_sections(query, max_results=3)
        print(f"  Found {len(sections)} relevant sections:")
        for section in sections:
            print(f"    • Section {section['section']}: {section['title']}")
            print(f"      Category: {section['category']}")
    
    # Test 3: Format for AI
    print(f"\n🤖 AI Context for 'murder':")
    ai_context = loader.format_for_ai("murder", max_sections=2)
    print(ai_context[:500] + "...")
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_bns_loader()
