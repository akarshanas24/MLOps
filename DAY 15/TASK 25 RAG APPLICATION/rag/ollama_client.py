import subprocess
from typing import Optional
import shlex
import time


def call_ollama(prompt: str, model: str = "llama3", timeout: int = 60) -> str:
    """Call local Ollama CLI to generate a response using positional prompt argument.

    Returns stdout on success or a descriptive error string on failure.
    Ensures Ollama service is running and properly configured.
    """
    try:
        # First check if ollama CLI is available
        try:
            subprocess.run(["ollama", "--version"], capture_output=True, timeout=5, check=False)
        except FileNotFoundError:
            return "ERROR: Ollama CLI not found. Please install Ollama from https://ollama.ai and add it to PATH."

        # Check if the model is available locally
        try:
            list_proc = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
            if list_proc.returncode != 0:
                return f"ERROR: Could not list Ollama models. Ensure Ollama service is running on localhost:11434"
            if model not in list_proc.stdout:
                return f"ERROR: Model '{model}' not found. Run 'ollama pull {model}' first."
        except subprocess.TimeoutExpired:
            return "ERROR: Ollama service timeout. Check if Ollama is running."
        except Exception as e:
            return f"ERROR: Could not verify Ollama model: {e}"

        # Use positional prompt argument (MODEL PROMPT)
        cmd = ["ollama", "run", model, prompt]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

        # Success path
        if proc.returncode == 0:
            result = proc.stdout.strip()
            if not result:
                return "ERROR: Ollama returned empty response. Try again."
            return result

        # Provide stderr for debugging
        err = (proc.stderr or proc.stdout or "").strip()
        if not err:
            err = "Unknown error - Ollama service may not be responding"

        # If the failure appears CUDA-related, try a CPU-only retry automatically
        low_err = err.lower()
        if ("cuda" in low_err or "shared object initialization" in low_err or "cuda error" in low_err) :
            try:
                cpu_cmd = ["ollama", "run", "--cpu", model, prompt]
                cpu_proc = subprocess.run(cpu_cmd, capture_output=True, text=True, timeout=timeout)
                if cpu_proc.returncode == 0:
                    cpu_result = cpu_proc.stdout.strip()
                    if cpu_result:
                        return cpu_result
                    return "ERROR: Ollama (CPU) returned empty response."
                cpu_err = (cpu_proc.stderr or cpu_proc.stdout or "").strip()
                return f"ERROR: Ollama GPU failed: {err}\nERROR: Ollama CPU retry failed: {cpu_err}"
            except Exception as e:
                return f"ERROR: Ollama GPU failed: {err}\nERROR: CPU retry exception: {e}"

        return f"ERROR: Ollama call failed.\n{err}"
        
    except subprocess.TimeoutExpired:
        return f"ERROR: Ollama call timed out after {timeout}s. Model response too slow. Try increasing timeout or simplifying query."
    except FileNotFoundError:
        return "ERROR: Ollama CLI not found. Install from https://ollama.ai and ensure it's in PATH."
    except Exception as e:
        return f"ERROR: Unexpected error calling Ollama: {str(e)}"
