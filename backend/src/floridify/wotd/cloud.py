"""Cloud deployment for WOTD system - RunPod and Modal Labs integration."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CloudConfig:
    """Simple cloud configuration."""
    provider: str  # "runpod" or "modal"
    api_key: str
    gpu_type: str = "RTX4090"  # RunPod GPU type
    instance_count: int = 1
    region: str = "US"


class RunPodDeployment:
    """Simple RunPod deployment for WOTD training and inference."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.runpod.ai/v2"
        
    async def create_training_pod(
        self,
        gpu_type: str = "RTX4090",
        docker_image: str = "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-devel"
    ) -> dict[str, Any]:
        """Create a pod for training."""
        
        import httpx
        
        payload = {
            "name": "wotd-training",
            "imageName": docker_image,
            "gpuType": gpu_type,
            "containerDiskInGb": 20,
            "volumeInGb": 50,
            "minVcpuCount": 4,
            "minMemoryInGb": 16,
            "dockerArgs": "",
            "ports": "8080/http",
            "env": [
                {"key": "WANDB_MODE", "value": "offline"},
                {"key": "TOKENIZERS_PARALLELISM", "value": "false"}
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/pods",
                json=payload,
                headers=headers
            )
            
        response_data: dict[str, Any] = response.json()
        return response_data
    
    async def upload_training_code(self, pod_id: str, local_path: str) -> bool:
        """Upload training code to pod (simplified)."""
        
        # In practice, this would use the RunPod API to upload files
        # For now, we'll assume code is baked into the Docker image
        print(f"Uploading code from {local_path} to pod {pod_id}")
        return True
    
    async def start_training(
        self,
        pod_id: str,
        training_script: str = "train_wotd.py"
    ) -> dict[str, Any]:
        """Start training on pod."""
        
        import httpx
        
        # Execute training command
        command = f"python {training_script}"
        
        payload = {
            "input": {
                "command": command,
                "workingDir": "/workspace"
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/pods/{pod_id}/run",
                json=payload,
                headers=headers
            )
        
        response_data: dict[str, Any] = response.json()
        return response_data
    
    async def monitor_training(self, pod_id: str) -> dict[str, Any]:
        """Monitor training progress."""
        
        import httpx
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/pods/{pod_id}",
                headers=headers
            )
        
        response_data: dict[str, Any] = response.json()
        return response_data
    
    async def download_model(self, pod_id: str, model_path: str) -> str:
        """Download trained model from pod."""
        
        # This would implement file download from the pod
        print(f"Downloading model from pod {pod_id} to {model_path}")
        return model_path
    
    async def terminate_pod(self, pod_id: str) -> bool:
        """Terminate training pod."""
        
        import httpx
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/pods/{pod_id}",
                headers=headers
            )
        
        return response.status_code == 200


def create_training_dockerfile() -> str:
    """Create Dockerfile for RunPod training."""
    
    dockerfile_content = """
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-devel

# Install dependencies
RUN pip install transformers datasets accelerate wandb

# Copy training code
COPY . /workspace
WORKDIR /workspace

# Install local package
RUN pip install -e .

# Default command
CMD ["python", "train_wotd.py"]
"""
    
    return dockerfile_content


def create_training_script() -> str:
    """Create training script for cloud deployment."""
    
    script_content = """
#!/usr/bin/env python3
\"\"\"
WOTD Training Script for Cloud Deployment
\"\"\"

import os
import sys
sys.path.append('/workspace')

from floridify.wotd import train_semantic_encoder, train_dsl_model
from floridify.wotd.semantic_encoder import learn_preference_vectors, encode_words

def main():
    print("Starting WOTD training on cloud...")
    
    # Sample word corpora (would be loaded from data files)
    word_corpora = {
        'shakespeare': ['doth', 'thou', 'wherefore', 'beauteous', 'fair', 'sweet'],
        'modern': ['amazing', 'brilliant', 'fantastic', 'wonderful', 'great'],
        'beautiful': ['luminous', 'ethereal', 'gossamer', 'efflorescent', 'radiant']
    }
    
    print("Learning preference vectors...")
    preference_vectors = learn_preference_vectors(word_corpora)
    
    print("Training semantic encoder...")
    encoder = train_semantic_encoder(preference_vectors)
    
    print("Encoding words...")
    semantic_ids = encode_words(encoder, preference_vectors)
    
    print("Training DSL model...")
    dsl_model = train_dsl_model(word_corpora, semantic_ids, num_epochs=5)
    
    print("Saving models...")
    # Save to mounted volume for persistence
    model_dir = "/workspace/models"
    os.makedirs(model_dir, exist_ok=True)
    
    # Save encoder
    from floridify.wotd.semantic_encoder import save_encoder
    save_encoder(encoder, f"{model_dir}/semantic_encoder.pt")
    
    # Save DSL model
    from floridify.wotd.language_model import save_dsl_model
    save_dsl_model(dsl_model, f"{model_dir}/dsl_model")
    
    # Save semantic IDs vocabulary
    import json
    with open(f"{model_dir}/semantic_ids.json", 'w') as f:
        json.dump(semantic_ids, f, indent=2)
    
    print("Training completed successfully!")

if __name__ == "__main__":
    main()
"""
    
    return script_content


async def deploy_training_to_runpod(
    config: CloudConfig,
    local_code_path: str
) -> str:
    """Deploy training job to RunPod."""
    
    print("Deploying WOTD training to RunPod...")
    
    # Initialize RunPod client
    client = RunPodDeployment(config.api_key)
    
    # Create training pod
    pod_response = await client.create_training_pod(config.gpu_type)
    pod_id: str | None = pod_response.get('id')
    
    if not pod_id:
        raise RuntimeError(f"Failed to create pod: {pod_response}")
    
    print(f"Created pod: {pod_id}")
    
    # Wait for pod to be ready
    await asyncio.sleep(30)  # Give pod time to start
    
    # Upload training code (in practice, this would be more sophisticated)
    await client.upload_training_code(pod_id, local_code_path)
    
    # Start training
    training_response = await client.start_training(pod_id, "train_wotd.py")
    print(f"Started training: {training_response}")
    
    return pod_id


async def monitor_runpod_training(config: CloudConfig, pod_id: str) -> dict[str, Any]:
    """Monitor RunPod training progress."""
    
    client = RunPodDeployment(config.api_key)
    
    while True:
        status = await client.monitor_training(pod_id)
        
        pod_status = status.get('status')
        print(f"Pod {pod_id} status: {pod_status}")
        
        if pod_status in ['COMPLETED', 'FAILED', 'STOPPED']:
            break
            
        await asyncio.sleep(60)  # Check every minute
    
    return status


def create_modal_deployment() -> str:
    """Create Modal Labs deployment script."""
    
    modal_script = """
import modal

# Define the Modal app
app = modal.App("wotd-training")

# Define the image with dependencies
image = modal.Image.debian_slim().pip_install([
    "torch",
    "transformers",
    "datasets",
    "accelerate"
])

@app.function(
    image=image,
    gpu="A100",
    memory=32768,  # 32GB RAM
    timeout=3600,  # 1 hour timeout
)
def train_wotd_modal():
    \"\"\"Train WOTD models on Modal.\"\"\"
    
    # Import training functions
    from floridify.wotd import train_semantic_encoder, train_dsl_model
    from floridify.wotd.semantic_encoder import learn_preference_vectors
    
    # Sample data
    word_corpora = {
        'shakespeare': ['doth', 'thou', 'wherefore', 'beauteous'],
        'modern': ['amazing', 'brilliant', 'fantastic', 'wonderful']
    }
    
    print("Training on Modal Labs...")
    
    # Train models
    preference_vectors = learn_preference_vectors(word_corpora)
    encoder = train_semantic_encoder(preference_vectors)
    
    # Return results (would save to volume in practice)
    return {"status": "completed", "models_trained": 2}

@app.local_entrypoint()
def main():
    \"\"\"Entry point for Modal deployment.\"\"\"
    result = train_wotd_modal.remote()
    print(f"Training result: {result}")
"""
    
    return modal_script


# Utility functions
def setup_cloud_environment(provider: str, api_key: str) -> CloudConfig:
    """Set up cloud configuration."""
    
    return CloudConfig(
        provider=provider,
        api_key=api_key,
        gpu_type="RTX4090" if provider == "runpod" else "A100"
    )


def prepare_deployment_files(output_dir: str) -> None:
    """Prepare all files needed for cloud deployment."""
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create Dockerfile
    with open(output_path / "Dockerfile", 'w') as f:
        f.write(create_training_dockerfile())
    
    # Create training script
    with open(output_path / "train_wotd.py", 'w') as f:
        f.write(create_training_script())
    
    # Create Modal script
    with open(output_path / "modal_deployment.py", 'w') as f:
        f.write(create_modal_deployment())
    
    print(f"Deployment files created in {output_dir}")


# Simple CLI for cloud deployment
async def main() -> None:
    """Simple CLI for cloud deployment."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy WOTD training to cloud")
    parser.add_argument("--provider", choices=["runpod", "modal"], required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--gpu-type", default="RTX4090")
    parser.add_argument("--local-path", default=".")
    parser.add_argument("--prepare-files", action="store_true")
    
    args = parser.parse_args()
    
    if args.prepare_files:
        prepare_deployment_files("./deployment")
        print("Deployment files prepared. Ready for cloud deployment.")
        return
    
    config = CloudConfig(
        provider=args.provider,
        api_key=args.api_key,
        gpu_type=args.gpu_type
    )
    
    if args.provider == "runpod":
        pod_id = await deploy_training_to_runpod(config, args.local_path)
        print(f"Training deployed to RunPod. Pod ID: {pod_id}")
        
        # Monitor training
        print("Monitoring training progress...")
        final_status = await monitor_runpod_training(config, pod_id)
        print(f"Training completed with status: {final_status}")
        
    elif args.provider == "modal":
        print("For Modal deployment, run: modal deploy modal_deployment.py")


if __name__ == "__main__":
    asyncio.run(main())