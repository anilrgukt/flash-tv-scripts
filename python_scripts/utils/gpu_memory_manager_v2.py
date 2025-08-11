from __future__ import annotations

import os
import gc
import subprocess
import time
import torch
import psutil
from typing import Dict, Optional, Tuple


class GPUMemoryManagerV2:
    """Enhanced GPU memory manager with strict 14GB enforcement and accurate monitoring"""
    
    # Updated allocation for 14GB total limit
    MEMORY_ALLOCATION = {
        'retinaface': 1.5,      # Face detection - reduced 
        'adaface': 5.5,         # Face verification - reduced
        'gaze_primary': 3.5,    # Primary gaze model - reduced
        'gaze_secondary': 2.5,  # Secondary gaze model - reduced
        'system_buffer': 1.0    # CUDA context, overhead
    }
    
    TOTAL_GPU_MEMORY_LIMIT = 14.0  # GB - strict limit
    
    @classmethod
    def get_nvidia_smi_memory(cls) -> Dict[str, float]:
        """Get accurate GPU memory usage from nvidia-smi"""
        try:
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=memory.used,memory.free,memory.total',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                line = result.stdout.strip().split('\n')[0]  # First GPU
                used_mb, free_mb, total_mb = map(int, line.split(', '))
                
                return {
                    'used_gb': used_mb / 1024.0,
                    'free_gb': free_mb / 1024.0,
                    'total_gb': total_mb / 1024.0,
                    'utilization_pct': (used_mb / total_mb) * 100
                }
        except Exception as e:
            print(f"nvidia-smi failed: {e}")
            
        return {}
    
    @classmethod
    def enforce_memory_limit(cls) -> None:
        """Enforce strict 14GB GPU memory limit using multiple methods"""
        print("="*70)
        print("FLASH-TV GPU Memory Manager V2 - Enforcing 14GB Limit")
        print("="*70)
        
        # Method 1: Environment variables (affects both PyTorch and MXNet)
        total_mb = int(cls.TOTAL_GPU_MEMORY_LIMIT * 1024)
        os.environ['CUDA_DEVICE_MAX_MEMORY'] = str(total_mb)
        os.environ['CUDA_MPS_PIPE_DIRECTORY'] = '/tmp/nvidia-mps'
        
        # Method 2: MXNet memory pool (stricter limits)
        mxnet_mb = int(cls.MEMORY_ALLOCATION['retinaface'] * 1024)
        os.environ['MXNET_GPU_MEM_POOL_RESERVE'] = str(mxnet_mb)
        os.environ['MXNET_GPU_MEM_POOL_TYPE'] = 'Round'
        os.environ['MXNET_GPU_WORKER_NTHREADS'] = '1'
        os.environ['MXNET_GPU_MEM_POOL_ROUND_LINEAR_CUTOFF'] = '26'  # Limit growth
        
        # Method 3: PyTorch memory fraction (more conservative)
        pytorch_memory = (
            cls.MEMORY_ALLOCATION['adaface'] + 
            cls.MEMORY_ALLOCATION['gaze_primary'] + 
            cls.MEMORY_ALLOCATION['gaze_secondary'] +
            cls.MEMORY_ALLOCATION['system_buffer']
        )
        # Use actual GPU memory, not theoretical 16GB
        gpu_info = cls.get_nvidia_smi_memory()
        if gpu_info:
            actual_total = gpu_info['total_gb']
            pytorch_fraction = min(pytorch_memory / actual_total, 0.8)  # Cap at 80%
        else:
            pytorch_fraction = pytorch_memory / 16.0  # Fallback
            
        if torch.cuda.is_available():
            torch.cuda.set_per_process_memory_fraction(pytorch_fraction)
            # Additional PyTorch memory management
            torch.cuda.empty_cache()
            print(f"PyTorch memory fraction set to {pytorch_fraction:.3f}")
        
        # Method 4: CUDA context limits
        os.environ['CUDA_LAUNCH_BLOCKING'] = '1'  # Force synchronous execution
        
        # Print allocation summary
        print("\nStrict Memory Allocation Plan (14GB Total):")
        total_allocated = 0
        for component, memory in cls.MEMORY_ALLOCATION.items():
            percentage = (memory / cls.TOTAL_GPU_MEMORY_LIMIT) * 100
            print(f"  {component:15s}: {memory:4.1f}GB ({percentage:5.1f}%)")
            total_allocated += memory
        print(f"  {'TOTAL':15s}: {total_allocated:4.1f}GB")
        print("="*70)
    
    @classmethod
    def get_comprehensive_memory_status(cls) -> Dict[str, any]:
        """Get comprehensive GPU memory status from multiple sources"""
        status = {}
        
        # PyTorch memory info
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / (1024**3)
            reserved = torch.cuda.memory_reserved() / (1024**3)
            max_allocated = torch.cuda.max_memory_allocated() / (1024**3)
            max_reserved = torch.cuda.max_memory_reserved() / (1024**3)
            
            status['pytorch'] = {
                'allocated_gb': allocated,
                'reserved_gb': reserved,
                'max_allocated_gb': max_allocated,
                'max_reserved_gb': max_reserved
            }
        
        # nvidia-smi memory info (most accurate)
        nvidia_info = cls.get_nvidia_smi_memory()
        if nvidia_info:
            status['nvidia_smi'] = nvidia_info
        
        # Process memory info
        process = psutil.Process()
        status['process'] = {
            'ram_gb': process.memory_info().rss / (1024**3),
            'cpu_percent': process.cpu_percent()
        }
        
        return status
    
    @classmethod
    def print_comprehensive_memory_status(cls, context: str = "") -> None:
        """Print detailed memory status from all sources"""
        status = cls.get_comprehensive_memory_status()
        
        print(f"\n{'='*50}")
        print(f"GPU Memory Status{' - ' + context if context else ''}")
        print(f"{'='*50}")
        
        # nvidia-smi info (most reliable)
        if 'nvidia_smi' in status:
            nvidia = status['nvidia_smi']
            print(f"NVIDIA-SMI (Actual GPU Usage):")
            print(f"  Used:      {nvidia['used_gb']:6.2f}GB")
            print(f"  Free:      {nvidia['free_gb']:6.2f}GB") 
            print(f"  Total:     {nvidia['total_gb']:6.2f}GB")
            print(f"  Usage:     {nvidia['utilization_pct']:6.1f}%")
            
            # Check if we're exceeding our 14GB limit
            if nvidia['used_gb'] > cls.TOTAL_GPU_MEMORY_LIMIT:
                print(f"  ⚠️  EXCEEDING 14GB LIMIT by {nvidia['used_gb'] - cls.TOTAL_GPU_MEMORY_LIMIT:.2f}GB!")
        
        # PyTorch info (partial view)
        if 'pytorch' in status:
            pytorch = status['pytorch']
            print(f"\nPyTorch (Partial View - PyTorch only):")
            print(f"  Allocated: {pytorch['allocated_gb']:6.2f}GB")
            print(f"  Reserved:  {pytorch['reserved_gb']:6.2f}GB")
            print(f"  Max Used:  {pytorch['max_allocated_gb']:6.2f}GB")
        
        # Process info
        if 'process' in status:
            proc = status['process']
            print(f"\nProcess Memory:")
            print(f"  RAM:       {proc['ram_gb']:6.2f}GB")
            print(f"  CPU:       {proc['cpu_percent']:6.1f}%")
        
        print(f"{'='*50}")
    
    @classmethod
    def estimate_model_sizes(cls) -> Dict[str, float]:
        """Estimate memory requirements for each model type"""
        estimates = {
            'retinaface_retina': 0.8,      # RetinaFace backbone
            'retinaface_context': 0.5,     # MXNet context overhead
            'adaface_ir101': 4.5,          # IR-101 backbone + embeddings
            'adaface_processing': 1.0,     # Face processing buffers
            'gaze_resnet50_1': 2.8,        # Primary gaze ResNet
            'gaze_resnet50_2': 2.8,        # Secondary gaze ResNet  
            'gaze_lstm': 0.4,              # LSTM components
            'pytorch_overhead': 0.8,       # PyTorch CUDA context
            'mxnet_overhead': 0.6          # MXNet CUDA context
        }
        
        return estimates
    
    @classmethod
    def check_model_fit(cls) -> bool:
        """Check if all models can fit within 14GB limit"""
        estimates = cls.estimate_model_sizes()
        total_estimated = sum(estimates.values())
        
        print(f"\nModel Memory Estimation:")
        for model, size in estimates.items():
            print(f"  {model:20s}: {size:4.1f}GB")
        print(f"  {'TOTAL ESTIMATED':20s}: {total_estimated:4.1f}GB")
        print(f"  {'LIMIT':20s}: {cls.TOTAL_GPU_MEMORY_LIMIT:4.1f}GB")
        
        fits = total_estimated <= cls.TOTAL_GPU_MEMORY_LIMIT
        margin = cls.TOTAL_GPU_MEMORY_LIMIT - total_estimated
        
        if fits:
            print(f"  ✓ Models fit with {margin:.1f}GB margin")
        else:
            print(f"  ✗ Models exceed limit by {-margin:.1f}GB")
            
        return fits
    
    @classmethod
    def monitor_model_loading_v2(cls, model_name: str, load_fn, max_attempts: int = 3):
        """Enhanced model loading with memory monitoring and retry logic"""
        print(f"\n{'='*60}")
        print(f"Loading: {model_name}")
        print(f"{'='*60}")
        
        # Pre-loading cleanup
        cls.clear_gpu_cache()
        cls.print_comprehensive_memory_status("Before Loading")
        
        for attempt in range(max_attempts):
            try:
                print(f"\nAttempt {attempt + 1}/{max_attempts}")
                
                # Check available memory
                status = cls.get_comprehensive_memory_status()
                if 'nvidia_smi' in status:
                    free_gb = status['nvidia_smi']['free_gb']
                    if free_gb < 2.0:  # Need at least 2GB free
                        print(f"⚠️  Low memory: {free_gb:.1f}GB free")
                        cls.aggressive_cleanup()
                
                # Load model
                start_time = time.time()
                result = load_fn()
                load_time = time.time() - start_time
                
                # Post-loading status
                cls.print_comprehensive_memory_status("After Loading")
                print(f"✓ {model_name} loaded successfully in {load_time:.2f}s")
                
                return result
                
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    print(f"✗ Attempt {attempt + 1} failed: GPU OOM")
                    print(f"Error: {e}")
                    
                    if attempt < max_attempts - 1:
                        print("Performing aggressive cleanup...")
                        cls.aggressive_cleanup()
                        time.sleep(2)  # Wait for cleanup
                    else:
                        print("All attempts failed - model too large!")
                        raise
                else:
                    print(f"✗ Non-memory error: {e}")
                    raise
        
        raise RuntimeError(f"Failed to load {model_name} after {max_attempts} attempts")
    
    @classmethod
    def clear_gpu_cache(cls) -> None:
        """Standard GPU cache clearing"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()
    
    @classmethod
    def aggressive_cleanup(cls) -> None:
        """Aggressive memory cleanup"""
        # Multiple rounds of cleanup
        for _ in range(3):
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            gc.collect()
            time.sleep(0.5)
        
        # Reset PyTorch memory stats
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.reset_accumulated_memory_stats()


def initialize_strict_gpu_memory() -> None:
    """Initialize strict 14GB GPU memory management"""
    manager = GPUMemoryManagerV2()
    manager.enforce_memory_limit()
    
    # Check if models can theoretically fit
    if not manager.check_model_fit():
        print("\n⚠️  WARNING: Estimated model sizes exceed 14GB limit!")
        print("Consider reducing model complexity or increasing memory limit.")
    
    return manager