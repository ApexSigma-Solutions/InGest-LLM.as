# InGest-LLM.as Training Guide
# New Team Member Onboarding & Operations Training

## QUICK START GUIDE

Welcome to the ApexSigma InGest-LLM.as service! This guide will get you up and running with file processing operations in 15 minutes.

### Prerequisites Checklist:
- [ ] InGest-LLM.as service running on port 8000
- [ ] memOS.as service running on port 8001
- [ ] PowerShell access to the workspace
- [ ] Basic understanding of REST APIs

### Your First File Processing Session:

#### Step 1: Verify System Status
```powershell
cd C:\Users\steyn\ApexSigmaProjects.Dev\InGest-LLM.as

# Check services are running
curl -X GET "http://localhost:8000/health"
curl -X GET "http://localhost:8001/health"
curl -X GET "http://localhost:8000/omega/status"
```

#### Step 2: Check Current Queue
```powershell
# See what files are waiting to be processed
.\.ingest\process_and_cleanup.ps1 -Action status
```

#### Step 3: Practice File Submission
```powershell
# Create a test file
"This is a test document for training purposes." | Out-File ".ingest/raw_documents/docs/training_test.txt"

# Process it (dry run first)
.\.ingest\process_and_cleanup.ps1 -Action process -Archive -DryRun

# Actually process it
.\.ingest\process_and_cleanup.ps1 -Action process -Archive
```

#### Step 4: Verify Processing
```powershell
# Check that file was processed and archived
.\.ingest\process_and_cleanup.ps1 -Action status

# Verify it's in the knowledge system
curl -X GET "http://localhost:8000/omega/knowledge-domains"
```

## DETAILED TRAINING MODULES

### Module 1: Understanding the File Lifecycle

**Learning Objective**: Understand how files move through the system

```
Raw File → Staging → Processing → Memory Storage → Archive/Cleanup
    ↓         ↓          ↓            ↓              ↓
 .ingest/  Content   Chunking    Multi-tier     .archive/
          Analysis  +Embedding   Storage       or Delete
```

**Hands-On Exercise**:
1. Place different file types in staging directories
2. Observe how content type affects processing
3. Check where content ends up in memory tiers

### Module 2: Content Type Classification

**Learning Objective**: Understand how different content gets processed

| File Type | Extension | Memory Tier | Storage System | Purpose |
|-----------|-----------|-------------|----------------|---------|
| Code | .py, .js, .sql | Procedural (Tier 2) | PostgreSQL+Qdrant | Implementation knowledge |
| Docs | .md, .txt, .pdf | Semantic (Tier 3) | Neo4j | Conceptual knowledge |
| Data | .json, .csv, .xml | Semantic (Tier 3) | Neo4j | Structured information |
| Logs | .log, .out | Episodic (Tier 2) | PostgreSQL+Qdrant | Historical events |

**Practice Exercise**:
```powershell
# Create sample files of each type
"print('Hello World')" | Out-File ".ingest/raw_documents/code/hello.py"
"# Training Documentation" | Out-File ".ingest/raw_documents/docs/training.md"
'{"training": true, "module": 2}' | Out-File ".ingest/raw_documents/data/sample.json"

# Process and observe the results
.\.ingest\process_and_cleanup.ps1 -Action process -Archive
```

### Module 3: API Interaction Patterns

**Learning Objective**: Master the different ingestion endpoints

#### Text Ingestion Endpoint:
```powershell
$content = Get-Content "sample.txt" -Raw
$request = @{
    content = $content
    metadata = @{
        source = "manual"
        content_type = "text"
        title = "Sample Document"
    }
    memory_tier = "SEMANTIC"
    chunk_size = 4000
} | ConvertTo-Json -Depth 10

$request | curl -X POST "http://localhost:8000/ingest/text" -H "Content-Type: application/json" -d "@-"
```

#### Omega Knowledge Graph Ingestion:
```powershell
$knowledgeGraph = @{
    scope = "comprehensive"
    preserve_historical = $true
    generate_poml = $true
} | ConvertTo-Json

$knowledgeGraph | curl -X POST "http://localhost:8000/omega/ingest" -H "Content-Type: application/json" -d "@-"
```

### Module 4: Troubleshooting Common Issues

**Learning Objective**: Diagnose and resolve typical problems

#### Issue: "memOS.as service unavailable"
```powershell
# Diagnosis
curl -X GET "http://localhost:8001/health"

# If down, check Docker containers
docker ps | findstr memos

# Restart if needed
docker-compose restart memos

# Verify recovery
curl -X GET "http://localhost:8001/health"
```

#### Issue: Files stuck in processing queue
```powershell
# Check queue status
.\.ingest\process_and_cleanup.ps1 -Action status

# Review failed files
Get-ChildItem ".ingest/.archive/failed/" -ErrorAction SilentlyContinue

# Retry failed files
Move-Item ".ingest/.archive/failed/*" ".ingest/raw_documents/" -ErrorAction SilentlyContinue
.\.ingest\process_and_cleanup.ps1 -Action process -Archive
```

#### Issue: Processing performance problems
```powershell
# Check system resources
Get-Process | Where-Object {$_.ProcessName -like "*docker*" -or $_.ProcessName -like "*python*"}

# Monitor processing in real-time
.\.ingest\process_and_cleanup.ps1 -Action process -Archive -Verbose
```

### Module 5: Advanced Operations

**Learning Objective**: Perform sophisticated knowledge management tasks

#### Bulk Processing Strategy:
```powershell
# Process in batches to avoid overwhelming the system
$files = Get-ChildItem ".ingest/raw_documents/" -File -Recurse
$batchSize = 10

for ($i = 0; $i -lt $files.Count; $i += $batchSize) {
    $batch = $files[$i..([Math]::Min($i + $batchSize - 1, $files.Count - 1))]
    Write-Host "Processing batch $([Math]::Floor($i / $batchSize) + 1)"
    .\.ingest\process_and_cleanup.ps1 -Action process -Archive
    Start-Sleep -Seconds 5  # Brief pause between batches
}
```

#### Knowledge Graph Maintenance:
```powershell
# Regular knowledge graph updates
$timestamp = Get-Date -Format "yyyyMMdd_HHmm"
$knowledgeSnapshot = @{
    scope = "incremental"
    preserve_historical = $true
    generate_poml = $true
    timestamp = $timestamp
} | ConvertTo-Json

$knowledgeSnapshot | curl -X POST "http://localhost:8000/omega/ingest" -H "Content-Type: application/json" -d "@-"
```

## PRACTICAL EXERCISES

### Exercise 1: Complete File Processing Workflow
**Time**: 10 minutes
**Objective**: Process a mixed set of files end-to-end

```powershell
# Setup
mkdir ".ingest/raw_documents/exercise1"

# Create diverse content
@"
# Project Documentation
This is sample project documentation.
It contains multiple paragraphs and technical information.
"@ | Out-File ".ingest/raw_documents/exercise1/docs.md"

@"
def calculate_metrics(data):
    return sum(data) / len(data)
"@ | Out-File ".ingest/raw_documents/exercise1/code.py"

@"
{"project": "exercise1", "files": 2, "status": "ready"}
"@ | Out-File ".ingest/raw_documents/exercise1/metadata.json"

# Process everything
.\.ingest\process_and_cleanup.ps1 -Action process -Archive

# Verify results
.\.ingest\process_and_cleanup.ps1 -Action status
```

### Exercise 2: Error Recovery Simulation
**Time**: 15 minutes
**Objective**: Practice recovering from processing failures

```powershell
# Create a problematic file (very large or malformed)
"x" * 100000 | Out-File ".ingest/raw_documents/large_file.txt"

# Attempt processing (this may fail)
.\.ingest\process_and_cleanup.ps1 -Action process -Archive

# Check for failures
Get-ChildItem ".ingest/.archive/failed/" -ErrorAction SilentlyContinue

# Implement recovery strategy
# (In real scenarios, you'd fix the file or adjust processing parameters)
```

### Exercise 3: Performance Monitoring
**Time**: 20 minutes
**Objective**: Monitor and optimize processing performance

```powershell
# Create multiple test files
1..20 | ForEach-Object {
    "Test content for file $_" | Out-File ".ingest/raw_documents/test_$_.txt"
}

# Time the processing
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
.\.ingest\process_and_cleanup.ps1 -Action process -Archive
$stopwatch.Stop()

Write-Host "Processing time: $($stopwatch.Elapsed.TotalSeconds) seconds"
Write-Host "Files per second: $(20 / $stopwatch.Elapsed.TotalSeconds)"
```

## KNOWLEDGE CHECK

### Quiz Questions:
1. What are the three main memory tiers and what type of content goes in each?
2. What's the difference between the `/ingest/text` and `/omega/ingest` endpoints?
3. How do you recover files that failed processing?
4. What's the purpose of the `.archive` directory?
5. How do you perform a dry run to preview processing results?

### Practical Assessment:
1. Process a Python file and verify it ends up in Procedural memory
2. Upload a knowledge graph via the Omega endpoint
3. Recover from a simulated service failure
4. Implement a custom batch processing strategy

## REFERENCE CARDS

### Quick Command Reference:
```powershell
# Essential commands for daily operations
.\.ingest\process_and_cleanup.ps1 -Action status              # Check queue
.\.ingest\process_and_cleanup.ps1 -Action process -Archive    # Process files
.\.ingest\process_and_cleanup.ps1 -Action cleanup             # Manual cleanup
curl -X GET "http://localhost:8000/health"                    # Service health
curl -X GET "http://localhost:8000/omega/status"              # Guardian status
```

### File Type Quick Reference:
- **Code files (.py, .js, .sql)** → Procedural Memory (Tier 2)
- **Documentation (.md, .txt, .pdf)** → Semantic Memory (Tier 3)
- **Data files (.json, .csv, .xml)** → Semantic Memory (Tier 3)
- **Log files (.log, .out)** → Episodic Memory (Tier 2)

### Troubleshooting Quick Reference:
- **Service unavailable** → Check Docker containers
- **Processing stuck** → Check queue status and system resources
- **Files failed** → Review `.archive/failed/` and retry
- **Performance slow** → Use batch processing and monitor resources

---

**Training Module Version**: 1.0
**Duration**: 2-3 hours (all modules)
**Prerequisites**: Basic PowerShell and API knowledge
**Certification**: Complete all exercises and pass knowledge check
**Next Steps**: Advanced Integration Training (Agent Society, Cross-Service Workflows)
