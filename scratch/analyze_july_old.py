import json

def parse_july_opps():
    try:
        with open('agent_memory/july_opportunity_audit_results.json', 'r', encoding='utf-8') as f:
            opps = json.load(f)
    except Exception as e:
        print(f"Error: {e}")
        return
        
    print(f"Total opportunities in July: {len(opps)}")
    for opp in opps:
        print(f"\nDate: {opp.get('date')} | Time: {opp.get('time_utc')}")
        # Extract Andrea and Fabio decisions
        andrea_text = opp.get('andrea', '')
        fabio_text = opp.get('fabio', '')
        
        # Look for summary decisions
        print("--- Fabio's feedback snippet ---")
        lines = [l.strip() for l in fabio_text.split('\n') if l.strip()]
        for l in lines[:10]:
            print(f"  {l}")
        print("--- Andrea's feedback snippet ---")
        lines = [l.strip() for l in andrea_text.split('\n') if l.strip()]
        for l in lines[:10]:
            print(f"  {l}")

if __name__ == '__main__':
    parse_july_opps()
