from __future__ import annotations

import os
import gc
import torch


class GPUMemoryManager:
    """Manages GPU memory allocation for FLASH-TV models on 16GB GPU"""
    
    # Memory allocation in GB for 16GB total GPU memory
    MEMORY_ALLOCATION = {
        'retinaface': 2.0,      # Face detection - critical, continuous
        'adaface': 6.0,         # Face verification - heavy model, frequent 
        'gaze_primary': 4.0,    # Primary gaze model - high priority
        'gaze_secondary': 3.0,  # Secondary gaze model - medium priority
        'system_buffer': 1.0    # CUDA context, overhead
    }
    
    TOTAL_GPU_MEMORY = 16.0  # GB
    
    @classmethod
    def configure_mxnet_memory(cls, memory_gb: float) -> None:
        """Configure MXNet memory settings for RetinaFace"""
        memory_mb = int(memory_gb * 1024)
        os.environ['MXNET_GPU_MEM_POOL_RESERVE'] = str(memory_mb)
        os.environ['MXNET_GPU_MEM_POOL_TYPE'] = 'Round'
        os.environ['MXNET_GPU_WORKER_NTHREADS'] = '1'
        print(f"MXNet configured with {memory_gb:.1f}GB reserved memory")
    
    @classmethod
    def set_pytorch_memory_fraction(cls, fraction: float) -> None:
        """Set PyTorch memory fraction before any CUDA operations"""
        if torch.cuda.is_available():
            torch.cuda.set_per_process_memory_fraction(fraction)
            print(f"PyTorch memory fraction set to {fraction:.3f} ({fraction * cls.TOTAL_GPU_MEMORY:.1f}GB)")
    
    @classmethod
    def initialize_gpu_memory(cls) -> None:
        """Initialize GPU memory configuration before loading any models"""
        print("="*60)
        print("FLASH-TV GPU Memory Manager - Initializing 16GB Allocation")
        print("="*60)
        
        # Configure MXNet for RetinaFace first (MXNet is aggressive with memory)
        cls.configure_mxnet_memory(cls.MEMORY_ALLOCATION['retinaface'])
        
        # Calculate PyTorch memory fraction (everything except RetinaFace)
        pytorch_memory = (
            cls.MEMORY_ALLOCATION['adaface'] + 
            cls.MEMORY_ALLOCATION['gaze_primary'] + 
            cls.MEMORY_ALLOCATION['gaze_secondary'] +
            cls.MEMORY_ALLOCATION['system_buffer']
        )
        pytorch_fraction = pytorch_memory / cls.TOTAL_GPU_MEMORY
        cls.set_pytorch_memory_fraction(pytorch_fraction)
        
        # Print allocation summary
        print("\nMemory Allocation Plan:")
        for component, memory in cls.MEMORY_ALLOCATION.items():
            percentage = (memory / cls.TOTAL_GPU_MEMORY) * 100
            print(f"  {component:15s}: {memory:4.1f}GB ({percentage:5.1f}%)")
        print(f"  {'TOTAL':15s}: {sum(cls.MEMORY_ALLOCATION.values()):4.1f}GB")
        print("="*60)
    
    @classmethod
    def clear_gpu_cache(cls) -> None:
        """Clear GPU cache and run garbage collection"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()
    
    @classmethod
    def get_gpu_memory_status(cls) -> dict[str, float]:
        """Get current GPU memory usage in GB"""
        if not torch.cuda.is_available():
            return {}
        
        allocated = torch.cuda.memory_allocated() / (1024**3)
        reserved = torch.cuda.memory_reserved() / (1024**3)
        total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        free = total - reserved
        
        return {
            'allocated_gb': allocated,
            'reserved_gb': reserved, 
            'free_gb': free,
            'total_gb': total,
            'utilization_pct': (reserved / total) * 100
        }
    
    @classmethod
    def print_memory_status(cls, context: str = "") -> None:
        """Print current GPU memory status"""
        status = cls.get_gpu_memory_status()
        if not status:
            print("CUDA not available")
            return
            
        print(f"\nGPU Memory Status{' - ' + context if context else ''}:")
        print(f"  Allocated: {status['allocated_gb']:5.2f}GB")
        print(f"  Reserved:  {status['reserved_gb']:5.2f}GB") 
        print(f"  Free:      {status['free_gb']:5.2f}GB")
        print(f"  Total:     {status['total_gb']:5.2f}GB")
        print(f"  Usage:     {status['utilization_pct']:5.1f}%")
    
    @classmethod
    def monitor_model_loading(cls, model_name: str, before_fn, after_fn) -> any:
        """Monitor memory usage during model loading"""
        print(f"\nLoading {model_name}...")
        cls.print_memory_status(f"Before {model_name}")
        
        result = before_fn()
        cls.clear_gpu_cache()
        
        cls.print_memory_status(f"After {model_name}")
        
        if after_fn:
            after_fn()
            
        return result


def initialize_flash_tv_memory() -> None:
    """Initialize GPU memory management for FLASH-TV system"""
    GPUMemoryManager.initialize_gpu_memory()