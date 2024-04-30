MODEL_ARGS="pretrained=stabilityai/japanese-stablelm-instruct-gamma-7b,trust_remote_code=True,tokenizer=novelai/nerdstash-tokenizer-v1,dtype=float32"
TASK="chabsa-1.0-0.5,cma_basics-1.0-0.5,cpa_audit-1.0-0.5,fp2-1.0-0.5,security_sales_1-1.0-0.5"
python main.py --model hf --model_args $MODEL_ARGS --tasks $TASK --num_fewshot 0 --output_path "models/stabilityai/japanese-stablelm-instruct-gamma-7b/result-1.0-0.5.json"
# a100-80gb: 1
# a30-24gb: 0
# v100-32gb: 0
# v100-16gb: 0
