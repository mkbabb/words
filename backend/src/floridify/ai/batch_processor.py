"""Batch processing for synthesis operations using OpenAI Batch API.

This module provides efficient batch processing for large-scale synthesis
operations, reducing costs by 50% through the OpenAI Batch API.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import openai
from rich.console import Console
from rich.progress import Progress

from ..models import Definition, Word
from ..utils.logging import get_logger
from .connector import OpenAIConnector
from .synthesis_functions import enhance_definitions_parallel
from .synthesizer import DefinitionSynthesizer

logger = get_logger(__name__)
console = Console()


class SynthesisBatchProcessor:
    """Processes large-scale synthesis operations using OpenAI Batch API."""
    
    def __init__(
        self,
        openai_connector: OpenAIConnector,
        output_dir: Path | None = None
    ):
        self.ai = openai_connector
        self.synthesizer = DefinitionSynthesizer(openai_connector)
        self.output_dir = output_dir or Path("/tmp/floridify_batches")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = openai.AsyncOpenAI(api_key=openai_connector.api_key)
    
    async def process_words_batch(
        self,
        words_with_data: list[tuple[Word, list[Definition]]],
        components: set[str] | None = None,
        batch_size: int = 1000
    ) -> dict[str, Any]:
        """Process multiple words through synthesis in batches.
        
        Args:
            words_with_data: List of (Word, Definitions) tuples
            components: Which components to synthesize
            batch_size: Max words per batch
            
        Returns:
            Processing summary with batch IDs
        """
        console.print(f"[blue]Processing {len(words_with_data)} words in batches[/blue]")
        
        batch_jobs = []
        
        # Process in chunks
        for i in range(0, len(words_with_data), batch_size):
            chunk = words_with_data[i:i + batch_size]
            
            # Create batch for this chunk
            batch_id = f"synthesis_{datetime.now():%Y%m%d_%H%M%S}_{i//batch_size:04d}"
            
            console.print(f"[blue]Creating batch {batch_id} with {len(chunk)} words[/blue]")
            
            # Create batch requests
            batch_requests = []
            
            for word, definitions in chunk:
                # Create requests for each synthesis operation
                requests = self._create_synthesis_requests(
                    word, definitions, components
                )
                batch_requests.extend(requests)
            
            if batch_requests:
                # Submit batch
                job_info = await self._submit_batch(batch_id, batch_requests)
                batch_jobs.append(job_info)
        
        return {
            "status": "submitted",
            "batches": len(batch_jobs),
            "total_words": len(words_with_data),
            "batch_jobs": batch_jobs
        }
    
    def _create_synthesis_requests(
        self,
        word: Word,
        definitions: list[Definition],
        components: set[str] | None
    ) -> list[dict[str, Any]]:
        """Create OpenAI batch requests for synthesis operations."""
        from .templates import PromptTemplateManager
        from .constants import SynthesisComponent
        
        if components is None:
            components = SynthesisComponent.default_components()
        
        template_manager = PromptTemplateManager()
        requests = []
        
        for i, definition in enumerate(definitions):
            # Synonyms
            if SynthesisComponent.SYNONYMS.value in components:
                prompt = template_manager.get_synthesize_synonyms_prompt(
                    word.text,
                    definition.text,
                    definition.part_of_speech,
                    [],  # existing synonyms
                    10   # count
                )
                requests.append(self._create_batch_request(
                    f"{word.text}_def{i}_synonyms",
                    prompt,
                    "synonym_generation_response"
                ))
            
            # Examples
            if SynthesisComponent.EXAMPLES.value in components:
                prompt = template_manager.get_generate_examples_prompt(
                    word.text,
                    definition.text,
                    definition.part_of_speech,
                    3  # count
                )
                requests.append(self._create_batch_request(
                    f"{word.text}_def{i}_examples",
                    prompt,
                    "example_generation_response"
                ))
            
            # CEFR Level
            if SynthesisComponent.CEFR_LEVEL.value in components:
                prompt = template_manager.get_assess_cefr_prompt(
                    word.text,
                    definition.text
                )
                requests.append(self._create_batch_request(
                    f"{word.text}_def{i}_cefr",
                    prompt,
                    "cefr_level_response"
                ))
            
            # Add more components as needed...
        
        return requests
    
    def _create_batch_request(
        self,
        custom_id: str,
        prompt: str,
        response_format: str
    ) -> dict[str, Any]:
        """Create a single batch request in OpenAI format."""
        # Get the response model schema based on the format name
        from .models import (
            SynonymGenerationResponse,
            ExampleGenerationResponse,
            CEFRLevelResponse
        )
        
        model_map = {
            "synonym_generation_response": SynonymGenerationResponse,
            "example_generation_response": ExampleGenerationResponse,
            "cefr_level_response": CEFRLevelResponse,
        }
        
        response_model = model_map.get(response_format)
        if not response_model:
            raise ValueError(f"Unknown response format: {response_format}")
        
        return {
            "custom_id": custom_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": self.ai.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_format,
                        "schema": response_model.model_json_schema(),
                        "strict": True
                    }
                },
                "temperature": 0.3,
                "max_tokens": 1000
            }
        }
    
    async def _submit_batch(
        self,
        batch_id: str,
        requests: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Submit a batch to OpenAI."""
        # Create JSONL file
        batch_file = self.output_dir / f"{batch_id}.jsonl"
        
        with open(batch_file, "w") as f:
            for request in requests:
                f.write(json.dumps(request) + "\n")
        
        # Upload file
        with open(batch_file, "rb") as f:
            file_response = await self.client.files.create(
                file=f,
                purpose="batch"
            )
        
        # Create batch
        batch = await self.client.batches.create(
            input_file_id=file_response.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={
                "batch_id": batch_id,
                "requests": str(len(requests))
            }
        )
        
        console.print(f"[green]Submitted batch {batch.id} with {len(requests)} requests[/green]")
        
        return {
            "batch_id": batch_id,
            "openai_batch_id": batch.id,
            "file_id": file_response.id,
            "requests": len(requests),
            "status": "submitted"
        }
    
    async def check_batch_status(self, openai_batch_id: str) -> dict[str, Any]:
        """Check the status of a batch job."""
        batch = await self.client.batches.retrieve(openai_batch_id)
        
        result = {
            "id": batch.id,
            "status": batch.status,
            "created_at": batch.created_at,
        }
        
        if hasattr(batch, "completed_at"):
            result["completed_at"] = batch.completed_at
        
        if hasattr(batch, "request_counts") and batch.request_counts:
            result["progress"] = {
                "total": getattr(batch.request_counts, "total", 0),
                "completed": getattr(batch.request_counts, "completed", 0),
                "failed": getattr(batch.request_counts, "failed", 0),
            }
        
        if batch.status == "completed" and batch.output_file_id:
            result["output_file_id"] = batch.output_file_id
        
        return result
    
    async def process_batch_results(
        self,
        openai_batch_id: str,
        output_file_id: str
    ) -> dict[str, Any]:
        """Process results from a completed batch."""
        # Download results
        response = await self.client.files.content(output_file_id)
        
        # Save results
        results_file = self.output_dir / f"results_{openai_batch_id}.jsonl"
        with open(results_file, "wb") as f:
            f.write(response.content)
        
        # Process results
        processed = 0
        errors = 0
        
        with open(results_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                
                result = json.loads(line)
                
                if "error" in result:
                    errors += 1
                    logger.error(f"Batch error for {result['custom_id']}: {result['error']}")
                else:
                    processed += 1
                    # Here you would update the database with results
                    # This is where the actual synthesis results get applied
        
        return {
            "processed": processed,
            "errors": errors,
            "results_file": str(results_file)
        }
    
    async def run_full_batch_synthesis(
        self,
        words: list[str],
        poll_interval: int = 60
    ) -> dict[str, Any]:
        """Run a complete batch synthesis workflow.
        
        This demonstrates the full flow:
        1. Prepare word data
        2. Create and submit batches
        3. Poll for completion
        4. Process results
        """
        console.print("[bold blue]Starting Batch Synthesis Workflow[/bold blue]")
        
        # 1. Prepare word data (simplified - you'd fetch definitions)
        words_with_data = []
        for word in words:
            word_obj = Word(text=word, normalized=word.lower(), language="en")
            # In reality, you'd fetch definitions from providers
            definitions = [
                Definition(
                    text=f"Test definition for {word}",
                    part_of_speech="noun",
                    provider="test"
                )
            ]
            words_with_data.append((word_obj, definitions))
        
        # 2. Submit batches
        submission_result = await self.process_words_batch(words_with_data)
        
        # 3. Poll for completion
        console.print(f"[blue]Monitoring {len(submission_result['batch_jobs'])} batch jobs[/blue]")
        
        completed_batches = []
        
        with Progress() as progress:
            for job in submission_result["batch_jobs"]:
                task = progress.add_task(
                    f"Batch {job['batch_id']}", 
                    total=job["requests"]
                )
                
                while True:
                    status = await self.check_batch_status(job["openai_batch_id"])
                    
                    if "progress" in status:
                        completed = status["progress"]["completed"]
                        progress.update(task, completed=completed)
                    
                    if status["status"] == "completed":
                        progress.update(task, completed=job["requests"])
                        completed_batches.append({
                            **job,
                            "output_file_id": status["output_file_id"]
                        })
                        break
                    elif status["status"] in ["failed", "expired", "cancelled"]:
                        console.print(f"[red]Batch {job['batch_id']} failed: {status['status']}[/red]")
                        break
                    
                    await asyncio.sleep(poll_interval)
        
        # 4. Process results
        console.print(f"[blue]Processing results from {len(completed_batches)} completed batches[/blue]")
        
        total_processed = 0
        total_errors = 0
        
        for batch in completed_batches:
            result = await self.process_batch_results(
                batch["openai_batch_id"],
                batch["output_file_id"]
            )
            total_processed += result["processed"]
            total_errors += result["errors"]
        
        console.print(f"[bold green]Batch synthesis complete![/bold green]")
        console.print(f"Processed: {total_processed} | Errors: {total_errors}")
        
        return {
            "status": "completed",
            "total_words": len(words),
            "total_processed": total_processed,
            "total_errors": total_errors,
            "batches": len(completed_batches)
        }