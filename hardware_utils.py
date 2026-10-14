import ctypes, glob, os, subprocess
import numpy as np
import psutil
from faster_whisper import WhisperModel

# Approximate memory (GB) needed per faster-whisper model (fp16 on GPU; int8 on CPU is smaller).
VALID_MODELS = {
    "tiny": 1, "base": 1, "small": 2, "medium": 3,
    "distil-large-v3.5": 3, "large-v3-turbo": 3, "turbo": 3, "large-v3": 5,
}


def bytes_to_gb(b):
    """Convert bytes to gigabytes with 2 decimal places."""
    return None if b is None else round(b / (1024 ** 3), 2)


def detect_hardware():
    """Detect NVIDIA GPUs via nvidia-smi (no torch needed) and pick the one with most VRAM."""
    hardware = {
        "device": "cpu",
        "device_index": 0,
        "accelerator": None,
        "gpu_name": None,
        "gpu_count": 0,
        "total_vram_bytes": None,
        "system_ram_bytes": psutil.virtual_memory().total,
    }
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout
        gpus = [line.split(", ") for line in out.strip().splitlines() if line.strip()]
    except Exception:
        return hardware

    if gpus:
        idx, name, mib = max(gpus, key=lambda g: int(g[2]))
        hardware.update({
            "device": f"cuda:{idx}",
            "device_index": int(idx),
            "accelerator": "cuda",
            "gpu_name": name,
            "gpu_count": len(gpus),
            "total_vram_bytes": int(mib) * 1024 ** 2,
        })
    return hardware


def model_pick(hardware):
    """Select the faster-whisper model based on available hardware. Returns (name, gpu)."""
    if hardware["accelerator"] == "cuda":
        vram = bytes_to_gb(hardware["total_vram_bytes"])
        if vram >= 4:
            return "large-v3-turbo", True
        if vram >= 2:
            return "small", True
        return "base", True
    # CPU: turbo with int8 is usable on machines with plenty of RAM, otherwise stay small.
    return ("large-v3-turbo" if bytes_to_gb(hardware["system_ram_bytes"]) >= 16 else "small"), False


def _preload_pip_cuda_libs():
    """CTranslate2 dlopens cuBLAS/cuDNN by soname; make the pip `nvidia-*-cu12` wheels findable."""
    try:
        import nvidia
    except ImportError:
        return
    for base in nvidia.__path__:
        for lib in sorted(glob.glob(os.path.join(base, "*", "lib", "lib*.so*"))):
            try:
                ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
            except OSError:
                pass


def load_model(name, hardware, gpu):
    """Load a model on the chosen GPU, falling back to CPU int8 if CUDA libs are unavailable."""
    if gpu:
        try:
            _preload_pip_cuda_libs()
            model = WhisperModel(name, device="cuda", device_index=hardware["device_index"],
                                 compute_type="float16")
            # CUDA libs load lazily, so run one tiny decode to catch a broken setup now.
            list(model.transcribe(np.zeros(16000, dtype=np.float32), language="en")[0])
            return model, True
        except Exception as e:
            print(f"GPU load failed ({e}); falling back to CPU")
    return WhisperModel(name, device="cpu", compute_type="int8"), False


def model_override(model_name, hardware, gpu=False):
    """Validate a requested model name against available memory."""
    if model_name not in VALID_MODELS:
        raise ValueError(f"Invalid model name '{model_name}'. Valid options are: {', '.join(VALID_MODELS)}")
    if gpu:
        if VALID_MODELS[model_name] > bytes_to_gb(hardware["total_vram_bytes"]):
            raise ValueError("Insufficient VRAM for the selected model")
    elif VALID_MODELS[model_name] > bytes_to_gb(hardware["system_ram_bytes"]):
        raise ValueError("Insufficient system RAM for the selected model")
    return model_name
