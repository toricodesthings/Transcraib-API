import torch
import psutil

def bytes_to_gb(b):
    """Convert bytes to gigabytes with 2 decimal places."""
    return None if b is None else round(b / (1024 ** 3), 2)


def detect_hardware():
    """Detect available hardware and return system information."""
    hardware = {
        "device": "cpu/unknown",
        "accelerator": None,       
        "gpu_name": None,
        "gpu_count": 0,
        "total_vram_bytes": None, 
        "system_ram_bytes": psutil.virtual_memory().total,
    }
    
    if torch.cuda.is_available():
        try: 
            gpu_count = torch.cuda.device_count()
            highest_vram = max(range(gpu_count), key=lambda i: torch.cuda.get_device_properties(i).total_memory )
            total_vram = torch.cuda.get_device_properties(0).total_memory if gpu_count > 0 else None
            hardware.update({
                "device": f"cuda:{highest_vram}",
                "accelerator": "cuda",
                "gpu_name": torch.cuda.get_device_name(highest_vram),
                "gpu_count": gpu_count,
                "total_vram_bytes": total_vram,
            })
            return hardware
        except Exception:
            pass
        
        return hardware
    return hardware

# Select model based on hardware capabilities
def model_pick(hardware):
    """Select the appropriate Whisper model based on available hardware."""
    if hardware["accelerator"] == "cuda":
        gpu = True
        vram_size = bytes_to_gb(hardware["total_vram_bytes"])
        if vram_size > 6:
            return "turbo", gpu
        elif vram_size > 5:
            return "medium", gpu
        elif vram_size > 2:
            return "small", gpu
        else:
            return "base", gpu
    else:
        gpu = False
        return "base", gpu

def model_override(model_name, hardware, gpu=False):
    """Override model selection, useful for testing."""
    valid_models = {"tiny": 1, "base": 1, "small": 2, "medium": 5, "large": 10, "turbo": 6}
        
    if model_name in valid_models:
        
        if gpu:
            vram_size = bytes_to_gb(hardware["total_vram_bytes"])
            if valid_models[model_name] > vram_size:
                raise ValueError("Insufficient VRAM for the selected model")
            return model_name
                
        else:
            size = bytes_to_gb(hardware["system_ram_bytes"])
            if valid_models[model_name] > size * 1.5:
                raise ValueError("Insufficient system RAM for the selected model")
            return model_name
            
    else:
        raise ValueError(f"Invalid model name '{model_name}'. Valid options are: {', '.join(valid_models)}")