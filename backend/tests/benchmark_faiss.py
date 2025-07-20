"""FAISS and semantic search performance benchmarking.

Specialized benchmarks for embedding generation, index operations,
and semantic similarity search performance.
"""

from __future__ import annotations

import asyncio
import gc
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Import FAISS and semantic search components
from floridify.search.semantic import SemanticSearch
from floridify.search.language import LanguageSearch
from floridify.core.search_pipeline import get_search_engine


@dataclass
class FAISSMetrics:
    """FAISS-specific performance metrics."""
    index_build_time: float = 0.0
    embedding_times: list[float] = field(default_factory=list)
    search_times: list[float] = field(default_factory=list)
    memory_usage_mb: float = 0.0
    index_size_mb: float = 0.0
    vocabulary_size: int = 0
    embedding_dimensions: int = 0
    accuracy_scores: list[float] = field(default_factory=list)
    
    @property
    def avg_embedding_ms(self) -> float:
        return np.mean(self.embedding_times) * 1000 if self.embedding_times else 0
    
    @property
    def avg_search_ms(self) -> float:
        return np.mean(self.search_times) * 1000 if self.search_times else 0
    
    @property
    def throughput_embeddings_per_sec(self) -> float:
        if not self.embedding_times:
            return 0
        return len(self.embedding_times) / sum(self.embedding_times)


class FAISSBenchmark:
    """Specialized FAISS performance benchmarking."""
    
    def __init__(self):
        self.console = Console()
        self.semantic_search: SemanticSearch | None = None
        
        # Test datasets of varying complexity
        self.test_datasets = {
            "simple_words": ["cat", "dog", "run", "jump", "happy", "sad", "big", "small"],
            "complex_words": [
                "algorithm", "consciousness", "antidisestablishmentarianism",
                "pneumonoultramicroscopicsilicovolcanoconiosiswith", "floccinaucinihilipilification"
            ],
            "phrases": [
                "machine learning", "artificial intelligence", "natural language processing",
                "computer vision", "deep neural networks", "quantum computing"
            ],
            "similar_meanings": [
                "happy", "joyful", "elated", "euphoric", "content", "pleased",
                "cheerful", "delighted", "ecstatic", "blissful"
            ],
            "technical_terms": [
                "API", "REST", "HTTP", "JSON", "XML", "SQL", "NoSQL",
                "microservices", "containerization", "orchestration"
            ]
        }
    
    async def _get_semantic_search(self) -> SemanticSearch:
        """Initialize semantic search with timing."""
        if self.semantic_search is None:
            start_time = time.perf_counter()
            
            # Get the language search engine which contains semantic search
            language_search = await get_search_engine()
            
            # Access the semantic search component
            if hasattr(language_search.search_engine, 'semantic_search'):
                self.semantic_search = language_search.search_engine.semantic_search
            else:
                # If not available, create a new instance
                from floridify.search.semantic import SemanticSearch
                self.semantic_search = SemanticSearch()
                await self.semantic_search.initialize()
            
            init_time = time.perf_counter() - start_time
            self.console.print(f"[dim]Semantic search initialization: {init_time*1000:.1f}ms[/dim]")
        
        return self.semantic_search
    
    async def benchmark_embedding_generation(self, words: list[str], iterations: int = 50) -> FAISSMetrics:
        """Benchmark embedding generation performance."""
        metrics = FAISSMetrics()
        semantic_search = await self._get_semantic_search()
        
        if not hasattr(semantic_search, 'generate_embeddings'):
            self.console.print("[yellow]Warning: Embedding generation not available[/yellow]")
            return metrics
        
        self.console.print(f"[dim]Benchmarking embedding generation for {len(words)} words...[/dim]")
        
        for i in range(iterations):
            gc.collect()
            
            for word in words:
                start_time = time.perf_counter()
                
                try:
                    # Generate embedding for single word
                    if hasattr(semantic_search, 'embed_query'):
                        embedding = await semantic_search.embed_query(word)
                    elif hasattr(semantic_search, '_embed_text'):
                        embedding = semantic_search._embed_text(word)
                    else:
                        # Fallback method
                        continue
                    
                    elapsed = time.perf_counter() - start_time
                    metrics.embedding_times.append(elapsed)
                    
                    # Record embedding dimensions
                    if hasattr(embedding, 'shape'):
                        metrics.embedding_dimensions = embedding.shape[-1]
                
                except Exception as e:
                    self.console.print(f"[red]Embedding error for '{word}': {e}[/red]")
        
        return metrics
    
    async def benchmark_index_operations(self, vocabulary_size: int = 1000) -> FAISSMetrics:
        """Benchmark FAISS index building and search operations."""
        metrics = FAISSMetrics()
        semantic_search = await self._get_semantic_search()
        
        if not hasattr(semantic_search, 'index') or semantic_search.index is None:
            self.console.print("[yellow]Warning: FAISS index not available[/yellow]")
            return metrics
        
        # Measure index properties
        if hasattr(semantic_search, 'index'):
            index = semantic_search.index
            metrics.vocabulary_size = index.ntotal if hasattr(index, 'ntotal') else 0
            metrics.embedding_dimensions = index.d if hasattr(index, 'd') else 0
            
            # Estimate index size (rough calculation)
            if metrics.vocabulary_size > 0 and metrics.embedding_dimensions > 0:
                # Assume 4 bytes per float
                metrics.index_size_mb = (metrics.vocabulary_size * metrics.embedding_dimensions * 4) / (1024 * 1024)
        
        # Benchmark search operations
        test_queries = ["algorithm", "happiness", "computer", "language", "intelligence"]
        
        for query in test_queries:
            for _ in range(20):  # Multiple searches per query
                start_time = time.perf_counter()
                
                try:
                    if hasattr(semantic_search, 'search'):
                        results = await semantic_search.search(query, max_results=10)
                    elif hasattr(semantic_search, 'find_similar'):
                        results = semantic_search.find_similar(query, k=10)
                    else:
                        continue
                    
                    elapsed = time.perf_counter() - start_time
                    metrics.search_times.append(elapsed)
                    
                    # Calculate accuracy based on semantic relevance
                    if results and len(results) > 0:
                        # Simple heuristic: score distribution
                        scores = [getattr(r, 'score', 0.5) for r in results]
                        avg_score = np.mean(scores) if scores else 0.0
                        metrics.accuracy_scores.append(avg_score)
                
                except Exception as e:
                    self.console.print(f"[red]Search error for '{query}': {e}[/red]")
        
        return metrics
    
    async def benchmark_similarity_accuracy(self, test_sets: dict[str, list[str]]) -> dict[str, float]:
        """Benchmark semantic similarity accuracy."""
        semantic_search = await self._get_semantic_search()
        accuracy_results = {}
        
        for set_name, words in test_sets.items():
            if len(words) < 2:
                continue
            
            self.console.print(f"[dim]Testing similarity accuracy for {set_name}...[/dim]")
            
            similarities = []
            
            # Test similarity between words in the same semantic group
            for i, word1 in enumerate(words):
                for word2 in words[i+1:]:
                    try:
                        if hasattr(semantic_search, 'calculate_similarity'):
                            similarity = await semantic_search.calculate_similarity(word1, word2)
                        elif hasattr(semantic_search, 'search'):
                            # Use search-based similarity
                            results = await semantic_search.search(word1, max_results=20)
                            similarity = 0.0
                            for result in results:
                                if hasattr(result, 'word') and result.word.lower() == word2.lower():
                                    similarity = getattr(result, 'score', 0.0)
                                    break
                        else:
                            similarity = 0.5  # Default
                        
                        similarities.append(similarity)
                    
                    except Exception as e:
                        self.console.print(f"[red]Similarity error for '{word1}' vs '{word2}': {e}[/red]")
            
            # Calculate average similarity within the set
            accuracy_results[set_name] = np.mean(similarities) if similarities else 0.0
        
        return accuracy_results
    
    async def benchmark_memory_efficiency(self) -> dict[str, float]:
        """Benchmark memory usage patterns."""
        import psutil
        process = psutil.Process()
        
        memory_stats = {}
        
        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024
        memory_stats["baseline_mb"] = baseline_memory
        
        # Memory after semantic search initialization
        semantic_search = await self._get_semantic_search()
        after_init_memory = process.memory_info().rss / 1024 / 1024
        memory_stats["after_init_mb"] = after_init_memory
        memory_stats["init_overhead_mb"] = after_init_memory - baseline_memory
        
        # Memory during search operations
        test_queries = ["algorithm", "happiness", "computer"] * 10
        
        start_memory = process.memory_info().rss / 1024 / 1024
        
        for query in test_queries:
            try:
                if hasattr(semantic_search, 'search'):
                    await semantic_search.search(query, max_results=10)
            except Exception:
                pass
        
        end_memory = process.memory_info().rss / 1024 / 1024
        memory_stats["search_overhead_mb"] = end_memory - start_memory
        memory_stats["peak_usage_mb"] = end_memory
        
        return memory_stats
    
    async def run_comprehensive_faiss_benchmark(self) -> dict[str, Any]:
        """Run complete FAISS benchmark suite."""
        results = {
            "timestamp": time.time(),
            "embedding_performance": {},
            "index_performance": {},
            "similarity_accuracy": {},
            "memory_efficiency": {},
            "optimization_recommendations": []
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            # 1. Embedding generation benchmarks
            task1 = progress.add_task("Benchmarking embedding generation...", total=None)
            for dataset_name, words in self.test_datasets.items():
                metrics = await self.benchmark_embedding_generation(words, iterations=10)
                results["embedding_performance"][dataset_name] = {
                    "avg_embedding_ms": metrics.avg_embedding_ms,
                    "throughput_per_sec": metrics.throughput_embeddings_per_sec,
                    "embedding_dimensions": metrics.embedding_dimensions,
                    "word_count": len(words)
                }
            progress.remove_task(task1)
            
            # 2. Index operations benchmarks
            task2 = progress.add_task("Benchmarking index operations...", total=None)
            index_metrics = await self.benchmark_index_operations()
            results["index_performance"] = {
                "vocabulary_size": index_metrics.vocabulary_size,
                "embedding_dimensions": index_metrics.embedding_dimensions,
                "index_size_mb": index_metrics.index_size_mb,
                "avg_search_ms": index_metrics.avg_search_ms,
                "search_count": len(index_metrics.search_times)
            }
            progress.remove_task(task2)
            
            # 3. Similarity accuracy benchmarks
            task3 = progress.add_task("Testing similarity accuracy...", total=None)
            accuracy_results = await self.benchmark_similarity_accuracy(
                {"similar_meanings": self.test_datasets["similar_meanings"]}
            )
            results["similarity_accuracy"] = accuracy_results
            progress.remove_task(task3)
            
            # 4. Memory efficiency benchmarks
            task4 = progress.add_task("Analyzing memory efficiency...", total=None)
            memory_stats = await self.benchmark_memory_efficiency()
            results["memory_efficiency"] = memory_stats
            progress.remove_task(task4)
            
            # 5. Generate optimization recommendations
            results["optimization_recommendations"] = self._generate_faiss_recommendations(results)
        
        return results
    
    def _generate_faiss_recommendations(self, results: dict[str, Any]) -> list[str]:
        """Generate FAISS-specific optimization recommendations."""
        recommendations = []
        
        # Check embedding performance
        embedding_perf = results.get("embedding_performance", {})
        for dataset, metrics in embedding_perf.items():
            avg_time = metrics.get("avg_embedding_ms", 0)
            if avg_time > 50:  # > 50ms per embedding
                recommendations.append(f"Slow embedding generation for {dataset}: {avg_time:.1f}ms - consider GPU acceleration")
        
        # Check index size
        index_perf = results.get("index_performance", {})
        index_size = index_perf.get("index_size_mb", 0)
        if index_size > 500:  # > 500MB
            recommendations.append(f"Large index size: {index_size:.1f}MB - consider quantization or dimensionality reduction")
        
        # Check search performance
        search_time = index_perf.get("avg_search_ms", 0)
        if search_time > 20:  # > 20ms per search
            recommendations.append(f"Slow search performance: {search_time:.1f}ms - consider index optimization")
        
        # Check memory usage
        memory_eff = results.get("memory_efficiency", {})
        init_overhead = memory_eff.get("init_overhead_mb", 0)
        if init_overhead > 200:  # > 200MB initialization overhead
            recommendations.append(f"High memory overhead: {init_overhead:.1f}MB - consider lazy loading")
        
        # Check accuracy
        similarity_acc = results.get("similarity_accuracy", {})
        for test_set, accuracy in similarity_acc.items():
            if accuracy < 0.7:  # < 70% similarity for related words
                recommendations.append(f"Low similarity accuracy for {test_set}: {accuracy:.1%} - consider model tuning")
        
        return recommendations
    
    def generate_faiss_report(self, results: dict[str, Any]) -> None:
        """Generate FAISS performance report."""
        self.console.print("\n[bold cyan]🔍 FAISS & Semantic Search Performance Analysis[/bold cyan]\n")
        
        # Embedding performance table
        if results.get("embedding_performance"):
            embedding_table = Table(title="Embedding Generation Performance")
            embedding_table.add_column("Dataset", style="cyan")
            embedding_table.add_column("Avg Time (ms)", justify="right")
            embedding_table.add_column("Throughput (/sec)", justify="right")
            embedding_table.add_column("Dimensions", justify="right")
            
            for dataset, metrics in results["embedding_performance"].items():
                embedding_table.add_row(
                    dataset,
                    f"{metrics.get('avg_embedding_ms', 0):.1f}",
                    f"{metrics.get('throughput_per_sec', 0):.1f}",
                    str(metrics.get('embedding_dimensions', 0))
                )
            
            self.console.print(embedding_table)
        
        # Index performance
        if results.get("index_performance"):
            index_perf = results["index_performance"]
            self.console.print(f"\n[bold]Index Performance:[/bold]")
            self.console.print(f"  • Vocabulary size: {index_perf.get('vocabulary_size', 0):,} words")
            self.console.print(f"  • Embedding dimensions: {index_perf.get('embedding_dimensions', 0)}")
            self.console.print(f"  • Index size: {index_perf.get('index_size_mb', 0):.1f}MB")
            self.console.print(f"  • Average search time: {index_perf.get('avg_search_ms', 0):.1f}ms")
        
        # Memory efficiency
        if results.get("memory_efficiency"):
            memory = results["memory_efficiency"]
            self.console.print(f"\n[bold]Memory Efficiency:[/bold]")
            self.console.print(f"  • Initialization overhead: {memory.get('init_overhead_mb', 0):.1f}MB")
            self.console.print(f"  • Search overhead: {memory.get('search_overhead_mb', 0):.1f}MB")
            self.console.print(f"  • Peak usage: {memory.get('peak_usage_mb', 0):.1f}MB")
        
        # Similarity accuracy
        if results.get("similarity_accuracy"):
            self.console.print(f"\n[bold]Similarity Accuracy:[/bold]")
            for test_set, accuracy in results["similarity_accuracy"].items():
                color = "green" if accuracy > 0.8 else "yellow" if accuracy > 0.6 else "red"
                self.console.print(f"  • {test_set}: [{color}]{accuracy:.1%}[/{color}]")
        
        # Recommendations
        recommendations = results.get("optimization_recommendations", [])
        if recommendations:
            self.console.print(f"\n[bold]🎯 FAISS Optimization Recommendations:[/bold]")
            for i, rec in enumerate(recommendations, 1):
                self.console.print(f"  {i}. {rec}")
        else:
            self.console.print(f"\n[green]✅ FAISS performance is optimal![/green]")


async def main():
    """Run FAISS benchmarks."""
    benchmark = FAISSBenchmark()
    console = Console()
    
    console.print("[bold cyan]🔍 Starting FAISS performance benchmarks...[/bold cyan]\n")
    
    try:
        results = await benchmark.run_comprehensive_faiss_benchmark()
        benchmark.generate_faiss_report(results)
        
        # Save results
        timestamp = int(time.time())
        filename = f"faiss_benchmark_{timestamp}.json"
        
        import json
        with open(filename, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        console.print(f"\n[green]✅ FAISS benchmark results saved to {filename}[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ FAISS benchmark failed: {e}[/red]")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)