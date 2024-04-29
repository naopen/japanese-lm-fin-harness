MODEL_ARGS="pretrained=line-corporation/japanese-large-lm-1.7b-instruction-sft,trust_remote_code=True,dtype=float16"
TASK="chabsa-1.0-0.4,cma_basics-1.0-0.4,cpa_audit-1.0-0.4,fp2-1.0-0.4,security_sales_1-1.0-0.4"
python main.py --model vllm --model_args $MODEL_ARGS --tasks $TASK --num_fewshot 0 --output_path "models/line-corporation/japanese-large-lm-1.7b-instruction-sft/result-1.0-0.4.json"
# a100-80gb: 1
# a30-24gb: 1
# v100-32gb: 1
# v100-16gb: 1
