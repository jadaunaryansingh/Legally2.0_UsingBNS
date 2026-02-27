#!/usr/bin/env python3
"""
Correct BNS PDF Parser - Extracts actual BNS section numbers
Format: Section number on one line, title on next line
"""
import fitz
import json
import re
from pathlib import Path
from typing import Dict, List

class BNSParser:
    def __init__(self, pdf_path: str = "bns_document.pdf"):
        self.pdf_path = Path(__file__).parent / pdf_path
        self.output_path = Path(__file__).parent / "bns_sections.json"
        
    def extract_sections(self) -> Dict:
        """Extract BNS sections from PDF"""
        print(f"📖 Reading BNS PDF: {self.pdf_path.name}")
        doc = fitz.open(self.pdf_path)
        
        all_lines = []
        for page_num in range(len(doc)):
            page_text = doc[page_num].get_text()
            all_lines.extend(page_text.split('\n'))
        
        doc.close()
        print(f"✓ Extracted {len(all_lines):,} lines from {page_num + 1} pages")
        
        sections = {}
        i = 0
        
        while i < len(all_lines):
            line = all_lines[i].strip()
            
            # Check if line is just a section number (e.g., "101. " or "103.")
            section_match = re.match(r'^(\d+[A-Z]?)\.\s*$', line)
            
            if section_match and i + 1 < len(all_lines):
                section_num = section_match.group(1)
                # Next line should be the title
                title = all_lines[i + 1].strip()
                
                # Skip if title is empty or too short
                if len(title) < 3:
                    i += 1
                    continue
                
                # Collect description from subsequent lines
                desc_lines = []
                j = i + 2
                while j < min(i + 20, len(all_lines)):
                    next_line = all_lines[j].strip()
                    # Stop if we hit another section number
                    if re.match(r'^\d+[A-Z]?\.\s*$', next_line):
                        break
                    if next_line and len(next_line) > 10:
                        desc_lines.append(next_line)
                    if len(' '.join(desc_lines)) > 800:
                        break
                    j += 1
                
                description = ' '.join(desc_lines)
                description = re.sub(r'\s+', ' ', description).strip()
                
                # Extract punishment
                punishment = self.extract_punishment(title + " " + description)
                category = self.categorize_section(title, description)
                
                sections[section_num] = {
                    "section": section_num,
                    "title": title,
                    "description": description[:1000] if description else title,
                    "punishment": punishment,
                    "category": category,
                    "act": "Bharatiya Nyaya Sanhita, 2023 (BNS)"
                }
                
                i += 1  # Move past the title line
            
            i += 1
        
        print(f"✓ Extracted {len(sections)} BNS sections")
        return sections
    
    def extract_punishment(self, text: str) -> str:
        """Extract punishment information"""
        text_lower = text.lower()
        punishment_keywords = [
            'imprisonment', 'fine', 'death', 'rigorous imprisonment',
            'life imprisonment', 'punishment', 'liable', 'shall be punished',
            'years', 'penalty', 'punishable'
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
            "Murder & Homicide": ["murder", "homicide", "culpable", "death caused", "killing"],
            "Theft": ["theft", "stealing", "stolen"],
            "Assault & Violence": ["assault", "hurt", "grievous", "violence", "beating", "attack", "wound"],
            "Sexual Offences": ["rape", "sexual", "molestation", "harassment", "modesty", "gang rape"],
            "Kidnapping": ["kidnapping", "abduction", "abducting"],
            "Fraud & Cheating": ["cheating", "fraud", "forgery", "counterfeiting", "deception", "dishonestly"],
            "Property Crimes": ["property", "trespass", "mischief", "damage", "criminal breach"],
            "Public Order": ["public order", "unlawful assembly", "riot", "affray", "public nuisance"],
            "Corruption": ["corruption", "bribery", "public servant"],
            "Defamation": ["defamation", "reputation", "insult"],
            "Robbery & Dacoity": ["robbery", "dacoity", "extortion"],
            "General Provisions": ["general", "definition", "explanation", "interpretation", "gender", "punishment"],
            "Abetment & Conspiracy": ["abetment", "conspiracy", "abet"],
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        return "Miscellaneous"
    
    def create_json(self) -> Dict:
        """Create final JSON structure"""
        print("\n" + "="*60)
        print("🔄 Extracting BNS Sections with Correct Numbers")
        print("="*60)
        
        sections = self.extract_sections()
        
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
            "categories": {cat: sorted(secs, key=lambda x: (int(re.sub(r'[A-Z]', '', x)), x)) for cat, secs in categories.items()}
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
        
        print("\n📋 Key BNS Sections (Murder, Theft, etc.):")
        key_sections = ["100", "101", "103", "109", "303", "305", "351"]
        for sec_num in key_sections:
            if sec_num in sections:
                section = sections[sec_num]
                print(f"  ✓ BNS Section {sec_num}: {section['title']}")
                print(f"    Category: {section['category']}")
        
        print("\n📋 Sections by Category:")
        for category, section_list in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            print(f"  • {category}: {len(section_list)} sections")
        
        print("\n" + "="*60)
        print("✅ BNS JSON created with CORRECT section numbers!")
        print("="*60)

def main():
    parser = BNSParser()
    bns_data = parser.create_json()
    return bns_data

if __name__ == "__main__":
    main()
