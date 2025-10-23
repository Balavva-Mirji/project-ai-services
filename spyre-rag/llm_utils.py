import json

import requests
import time
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from transformers import AutoTokenizer
from misc_utils import get_prompts



tokenizer=AutoTokenizer.from_pretrained('ibm-granite/granite-3.3-8b-instruct')
llm_classify, table_summary, query_vllm_pmt, query_vllm_stream_pmt, gen_qa_pairs_pmt = get_prompts()


def classify_text_with_llm(text_blocks, gen_model, gen_endpoint, batch_size=128):
    all_prompts = [llm_classify.format(text=item.strip()) for item in text_blocks]
    
    decisions = []
    for i in tqdm(range(0, len(all_prompts), batch_size), desc="Classifying Text with LLM"):
        batch_prompts = all_prompts[i:i + batch_size]

        payload = {
            "model": gen_model,
            "prompt": batch_prompts,
            "temperature": 0,
            "max_tokens": 3,
        }
        try:
            response = requests.post(gen_endpoint, json=payload)
            response.raise_for_status()
            result = response.json()
            choices = result.get("choices", [])
            for choice in choices:
                reply = choice.get("text", "").strip().lower()
                decisions.append("yes" in reply)
        except Exception as e:
            print(f"Error in vLLM: {e}")
            decisions.append(True)
    return decisions


def filter_with_llm(text_blocks, gen_model, gen_endpoint):
    text_contents = [block.get('text') for block in text_blocks]

    # Run classification
    decisions = classify_text_with_llm(text_contents, gen_model, gen_endpoint)
    print(f"[Debug] Prompts: {len(text_contents)}, Decisions: {len(decisions)}")
    filtered_blocks = [block for dcsn, block in zip(decisions, text_blocks) if dcsn]
    print(f"[Debug] Filtered Blocks: {len(filtered_blocks)}, True Decisions: {sum(decisions)}")
    return filtered_blocks


def summarize_single_table(prompt, gen_model, gen_endpoint):
    payload = {
        "model": gen_model,
        "prompt": prompt,
        "temperature": 0,
        "repetition_penalty": 1.1,
        "max_tokens": 512,
        "stream": False,
    }
    try:
        response = requests.post(gen_endpoint, json=payload)
        response.raise_for_status()
        result = response.json()
        reply = result.get("choices", [{}])[0].get("text", "").strip()
        return reply
    except Exception as e:
        print(f"Error summarizing table: {e}")
        return "No summary."


def summarize_table(table_html, table_caption, gen_model, gen_endpoint, max_workers=32):
    all_prompts = [table_summary.format(content=html) for html in table_html]

    summaries = [None] * len(all_prompts)

    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(all_prompts)))) as executor:
        futures = {
            executor.submit(summarize_single_table, prompt, gen_model, gen_endpoint): idx
            for idx, prompt in enumerate(all_prompts)
        }

        for future in tqdm(as_completed(futures), total=len(futures), desc="Summarizing Tables"):
            idx = futures[future]
            try:
                summaries[idx] = future.result()
            except Exception as e:
                print(f"Thread failed at index {idx}: {e}")
                summaries[idx] = "No summary."

    return summaries


def query_vllm(question, documents, endpoint, ckpt, language, stop_words, max_new_tokens, stream=False, max_input_length=6000, dynamic_chunk_truncation=True):
    template_token_count=250
    context = "\n\n".join([doc.get("page_content") for doc in documents])
    
    print(f'Original Context: {context}')
    if dynamic_chunk_truncation:
        question_token_count=len(tokenizer.encode(question))
        remaining_tokens=max_input_length-(template_token_count+question_token_count)
        context=tokenizer.decode(tokenizer.encode(context)[:remaining_tokens])
        print(f"Truncated Context: {context}")

    prompt = query_vllm_pmt.format(context=context, question=question)
    print("PROMPT:  ", prompt)
    headers = {
        "accept": "application/json",
        "Content-type": "application/json"
    }
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "model": ckpt,
        "max_tokens": max_new_tokens,
        "repetition_penalty": 1.1,
        "temperature": 0.0,
        "stop": stop_words,
        "stream": stream
    }
    
    try:
        start_time = time.time()
        # Use requests for synchronous HTTP requests
        response = requests.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        end_time = time.time()
        request_time = end_time - start_time
        return response_data, request_time
    except Exception as e:
        return {"error": str(e)}, 0.


def query_vllm_stream(question, documents, endpoint, ckpt, language, stop_words, max_new_tokens, stream=False,
                max_input_length=6000, dynamic_chunk_truncation=True):
    template_token_count = 250
    context = "\n\n".join([doc.get("page_content") for doc in documents])

    print(f'Original Context: {context}')
    if dynamic_chunk_truncation:
        question_token_count = len(tokenizer.encode(question))
        reamining_tokens = max_input_length - (template_token_count + question_token_count)
        context = tokenizer.decode(tokenizer.encode(context)[:reamining_tokens])
        print(f"Truncated Context: {context}")

    prompt = query_vllm_stream_pmt.format(context=context, question=question)
    print("PROMPT:  ", prompt)
    headers = {
        "accept": "application/json",
        "Content-type": "application/json"
    }
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "model": ckpt,
        "max_tokens": max_new_tokens,
        "repetition_penalty": 1.1,
        "temperature": 0.0,
        "stop": stop_words,
        "stream": stream
    }

    try:
        # Use requests for synchronous HTTP requests
        print("STREAMING RESPONSE")
        with requests.post(endpoint, json=payload, headers=headers, stream=True) as r:
            for line in r.iter_lines(decode_unicode=True):
                if line:
                    print("Earlier response: ", line)
                    line = line.replace("data: ", "")
                    try:
                        data = json.loads(line)
                        yield data.get("choices", [{}])[0]['delta']['content']
                    except json.JSONDecodeError:
                        print("error in decoding")
                        pass  # ignore malformed lines
    except Exception as e:
        return {"error": str(e)}, 0.


def generate_qa_pairs(records, gen_model, gen_endpoint, batch_size=32):
    all_prompts = []
    for r in records:
        prompt = gen_qa_pairs_pmt.format(text=r.get("page_content"))
        all_prompts.append(prompt)

    qa_pairs = []

    for i in tqdm(range(0, len(all_prompts), batch_size), desc="Generating QA Pairs"):
        batch_prompts = all_prompts[i:i+batch_size]

        payload = {
            "model": gen_model,
            "prompt": batch_prompts,
            "temperature": 0.0,
            "max_tokens": 512
        }

        try:
            response = requests.post(gen_endpoint, json=payload)
            response.raise_for_status()
            result = response.json()
            choices = result.get("choices", [])

            for j, choice in enumerate(choices):
                text = choice.get("text", "").strip()
                if "Q:" in batch_prompts[j]:
                    # Try to split into question and answer
                    parts = text.split("A:", 1)
                    question = parts[0].strip().lstrip("Q:").strip()
                    answer = parts[1].strip() if len(parts) > 1 else ""
                    qa_pairs.append({
                        "question": question,
                        "answer": answer,
                        "context": records[i + j].get("page_content", ""),
                        "chunk_id": records[i + j].get("chunk_id", "")
                    })

        except Exception as e:
            print(f"❌ Error generating QA batch: {e}")

    return qa_pairs
