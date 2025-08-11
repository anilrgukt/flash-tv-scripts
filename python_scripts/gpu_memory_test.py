#!/usr/bin/env python3
"""
GPU Memory Test Script for FLASH-TV System
Tests the GPU memory allocation strategy before running full system.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from utils.gpu_memory_manager import GPUMemoryManager


def test_gpu_memory_allocation():
    """Test GPU memory allocation without loading actual models"""
    print("="*70)
    print("FLASH-TV GPU Memory Allocation Test")
    print("="*70)
    
    # Initialize memory management
    GPUMemoryManager.initialize_gpu_memory()
    
    # Check initial GPU status
    GPUMemoryManager.print_memory_status("Initial State")
    
    # Test PyTorch memory allocation
    import torch
    if torch.cuda.is_available():
        print("\nTesting PyTorch memory allocation...")
        
        # Allocate test tensors to verify memory limits
        test_tensors = []
        try:
            # Test 1GB allocation
            print("  Allocating 1GB test tensor...")
            tensor_1gb = torch.randn(1024, 1024, 256, device='cuda')  # ~1GB
            test_tensors.append(tensor_1gb)
            GPUMemoryManager.print_memory_status("After 1GB allocation")
            
            # Test 2GB allocation
            print("  Allocating additional 2GB test tensor...")
            tensor_2gb = torch.randn(1024, 1024, 512, device='cuda')  # ~2GB  
            test_tensors.append(tensor_2gb)
            GPUMemoryManager.print_memory_status("After 3GB total allocation")
            
            # Test larger allocation
            print("  Allocating additional 4GB test tensor...")
            tensor_4gb = torch.randn(1024, 1024, 1024, device='cuda')  # ~4GB
            test_tensors.append(tensor_4gb)
            GPUMemoryManager.print_memory_status("After 7GB total allocation")
            
            print("\n✓ Memory allocation test successful")
            
        except RuntimeError as e:
            print(f"\n✗ Memory allocation failed: {e}")
            GPUMemoryManager.print_memory_status("After allocation failure")
        
        finally:
            # Clean up test tensors
            del test_tensors
            GPUMemoryManager.clear_gpu_cache()
            GPUMemoryManager.print_memory_status("After cleanup")
    
    else:
        print("CUDA not available - cannot test GPU memory allocation")
    
    print("\n" + "="*70)
    print("GPU Memory Test Complete")
    print("="*70)


def simulate_model_loading():
    """Simulate the memory usage pattern of actual models"""
    print("\nSimulating FLASH-TV model loading pattern...")
    
    import torch
    if not torch.cuda.is_available():
        print("CUDA not available for simulation")
        return
    
    models = {}
    
    try:
        # Simulate RetinaFace (~1GB)
        print("  Simulating RetinaFace loading (1GB)...")
        models['retinaface'] = torch.randn(512, 512, 1024, device='cuda')
        time.sleep(1)
        GPUMemoryManager.print_memory_status("RetinaFace loaded")
        
        # Simulate AdaFace (~4GB) 
        print("  Simulating AdaFace loading (4GB)...")
        models['adaface'] = torch.randn(1024, 1024, 1024, device='cuda')
        time.sleep(1)
        GPUMemoryManager.print_memory_status("AdaFace loaded")
        
        # Simulate Gaze Model 1 (~2GB)
        print("  Simulating Gaze Model 1 loading (2GB)...")
        models['gaze1'] = torch.randn(512, 1024, 1024, device='cuda')
        time.sleep(1)
        GPUMemoryManager.print_memory_status("Gaze Model 1 loaded")
        
        # Simulate Gaze Model 2 (~2GB)
        print("  Simulating Gaze Model 2 loading (2GB)...")  
        models['gaze2'] = torch.randn(512, 1024, 1024, device='cuda')
        time.sleep(1)
        GPUMemoryManager.print_memory_status("All models loaded")
        
        print("\n✓ Model loading simulation successful")
        
    except RuntimeError as e:
        print(f"\n✗ Model loading simulation failed: {e}")
        
    finally:
        # Cleanup
        del models
        GPUMemoryManager.clear_gpu_cache()
        GPUMemoryManager.print_memory_status("After model cleanup")


if __name__ == "__main__":
    test_gpu_memory_allocation()
    simulate_model_loading()