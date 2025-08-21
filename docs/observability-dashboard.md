# Embedding Model Efficiency Dashboard

This document outlines the comprehensive observability setup for tracking and comparing embedding model performance in InGest-LLM.as using Langfuse.

## 🎯 Key Metrics Tracked

### Embedding Model Performance
- **Model Selection Quality**: Track which models are chosen for different content types
- **Processing Speed**: Characters/second and embeddings/second for each model
- **Batch Efficiency**: Performance comparison between single vs batch embedding generation
- **Error Rates**: Track failures and connection issues per model
- **Dimension Consistency**: Ensure embedding dimensions meet expectations

### AST Parser Efficiency
- **Parsing Success Rate**: Success/failure ratio for Python code parsing
- **Elements Extraction Speed**: Elements per second processing rate
- **Code Complexity Analysis**: Average complexity scores and processing impact
- **Chunking Efficiency**: Time spent converting AST elements to searchable content

### Content Type Detection
- **Detection Accuracy**: Confidence scores for content type identification
- **Method Reliability**: Effectiveness of file extension vs content analysis
- **Detection Speed**: Time spent on content type classification

## 📊 Langfuse Trace Structure

### Embedding Generation Traces
```
embedding_generation
├── model_selection (generation)
├── api_call_timing
└── scores:
    ├── embedding_performance (0-1)
    ├── embedding_efficiency (normalized chars/sec)
    └── model_efficiency_{model_name} (model-specific)
```

### Batch Processing Traces
```
batch_embedding_generation
├── batch_statistics
├── model_selection
├── api_timing
└── scores:
    ├── batch_embedding_performance (0-1)
    ├── batch_embedding_efficiency (emb/sec)
    └── model_efficiency_{model_name} (model-specific)
```

### AST Processing Traces
```
python_ast_processing
├── ast_parsing (generation)
├── chunking_processing
├── embedding_generation (nested trace)
└── scores:
    ├── ast_parsing_success (0 or 1)
    ├── python_processing_efficiency (elements/sec)
    └── code_complexity_score (inverse complexity)
```

### Content Detection Traces
```
content_type_detection
├── file_extension_analysis
├── content_pattern_analysis
└── scores:
    ├── content_type_confidence (0-1)
    └── detection_method_reliability (0-1)
```

## 🔍 Model Comparison Queries

### Top Performing Models by Speed
```sql
-- Langfuse Analytics Query
SELECT 
    metadata->>'model_used' as model,
    AVG(output->>'chars_per_second'::float) as avg_chars_per_second,
    AVG(scores.embedding_efficiency) as avg_efficiency,
    COUNT(*) as total_calls,
    AVG(output->>'total_duration_ms'::float) as avg_duration_ms
FROM traces 
WHERE name = 'embedding_generation' 
    AND output->>'success' = 'true'
    AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY metadata->>'model_used'
ORDER BY avg_efficiency DESC;
```

### Model Effectiveness by Content Type
```sql
-- Model performance segmented by content type
SELECT 
    metadata->>'content_type' as content_type,
    metadata->>'model_used' as model,
    AVG(scores.embedding_performance) as avg_performance,
    AVG(output->>'chars_per_second'::float) as avg_speed,
    COUNT(*) as usage_count
FROM traces 
WHERE name = 'embedding_generation'
    AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY metadata->>'content_type', metadata->>'model_used'
ORDER BY content_type, avg_performance DESC;
```

### Batch vs Single Processing Efficiency
```sql
-- Compare batch vs single embedding generation
SELECT 
    CASE 
        WHEN name = 'batch_embedding_generation' THEN 'batch'
        ELSE 'single'
    END as processing_type,
    AVG(scores.embedding_efficiency) as avg_efficiency,
    AVG(output->>'embeddings_per_second'::float) as avg_emb_per_sec,
    COUNT(*) as total_operations
FROM traces 
WHERE name IN ('embedding_generation', 'batch_embedding_generation')
    AND output->>'success' = 'true'
    AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY processing_type;
```

### AST Parser Performance Analysis
```sql
-- AST parsing efficiency and complexity insights
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    AVG(output->>'total_elements'::int) as avg_elements_extracted,
    AVG(output->>'efficiency_metrics'->>'elements_per_second'::float) as avg_elements_per_sec,
    AVG(scores.code_complexity_score) as avg_complexity_score,
    COUNT(*) as parsing_operations
FROM traces 
WHERE name = 'python_ast_processing'
    AND output->>'ast_parsing_success' = 'true'
    AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour;
```

## 📈 Performance Benchmarks

### Expected Performance Targets
- **nomic-embed-text-v1.5**: 800-1200 chars/second
- **nomic-embed-code-v1**: 600-1000 chars/second (due to code complexity)
- **Batch Processing**: 20-50 embeddings/second
- **AST Parsing**: 5-15 elements/second
- **Content Detection**: <10ms per detection

### Alert Thresholds
- **Embedding Performance < 0.5**: Model selection or API issues
- **Batch Efficiency < 10 emb/sec**: Potential batch size optimization needed
- **AST Parsing Success Rate < 90%**: Review Python code complexity or parser robustness
- **Content Detection Confidence < 0.6**: May need improved detection patterns

## 🚨 Monitoring Alerts

### Performance Degradation
```
embedding_efficiency < 0.3 AND error_rate > 5%
```

### Model Selection Issues
```
model_selection_quality < 0.5 AND content_type IN ('code', 'python')
```

### AST Parser Problems
```
ast_parsing_success_rate < 0.9 AND python_processing_volume > 10/hour
```

## 📊 Dashboard Widgets

### Real-time Model Performance
- **Embedding Speed by Model**: Live chart showing chars/second
- **Model Usage Distribution**: Pie chart of model selection frequency
- **Error Rate by Model**: Bar chart of failure percentages
- **Batch vs Single Efficiency**: Comparative speed metrics

### Content Processing Insights
- **Content Type Detection Accuracy**: Confidence score trends
- **AST Elements Extracted**: Volume and complexity trends
- **Processing Pipeline Duration**: End-to-end timing breakdown

### Efficiency Comparison
- **Model Efficiency Heatmap**: Performance across content types
- **Processing Speed Trends**: Historical performance over time
- **Resource Utilization**: API call patterns and batch optimization

## 🔧 Configuration for Maximum Insight

### Environment Variables
```bash
# Enable comprehensive tracing
INGEST_LANGFUSE_ENABLED=true
INGEST_LANGFUSE_DEBUG=true

# Trace sampling (adjust based on volume)
INGEST_LANGFUSE_SAMPLE_RATE=1.0  # 100% for development

# Model-specific tracking
INGEST_EMBEDDING_TRACK_MODEL_PERFORMANCE=true
INGEST_AST_PARSER_TRACE_ENABLED=true
```

### Recommended Langfuse Setup
1. **Create Project**: Set up dedicated "InGest-LLM-Embedding-Analysis" project
2. **Configure Datasets**: Organize traces by content type and model
3. **Set up Experiments**: Compare model performance across different configurations
4. **Custom Scoring**: Implement domain-specific efficiency metrics

## 🎯 Using This Data

### Model Selection Optimization
Use the dashboard to identify:
- Which models perform best for specific content types
- Optimal batch sizes for different scenarios
- Content patterns that cause processing bottlenecks

### Performance Tuning
Monitor trends to optimize:
- LM Studio model configurations
- Batch processing strategies
- AST parser complexity handling
- Content detection accuracy

### Capacity Planning
Track usage patterns to plan:
- Model deployment strategies
- Infrastructure scaling needs
- Processing pipeline optimization

This comprehensive observability setup provides you with detailed insights into embedding model efficiency, enabling data-driven decisions for optimal model selection and performance tuning.