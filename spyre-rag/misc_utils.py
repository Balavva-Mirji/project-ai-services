import os
import json

def get_prompts():
    prompts_path = os.getenv("PROMPT_PATH")

    if not prompts_path:
        raise EnvironmentError("Environment variable 'PROMPT_PATH' is not set.")

    try:
        with open(prompts_path, "r", encoding="utf-8") as file:
            data = json.load(file)

            llm_classify = data.get("llm_classify")
            table_summary = data.get("table_summary")
            query_vllm = data.get("query_vllm")
            query_vllm_stream = data.get("query_vllm_stream")
            gen_qa_pairs = data.get("gen_qa_pairs")

            if any(prompt in (None, "") for prompt in (
                    llm_classify,
                    table_summary,
                    query_vllm,
                    query_vllm_stream,
                    gen_qa_pairs,
            )):
                raise ValueError(f"One or more prompt variables are missing or empty in '{prompts_path}' file.")

            return llm_classify, table_summary, query_vllm, query_vllm_stream, gen_qa_pairs
    except FileNotFoundError:
        raise FileNotFoundError(f"JSON file not found at: {prompts_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing JSON at {prompts_path}: {e}")


def get_txt_img_tab_filenames(file_paths, out_path):
    original_filenames = [fp.split('/')[-1] for fp in file_paths]
    input_txt_files, input_img_files, input_tab_files = [], [], []
    for fn in original_filenames:
        f, ext = os.path.splitext(fn)
        input_txt_files.append(f'{out_path}/{f}_clean_text.json')
        input_img_files.append(f'{out_path}/{f}_images.json')
        input_tab_files.append(f'{out_path}/{f}_tables.json')
    return original_filenames, input_txt_files, input_img_files, input_tab_files


def get_model_endpoints(deployment_type):
    if deployment_type == 'spyre':
        emb_model_dict = {
            'emb_endpoint': os.getenv("EMB_ENDPOINT"),
            'emb_model':    os.getenv("EMB_MODEL"),
            'max_tokens':   os.getenv("EMB_MAX_TOKENS"),
        }

        llm_model_dict = {
            'llm_endpoint': os.getenv("LLM_ENDPOINT"),
            'llm_model':    os.getenv("LLM_MODEL"),
        }

        reranker_model_dict = {
            'reranker_endpoint': os.getenv("RERANKER_ENDPOINT"),
            'reranker_model':    os.getenv("RERANKER_MODEL"),
        }

        return emb_model_dict, llm_model_dict, reranker_model_dict
    else:
        raise ValueError(f'Endpoints not available for {deployment_type} deployment type.')
