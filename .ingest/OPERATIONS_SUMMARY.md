# InGest-LLM.as Operations Summary
# Quick Reference for File Processing Strategy

## SYSTEM STATUS CHECK
```powershell
cd C:\Users\steyn\ApexSigmaProjects.Dev\InGest-LLM.as
.\.ingest\process_and_cleanup.ps1 -Action status
curl -X GET "http://localhost:8000/omega/status"
```

## DAILY OPERATIONS WORKFLOW

### 1. Morning Health Check
- Verify all services are running (InGest-LLM:8000, memOS:8001)
- Check processing queue status
- Review any overnight processing failures

### 2. File Processing
- Place new files in `.ingest/raw_documents/` subdirectories
- Run processing script with archival: `process_and_cleanup.ps1 -Action process -Archive`
- Monitor results and handle any failures

### 3. Knowledge Graph Maintenance
- Upload new master knowledge graphs via Omega endpoint
- Verify knowledge domains are updated
- Archive processed knowledge datasets

## DIRECTORY STRUCTURE MAINTAINED
```
.ingest/
├── raw_documents/          # ACTIVE: Unprocessed files only
│   ├── text/              # Text documents
│   ├── code/              # Source code
│   ├── docs/              # Documentation
│   └── data/              # Structured data
├── .archive/              # HISTORICAL: Processed files
│   ├── processed/         # Success archive
│   └── failed/           # Retry queue
└── process_and_cleanup.ps1 # Automation
```

## PROCESSING ENDPOINTS
- **Text/Documents**: `POST /ingest/text` → Multi-tier memory storage
- **Knowledge Graphs**: `POST /omega/ingest` → Master knowledge synthesis
- **Repositories**: `POST /ingest/python-repo` → Code analysis pipeline

## RESOURCE MANAGEMENT ACHIEVED
✅ **No dormant files**: Only unprocessed files remain in staging
✅ **Automated cleanup**: Successful processing triggers archival/removal
✅ **Failure recovery**: Failed files moved to retry queue
✅ **Performance monitoring**: Processing metrics tracked
✅ **Documentation complete**: Full operational manual created

## TEAM TRAINING RESOURCES
- **Operations Manual**: `docs/File_Processing_Operations_Manual.md`
- **Training Guide**: `docs/Training_Guide.md`
- **This Summary**: Quick daily reference

---
**Strategy Implementation**: COMPLETE ✅
**Documentation Status**: COMPREHENSIVE ✅
**Team Training**: READY ✅
