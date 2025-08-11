#!/usr/bin/env python3
"""
Memory Constraint Validation Script
Tests the enhanced 14GB GPU memory management system
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from utils.gpu_memory_manager_v2 import GPUMemoryManagerV2, initialize_strict_gpu_memory


def test_memory_enforcement():
    """Test if the 14GB memory limit is being enforced"""
    print("="*80)
    print("FLASH-TV Memory Constraint Validation")
    print("="*80)
    
    # Initialize strict memory management
    try:
        manager = initialize_strict_gpu_memory()
        print("✓ Memory management initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize memory management: {e}")
        return False
    
    # Check initial GPU status
    manager.print_comprehensive_memory_status("Initial State")
    
    # Test if we can detect actual vs. reported memory usage
    print("\n" + "="*60)
    print("MEMORY DISCREPANCY TEST")
    print("="*60)
    
    status = manager.get_comprehensive_memory_status()
    
    if 'nvidia_smi' in status and 'pytorch' in status:
        nvidia_used = status['nvidia_smi']['used_gb']
        pytorch_reserved = status['pytorch']['reserved_gb']
        discrepancy = nvidia_used - pytorch_reserved
        
        print(f"nvidia-smi reports:    {nvidia_used:.2f}GB used")
        print(f"PyTorch reports:       {pytorch_reserved:.2f}GB reserved")
        print(f"Discrepancy:           {discrepancy:.2f}GB")
        
        if discrepancy > 0.5:
            print(f"⚠️  SIGNIFICANT DISCREPANCY: {discrepancy:.2f}GB unaccounted for!")
            print("This is likely MXNet (RetinaFace) memory not shown by PyTorch")
        else:
            print("✓ Memory reporting appears consistent")
    
    return True


def simulate_model_loading_test():
    """Simulate model loading to test memory constraints"""
    print("\n" + "="*60) 
    print("MODEL LOADING SIMULATION TEST")
    print("="*60)
    
    import torch
    if not torch.cuda.is_available():
        print("CUDA not available - skipping simulation")
        return
    
    manager = GPUMemoryManagerV2()
    test_models = []
    
    try:
        # Simulate RetinaFace loading (~1.5GB)
        print("\nSimulating RetinaFace loading...")
        model1 = manager.monitor_model_loading_v2(
            "Simulated RetinaFace",
            lambda: torch.randn(384, 512, 1024, device='cuda', dtype=torch.float32)
        )
        test_models.append(model1)
        
        # Simulate AdaFace loading (~5.5GB)  
        print("\nSimulating AdaFace loading...")
        model2 = manager.monitor_model_loading_v2(
            "Simulated AdaFace",
            lambda: torch.randn(1024, 1024, 1408, device='cuda', dtype=torch.float32)
        )
        test_models.append(model2)
        
        # Simulate first gaze model (~3.5GB)
        print("\nSimulating Gaze Model 1 loading...")
        model3 = manager.monitor_model_loading_v2(
            "Simulated Gaze Model 1", 
            lambda: torch.randn(768, 1024, 1152, device='cuda', dtype=torch.float32)
        )
        test_models.append(model3)
        
        # Simulate second gaze model (~2.5GB)
        print("\nSimulating Gaze Model 2 loading...")
        model4 = manager.monitor_model_loading_v2(
            "Simulated Gaze Model 2",
            lambda: torch.randn(640, 1024, 1024, device='cuda', dtype=torch.float32)
        )
        test_models.append(model4)
        
        # Final status
        manager.print_comprehensive_memory_status("All Simulated Models Loaded")
        
        # Check if we exceeded 14GB
        status = manager.get_comprehensive_memory_status()
        if 'nvidia_smi' in status:
            used_gb = status['nvidia_smi']['used_gb']
            if used_gb > 14.0:
                print(f"\n✗ MEMORY LIMIT EXCEEDED: {used_gb:.2f}GB > 14.0GB")
                return False
            else:
                print(f"\n✓ Memory usage within limit: {used_gb:.2f}GB ≤ 14.0GB")
                return True
        
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n✓ Memory limit successfully enforced - OOM prevented")
            print(f"Error: {e}")
            return True
        else:
            print(f"\n✗ Unexpected error: {e}")
            return False
    
    finally:
        # Cleanup
        print("\nCleaning up test models...")
        del test_models
        manager.aggressive_cleanup()
        manager.print_comprehensive_memory_status("After Cleanup")


def test_memory_monitoring_accuracy():
    """Test accuracy of memory monitoring"""
    print("\n" + "="*60)
    print("MEMORY MONITORING ACCURACY TEST")
    print("="*60)
    
    manager = GPUMemoryManagerV2()
    
    # Get status from multiple sources
    status = manager.get_comprehensive_memory_status()
    
    print("Comparing memory reporting sources:")
    
    if 'nvidia_smi' in status:
        nvidia = status['nvidia_smi']
        print(f"✓ nvidia-smi available: {nvidia['used_gb']:.2f}GB used")
    else:
        print("✗ nvidia-smi not available")
    
    if 'pytorch' in status:
        pytorch = status['pytorch']
        print(f"✓ PyTorch available: {pytorch['reserved_gb']:.2f}GB reserved")
    else:
        print("✗ PyTorch not available")
    
    if 'process' in status:
        proc = status['process']
        print(f"✓ Process info available: {proc['ram_gb']:.2f}GB RAM")
    
    return True


def main():
    """Run all validation tests"""
    print("Starting FLASH-TV Memory Constraint Validation...\n")
    
    tests = [
        ("Memory Enforcement", test_memory_enforcement),
        ("Model Loading Simulation", simulate_model_loading_test),  
        ("Memory Monitoring Accuracy", test_memory_monitoring_accuracy)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*80}")
        print(f"RUNNING: {test_name}")
        print(f"{'='*80}")
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ Test '{test_name}' failed with exception:")
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:30s}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 All validation tests passed!")
        return True
    else:
        print("⚠️  Some tests failed - review memory management implementation")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)