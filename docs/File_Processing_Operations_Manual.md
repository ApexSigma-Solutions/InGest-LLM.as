# InGest-LLM.as File Processing Strategy & Operations Manual
# Version 2.0 - August 26, 2025
#
# COMPREHENSIVE GUIDE FOR APEXSIGMA ECOSYSTEM FILE INGESTION
# This document serves as the definitive reference for file processing
# workflows, training materials, and operational procedures.

## EXECUTIVE SUMMARY

The InGest-LLM.as service implements a sophisticated file lifecycle management system
that transforms raw documents into searchable, queryable knowledge distributed across
specialized memory tiers. This manual documents the complete process for future
reference and team training.

## SYSTEM ARCHITECTURE

### Core Components:
1. **InGest-LLM.as Service** (Port 8000) - Main ingestion pipeline
2. **Omega Ingest Guardian v8.0** - Master knowledge graph processor
3. **memOS.as Service** (Port 8001) - Multi-tier memory storage
4. **Processing Scripts** - Automated file lifecycle management

### Memory Tier Architecture:
- **Tier 1 (Working Memory)**: Redis - Active processing, temporary storage
- **Tier 2 (Episodic/Procedural)**: PostgreSQL + Qdrant - Code, events, structured data
- **Tier 3 (Semantic Memory)**: Neo4j - Concepts, relationships, knowledge graphs

## FILE PROCESSING WORKFLOW

### Phase 1: Staging (.ingest Directory)
```
Location: C:\Users\steyn\ApexSigmaProjects.Dev\InGest-LLM.as\.ingest\

Structure:
├── raw_documents/              # STAGING AREA - Unprocessed files only
│   ├── text/                  # Text documents, logs, notes
│   ├── code/                  # Source code, scripts, configs
│   ├── docs/                  # Documentation, manuals, specs
│   └── data/                  # JSON, CSV, structured data
├── .archive/                  # POST-PROCESSING STORAGE
│   ├── processed/             # Successfully ingested files
│   └── failed/                # Failed processing attempts
├── process_and_cleanup.ps1    # Automation script
├── .ingest_config            # Configuration settings
└── [master knowledge graphs]  # POML/JSON knowledge datasets
```

### Phase 2: Content Analysis & Processing
1. **File Detection**: Automatic content type identification
2. **Chunking**: Default 4000-character chunks with overlap
3. **Embedding Generation**: Vector embeddings for semantic search
4. **Memory Tier Assignment**: Based on content type and purpose
5. **Storage Distribution**: Across appropriate memory systems

### Phase 3: Storage & Indexing
```
Content Type → Memory Tier → Storage System → Access Method

Code Files → Procedural (Tier 2) → PostgreSQL+Qdrant → Vector/Text Search
Documentation → Semantic (Tier 3) → Neo4j → Graph Traversal
Events/Logs → Episodic (Tier 2) → PostgreSQL+Qdrant → Chronological Query
Active Data → Working (Tier 1) → Redis → Real-time Access
```

### Phase 4: Cleanup & Archival
- **Success**: File moved to `.archive/processed/` or deleted (configurable)
- **Failure**: File moved to `.archive/failed/` for retry
- **Monitoring**: Processing logs and metrics tracked

## OPERATIONAL PROCEDURES

### Daily Operations:
```powershell
# 1. Check processing queue status
.\.ingest\process_and_cleanup.ps1 -Action status

# 2. Process pending files (with archival)
.\.ingest\process_and_cleanup.ps1 -Action process -Archive

# 3. Verify system health
curl -X GET "http://localhost:8000/health"
curl -X GET "http://localhost:8000/omega/status"
```

### File Submission Process:
```powershell
# Step 1: Place files in appropriate staging directories
Copy-Item "source_file.py" ".ingest/raw_documents/code/"
Copy-Item "documentation.md" ".ingest/raw_documents/docs/"

# Step 2: Run processing
.\.ingest\process_and_cleanup.ps1 -Action process -Archive

# Step 3: Verify ingestion
curl -X GET "http://localhost:8000/omega/knowledge-domains"
```

### Bulk Knowledge Graph Upload:
```powershell
# For POML/JSON knowledge graphs
$content = Get-Content ".ingest/knowledge_graph.json" -Raw
$request = @{ scope = "comprehensive"; preserve_historical = $true } | ConvertTo-Json
$request | curl -X POST "http://localhost:8000/omega/ingest" -H "Content-Type: application/json" -d "@-"
```

## API ENDPOINTS REFERENCE

### Primary Ingestion Endpoints:
1. **Text/Document Processing**: `POST /ingest/text`
2. **Repository Analysis**: `POST /ingest/python-repo`
3. **Master Knowledge Ingestion**: `POST /omega/ingest`

### Monitoring Endpoints:
1. **Service Health**: `GET /health`
2. **Omega Status**: `GET /omega/status`
3. **Knowledge Domains**: `GET /omega/knowledge-domains`

### Query Endpoints (memOS.as):
1. **Memory Search**: `GET /memory/{tier}/search`
2. **Content Retrieval**: `GET /memory/{tier}/content/{id}`
3. **Relationship Queries**: `GET /graph/relationships`

## CONFIGURATION MANAGEMENT

### Processing Configuration (.ingest_config):
```
ARCHIVE_PROCESSED_FILES=true     # Archive vs delete processed files
KEEP_FAILED_FILES=true          # Retain failed files for retry
AUTO_CLEANUP_DAYS=30            # Archive retention period
MAX_RAW_DOCUMENTS=100           # Alert threshold
BATCH_SIZE=10                   # Processing batch size
RETRY_FAILED_FILES=true         # Automatic retry capability
```

### Service Configuration:
- **InGest-LLM**: Port 8000, chunking, embedding generation
- **memOS**: Port 8001, multi-tier storage, graph relationships
- **Omega Guardian**: v8.0, POML processing, knowledge synthesis

## TROUBLESHOOTING GUIDE

### Common Issues:

1. **"memOS.as service unavailable"**
   - Check memOS service status: `curl http://localhost:8001/health`
   - Restart if needed: `docker-compose restart memos`
   - Use Omega endpoint as fallback

2. **Processing Fails with Large Files**
   - Check file size limits in configuration
   - Consider pre-chunking large documents
   - Use batch processing for multiple files

3. **Incomplete Processing Status**
   - Verify all services are running
   - Check network connectivity between services
   - Review processing logs for specific errors

4. **Storage Tier Misassignment**
   - Review content type detection logic
   - Manually specify memory tier in requests
   - Update tier mapping configuration

### Recovery Procedures:

1. **Failed Processing Recovery**:
```powershell
# Move failed files back to staging
Move-Item ".archive/failed/*" ".ingest/raw_documents/"
# Retry processing
.\.ingest\process_and_cleanup.ps1 -Action process -Archive
```

2. **Data Consistency Check**:
```powershell
# Verify storage integrity
curl -X GET "http://localhost:8001/health"
curl -X GET "http://localhost:8000/omega/knowledge-domains"
```

## PERFORMANCE OPTIMIZATION

### Best Practices:
1. **Batch Processing**: Process files in groups rather than individually
2. **Async Operations**: Use background processing for large files
3. **Resource Monitoring**: Track memory and CPU usage during processing
4. **Storage Cleanup**: Regular archival of old processed files

### Scaling Considerations:
- **Horizontal Scaling**: Multiple InGest-LLM instances behind load balancer
- **Storage Optimization**: Separate read/write replicas for memory tiers
- **Caching Strategy**: Redis optimization for frequently accessed content

## TRAINING MATERIALS

### New Team Member Onboarding:
1. **System Overview**: Review architecture diagram and data flow
2. **Hands-On Practice**: Process sample files through complete workflow
3. **Troubleshooting Scenarios**: Practice common issue resolution
4. **API Familiarization**: Test all endpoints with sample data

### Advanced Operations Training:
1. **POML Processing**: Understanding knowledge graph structures
2. **Memory Tier Optimization**: Content classification and storage strategy
3. **Performance Tuning**: Monitoring and optimization techniques
4. **Integration Patterns**: Connecting with other ApexSigma services

## MONITORING & METRICS

### Key Performance Indicators:
- **Processing Throughput**: Files processed per hour
- **Success Rate**: Percentage of successful ingestions
- **Storage Efficiency**: Memory utilization across tiers
- **Query Performance**: Response times for content retrieval

### Alerting Thresholds:
- **Queue Backup**: >50 files in raw_documents
- **Processing Failures**: >10% failure rate
- **Storage Limits**: >80% capacity in any tier
- **Service Availability**: <99% uptime

## FUTURE ENHANCEMENTS

### Planned Improvements:
1. **Intelligent Content Classification**: ML-based content type detection
2. **Automated Quality Scoring**: Content relevance and accuracy metrics
3. **Real-time Processing**: Streaming ingestion for live data sources
4. **Advanced Relationship Mapping**: Enhanced semantic linking

### Integration Roadmap:
1. **Agent Society Integration**: Direct agent-to-ingestion workflows
2. **Cross-Service Knowledge Sharing**: Unified knowledge graph across services
3. **External Data Sources**: API connectors for external content
4. **Federated Search**: Cross-tier unified query interface

## SECURITY & COMPLIANCE

### Data Protection:
- **Content Encryption**: At-rest and in-transit encryption
- **Access Controls**: Role-based access to different memory tiers
- **Audit Logging**: Complete processing history tracking
- **Data Retention**: Configurable retention policies per content type

### Compliance Requirements:
- **Data Lineage**: Full traceability from source to storage
- **Content Validation**: Integrity checking and verification
- **Privacy Protection**: PII detection and handling
- **Backup & Recovery**: Disaster recovery procedures

---

## APPENDIX: COMMAND REFERENCE

### Quick Commands:
```powershell
# Status check
.\.ingest\process_and_cleanup.ps1 -Action status

# Process files with archival
.\.ingest\process_and_cleanup.ps1 -Action process -Archive

# Dry run (preview mode)
.\.ingest\process_and_cleanup.ps1 -Action process -Archive -DryRun

# Manual cleanup
.\.ingest\process_and_cleanup.ps1 -Action cleanup

# Service health checks
curl -X GET "http://localhost:8000/health"
curl -X GET "http://localhost:8001/health"
curl -X GET "http://localhost:8000/omega/status"

# Knowledge graph upload
$content = Get-Content "knowledge_graph.json" -Raw
@{ scope = "comprehensive" } | ConvertTo-Json | curl -X POST "http://localhost:8000/omega/ingest" -H "Content-Type: application/json" -d "@-"
```

---
**Document Version**: 2.0
**Last Updated**: August 26, 2025
**Maintained By**: ApexSigma Operations Team
**Next Review**: September 26, 2025
