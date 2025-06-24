import json
import os
import time
from pathlib import Path

import yaml
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

with open('configs/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize OpenAI client
api_key = config['api-endpoint']['api_key']
os.environ["OPENAI_API_KEY"] = api_key


def deduplicate_questions(qa_pairs, threshold):
    questions = [qa_pair["question"] for qa_pair in qa_pairs]
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Compute embeddings
    embeddings = model.encode(questions)
    # compute cosine similarity matrix
    similarity_matrix = cosine_similarity(embeddings)
    # drop duplicates based on the threshold
    unique_indices = set()
    for i in range(len(questions)):
        if i in unique_indices:
            continue
        unique_indices.add(i)
        for j in range(i + 1, len(questions)):
            if similarity_matrix[i][j] >= threshold:
                unique_indices.add(j)

    # report number of duplicates
    num_duplicates = len(questions) - len(unique_indices)
    print(f"Found {num_duplicates} duplicate questions with threshold {threshold}.")
    # return the unique qa_pairs
    return [qa_pairs[i] for i in unique_indices]


def main():
    input_dir = Path(config['filtering']['input_dir'])
    dedup_dir = input_dir / "deduplicated"
    filtered_dir = input_dir / "filtered"
    rejected_dir = input_dir / "rejected"
    filtered_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)
    dedup_dir.mkdir(parents=True, exist_ok=True)

    # load the thresholds from the config file
    faithfulness_threshold = config['filtering']['faithfulness_threshold']
    answer_relevancy_threshold = config['filtering']['answer_relevancy_threshold']
    context_precision_threshold = config['filtering']['context_precision_threshold']
    deduplicate_threshold = config['filtering']['deduplicate_threshold']
    start = time.perf_counter()
    for input_file in input_dir.glob("*.json"):
        print(f"Processing {input_file.name}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            qa_pairs = json.load(f)

        # deduplicate the qa_pairs if necessary
        if deduplicate_threshold is not None:
            qa_pairs = deduplicate_questions(qa_pairs, deduplicate_threshold)
            # save the deduplicated pairs
            dedup_file = dedup_dir / input_file.name
            with open(dedup_file, 'w', encoding='utf-8') as f:
                json.dump(qa_pairs, f, indent=2, ensure_ascii=False)

        filtered_pairs = []
        rejected_pairs = []
        # save contexts for context precision computation
        contexts = [qa_pair["reference"]["chunk_text"] for qa_pair in qa_pairs]
        qa_pairs_with_metrics = []
        for qa_pair in qa_pairs:
            question = qa_pair["question"]
            answer = qa_pair["answer"]
            context = qa_pair["reference"]["chunk_text"]
            data_sample = {
                "question": [question],
                "answer": [answer],
                "contexts": [[context]]
            }
            metrics = {}
            should_keep = True
            if faithfulness_threshold is not None:
                score = evaluate(Dataset.from_dict(data_sample), metrics=[faithfulness])
                metrics["faithfulness"] = score["faithfulness"][0]
                should_keep = should_keep and (metrics["faithfulness"] >= faithfulness_threshold)
            if answer_relevancy_threshold is not None:
                score = evaluate(Dataset.from_dict(data_sample), metrics=[answer_relevancy])
                metrics["answer_relevancy"] = score["answer_relevancy"][0]
                should_keep = should_keep and (metrics["answer_relevancy"] >= answer_relevancy_threshold)

            if context_precision_threshold is not None:
                # compute context precision
                data_sample["contexts"] = [contexts]
                data_sample["ground_truth"] = [answer]
                score = evaluate(Dataset.from_dict(data_sample), metrics=[context_precision])
                metrics["context_precision"] = score["context_precision"][0]
                should_keep = should_keep and (metrics["context_precision"] >= context_precision_threshold)

            # save metrics
            qa_pair["metrics"] = metrics
            qa_pairs_with_metrics.append(qa_pair)

            if should_keep:
                filtered_pairs.append(qa_pair)
            else:
                print(f"Rejected pair: {qa_pair['question']} -> {qa_pair['answer']}")
                rejected_pairs.append(qa_pair)

        output_file = filtered_dir / input_file.name
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_pairs, f, indent=2, ensure_ascii=False)

        rejected_file = rejected_dir / input_file.name
        with open(rejected_file, 'w', encoding='utf-8') as f:
            json.dump(rejected_pairs, f, indent=2, ensure_ascii=False)

        print(f"Filtered pairs saved to {output_file}")

    stop = time.perf_counter()
    print(f"Filtering completed in {stop - start:.2f} seconds.")


if __name__ == "__main__":
    main()
