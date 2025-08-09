#!/usr/bin/env python3
"""
Comprehensive Fuzzing Test Suite for Search Quality Analysis

Tests fuzzy and semantic search across different error categories to tune 
implementation without overfitting to specific cases.
"""

import asyncio
import json
import statistics
import time
from dataclasses import dataclass
from enum import Enum

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

class ErrorCategory(Enum):
    """Error severity categories for systematic testing"""
    EXACT = "exact"           # Perfect matches
    MINIMAL = "minimal"       # 1-2 character errors  
    MODERATE = "moderate"     # 3-4 character errors
    HIGH = "high"            # 5-6 character errors
    EXTREME = "extreme"       # 7+ character errors, should fail
    SEMANTIC = "semantic"     # Meaning-preserving alternatives

@dataclass
class TestCase:
    """Individual test case with expected behavior"""
    query: str
    expected_word: str
    category: ErrorCategory
    should_find: bool
    description: str
    min_score: float = 0.0
    max_position: int = 5  # Should appear in top 5 results

@dataclass
class SearchResult:
    """Search result for analysis"""
    word: str
    score: float
    method: str
    position: int

@dataclass
class TestResult:
    """Test case execution result"""
    test_case: TestCase
    found: bool
    result: SearchResult | None
    all_results: list[SearchResult]
    fuzzy_time_ms: float
    semantic_time_ms: float

# Comprehensive test cases covering French phrases and challenging English words
TEST_CASES = [
    # === FRENCH PHRASES - EXACT ===
    TestCase("mise en place", "mise en place", ErrorCategory.EXACT, True, "Perfect French phrase"),
    TestCase("raison d'être", "raison d'être", ErrorCategory.EXACT, True, "Perfect French phrase with diacritic"),
    TestCase("joie de vivre", "joie de vivre", ErrorCategory.EXACT, True, "Perfect French phrase"),
    TestCase("a fond", "à fond", ErrorCategory.EXACT, True, "Perfect French phrase - short (with diacritic)"),
    TestCase("en coulisse", "en coulisse", ErrorCategory.EXACT, True, "Perfect French phrase - corrected spelling"),
    TestCase("recueillement", "recueillement", ErrorCategory.EXACT, True, "Perfect French word - long"),
    
    # === FRENCH PHRASES - MINIMAL ERRORS (1-2 chars) ===
    TestCase("mise en plase", "mise en place", ErrorCategory.MINIMAL, True, "French: single letter substitution", min_score=0.8),
    TestCase("mize en place", "mise en place", ErrorCategory.MINIMAL, True, "French: single letter substitution", min_score=0.8),
    TestCase("raison detre", "raison d'être", ErrorCategory.MINIMAL, True, "French: missing apostrophe", min_score=0.8),
    TestCase("razon detre", "raison d'être", ErrorCategory.MINIMAL, True, "French: substitution + missing apostrophe", min_score=0.7),
    TestCase("joi de vivre", "joie de vivre", ErrorCategory.MINIMAL, True, "French: missing letter", min_score=0.8),
    TestCase("a fon", "à fond", ErrorCategory.MINIMAL, True, "French: missing final letter", min_score=0.8),
    TestCase("en couliss", "en coulisse", ErrorCategory.MINIMAL, True, "French: missing final letter", min_score=0.8),
    TestCase("recueilment", "recueillement", ErrorCategory.MINIMAL, True, "French: missing double letter", min_score=0.8),
    
    # === FRENCH PHRASES - MODERATE ERRORS (3-4 chars) ===
    TestCase("mize en plase", "mise en place", ErrorCategory.MODERATE, True, "French: multiple substitutions", min_score=0.7),
    TestCase("razon detere", "raison d'être", ErrorCategory.MODERATE, True, "French: multiple errors", min_score=0.6),
    TestCase("joye de vivr", "joie de vivre", ErrorCategory.MODERATE, True, "French: multiple errors", min_score=0.6),
    TestCase("en couliss", "en coulisse", ErrorCategory.MODERATE, True, "French: missing final letter", min_score=0.7),
    TestCase("recueilmnt", "recueillement", ErrorCategory.MODERATE, True, "French: missing vowels", min_score=0.6),
    
    # === FRENCH PHRASES - HIGH ERRORS (5-6 chars) ===
    TestCase("mizz en plase", "mise en place", ErrorCategory.HIGH, False, "French: too many errors", max_position=10),
    TestCase("razoon deteer", "raison d'etre", ErrorCategory.HIGH, False, "French: too many errors"),
    TestCase("joyyy de vivvr", "joie de vivre", ErrorCategory.HIGH, False, "French: too many errors"),
    TestCase("en coulissee", "en coulisse", ErrorCategory.HIGH, True, "French: borderline recoverable", min_score=0.5, max_position=10),
    
    # === ENGLISH CHALLENGING WORDS - MINIMAL ===
    TestCase("definatly", "definitely", ErrorCategory.MINIMAL, True, "English: common misspelling", min_score=0.7),
    TestCase("seperate", "separate", ErrorCategory.MINIMAL, True, "English: common misspelling", min_score=0.8),
    TestCase("necesary", "necessary", ErrorCategory.MINIMAL, True, "English: missing double letter", min_score=0.7),
    TestCase("occured", "occurred", ErrorCategory.MINIMAL, True, "English: missing double letter", min_score=0.8),
    TestCase("recieve", "receive", ErrorCategory.MINIMAL, True, "English: i-e confusion", min_score=0.8),
    TestCase("embarass", "embarrass", ErrorCategory.MINIMAL, True, "English: missing double letter", min_score=0.7),
    
    # === ENGLISH CHALLENGING WORDS - MODERATE ===
    TestCase("definatley", "definitely", ErrorCategory.MODERATE, True, "English: multiple errors", min_score=0.6),
    TestCase("sepparate", "separate", ErrorCategory.MODERATE, True, "English: wrong double letter", min_score=0.6),
    TestCase("necesssary", "necessary", ErrorCategory.MODERATE, True, "English: wrong double letter", min_score=0.6),
    TestCase("recieveing", "receiving", ErrorCategory.MODERATE, True, "English: multiple errors", min_score=0.6),
    TestCase("embarrasing", "embarrassing", ErrorCategory.MODERATE, True, "English: double letter + suffix", min_score=0.6),
    
    # === EXTREME ERRORS - SHOULD FAIL ===
    TestCase("xqzwerty", "definitely", ErrorCategory.EXTREME, False, "Random characters - should fail"),
    TestCase("abcdefgh", "mise en place", ErrorCategory.EXTREME, False, "No similarity - should fail"),
    TestCase("zzzzz", "necessary", ErrorCategory.EXTREME, False, "Repeated char - should fail"),
    TestCase("mise place en", "mise en place", ErrorCategory.EXTREME, False, "Wrong word order - should fail"),
    
    # === SEMANTIC ALTERNATIVES ===
    TestCase("setup", "mise en place", ErrorCategory.SEMANTIC, True, "Semantic: English equivalent", min_score=0.3, max_position=10),
    TestCase("reason for being", "raison d'être", ErrorCategory.SEMANTIC, True, "Semantic: English translation", min_score=0.3, max_position=10),
    TestCase("joy of living", "joie de vivre", ErrorCategory.SEMANTIC, True, "Semantic: English translation", min_score=0.3, max_position=10),
    TestCase("backstage", "en coulisse", ErrorCategory.SEMANTIC, True, "Semantic: English equivalent", min_score=0.3, max_position=10),
    TestCase("contemplation", "recueillement", ErrorCategory.SEMANTIC, True, "Semantic: English equivalent", min_score=0.3, max_position=10),
]

class SearchTester:
    """Comprehensive search testing framework"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_search_mode(self, query: str, mode: str) -> tuple[list[SearchResult], float]:
        """Test a single search mode and return results with timing"""
        start_time = time.perf_counter()
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/search",
                params={"q": query, "mode": mode, "max_results": 20}
            )
            response.raise_for_status()
            data = response.json()
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            results = []
            for i, result in enumerate(data.get("results", [])):
                results.append(SearchResult(
                    word=result["word"],
                    score=result["score"],
                    method=result["method"],
                    position=i + 1
                ))
            
            return results, elapsed_ms
            
        except Exception as e:
            console.print(f"[red]Error testing {mode} for '{query}': {e}[/red]")
            return [], (time.perf_counter() - start_time) * 1000
    
    async def run_test_case(self, test_case: TestCase) -> TestResult:
        """Run a single test case across fuzzy and semantic modes"""
        
        # Test fuzzy search
        fuzzy_results, fuzzy_time = await self.test_search_mode(test_case.query, "fuzzy")
        
        # Test semantic search for semantic test cases
        if test_case.category == ErrorCategory.SEMANTIC:
            # Skip semantic search for now (disabled in backend)
            semantic_results, semantic_time = [], 0.0
            primary_results = semantic_results
        else:
            semantic_results, semantic_time = [], 0.0
            primary_results = fuzzy_results
        
        # Check if expected word was found
        found_result = None
        for result in primary_results:
            if result.word.lower() == test_case.expected_word.lower():
                if (result.score >= test_case.min_score and 
                    result.position <= test_case.max_position):
                    found_result = result
                    break
        
        found = found_result is not None
        
        return TestResult(
            test_case=test_case,
            found=found,
            result=found_result,
            all_results=primary_results[:10],  # Top 10 for analysis
            fuzzy_time_ms=fuzzy_time,
            semantic_time_ms=semantic_time
        )
    
    async def run_all_tests(self) -> list[TestResult]:
        """Run all test cases with progress tracking"""
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Running fuzzing tests...", total=len(TEST_CASES))
            
            for i, test_case in enumerate(TEST_CASES):
                progress.update(task, description=f"Testing: {test_case.query[:30]}...")
                result = await self.run_test_case(test_case)
                results.append(result)
                progress.advance(task)
        
        return results
    
    async def close(self):
        """Clean up resources"""
        await self.client.aclose()

def analyze_results(results: list[TestResult]) -> dict:
    """Comprehensive analysis of test results"""
    
    # Group by category
    by_category = {}
    for result in results:
        category = result.test_case.category.value
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(result)
    
    # Calculate statistics
    analysis = {
        "overall": {
            "total_tests": len(results),
            "passed": sum(1 for r in results if r.found == r.test_case.should_find),
            "failed": sum(1 for r in results if r.found != r.test_case.should_find),
            "accuracy": 0.0,
            "avg_fuzzy_time_ms": statistics.mean(r.fuzzy_time_ms for r in results),
            "avg_semantic_time_ms": statistics.mean(r.semantic_time_ms for r in results if r.semantic_time_ms > 0) if any(r.semantic_time_ms > 0 for r in results) else 0,
        },
        "by_category": {},
        "failures": [],
        "edge_cases": []
    }
    
    analysis["overall"]["accuracy"] = analysis["overall"]["passed"] / analysis["overall"]["total_tests"]
    
    # Per-category analysis
    for category, cat_results in by_category.items():
        passed = sum(1 for r in cat_results if r.found == r.test_case.should_find)
        total = len(cat_results)
        
        avg_score = 0.0
        avg_position = 0.0
        score_count = 0
        
        for r in cat_results:
            if r.found and r.result:
                avg_score += r.result.score
                avg_position += r.result.position
                score_count += 1
        
        analysis["by_category"][category] = {
            "total": total,
            "passed": passed,
            "accuracy": passed / total if total > 0 else 0,
            "avg_score": avg_score / score_count if score_count > 0 else 0,
            "avg_position": avg_position / score_count if score_count > 0 else 0,
        }
    
    # Collect failures and interesting edge cases
    for result in results:
        if result.found != result.test_case.should_find:
            analysis["failures"].append({
                "query": result.test_case.query,
                "expected": result.test_case.expected_word,
                "category": result.test_case.category.value,
                "should_find": result.test_case.should_find,
                "actually_found": result.found,
                "top_results": [r.word for r in result.all_results[:3]]
            })
        
        # Edge cases: barely passing or failing
        if result.found and result.result and result.result.score < 0.7:
            analysis["edge_cases"].append({
                "query": result.test_case.query,
                "expected": result.test_case.expected_word,
                "score": result.result.score,
                "position": result.result.position
            })
    
    return analysis

def display_results(results: list[TestResult], analysis: dict):
    """Display comprehensive test results"""
    
    console.print("\n[bold blue]🧪 FUZZING TEST RESULTS[/bold blue]")
    console.print("=" * 60)
    
    # Overall statistics
    overall = analysis["overall"]
    console.print("\n[bold]Overall Performance:[/bold]")
    console.print(f"  Total Tests: {overall['total_tests']}")
    console.print(f"  Passed: [green]{overall['passed']}[/green]")
    console.print(f"  Failed: [red]{overall['failed']}[/red]")
    console.print(f"  Accuracy: [cyan]{overall['accuracy']:.1%}[/cyan]")
    console.print(f"  Avg Fuzzy Time: {overall['avg_fuzzy_time_ms']:.1f}ms")
    if overall['avg_semantic_time_ms'] > 0:
        console.print(f"  Avg Semantic Time: {overall['avg_semantic_time_ms']:.1f}ms")
    
    # Category breakdown
    console.print("\n[bold]Performance by Error Category:[/bold]")
    
    table = Table()
    table.add_column("Category", style="cyan")
    table.add_column("Tests", justify="center")
    table.add_column("Passed", justify="center")
    table.add_column("Accuracy", justify="center")
    table.add_column("Avg Score", justify="center")
    table.add_column("Avg Position", justify="center")
    
    for category, stats in analysis["by_category"].items():
        accuracy_color = "green" if stats['accuracy'] >= 0.8 else "yellow" if stats['accuracy'] >= 0.6 else "red"
        table.add_row(
            category.title(),
            str(stats['total']),
            str(stats['passed']),
            f"[{accuracy_color}]{stats['accuracy']:.1%}[/{accuracy_color}]",
            f"{stats['avg_score']:.3f}" if stats['avg_score'] > 0 else "N/A",
            f"{stats['avg_position']:.1f}" if stats['avg_position'] > 0 else "N/A"
        )
    
    console.print(table)
    
    # Failures analysis
    if analysis["failures"]:
        console.print(f"\n[bold red]❌ FAILURES ({len(analysis['failures'])} total):[/bold red]")
        for i, failure in enumerate(analysis["failures"][:10]):  # Show top 10
            console.print(f"  {i+1}. [red]'{failure['query']}'[/red] → expected '{failure['expected']}' ({failure['category']})")
            if failure['top_results']:
                console.print(f"     Got instead: {', '.join(failure['top_results'][:3])}")
    
    # Edge cases
    if analysis["edge_cases"]:
        console.print(f"\n[bold yellow]⚠️ EDGE CASES ({len(analysis['edge_cases'])} total):[/bold yellow]")
        for i, edge in enumerate(analysis["edge_cases"][:5]):  # Show top 5
            console.print(f"  {i+1}. [yellow]'{edge['query']}'[/yellow] → '{edge['expected']}' (score: {edge['score']:.3f}, pos: {edge['position']})")

async def main():
    """Main fuzzing test execution"""
    console.print("[bold blue]🚀 Starting Comprehensive Search Fuzzing Test Suite[/bold blue]")
    
    tester = SearchTester()
    
    try:
        # Run all tests
        results = await tester.run_all_tests()
        
        # Analyze results
        analysis = analyze_results(results)
        
        # Display results
        display_results(results, analysis)
        
        # Save detailed results
        output_file = f"fuzzing_results_{int(time.time())}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "results": [
                    {
                        "query": r.test_case.query,
                        "expected": r.test_case.expected_word,
                        "category": r.test_case.category.value,
                        "should_find": r.test_case.should_find,
                        "found": r.found,
                        "score": r.result.score if r.result else 0,
                        "position": r.result.position if r.result else -1,
                        "fuzzy_time_ms": r.fuzzy_time_ms,
                        "semantic_time_ms": r.semantic_time_ms,
                        "top_results": [res.word for res in r.all_results[:5]]
                    } for r in results
                ],
                "analysis": analysis
            }, f, indent=2)
        
        console.print(f"\n[green]✅ Detailed results saved to: {output_file}[/green]")
        
        # Performance tuning recommendations
        console.print("\n[bold]🔧 TUNING RECOMMENDATIONS:[/bold]")
        
        if analysis["by_category"].get("minimal", {}).get("accuracy", 0) < 0.9:
            console.print("  • Consider lowering character overlap threshold for minimal errors")
        
        if analysis["by_category"].get("moderate", {}).get("accuracy", 0) < 0.7:
            console.print("  • Consider increasing dynamic character difference threshold")
        
        if analysis["by_category"].get("extreme", {}).get("accuracy", 0) < 0.8:
            console.print("  • Check if extreme error rejection is working correctly")
        
        if analysis["by_category"].get("semantic", {}).get("accuracy", 0) < 0.6:
            console.print("  • Semantic search may need embedding model tuning")
        
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())