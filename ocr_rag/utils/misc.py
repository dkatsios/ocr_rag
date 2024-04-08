import yaml
from openai import OpenAI


def get_cfg(cfg_path: str):
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    return cfg


def translate(
    text: str, openai_api_key: str, model_name: str = "gpt-3.5-turbo"
) -> tuple[bool, None | str]:
    text = text[:500]
    client = OpenAI(api_key=openai_api_key)

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": """
                    You will be provided with a sentence, and your task is
                    to translate it into English. If it is already in English, 
                    return the text without changing it.""",
            },
            {"role": "user", "content": text},
        ],
        temperature=0.7,
        top_p=1,
    )
    tr_text = response.choices[0].message.content
    return tr_text
