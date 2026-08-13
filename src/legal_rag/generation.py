from typing import Protocol


SYSTEM_PROMPT = """Bạn là trợ lý pháp luật Việt Nam. Chỉ trả lời từ căn cứ được cung cấp. Nêu căn cứ pháp lý, trình bày quy định theo đúng thứ tự và kết luận trực tiếp. Không tự tạo số Điều, Khoản, mức tiền hoặc thủ tục. Nếu căn cứ không đủ, nói rõ chưa đủ căn cứ."""


class TextGenerator(Protocol):
    def generate(self, prompt: str, **kwargs) -> str: ...


def build_prompt(question: str, context: str) -> str:
    return f"{SYSTEM_PROMPT}\n\nCĂN CỨ:\n{context or '[Không có căn cứ phù hợp]'}\n\nCÂU HỎI:\n{question}\n\nTRẢ LỜI:"


class TransformersGenerator:
    def __init__(self, model_id: str, device: str | None = None, quantize_4bit: bool = False):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.device = _resolve_device(torch, device)
        kwargs = {"torch_dtype": _resolve_dtype(torch, self.device)}
        if quantize_4bit:
            if self.device != "cuda":
                raise ValueError("4-bit quantization requires a CUDA device")
            kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
            kwargs["device_map"] = "auto"
        elif self.device == "cuda":
            kwargs["device_map"] = "auto"
        self.model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs).eval()
        if self.device != "cuda" and not quantize_4bit:
            self.model = self.model.to(self.device)

    def generate(self, prompt: str, max_new_tokens: int = 1024, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        if getattr(self.tokenizer, "chat_template", None):
            text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            text = prompt
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, repetition_penalty=1.05)
        return self.tokenizer.decode(output[0, inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()


def _resolve_device(torch, requested: str | None) -> str:
    if requested:
        return requested
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(getattr(torch, "backends", None), "mps", None)
    if mps and mps.is_available():
        return "mps"
    return "cpu"


def _resolve_dtype(torch, device: str):
    if device == "cuda":
        return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    return torch.float32
