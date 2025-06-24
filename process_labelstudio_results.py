#!/usr/bin/env python3
"""
Process Label Studio review results and filter QA pairs based on quality
"""
import json
from pathlib import Path
import argparse
from collections import Counter

def load_labelstudio_export(export_file):
    """Load Label Studio export"""
    
    # Check if export file exists and is not empty
    if not Path(export_file).exists():
        print(f"Error: Export file not found: {export_file}")
        print("\nTo export from Label Studio:")
        print("1. Go to your project in Label Studio")
        print("2. Click 'Export' button")
        print("3. Choose 'JSON' format")
        print("4. Save the file and run this command again with the correct path")
        exit(1)
    
    if Path(export_file).stat().st_size == 0:
        print(f"Error: Export file is empty: {export_file}")
        print("Make sure you've completed some reviews before exporting.")
        exit(1)
    
    # Read Label Studio export
    try:
        with open(export_file, 'r', encoding='utf-8') as f:
            reviewed_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in export file: {export_file}")
        print(f"JSON Error: {e}")
        print("\nMake sure you exported in JSON format from Label Studio.")
        exit(1)
    
    return reviewed_data

def filter_qa_by_quality(processed_qa):
    """Filter QA pairs based on question response from the annotator"""

    filtered_qa = []
    rejected_qa = []
    for qa in processed_qa:
        accuracy = qa.get('accuracy', 'Yes')
        relevance = qa.get('relevance', 'Yes')
        issues = qa.get('issues', [])

        if accuracy == 'Yes' and relevance == 'Yes' and not issues:
            filtered_qa.append(qa)
        else:
            rejected_qa.append(qa)
    
    return filtered_qa, rejected_qa

def main():
    parser = argparse.ArgumentParser(description='Process Label Studio review results')
    parser.add_argument('export_file', help='Label Studio JSON export file')
    args = parser.parse_args()
    
    # Create output directory
    output_path = Path("data/labelstudio/verified_results")
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Process the export
    print(f"Processing Label Studio export: {args.export_file}")
    processed_qa = load_labelstudio_export(args.export_file)
    print(f"Loaded {len(processed_qa)} QA pairs from export file.")
    
    # Filter by quality
    filtered_qa, rejected_qa = filter_qa_by_quality(processed_qa)
    
    # Save filtered results
    filtered_file = output_path / "filtered_qa_pairs.json"
    with open(filtered_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_qa, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved {len(filtered_qa)} accepted QA pairs to {filtered_file}")
    
    # Save rejected for review
    rejected_file = output_path / "rejected_qa_pairs.json"
    with open(rejected_file, 'w', encoding='utf-8') as f:
        json.dump(rejected_qa, f, indent=2, ensure_ascii=False)
    print(f"📝 Saved {len(rejected_qa)} rejected QA pairs to {rejected_file}")

if __name__ == "__main__":
    main()