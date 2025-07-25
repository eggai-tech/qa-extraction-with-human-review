#!/usr/bin/env python3
"""
Export QA pairs to Label Studio format for review
"""
import json
from pathlib import Path
from typing import List


def convert_to_labelstudio_format(qa_pairs_files: List[Path]):
    """Convert QA pairs with references to Label Studio format"""

    # Create Label Studio tasks
    tasks = []

    i = 0
    for qa_pairs_file in qa_pairs_files:
        # Read QA pairs
        with open(qa_pairs_file, 'r', encoding='utf-8') as f:
            qa_pairs = json.load(f)

        # Get source document name
        doc_name = qa_pairs[0].get('reference', {}).get('source_document', 'Unknown Document')

        for qa in qa_pairs:
            i += 1
            ref = qa.get('reference', {})

            # Extract the relevant chunk from the original document
            chunk_start = ref['char_start']
            chunk_end = ref['char_end']
            context_chunk = ref['chunk_text']

            # Create a task for Label Studio
            task = {
                "id": i,
                "data": {
                    # Main data for review
                    "question": qa['question'],
                    "answer": qa['answer'],
                    "context": context_chunk,

                    # Source document info
                    "source_document": doc_name,
                    "document_path": str("data/txt/" + doc_name),

                    # Metadata
                    "chunk_id": ref.get('chunk_id', ''),
                    "line_range": f"{ref.get('line_start', '')}-{ref.get('line_end', '')}",
                    "char_range": f"{chunk_start}-{chunk_end}",

                    # For display
                    "qa_pair_id": f"QA_{i}",
                    "chunk_preview": ref.get('chunk_preview', '')
                }
            }

            tasks.append(task)

    return tasks


def create_labelstudio_config():
    """Create Label Studio labeling configuration"""

    config = """
<View>
  <Header value="QA Pair Review" />
  
  <View style="box-shadow: 2px 2px 5px #999; padding: 20px; margin-top: 2em; border-radius: 5px; background-color: #e8f4f8;">
    <Header value="Source Document" />
    <Text name="source_doc" value="📄 $source_document" />
  </View>
  
  <View style="box-shadow: 2px 2px 5px #999; padding: 20px; margin-top: 2em; border-radius: 5px;">
    <Header value="Question" />
    <Text name="question" value="$question" />
    
    <Header value="Answer" />
    <Text name="answer" value="$answer" />
    
    <Header value="Source Context" />
    <Text name="context" value="$context" />
  </View>
  
  <View style="box-shadow: 2px 2px 5px #999; padding: 20px; margin-top: 2em; border-radius: 5px;">
    <Header value="Review Questions" />
    
    <Choices name="accuracy" toName="question" choice="single" showInLine="true">
      <Header value="Is the answer accurate based on the context?" />
      <Choice value="Yes" />
      <Choice value="No" />
    </Choices>
    
    <Choices name="relevance" toName="question" choice="single" showInLine="true">
      <Header value="Is the question relevant and well-formed?" />
      <Choice value="Yes" />
      <Choice value="No" />
    </Choices>
    
    <Choices name="issues" toName="answer" choice="multiple" showInLine="true">
      <Header value="Select any issues (multiple allowed):" />
      <Choice value="Answer too long" />
      <Choice value="Answer too short" />
      <Choice value="Grammar issues" />
      <Choice value="Factual error" />
      <Choice value="Ambiguous question" />
      <Choice value="Answer not in context" />
      <Choice value="Too specific" />
      <Choice value="Too general" />
    </Choices>
    
    <TextArea name="notes" toName="answer" rows="3" placeholder="Additional notes or suggested improvements..." />
  </View>
  
  <View style="box-shadow: 2px 2px 5px #999; padding: 20px; margin-top: 2em; border-radius: 5px; background-color: #f5f5f5;">
    <Header value="Metadata" />
    <Text name="qa_id" value="QA Pair ID: $qa_pair_id" />
    <Text name="chunk_info" value="Chunk $chunk_id (Lines: $line_range)" />
    <Text name="doc_path" value="Path: $document_path" />
  </View>
</View>
"""
    return config


def create_labelstudio_project_files(
        qa_pairs_files: List[Path],
        output_dir: Path
):
    """Create all necessary files for Label Studio import"""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Convert to Label Studio format
    print("Converting QA pairs to Label Studio format...")
    tasks = convert_to_labelstudio_format(qa_pairs_files)

    # Save tasks
    tasks_file = output_path / "qa_review_tasks.json"
    with open(tasks_file, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(tasks)} tasks to {tasks_file}")

    # Save labeling configuration
    config_file = output_path / "label_config.xml"
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(create_labelstudio_config())
    print(f"Saved labeling configuration to {config_file}")

    # Create instructions file
    instructions_file = output_path / "REVIEWER_GUIDE.md"
    with open(instructions_file, 'w', encoding='utf-8') as f:
        f.write(f"""# QA Review Guide for Label Studio

This guide is for reviewers using Label Studio to validate QA pairs.

## Files in This Directory

- `qa_review_tasks.json` - The QA pairs to review ({len(tasks)} tasks)
- `label_config.xml` - The review interface configuration
- `REVIEWER_GUIDE.md` - This file

## Quick Start

### 1. Access Label Studio

Open http://localhost:8080 in your browser (or the URL provided by your administrator)

### 2. Project Setup (if not already done)

1. Click "Create Project" → Name it "QA Pairs Review"
2. Go to Settings → Labeling Interface → Code
3. Copy ALL content from `label_config.xml` and paste it
4. Save the configuration

### 3. Import Review Tasks

1. Go to "Data Import"
2. Upload `qa_review_tasks.json`
3. Click "Import"

### 4. Review Process

For each QA pair, you will evaluate:

**Accuracy** - Is the answer factually correct based on the context?
- ✅ Accurate - Answer is fully supported by the text
- ⚠️ Partially Accurate - Some details are correct but incomplete
- ❌ Inaccurate - Answer contains errors or unsupported claims
- ❓ Cannot Determine - Not enough context to verify

**Relevance** - Is the question well-formed and meaningful?
- ⭐⭐⭐ Highly Relevant - Important question for understanding the document
- ⭐⭐ Relevant - Good question but not critical
- ⭐ Somewhat Relevant - Acceptable but could be better
- ❌ Not Relevant - Poor question or too trivial

**Quality** - Overall rating for training purposes
- 🏆 Excellent - Perfect for model training
- ✅ Good - Suitable with minor issues
- ⚠️ Fair - Usable but needs improvement
- ❌ Poor - Should not be used for training

**Common Issues to Flag:**
- Answer too long/short
- Grammar or spelling errors
- Factual errors
- Ambiguous questions
- Answer not found in context
- Too specific or too general

### 5. Export Results

After completing reviews:
1. Go to "Export" 
2. Select "JSON" format
3. Download and share with the project team

## Review Tips

1. **Read the full context** before evaluating
2. **Check line references** to verify answer location
3. **Be consistent** in your ratings across all QA pairs
4. **Use notes** to explain your reasoning for Poor/Fair ratings
5. **Flag issues** even for Good/Excellent pairs to help improve future generation

## Questions?

Contact the project maintainer or refer to the main README for technical details.
""")
    print(f"Saved instructions to {instructions_file}")

    return output_path


def main():
    qa_dir = "data/generated/filtered"
    output_dir = Path("data/labelstudio")
    # Check if files exist
    if not Path(qa_dir).exists():
        print(f"Error: QA qa_dir not found: {qa_dir}")
        return
    qa_files = list(Path(qa_dir).glob('*.json'))
    if not qa_files:
        print(f"Error: No QA files found in {qa_dir}")
        return

    # Create Label Studio files
    output_path = create_labelstudio_project_files(
        qa_files,
        output_dir
    )

    print(f"\n✅ Label Studio files created successfully!")
    print(f"📁 Output directory: {output_path}")
    print(f"\nNext steps:")
    print(f"1. Start Label Studio: make start-labelstudio")
    print(f"2. Open http://localhost:8080 in your browser")
    print(f"3. Follow the instructions in {output_path}/REVIEWER_GUIDE.md")


if __name__ == "__main__":
    main()
