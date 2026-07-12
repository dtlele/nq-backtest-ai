import os
import json

def parse_trader_knowledge():
    base_dir = os.path.dirname(__file__)
    knowledge_dir = os.path.join(base_dir, '..', '..', '..', 'knowledge')
    output_dir = os.path.join(knowledge_dir, 'trader_lessons_graph')
    
    os.makedirs(output_dir, exist_ok=True)
    
    trader_files = ['fabio_knowledge.json', 'andrea_knowledge.json']
    converted_count = 0
    
    for t_file in trader_files:
        file_path = os.path.join(knowledge_dir, t_file)
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        knowledge_dict = data.get("knowledge_by_topic", {})
        agent_name = data.get('agent', 'Unknown')
        
        for topic, content in knowledge_dict.items():
            # Scriviamo in Markdown per permettere a Graphify di leggerli come documenti
            md_content = f"# {topic.replace('_', ' ').title()}\n\n"
            md_content += f"**Trader**: {agent_name.capitalize()}\n"
            md_content += f"**Knowledge Node**: {topic}\n\n"
            md_content += "## Dettagli e Regole Operative\n"
            md_content += content.replace("Continuing conversation 34db14c7...\nAnswer:\n", "")
            
            file_name = f"rule_{agent_name}_{topic}.md"
            out_path = os.path.join(output_dir, file_name)
            
            with open(out_path, 'w', encoding='utf-8') as out_f:
                out_f.write(md_content)
                
            converted_count += 1

    print(f"Salvati {converted_count} file Markdown in {output_dir}")

if __name__ == "__main__":
    parse_trader_knowledge()
