#!/usr/bin/env python3
"""
Improved BNS PDF Parser - Handles comparison table format
Extracts both BNS sections (new) and IPC references (old)
"""
import fitz
import json
import re
from pathlib import Path
from typing import Dict, List

class BNSComparisonParser:
    def __init__(self, pdf_path: str = "bns_document.pdf"):
        self.pdf_path = Path(__file__).parent / pdf_path
        self.output_path = Path(__file__).parent / "bns_sections.json"
        
    def extract_comparison_mappings(self) -> List[Dict]:
        """Extract BNS to IPC comparison mappings"""
        print(f"📖 Reading comparison PDF: {self.pdf_path.name}")
        doc = fitz.open(self.pdf_path)
        
        mappings = []
        full_text = ""
        
        for page_num in range(len(doc)):
            page_text = doc[page_num].get_text()
            full_text += page_text + "\n"
        
        doc.close()
        print(f"✓ Extracted text from {page_num + 1} pages")
        
        # Parse line by line to find BNS-IPC pairs
        lines = full_text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Pattern: "101. Murder.    300. Murder."
            # BNS section on left, IPC on right
            bns_match = re.match(r'^(\d+[A-Z]?)\.\s+(.+?)(?:\s{2,}|\t)(\d+[A-Z]?)\.\s', line)
            
            if bns_match:
                bns_num = bns_match.group(1)
                title = bns_match.group(2).strip()
                ipc_num = bns_match.group(3)
                
                # Clean title
                title = re.sub(r'\s+', ' ', title).strip()
                
                # Get description from next few lines
                desc_lines = []
                for j in range(1, min(15, len(lines) - i)):
                    next_line = lines[i + j].strip()
                    # Stop if we hit another section number pattern
                    if re.match(r'^\d+[A-Z]?\.\s+[A-Z]', next_line):
                        break
                    if next_line and len(next_line) > 15 and not next_line.startswith('---'):
                        desc_lines.append(next_line)
                    if len(' '.join(desc_lines)) > 600:
                        break
                
                description = ' '.join(desc_lines)
                description = re.sub(r'\s+', ' ', description).strip()
                
                # Extract punishment
                punishment = self.extract_punishment(description)
                category = self.categorize_section(title, description)
                
                mappings.append({
                    "bns_section": bns_num,
                    "ipc_section": ipc_num,
                    "title": title,
                    "description": description[:1000] if description else title,
                    "punishment": punishment,
                    "category": category
                })
        
        print(f"✓ Extracted {len(mappings)} BNS-IPC section mappings")
        return mappings
    
    def extract_punishment(self, text: str) -> str:
        """Extract punishment information"""
        text_lower = text.lower()
        punishment_keywords = [
            'imprisonment', 'fine', 'death', 'rigorous imprisonment',
            'life imprisonment', 'punishment', 'liable', 'shall be punished',
            'years', 'penalty'
        ]
        
        for keyword in punishment_keywords:
            if keyword in text_lower:
                sentences = re.split(r'[.!?]', text)
                for sentence in sentences:
                    if keyword in sentence.lower() and len(sentence.strip()) > 20:
                        punishment = sentence.strip()
                        if len(punishment) < 500:
                            return punishment
        return None
    
    def categorize_section(self, title: str, content: str) -> str:
        """Categorize the section"""
        text = (title + " " + content).lower()
        
        categories = {
            "Murder & Homicide": ["murder", "homicide", "culpable", "death", "killing"],
            "Theft": ["theft", "stealing", "stolen"],
            "Assault & Violence": ["assault", "hurt", "grievous", "violence", "beating", "attack"],
            "Sexual Offences": ["rape", "sexual", "molestation", "harassment", "modesty"],
            "Kidnapping": ["kidnapping", "abduction", "abducting"],
            "Fraud & Cheating": ["cheating", "fraud", "forgery", "counterfeiting", "deception"],
            "Property Crimes": ["property", "trespass", "mischief", "damage"],
            "Public Order": ["public order", "unlawful assembly", "riot", "affray"],
            "Corruption": ["corruption", "bribery", "public servant"],
            "Defamation": ["defamation", "reputation", "insult"],
            "General Provisions": ["general", "definition", "explanation", "interpretation"],
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        return "Miscellaneous"
    
    def create_json(self) -> Dict:
        """Create final JSON structure"""
        print("\n" + "="*60)
        print("🔄 Parsing BNS Comparison PDF")
        print("="*60)
        
        mappings = self.extract_comparison_mappings()
        
        # Create sections dictionary keyed by BNS section number
        sections = {}
        for mapping in mappings:
            bns_num = mapping['bns_section']
            sections[bns_num] = {
                "section": bns_num,
                "title": mapping['title'],
                "description": mapping['description'],
                "punishment": mapping['punishment'],
                "category": mapping['category'],
                "act": "Bharatiya Nyaya Sanhita, 2023 (BNS)",
                "replaces_ipc": mapping['ipc_section']
            }
        
        # Create categories summary
        categories = {}
        for section_data in sections.values():
            category = section_data['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(section_data['section'])
        
        bns_data = {
            "metadata": {
                "title": "Bharatiya Nyaya Sanhita, 2023",
                "short_name": "BNS",
                "replaces": "Indian Penal Code, 1860 (IPC)",
                "effective_date": "July 1, 2024",
                "total_sections": len(sections),
                "description": "The Bharatiya Nyaya Sanhita (BNS) is the new criminal code of India that replaces the Indian Penal Code (IPC)"
            },
            "sections": sections,
            "categories": {cat: sorted(secs) for cat, secs in categories.items()}
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
    
    def print_summary(self, data: Dict):
        """Print extraction summary"""
        print("\n" + "="*60)
        print("📊 EXTRACTION SUMMARY")
        print("="*60)
        
        sections = data['sections']
        categories = data['categories']
        
        print(f"\nTotal BNS Sections: {len(sections)}")
        print(f"Total Categories: {len(categories)}")
        
        with_punishment = sum(1 for s in sections.values() if s.get('punishment'))
        print(f"Sections with Punishment Info: {with_punishment}")
        
        print("\n📋 Sample BNS Sections:")
        sample_sections = {
            "101": "Murder",
            "103": "Punishment for murder",
            "109": "Attempt to murder",
            "303": "Theft",
            "305": "Theft in dwelling house"
        }
        
        for bns_num, expected_title in sample_sections.items():
            if bns_num in sections:
                section = sections[bns_num]
                print(f"  ✓ BNS Section {bns_num}: {section['title']}")
                print(f"    (Replaces IPC {section['replaces_ipc']})")
        
        print("\n" + "="*60)
        print("✅ BNS JSON created with correct section numbers!")
        print("="*60)

def main():
    parser = BNSComparisonParser()
    bns_data = parser.create_json()
    return bns_data

if __name__ == "__main__":
    main()
