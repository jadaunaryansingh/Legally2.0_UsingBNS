#!/usr/bin/env python3
"""
Enhanced BNS PDF to JSON Converter
Extracts structured legal information from the BNS PDF document
"""
import fitz  # PyMuPDF
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

class BNSToJSON:
    def __init__(self, pdf_path: str = "bns_document.pdf"):
        self.pdf_path = Path(__file__).parent / pdf_path
        self.output_path = Path(__file__).parent / "bns_sections.json"
        
    def extract_full_text(self) -> str:
        """Extract all text from PDF"""
        print(f"📖 Reading PDF: {self.pdf_path.name}")
        doc = fitz.open(self.pdf_path)
        
        full_text = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            full_text += f"\n[PAGE {page_num + 1}]\n"
            full_text += page.get_text()
        
        doc.close()
        print(f"✓ Extracted {len(full_text):,} characters from {page_num + 1} pages")
        return full_text
    
    def extract_section_info(self, text: str) -> Dict:
        """Extract section number, title, and content"""
        # Multiple patterns to catch different formats in the PDF
        patterns = [
            # Pattern 1: "Section 123 - Title"
            r'Section\s+(\d+[A-Z]?)\s*[-–—.]\s*([^\n]+)',
            # Pattern 2: "Section 123. Title"
            r'Section\s+(\d+[A-Z]?)\.\s*([^\n]+)',
            # Pattern 3: Just "123. Title" at start of line
            r'^(\d+[A-Z]?)\.\s+([^\n]+)',
            # Pattern 4: "Section\n123\nTitle"
            r'Section\s*\n\s*(\d+[A-Z]?)\s*\n\s*([^\n]+)',
        ]
        
        sections = {}
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    section_num = match.group(1).strip()
                    title = match.group(2).strip()
                    
                    # Clean up title
                    title = re.sub(r'\s+', ' ', title)
                    title = title.rstrip('.')
                    
                    # Collect content from next few lines
                    content_lines = []
                    for j in range(1, min(20, len(lines) - i)):
                        next_line = lines[i + j].strip()
                        
                        # Stop if we hit another section
                        if re.match(r'Section\s+\d+|^\d+[A-Z]?\.\s+[A-Z]', next_line, re.IGNORECASE):
                            break
                        
                        if next_line and len(next_line) > 10:
                            content_lines.append(next_line)
                        
                        if len(' '.join(content_lines)) > 800:
                            break
                    
                    content = ' '.join(content_lines)
                    content = re.sub(r'\s+', ' ', content).strip()
                    
                    # Extract punishment if mentioned
                    punishment = self.extract_punishment(content)
                    
                    # Categorize offense
                    category = self.categorize_section(title, content)
                    
                    if section_num not in sections:
                        sections[section_num] = {
                            "section": section_num,
                            "title": title,
                            "description": content[:1000] if content else title,
                            "punishment": punishment,
                            "category": category,
                            "act": "Bharatiya Nyaya Sanhita, 2023 (BNS)"
                        }
                    break
        
        return sections
    
    def extract_punishment(self, text: str) -> Optional[str]:
        """Extract punishment information from text"""
        text_lower = text.lower()
        
        # Keywords indicating punishment
        punishment_keywords = [
            'imprisonment', 'fine', 'death', 'rigorous imprisonment',
            'life imprisonment', 'punishment', 'liable', 'shall be punished'
        ]
        
        for keyword in punishment_keywords:
            if keyword in text_lower:
                # Find sentence containing punishment
                sentences = re.split(r'[.!?]', text)
                for sentence in sentences:
                    if keyword in sentence.lower():
                        punishment = sentence.strip()
                        if len(punishment) > 20 and len(punishment) < 500:
                            return punishment
        
        return None
    
    def categorize_section(self, title: str, content: str) -> str:
        """Categorize the section based on content"""
        text = (title + " " + content).lower()
        
        categories = {
            "Murder & Homicide": ["murder", "homicide", "culpable", "death", "killing"],
            "Theft": ["theft", "stealing", "stolen", "larceny"],
            "Assault & Violence": ["assault", "hurt", "grievous", "violence", "beating", "attack"],
            "Sexual Offences": ["rape", "sexual", "molestation", "harassment", "outraging modesty"],
            "Kidnapping": ["kidnapping", "abduction", "abducting"],
            "Fraud & Cheating": ["cheating", "fraud", "forgery", "counterfeiting", "deception"],
            "Property Crimes": ["property", "trespass", "mischief", "damage"],
            "Public Order": ["public order", "unlawful assembly", "riot", "affray"],
            "Corruption": ["corruption", "bribery", "public servant"],
            "Defamation": ["defamation", "reputation", "insult"],
            "Criminal Procedure": ["procedure", "arrest", "bail", "investigation", "trial"],
            "Evidence": ["evidence", "witness", "testimony", "proof"],
            "General Provisions": ["general", "definition", "explanation", "interpretation"],
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        
        return "Miscellaneous"
    
    def create_json(self) -> Dict:
        """Create comprehensive JSON structure"""
        print("\n" + "="*60)
        print("🔄 Converting BNS PDF to JSON")
        print("="*60)
        
        # Extract text
        full_text = self.extract_full_text()
        
        # Extract sections
        print("\n🔍 Parsing sections...")
        sections = self.extract_section_info(full_text)
        
        # Create structured output
        bns_data = {
            "metadata": {
                "title": "Bharatiya Nyaya Sanhita, 2023",
                "short_name": "BNS",
                "replaces": "Indian Penal Code, 1860 (IPC)",
                "effective_date": "2023",
                "total_sections": len(sections),
                "description": "The Bharatiya Nyaya Sanhita (BNS) is the new criminal code of India that replaces the Indian Penal Code (IPC)"
            },
            "sections": sections,
            "categories": self.get_category_summary(sections)
        }
        
        # Save to JSON
        print(f"\n💾 Saving to {self.output_path.name}...")
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(bns_data, f, indent=2, ensure_ascii=False)
        
        file_size = self.output_path.stat().st_size
        print(f"✓ Created JSON file: {file_size:,} bytes")
        
        # Print summary
        self.print_summary(bns_data)
        
        return bns_data
    
    def get_category_summary(self, sections: Dict) -> Dict:
        """Create category summary"""
        categories = {}
        for section_num, section_info in sections.items():
            category = section_info.get('category', 'Miscellaneous')
            if category not in categories:
                categories[category] = []
            categories[category].append(section_num)
        
        return {cat: sorted(secs) for cat, secs in categories.items()}
    
    def print_summary(self, data: Dict):
        """Print summary of extracted data"""
        print("\n" + "="*60)
        print("📊 EXTRACTION SUMMARY")
        print("="*60)
        
        sections = data['sections']
        categories = data['categories']
        
        print(f"\nTotal Sections: {len(sections)}")
        print(f"Total Categories: {len(categories)}")
        
        # Show punishment stats
        with_punishment = sum(1 for s in sections.values() if s.get('punishment'))
        print(f"Sections with Punishment Info: {with_punishment}")
        
        print("\n📋 Sections by Category:")
        for category, section_list in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  • {category}: {len(section_list)} sections")
        
        print("\n📄 Sample Sections:")
        for section_num, section_info in list(sections.items())[:5]:
            print(f"\n  Section {section_num}: {section_info['title']}")
            if section_info.get('punishment'):
                print(f"    Punishment: {section_info['punishment'][:80]}...")
        
        print("\n" + "="*60)
        print("✅ BNS JSON conversion completed successfully!")
        print("="*60)

def main():
    converter = BNSToJSON()
    bns_data = converter.create_json()
    return bns_data

if __name__ == "__main__":
    main()
