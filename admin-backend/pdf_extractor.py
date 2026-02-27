"""
PDF Extractor for BNS (Bharatiya Nyaya Sanhita) Document
Extracts and caches legal text for AI reference
"""
import fitz  # PyMuPDF
import os
import json
from pathlib import Path
import re

class BNSExtractor:
    def __init__(self, pdf_path: str = "bns_document.pdf"):
        self.pdf_path = Path(__file__).parent / pdf_path
        self.cache_path = Path(__file__).parent / "bns_cache.json"
        self.bns_data = None
        
    def extract_pdf_text(self) -> str:
        """Extract all text from the PDF"""
        print(f"Extracting text from {self.pdf_path}...")
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"BNS PDF not found at: {self.pdf_path}")
        
        text = ""
        try:
            doc = fitz.open(self.pdf_path)
            page_count = len(doc)
            for page_num, page in enumerate(doc):
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page.get_text()
            doc.close()
            print(f"✓ Extracted {len(text)} characters from {page_count} pages")
        except Exception as e:
            print(f"✗ Error extracting PDF: {e}")
            raise
        
        return text
    
    def parse_sections(self, text: str) -> dict:
        """Parse the PDF text into structured sections"""
        sections = {}
        
        # Pattern to match section numbers and titles
        # Adjust this regex based on the actual PDF format
        section_pattern = r'(?:Section\s+|Section\s*\n\s*)(\d+[A-Z]?)\s*[.:\-—–]\s*([^\n]+)'
        
        matches = re.finditer(section_pattern, text, re.IGNORECASE | re.MULTILINE)
        
        for match in matches:
            section_num = match.group(1).strip()
            section_title = match.group(2).strip()
            
            # Find the content after this section until the next section
            start_pos = match.end()
            # Look for next section or end of text (limit to next 2000 chars)
            next_match = re.search(
                r'(?:Section\s+|Section\s*\n\s*)\d+[A-Z]?',
                text[start_pos:start_pos+2000],
                re.IGNORECASE
            )
            
            end_pos = start_pos + (next_match.start() if next_match else min(1500, len(text) - start_pos))
            content = text[start_pos:end_pos].strip()
            
            # Clean up content
            content = re.sub(r'\n+', ' ', content)
            content = re.sub(r'\s+', ' ', content)
            content = content[:1000]  # Limit length
            
            sections[section_num] = {
                "title": section_title,
                "content": content
            }
        
        print(f"✓ Parsed {len(sections)} sections from BNS document")
        return sections
    
    def load_or_extract(self) -> dict:
        """Load from cache or extract fresh"""
        # Check if cache exists and is recent
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    print(f"✓ Loaded {len(cached_data.get('sections', {}))} BNS sections from cache")
                    return cached_data
            except Exception as e:
                print(f"Cache load failed: {e}, re-extracting...")
        
        # Extract fresh from PDF
        full_text = self.extract_pdf_text()
        sections = self.parse_sections(full_text)
        
        data = {
            "full_text": full_text[:50000],  # Store first 50k chars of full text
            "sections": sections,
            "total_sections": len(sections)
        }
        
        # Save to cache
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✓ Cached BNS data to {self.cache_path}")
        except Exception as e:
            print(f"Warning: Could not cache data: {e}")
        
        return data
    
    def get_relevant_sections(self, query: str, max_sections: int = 5) -> str:
        """Get relevant BNS sections based on query keywords"""
        if not self.bns_data:
            self.bns_data = self.load_or_extract()
        
        sections = self.bns_data.get("sections", {})
        query_lower = query.lower()
        
        # Keywords to section mapping
        relevant = []
        
        # Search for relevant sections
        for section_num, section_info in sections.items():
            title = section_info.get("title", "").lower()
            content = section_info.get("content", "").lower()
            
            # Calculate relevance score
            score = 0
            keywords = query_lower.split()
            for keyword in keywords:
                if len(keyword) > 3:  # Ignore short words
                    if keyword in title:
                        score += 3
                    if keyword in content:
                        score += 1
            
            if score > 0:
                relevant.append((section_num, section_info, score))
        
        # Sort by relevance score
        relevant.sort(key=lambda x: x[2], reverse=True)
        
        # Format top sections
        result = []
        for section_num, section_info, score in relevant[:max_sections]:
            result.append(
                f"**Section {section_num} - {section_info['title']}**\n"
                f"{section_info['content'][:500]}"
            )
        
        return "\n\n".join(result) if result else ""
    
    def get_context_for_ai(self, query: str) -> str:
        """Get formatted BNS context for AI prompt"""
        if not self.bns_data:
            self.bns_data = self.load_or_extract()
        
        relevant_sections = self.get_relevant_sections(query)
        
        if relevant_sections:
            return f"""
REFERENCE: Bharatiya Nyaya Sanhita, 2023 (BNS) - Relevant Sections:

{relevant_sections}

Use the above sections from BNS 2023 to provide accurate legal information.
"""
        else:
            return """
REFERENCE: Bharatiya Nyaya Sanhita, 2023 (BNS)
The BNS has replaced the Indian Penal Code, 1860. Use BNS sections in your response.
"""

# Global instance
bns_extractor = None

def get_bns_extractor() -> BNSExtractor:
    """Get or create the global BNS extractor instance"""
    global bns_extractor
    if bns_extractor is None:
        bns_extractor = BNSExtractor()
        # Load on first access
        bns_extractor.load_or_extract()
    return bns_extractor
