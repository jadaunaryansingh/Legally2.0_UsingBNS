#!/usr/bin/env python3
"""
Test script to verify BNS PDF extraction works correctly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_extractor import get_bns_extractor

def test_bns_extraction():
    print("=" * 60)
    print("Testing BNS PDF Extraction")
    print("=" * 60)
    
    try:
        # Get the extractor
        extractor = get_bns_extractor()
        print(f"\n✓ BNS Extractor initialized")
        
        # Test queries
        test_queries = [
            "murder",
            "theft",
            "punishment",
            "assault"
        ]
        
        for query in test_queries:
            print(f"\n--- Testing query: '{query}' ---")
            context = extractor.get_context_for_ai(query)
            print(f"Context length: {len(context)} characters")
            print(f"Preview:\n{context[:500]}...")
            
            relevant_sections = extractor.get_relevant_sections(query, max_sections=3)
            if relevant_sections:
                print(f"\n✓ Found relevant sections for '{query}'")
            else:
                print(f"\n⚠ No specific sections found for '{query}' (general context will be used)")
        
        # Show statistics
        if extractor.bns_data:
            total_sections = extractor.bns_data.get('total_sections', 0)
            print(f"\n{'=' * 60}")
            print(f"Total BNS sections extracted: {total_sections}")
            print(f"{'=' * 60}")
            
            # Show first 5 section titles
            sections = extractor.bns_data.get('sections', {})
            print("\nSample sections:")
            for i, (section_num, section_info) in enumerate(list(sections.items())[:5]):
                print(f"  - Section {section_num}: {section_info.get('title', 'N/A')}")
        
        print("\n✓ BNS PDF extraction test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bns_extraction()
    sys.exit(0 if success else 1)
