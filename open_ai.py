import os
import re
import time
from typing import Any, Dict, List, Literal, Optional, Tuple
from lm_eval.__main__ import parse_eval_args, setup_parser
import lm_eval.evaluator
from lm_eval.models.openai_completions import OpenaiCompletionsLM, oa_completion
import openai
from sympy import false
from tqdm import tqdm
from collections import defaultdict
from main import cli_evaluate
from lm_eval import utils
import copy

base_url = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
openai.api_type = os.environ.get("OPENAI_API_TYPE", "open_ai")
openai.api_version = os.environ.get("OPENAI_API_VERSION")
openai.api_key = os.environ.get("OPENAI_API_KEY")


def oa_chat_completion(
    client: openai.Client, chat: bool = False, **kwargs: Any
) -> Optional[Dict]:
    """Query OpenAI API for completion.

    Retry with back-off until they respond
    """
    import openai

    backoff_time = 3.0
    while True:
        try:
            if chat:
                return client.chat.completions.create(**kwargs)
            else:
                return client.completions.create(**kwargs)
        except openai.OpenAIError as e:
            if e.code == "content_filter":
                return None
            import traceback

            traceback.print_exc()
            time.sleep(backoff_time)
            backoff_time *= 1.5


class AzureOpenaiCompletionsLM(OpenaiCompletionsLM):
    def __init__(
        self,
        model: str,
        base_url: str,
        tokenizer: Optional[str] = None,
        tokenizer_backend: Literal["tiktoken", "huggingface"] = "tiktoken",
        truncate: bool = False,
        max_gen_toks: int = 256,
        batch_size: int = 1,
        seed: int = 1234,
        max_length: Optional[int] = None,
    ) -> None:
        super().__init__(
            model=model,
            base_url=base_url,
            tokenizer=tokenizer,
            tokenizer_backend=tokenizer_backend,
            truncate=truncate,
            max_gen_toks=max_gen_toks,
            batch_size=batch_size,
            seed=seed,
            max_length=max_length,
        )
        self.client = openai.AzureOpenAI(
            azure_endpoint=self.base_url,
            api_key=os.environ.get("OPENAI_API_KEY"),
            api_version=os.environ.get("OPENAI_API_VERSION"),
        )

    def _loglikelihood_tokens(
        self,
        requests: List[Tuple[Tuple[str, str], List[int], List[int]]],
        disable_tqdm: bool = False,
        override_bs: int = None,
    ) -> List[Tuple[float, bool]]:
        res = defaultdict(list)
        re_ords = {}

        # we group requests by their generation_kwargs,
        # so that we don't try to execute e.g. greedy sampling and temp=0.8 sampling
        # in the same batch.
        grouper = lm_eval.models.utils.Grouper(requests, lambda x: str(x[0][0]))

        pbar = tqdm(total=len(requests), disable=(disable_tqdm or (self.rank != 0)))
        for key, re_ord in grouper.get_grouped().items():
            inps = [{"role": "user", "content": key}]

            response = oa_chat_completion(
                client=self.client,
                chat=True,
                messages=inps,
                model=self.model,
                temperature=0.0,
                max_tokens=self.max_gen_toks,
            )

            # Azure content filter
            if response is not None and response.choices[0].message.content:
                resp_txt = response.choices[0].message.content
            else:
                resp_txt = ""
            choices = list(map(lambda x: x[0][1], re_ord))
            choice_found = [re.search(choice, resp_txt) for choice in choices]
            # Note: if the task employs likelihood, -1.0 is multiplied. But, others are dependent on the task.
            result = [
                -1.0 * (m.start() if m is not None else float("inf"))
                for m in choice_found
            ]

            for choice, ll, found, ord in zip(choices, result, choice_found, re_ord):
                answer = (ll, found is not None)
                res[key].append(answer)
                self.cache_hook.add_partial("loglikelihood", ord[0], answer)
                pbar.update(1)
        # reorder this group of results back to original unsorted form
        # res[key] = re_ord.get_original(res[key])

        pbar.close()

        return grouper.get_original(res)


if __name__ == "__main__":
    parser = setup_parser()
    args = parse_eval_args(parser)
    args.model = AzureOpenaiCompletionsLM.create_from_arg_string(
        args.model_args, {"base_url": base_url}
    )
    cli_evaluate(args=args)
