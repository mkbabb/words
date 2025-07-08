"""Batch processor for large-scale AI synthesis using OpenAI Batch API."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import openai
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from ..ai.connector import OpenAIConnector as AIConnector
from ..connectors.base import DictionaryConnector as DictionaryProvider
from ..models.models import Definition, SynthesizedDictionaryEntry
from ..search.core import SearchEngine
from ..storage.mongodb import MongoDBStorage as MongoDB
from .word_filter import FilterPresets

console = Console()

class BatchJobStatus(Enum):
    """Status of batch processing jobs."""
    PENDING = "pending"
    PREPARING = "preparing"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BatchJobConfig:
    """Configuration for batch synthesis jobs."""
    batch_size: int = 1000  # Words per batch file
    max_concurrent_batches: int = 5  # Max concurrent OpenAI batch jobs
    retry_attempts: int = 3
    processing_timeout_hours: int = 48
    output_directory: Path = field(default_factory=lambda: Path("./batch_output"))
    filter_preset: str = "standard"  # minimal, standard, aggressive
    providers: list[DictionaryProvider] = field(default_factory=list)
    force_refresh: bool = False
    enable_clustering: bool = True
    enable_synthesis: bool = True

@dataclass
class BatchJob:
    """Individual batch job tracking."""
    job_id: str
    batch_file_id: str
    openai_batch_id: str | None = None
    word_count: int = 0
    status: BatchJobStatus = BatchJobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    words: list[str] = field(default_factory=list)
    output_file_path: Path | None = None

class BatchProcessor:
    """Processes large word lists using OpenAI Batch API for cost-effective synthesis."""
    
    def __init__(
        self, 
        config: BatchJobConfig,
        ai_connector: AIConnector,
        search_engine: SearchEngine,
        mongodb: MongoDB
    ):
        self.config = config
        self.ai_connector = ai_connector
        self.search_engine = search_engine
        self.mongodb = mongodb
        self.client = openai.OpenAI()
        
        # Ensure output directory exists
        self.config.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize word filter
        if self.config.filter_preset == "minimal":
            self.word_filter = FilterPresets.minimal()
        elif self.config.filter_preset == "aggressive":
            self.word_filter = FilterPresets.aggressive()
        else:
            self.word_filter = FilterPresets.standard()
        
        self.active_jobs: dict[str, BatchJob] = {}
        self.completed_jobs: list[BatchJob] = []
        self.failed_jobs: list[BatchJob] = []
    
    async def get_word_corpus(self) -> list[str]:
        """Get all words from search engine for batch processing."""
        console.print("[blue]Loading word corpus from search engine...[/blue]")
        
        # Get words from search engine
        words = []
        if hasattr(self.search_engine, 'fuzzy_matcher') and self.search_engine.fuzzy_matcher:
            words.extend(self.search_engine.fuzzy_matcher.word_list)
        
        if hasattr(self.search_engine, 'exact_matcher') and self.search_engine.exact_matcher:
            words.extend(self.search_engine.exact_matcher.word_dict.keys())
        
        # Remove duplicates and filter
        unique_words = list(set(words))
        console.print(f"[blue]Found {len(unique_words):,} unique words in corpus[/blue]")
        
        return unique_words
    
    async def get_unprocessed_words(self, all_words: list[str]) -> list[str]:
        """Get words that haven't been synthesized yet."""
        console.print("[blue]Checking for already synthesized words...[/blue]")
        
        # Get list of words already in MongoDB
        synthesized_words = set()
        if hasattr(self.mongodb, 'client') and self.mongodb.client:
            try:
                # Query for existing synthesized entries
                existing_entries = await SynthesizedDictionaryEntry.find_all().to_list()
                synthesized_words = {entry.word.lower() for entry in existing_entries}
                console.print(f"[blue]Found {len(synthesized_words):,} already synthesized words[/blue]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not check existing entries: {e}[/yellow]")
        
        # Filter out already processed words unless force_refresh is enabled
        if self.config.force_refresh:
            unprocessed = all_words
            console.print("[yellow]Force refresh enabled - processing all words[/yellow]")
        else:
            unprocessed = [word for word in all_words if word.lower() not in synthesized_words]
        
        console.print(f"[green]Found {len(unprocessed):,} unprocessed words[/green]")
        return unprocessed
    
    def filter_words(self, words: list[str]) -> list[str]:
        """Apply word filtering heuristics."""
        console.print(f"[blue]Applying {self.config.filter_preset} word filtering...[/blue]")
        
        filtered_words, stats = self.word_filter.filter_words(words)
        
        # Display filtering summary
        console.print(self.word_filter.get_summary(stats))
        
        return filtered_words
    
    def create_batch_jobs(self, words: list[str]) -> list[BatchJob]:
        """Split words into batch jobs."""
        jobs = []
        
        for i in range(0, len(words), self.config.batch_size):
            batch_words = words[i:i + self.config.batch_size]
            job_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i // self.config.batch_size:04d}"
            
            job = BatchJob(
                job_id=job_id,
                batch_file_id="",  # Will be set during upload
                word_count=len(batch_words),
                words=batch_words
            )
            jobs.append(job)
        
        console.print(f"[green]Created {len(jobs)} batch jobs ({self.config.batch_size} words each)[/green]")
        return jobs
    
    async def fetch_definitions_for_word(self, word: str) -> list[Definition]:
        """Fetch definitions for a single word from providers."""
        definitions: list[Definition] = []
        
        # Use search engine to find the word first
        from ..search.constants import SearchMethod
        search_results = await self.search_engine.search(
            word, 
            methods=[SearchMethod.EXACT, SearchMethod.FUZZY],
            max_results=1
        )
        
        if not search_results:
            return definitions
        
        # Fetch from providers
        for provider in self.config.providers:
            try:
                provider_definitions = await provider.fetch_definition(word)
                definitions.extend(provider_definitions)
            except Exception as e:
                console.print(f"[yellow]Warning: Provider {provider.__class__.__name__} failed for '{word}': {e}[/yellow]")
        
        return definitions
    
    def create_cluster_mapping_request(self, word: str, definitions: list[Definition], custom_id: str) -> dict[str, Any]:
        """Create OpenAI batch request for cluster mapping."""
        definition_dicts = [def_.model_dump() for def_ in definitions]
        
        return {
            "custom_id": f"{custom_id}_cluster",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert lexicographer. Analyze definitions and group them into semantic clusters."
                    },
                    {
                        "role": "user", 
                        "content": f"Analyze these definitions for '{word}' and create cluster mappings:\\n\\n{json.dumps(definition_dicts, indent=2)}"
                    }
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "cluster_mapping_response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "clusters": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "cluster_id": {"type": "string"},
                                            "cluster_description": {"type": "string"},
                                            "definition_indices": {
                                                "type": "array",
                                                "items": {"type": "integer"}
                                            }
                                        },
                                        "required": ["cluster_id", "cluster_description", "definition_indices"]
                                    }
                                },
                                "confidence_score": {"type": "number"}
                            },
                            "required": ["clusters", "confidence_score"]
                        }
                    }
                }
            }
        }
    
    def create_synthesis_request(self, word: str, cluster_definitions: list[Definition], cluster_id: str, custom_id: str) -> dict[str, Any]:
        """Create OpenAI batch request for definition synthesis."""
        definition_dicts = [def_.model_dump() for def_ in cluster_definitions]
        
        return {
            "custom_id": f"{custom_id}_synth_{cluster_id}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert lexicographer. Synthesize multiple definitions into a single, comprehensive definition."
                    },
                    {
                        "role": "user",
                        "content": f"Synthesize these definitions for '{word}' (cluster: {cluster_id}):\\n\\n{json.dumps(definition_dicts, indent=2)}"
                    }
                ],
                "response_format": {
                    "type": "json_schema", 
                    "json_schema": {
                        "name": "synthesized_definition",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "definition": {"type": "string"},
                                "part_of_speech": {"type": "string"},
                                "meaning_cluster": {"type": "string"},
                                "confidence_score": {"type": "number"}
                            },
                            "required": ["definition", "part_of_speech", "meaning_cluster", "confidence_score"]
                        }
                    }
                }
            }
        }
    
    async def prepare_batch_file(self, job: BatchJob) -> str:
        """Prepare JSONL batch file for OpenAI."""
        job.status = BatchJobStatus.PREPARING
        
        batch_requests = []
        request_id = 0
        
        console.print(f"[blue]Preparing batch file for {job.word_count} words...[/blue]")
        
        with Progress() as progress:
            task = progress.add_task(f"Processing {job.job_id}", total=job.word_count)
            
            for word in job.words:
                # Fetch definitions
                definitions = await self.fetch_definitions_for_word(word)
                
                if not definitions:
                    progress.advance(task)
                    continue
                
                custom_id = f"{job.job_id}_{request_id:06d}_{word}"
                
                # Create cluster mapping request
                if self.config.enable_clustering:
                    cluster_request = self.create_cluster_mapping_request(word, definitions, custom_id)
                    batch_requests.append(cluster_request)
                
                # For now, create synthesis requests for each definition group
                # In production, this would be done after cluster mapping results
                if self.config.enable_synthesis:
                    synth_request = self.create_synthesis_request(word, definitions, "default", custom_id)
                    batch_requests.append(synth_request)
                
                request_id += 1
                progress.advance(task)
        
        # Write JSONL file
        batch_file_path = self.config.output_directory / f"{job.job_id}.jsonl"
        with open(batch_file_path, 'w', encoding='utf-8') as f:
            for request in batch_requests:
                f.write(json.dumps(request) + '\n')
        
        console.print(f"[green]Created batch file with {len(batch_requests)} requests: {batch_file_path}[/green]")
        return str(batch_file_path)
    
    async def upload_batch_file(self, job: BatchJob, file_path: str) -> str:
        """Upload batch file to OpenAI."""
        job.status = BatchJobStatus.UPLOADING
        
        console.print(f"[blue]Uploading batch file for {job.job_id}...[/blue]")
        
        try:
            with open(file_path, 'rb') as f:
                batch_file = self.client.files.create(
                    file=f,
                    purpose="batch"
                )
            
            job.batch_file_id = batch_file.id
            console.print(f"[green]Uploaded batch file: {batch_file.id}[/green]")
            return batch_file.id
            
        except Exception as e:
            job.status = BatchJobStatus.FAILED
            job.error_message = f"Upload failed: {str(e)}"
            console.print(f"[red]Upload failed for {job.job_id}: {e}[/red]")
            raise
    
    async def submit_batch_job(self, job: BatchJob) -> str:
        """Submit batch job to OpenAI."""
        console.print(f"[blue]Submitting batch job {job.job_id}...[/blue]")
        
        try:
            batch_job = self.client.batches.create(
                input_file_id=job.batch_file_id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={"job_id": job.job_id}
            )
            
            job.openai_batch_id = batch_job.id
            job.status = BatchJobStatus.PROCESSING
            job.started_at = datetime.now()
            
            console.print(f"[green]Submitted batch job: {batch_job.id}[/green]")
            return batch_job.id
            
        except Exception as e:
            job.status = BatchJobStatus.FAILED
            job.error_message = f"Submission failed: {str(e)}"
            console.print(f"[red]Submission failed for {job.job_id}: {e}[/red]")
            raise
    
    async def monitor_batch_jobs(self, jobs: list[BatchJob]) -> None:
        """Monitor batch job progress."""
        console.print(f"[blue]Monitoring {len(jobs)} batch jobs...[/blue]")
        
        with Progress() as progress:
            tasks = {}
            for job in jobs:
                if job.openai_batch_id:
                    tasks[job.openai_batch_id] = progress.add_task(
                        f"Job {job.job_id}", 
                        total=100
                    )
            
            while any(job.status == BatchJobStatus.PROCESSING for job in jobs):
                for job in jobs:
                    if job.status != BatchJobStatus.PROCESSING or not job.openai_batch_id:
                        continue
                    
                    try:
                        batch_status = self.client.batches.retrieve(job.openai_batch_id)
                        
                        if batch_status.status == "completed":
                            job.status = BatchJobStatus.COMPLETED
                            job.completed_at = datetime.now()
                            if batch_status.output_file_id:
                                job.output_file_path = await self.download_results(job, batch_status.output_file_id)
                            progress.update(tasks[job.openai_batch_id], completed=100)
                            console.print(f"[green]Job {job.job_id} completed[/green]")
                            
                        elif batch_status.status == "failed":
                            job.status = BatchJobStatus.FAILED
                            job.error_message = "OpenAI batch job failed"
                            progress.update(tasks[job.openai_batch_id], completed=100)
                            console.print(f"[red]Job {job.job_id} failed[/red]")
                            
                        elif batch_status.status == "cancelled":
                            job.status = BatchJobStatus.CANCELLED
                            progress.update(tasks[job.openai_batch_id], completed=100)
                            console.print(f"[yellow]Job {job.job_id} cancelled[/yellow]")
                        
                        else:
                            # Update progress based on completion estimates
                            if hasattr(batch_status, 'request_counts') and batch_status.request_counts:
                                counts = batch_status.request_counts
                                completed = getattr(counts, 'completed', 0)
                                total = getattr(counts, 'total', 1)
                                progress_pct = int((completed / total) * 100)
                                progress.update(tasks[job.openai_batch_id], completed=progress_pct)
                    
                    except Exception as e:
                        console.print(f"[yellow]Error checking job {job.job_id}: {e}[/yellow]")
                
                # Check for timeout
                for job in jobs:
                    if (job.status == BatchJobStatus.PROCESSING and 
                        job.started_at and 
                        datetime.now() - job.started_at > timedelta(hours=self.config.processing_timeout_hours)):
                        job.status = BatchJobStatus.FAILED
                        job.error_message = "Processing timeout"
                        console.print(f"[red]Job {job.job_id} timed out[/red]")
                
                await asyncio.sleep(30)  # Check every 30 seconds
    
    async def download_results(self, job: BatchJob, output_file_id: str) -> Path:
        """Download and save batch job results."""
        console.print(f"[blue]Downloading results for {job.job_id}...[/blue]")
        
        try:
            result_content = self.client.files.content(output_file_id).content
            
            output_path = self.config.output_directory / f"{job.job_id}_results.jsonl"
            with open(output_path, 'wb') as f:
                f.write(result_content)
            
            console.print(f"[green]Downloaded results: {output_path}[/green]")
            return output_path
            
        except Exception as e:
            console.print(f"[red]Download failed for {job.job_id}: {e}[/red]")
            raise
    
    async def process_results(self, job: BatchJob) -> int:
        """Process batch job results and save to MongoDB."""
        if not job.output_file_path or job.status != BatchJobStatus.COMPLETED:
            return 0
        
        console.print(f"[blue]Processing results for {job.job_id}...[/blue]")
        
        processed_count = 0
        
        try:
            with open(job.output_file_path, encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    result = json.loads(line)
                    
                    # Parse custom_id to extract word and request type
                    custom_id = result.get("custom_id", "")
                    if "_cluster" in custom_id or "_synth_" in custom_id:
                        # Process AI response and create SynthesizedDictionaryEntry
                        await self._process_synthesis_result(result)
                        processed_count += 1
            
            console.print(f"[green]Processed {processed_count} results from {job.job_id}[/green]")
            return processed_count
            
        except Exception as e:
            console.print(f"[red]Error processing results for {job.job_id}: {e}[/red]")
            return 0
    
    async def _process_synthesis_result(self, result: dict[str, Any]) -> None:
        """Process individual synthesis result and save to database."""
        # This would contain the logic to parse OpenAI responses
        # and create SynthesizedDictionaryEntry objects
        # Implementation depends on the exact response format
        pass
    
    async def run_batch_processing(self, word_limit: int | None = None) -> dict[str, Any]:
        """Run the complete batch processing pipeline."""
        console.print("[bold blue]Starting Batch Processing Pipeline[/bold blue]")
        
        start_time = datetime.now()
        
        try:
            # Step 1: Get word corpus
            all_words = await self.get_word_corpus()
            
            # Step 2: Filter unprocessed words
            unprocessed_words = await self.get_unprocessed_words(all_words)
            
            # Step 3: Apply word filtering
            filtered_words = self.filter_words(unprocessed_words)
            
            # Step 4: Apply word limit if specified
            if word_limit and len(filtered_words) > word_limit:
                filtered_words = filtered_words[:word_limit]
                console.print(f"[yellow]Limited to {word_limit} words for processing[/yellow]")
            
            if not filtered_words:
                console.print("[yellow]No words to process[/yellow]")
                return {"status": "completed", "processed": 0}
            
            # Step 5: Create batch jobs
            batch_jobs = self.create_batch_jobs(filtered_words)
            
            # Step 6: Process batches with concurrency limits
            completed_jobs = []
            failed_jobs = []
            
            # Process in chunks to respect concurrency limits
            for i in range(0, len(batch_jobs), self.config.max_concurrent_batches):
                chunk = batch_jobs[i:i + self.config.max_concurrent_batches]
                
                # Prepare and submit jobs
                for job in chunk:
                    try:
                        batch_file_path = await self.prepare_batch_file(job)
                        await self.upload_batch_file(job, batch_file_path)
                        await self.submit_batch_job(job)
                        self.active_jobs[job.job_id] = job
                    except Exception as e:
                        job.status = BatchJobStatus.FAILED
                        job.error_message = str(e)
                        failed_jobs.append(job)
                
                # Monitor current chunk
                active_chunk = [job for job in chunk if job.status == BatchJobStatus.PROCESSING]
                if active_chunk:
                    await self.monitor_batch_jobs(active_chunk)
                
                # Process results
                for job in chunk:
                    if job.status == BatchJobStatus.COMPLETED:
                        await self.process_results(job)
                        completed_jobs.append(job)
                    elif job.status == BatchJobStatus.FAILED:
                        failed_jobs.append(job)
            
            # Generate summary
            end_time = datetime.now()
            duration = end_time - start_time
            
            total_processed = sum(job.word_count for job in completed_jobs)
            total_failed = sum(job.word_count for job in failed_jobs)
            
            summary = {
                "status": "completed",
                "duration_minutes": duration.total_seconds() / 60,
                "total_words_input": len(filtered_words),
                "total_words_processed": total_processed,
                "total_words_failed": total_failed,
                "batch_jobs_completed": len(completed_jobs),
                "batch_jobs_failed": len(failed_jobs),
                "success_rate": (total_processed / len(filtered_words)) * 100 if filtered_words else 0
            }
            
            # Display summary table
            self._display_summary(summary, completed_jobs, failed_jobs)
            
            return summary
            
        except Exception as e:
            console.print(f"[red]Batch processing failed: {e}[/red]")
            return {"status": "failed", "error": str(e)}
    
    def _display_summary(self, summary: dict[str, Any], completed_jobs: list[BatchJob], failed_jobs: list[BatchJob]) -> None:
        """Display batch processing summary."""
        console.print("\\n[bold green]Batch Processing Summary[/bold green]")
        
        # Summary table
        table = Table(title="Processing Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="yellow")
        
        table.add_row("Duration", f"{summary['duration_minutes']:.1f} minutes")
        table.add_row("Input Words", f"{summary['total_words_input']:,}")
        table.add_row("Processed Words", f"{summary['total_words_processed']:,}")
        table.add_row("Failed Words", f"{summary['total_words_failed']:,}")
        table.add_row("Success Rate", f"{summary['success_rate']:.1f}%")
        table.add_row("Completed Jobs", str(summary['batch_jobs_completed']))
        table.add_row("Failed Jobs", str(summary['batch_jobs_failed']))
        
        console.print(table)
        
        # Cost estimation (based on 50% discount for batch API)
        if summary['total_words_processed'] > 0:
            # Rough estimation: ~2 requests per word (cluster + synthesis)
            estimated_tokens = summary['total_words_processed'] * 2 * 500  # ~500 tokens per request
            estimated_cost = (estimated_tokens / 1_000_000) * 0.075  # $0.075/1M tokens for GPT-4o-mini batch
            console.print(f"\\n[green]Estimated cost: ${estimated_cost:.2f}[/green]")
        
        if failed_jobs:
            console.print("\\n[red]Failed Jobs:[/red]")
            for job in failed_jobs[:5]:  # Show first 5 failed jobs
                console.print(f"  - {job.job_id}: {job.error_message}")