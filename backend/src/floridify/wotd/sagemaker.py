"""AWS SageMaker deployment for WOTD ML pipeline - clean and modular."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from ..utils.logging import get_logger
from .core import TrainingConfig

logger = get_logger(__name__)


class SageMakerDeployer:
    """Clean SageMaker deployment for WOTD ML system."""

    # Path constants
    DEPLOYMENT_DIR_NAME = "deployment"
    DEPLOYMENT_CONFIG_FILE = "deployment_config.json"

    # Deployment file constants
    DOCKERFILE_TRAINING = "Dockerfile.training"
    DOCKERFILE_INFERENCE = "Dockerfile.inference"
    TRAIN_SCRIPT = "train.py"
    INFERENCE_SCRIPT = "inference.py"
    NGINX_CONFIG = "nginx.conf"

    def __init__(
        self, role_arn: str, region: str = "us-east-1", ecr_repo_name: str = "wotd-ml"
    ) -> None:
        self.role_arn = role_arn
        self.region = region
        self.ecr_repo_name = ecr_repo_name

        # AWS clients
        self.sagemaker = boto3.client("sagemaker", region_name=region)
        self.ecr = boto3.client("ecr", region_name=region)
        self.s3 = boto3.client("s3", region_name=region)

        # Configuration
        self.account_id = boto3.client("sts").get_caller_identity()["Account"]
        self.training_image = (
            f"{self.account_id}.dkr.ecr.{region}.amazonaws.com/{ecr_repo_name}:training"
        )
        self.inference_image = (
            f"{self.account_id}.dkr.ecr.{region}.amazonaws.com/{ecr_repo_name}:inference"
        )

    def get_deployment_files_dir(self) -> Path:
        """Get deployment files directory."""
        return Path(__file__).parent / self.DEPLOYMENT_DIR_NAME

    async def deploy_training_job(
        self,
        job_name: str,
        s3_bucket: str,
        config: TrainingConfig | None = None,
        instance_type: str = "ml.g5.xlarge",
    ) -> str:
        """Deploy training job to SageMaker."""

        if not config:
            config = TrainingConfig()

        logger.info(f"🚀 Deploying training job: {job_name}")

        # Convert config to hyperparameters
        hyperparameters = {
            "words-per-corpus": str(config.words_per_corpus),
            "num-corpora": str(config.num_corpora),
            "encoder-epochs": str(config.encoder_epochs),
            "encoder-lr": str(config.encoder_lr),
            "lm-epochs": str(config.lm_epochs),
            "lm-lr": str(config.lm_lr),
            "base-model": config.base_model,
            "embedding-model": config.embedding_model,
        }

        # Training job configuration
        training_config = {
            "TrainingJobName": job_name,
            "RoleArn": self.role_arn,
            "AlgorithmSpecification": {
                "TrainingImage": self.training_image,
                "TrainingInputMode": "File",
            },
            "InputDataConfig": [
                {
                    "ChannelName": "train",
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            "S3Uri": f"s3://{s3_bucket}/wotd-training-data/",
                            "S3DataDistributionType": "FullyReplicated",
                        }
                    },
                    "ContentType": "application/json",
                    "CompressionType": "None",
                }
            ],
            "OutputDataConfig": {"S3OutputPath": f"s3://{s3_bucket}/wotd-models/"},
            "ResourceConfig": {
                "InstanceType": instance_type,
                "InstanceCount": 1,
                "VolumeSizeInGB": 30,
            },
            "StoppingCondition": {
                "MaxRuntimeInSeconds": 3600  # 1 hour max
            },
            "HyperParameters": hyperparameters,
        }

        try:
            response = self.sagemaker.create_training_job(**training_config)
            arn = response["TrainingJobArn"]

            logger.success(f"✅ Training job created: {arn}")
            return str(arn)

        except ClientError as e:
            logger.error(f"❌ Failed to create training job: {e}")
            raise

    async def deploy_inference_endpoint(
        self,
        model_name: str,
        endpoint_name: str,
        s3_model_path: str,
        instance_type: str = "ml.m5.xlarge",
    ) -> str:
        """Deploy inference endpoint to SageMaker."""

        logger.info(f"🚀 Deploying inference endpoint: {endpoint_name}")

        try:
            # Create model
            model_config = {
                "ModelName": model_name,
                "PrimaryContainer": {
                    "Image": self.inference_image,
                    "ModelDataUrl": s3_model_path,
                    "Environment": {
                        "SAGEMAKER_PROGRAM": "inference.py",
                        "SAGEMAKER_SUBMIT_DIRECTORY": "/opt/ml/code",
                    },
                },
                "ExecutionRoleArn": self.role_arn,
            }

            self.sagemaker.create_model(**model_config)
            logger.info(f"📦 Model created: {model_name}")

            # Create endpoint configuration
            endpoint_config_name = f"{endpoint_name}-config"
            endpoint_config = {
                "EndpointConfigName": endpoint_config_name,
                "ProductionVariants": [
                    {
                        "VariantName": "primary",
                        "ModelName": model_name,
                        "InitialInstanceCount": 1,
                        "InstanceType": instance_type,
                        "InitialVariantWeight": 1.0,
                    }
                ],
            }

            self.sagemaker.create_endpoint_config(**endpoint_config)
            logger.info(f"⚙️ Endpoint config created: {endpoint_config_name}")

            # Create endpoint
            endpoint_def = {
                "EndpointName": endpoint_name,
                "EndpointConfigName": endpoint_config_name,
            }

            response = self.sagemaker.create_endpoint(**endpoint_def)
            arn = response["EndpointArn"]

            logger.success(f"✅ Endpoint deployment started: {arn}")
            return str(arn)

        except ClientError as e:
            logger.error(f"❌ Failed to deploy endpoint: {e}")
            raise

    async def monitor_training_job(self, job_name: str) -> dict[str, Any]:
        """Monitor training job progress."""

        logger.info(f"👀 Monitoring training job: {job_name}")

        while True:
            try:
                response = self.sagemaker.describe_training_job(TrainingJobName=job_name)
                status = response["TrainingJobStatus"]

                if status == "Completed":
                    logger.success(f"✅ Training job completed: {job_name}")
                    return dict(response)
                elif status == "Failed":
                    logger.error(f"❌ Training job failed: {job_name}")
                    return dict(response)
                elif status in ["InProgress", "Stopping"]:
                    logger.info(f"🔄 Training job {status.lower()}: {job_name}")
                    await asyncio.sleep(30)  # Check every 30 seconds
                else:
                    logger.info(f"📋 Training job status: {status}")
                    await asyncio.sleep(30)

            except ClientError as e:
                logger.error(f"❌ Error monitoring job: {e}")
                break

        # Should not reach here in normal flow
        return {}

    def prepare_deployment_artifacts(self, output_dir: str) -> dict[str, str]:
        """Prepare deployment artifacts by copying from deployment directory."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        deployment_dir = self.get_deployment_files_dir()

        # Copy deployment files
        files_to_copy = [
            self.DOCKERFILE_TRAINING,
            self.DOCKERFILE_INFERENCE,
            self.TRAIN_SCRIPT,
            self.INFERENCE_SCRIPT,
            self.NGINX_CONFIG,
        ]

        copied_files = {}
        for filename in files_to_copy:
            src = deployment_dir / filename
            dst = output_path / filename

            if src.exists():
                dst.write_text(src.read_text())
                copied_files[filename] = str(dst)
                logger.debug(f"📄 Copied {filename} to {dst}")
            else:
                logger.warning(f"⚠️ Source file not found: {src}")

        # Create deployment configuration
        deployment_config = {
            "ecr_repository": self.ecr_repo_name,
            "training_image": self.training_image,
            "inference_image": self.inference_image,
            "region": self.region,
            "role_arn": self.role_arn,
            "recommended_instances": {
                "training": "ml.g5.xlarge",  # A10G GPU
                "inference": "ml.m5.xlarge",  # CPU for inference
            },
        }

        config_path = output_path / self.DEPLOYMENT_CONFIG_FILE
        import json

        with open(config_path, "w") as f:
            json.dump(deployment_config, f, indent=2)

        copied_files[self.DEPLOYMENT_CONFIG_FILE] = str(config_path)

        logger.info(f"📁 Deployment artifacts prepared in: {output_dir}")
        return copied_files


# Convenience functions
async def deploy_complete_wotd_pipeline(
    role_arn: str,
    s3_bucket: str,
    job_name: str | None = None,
    config: TrainingConfig | None = None,
    region: str = "us-east-1",
) -> dict[str, str]:
    """Deploy complete WOTD pipeline to SageMaker."""

    deployer = SageMakerDeployer(role_arn, region)

    # Generate unique job name if not provided
    if not job_name:
        timestamp = int(time.time())
        job_name = f"wotd-training-{timestamp}"

    # Deploy training job
    training_arn = await deployer.deploy_training_job(
        job_name=job_name, s3_bucket=s3_bucket, config=config
    )

    # Monitor training job
    training_result = await deployer.monitor_training_job(job_name)

    if training_result.get("TrainingJobStatus") != "Completed":
        raise RuntimeError(f"Training job failed: {training_result}")

    # Deploy inference endpoint
    model_name = f"{job_name}-model"
    endpoint_name = f"{job_name}-endpoint"
    model_s3_path = training_result["ModelArtifacts"]["S3ModelArtifacts"]

    endpoint_arn = await deployer.deploy_inference_endpoint(
        model_name=model_name, endpoint_name=endpoint_name, s3_model_path=model_s3_path
    )

    return {
        "training_job_arn": training_arn,
        "endpoint_arn": endpoint_arn,
        "endpoint_name": endpoint_name,
        "model_s3_path": model_s3_path,
    }
