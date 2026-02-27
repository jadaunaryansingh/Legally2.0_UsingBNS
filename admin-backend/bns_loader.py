"""
JSON-based BNS Loader - Fast access to BNS sections
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

class BNSLoader:
    def __init__(self, json_path: str = "bns_sections.json"):
        self.json_path = Path(__file__).parent / json_path
        self.bns_data = None
        
    def load(self) -> Dict:
        """Load BNS data from JSON file"""
        if self.bns_data is None:
            print(f"📚 Loading BNS data from {self.json_path.name}...")
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.bns_data = json.load(f)
            total = self.bns_data['metadata']['total_sections']
            print(f"✓ Loaded {total} BNS sections")
        return self.bns_data
    
    def search_sections(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search for relevant BNS sections"""
        if not self.bns_data:
            self.load()
        
        query_lower = query.lower()
        keywords = [k for k in query_lower.split() if len(k) > 3]
        
        results = []
        sections = self.bns_data['sections']
        
        for section_num, section_info in sections.items():
            title = section_info.get('title', '').lower()
            description = section_info.get('description', '').lower()
            category = section_info.get('category', '').lower()
            
            # Calculate relevance score
            score = 0
            for keyword in keywords:
                if keyword in title:
                    score += 5
                if keyword in description:
                    score += 2
                if keyword in category:
                    score += 3
            
            if score > 0:
                results.append({
                    'score': score,
                    'section': section_info
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return [r['section'] for r in results[:max_results]]
    
    def get_section(self, section_number: str) -> Optional[Dict]:
        """Get specific section by number"""
        if not self.bns_data:
            self.load()
        return self.bns_data['sections'].get(section_number)
    
    def get_category_sections(self, category: str) -> List[Dict]:
        """Get all sections in a category"""
        if not self.bns_data:
            self.load()
        
        section_numbers = self.bns_data['categories'].get(category, [])
        return [self.bns_data['sections'][num] for num in section_numbers]
    
    def format_for_ai(self, query: str, max_sections: int = 5) -> str:
        """Format relevant sections for AI context"""
        sections = self.search_sections(query, max_sections)
        
        if not sections:
            return """
REFERENCE: Bharatiya Nyaya Sanhita, 2023 (BNS)
The BNS has replaced the Indian Penal Code, 1860. Use BNS sections in your response.
"""
        
        formatted_sections = []
        for section in sections:
            section_text = f"""
**Section {section['section']} - {section['title']}**
Category: {section['category']}
Description: {section['description']}"""
            
            if section.get('punishment'):
                section_text += f"\nPunishment: {section['punishment']}"
            
            formatted_sections.append(section_text)
        
        return f"""
REFERENCE: Bharatiya Nyaya Sanhita, 2023 (BNS) - Relevant Sections:

{chr(10).join(formatted_sections)}

Use the above sections from BNS 2023 to provide accurate legal information.
"""
    
    def get_stats(self) -> Dict:
        """Get statistics about BNS data"""
        if not self.bns_data:
            self.load()
        
        sections = self.bns_data['sections']
        categories = self.bns_data['categories']
        
        return {
            'total_sections': len(sections),
            'total_categories': len(categories),
            'sections_with_punishment': sum(1 for s in sections.values() if s.get('punishment')),
            'categories': {cat: len(secs) for cat, secs in categories.items()}
        }

# Global instance
_bns_loader = None

def get_bns_loader() -> BNSLoader:
    """Get or create the global BNS loader instance"""
    global _bns_loader
    if _bns_loader is None:
        _bns_loader = BNSLoader()
        _bns_loader.load()
    return _bns_loader
