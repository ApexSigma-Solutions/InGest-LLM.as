"""
End-to-End Distributed Tracing for InGest-LLM.as - ApexSigma Data Ingestion Service

This module implements comprehensive E2E tracing for the InGest-LLM service in the ApexSigma ecosystem.
Handles data ingestion, processing pipelines, LLM interactions, and cross-service agent coordination.
"""

import uuid
from typing import Dict, Any, Optional
from contextlib import contextmanager

from opentelemetry import trace, baggage
from opentelemetry.trace import Status, StatusCode
from opentelemetry.propagate import extract, inject
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagators.jaeger import JaegerPropagator
from opentelemetry.propagators.b3 import B3MultiFormat, B3SingleFormat
from opentelemetry.propagators.composite import CompositePropagator
from fastapi import Request, Response
from structlog import get_logger

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)

# Composite propagator for maximum compatibility
propagator = CompositePropagator(
    [
        TraceContextTextMapPropagator(),
        B3MultiFormat(),
        B3SingleFormat(),
        JaegerPropagator(),
        W3CBaggagePropagator(),
    ]
)


class InGestE2ETracing:
    """End-to-end distributed tracing for InGest-LLM.as service."""

    def __init__(self):
        """
        Initialize the tracing helper with the service's identifying metadata.
        
        Sets the instance attributes `service_name` to "ingest-llm.as" and `service_version` to "1.0.0" for use in spans, baggage, and outbound headers.
        """
        self.service_name = "ingest-llm.as"
        self.service_version = "1.0.0"

    def extract_request_context(self, request: Request) -> Dict[str, Any]:
        """
        Extract tracing and ApexSigma correlation information from an incoming HTTP request.
        
        Parameters:
            request (Request): Incoming FastAPI request whose headers will be inspected.
        
        Returns:
            dict: Mapping containing:
                - context: Extracted OpenTelemetry context (propagation carrier) from request headers.
                - correlation_id: Value of `x-apexsigma-correlation-id` header or `None` if absent.
                - workflow_id: Value of `x-apexsigma-workflow-id` header or `None` if absent.
                - agent_chain: Value of `x-apexsigma-agent-chain` header or an empty string if absent.
                - source_service: Value of `x-apexsigma-source-service` header or `None` if absent.
                - request_id: Value of `x-request-id` header or a newly generated UUID string when not provided.
        """
        headers = dict(request.headers)

        # Extract OpenTelemetry context
        context = extract(headers)

        # Extract ApexSigma correlation headers
        correlation_id = headers.get("x-apexsigma-correlation-id")
        workflow_id = headers.get("x-apexsigma-workflow-id")
        agent_chain = headers.get("x-apexsigma-agent-chain", "")

        return {
            "context": context,
            "correlation_id": correlation_id,
            "workflow_id": workflow_id,
            "agent_chain": agent_chain,
            "source_service": headers.get("x-apexsigma-source-service"),
            "request_id": headers.get("x-request-id", str(uuid.uuid4())),
        }

    def inject_response_context(
        self, response: Response, correlation_id: str, workflow_id: Optional[str] = None
    ):
        """
        Inject OpenTelemetry context and ApexSigma correlation headers into an outgoing HTTP response.
        
        Parameters:
            response (Response): The HTTP response object to modify with tracing headers.
            correlation_id (str): ApexSigma correlation identifier to include as `x-apexsigma-correlation-id`.
            workflow_id (Optional[str]): Optional ApexSigma workflow identifier to include as `x-apexsigma-workflow-id` when provided.
        """
        carrier = {}
        inject(carrier)

        # Add OpenTelemetry headers
        for key, value in carrier.items():
            response.headers[key] = value

        # Add ApexSigma correlation headers
        response.headers["x-apexsigma-correlation-id"] = correlation_id
        if workflow_id:
            response.headers["x-apexsigma-workflow-id"] = workflow_id
        response.headers["x-apexsigma-service"] = self.service_name

    @contextmanager
    def trace_data_ingestion(
        self,
        data_source: str,
        ingestion_type: str,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        record_count: Optional[int] = None,
    ):
        """
        Create a tracing span for a data ingestion operation and yield it for use within a context.
        
        Parameters:
            data_source (str): Origin of the data (e.g., filename, stream id, bucket).
            ingestion_type (str): Specific ingestion category (e.g., "file", "stream", "batch").
            correlation_id (Optional[str]): ApexSigma correlation identifier to attach to the span and baggage.
            workflow_id (Optional[str]): ApexSigma workflow identifier to attach to the span and baggage.
            record_count (Optional[int]): Number of records involved in the ingestion, attached as an attribute when provided.
        
        Returns:
            span: An OpenTelemetry span representing the ingestion operation, yielded for use as a context manager.
        
        Notes:
            The span will be marked as OK on successful completion. If an exception occurs, the span is marked as ERROR, the exception is recorded on the span, and the exception is re-raised.
        """
        span_name = f"ingest.data.{ingestion_type}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", ingestion_type)
                span.set_attribute("data.source", data_source)
                span.set_attribute("ingestion.type", ingestion_type)

                if record_count is not None:
                    span.set_attribute("data.record_count", record_count)

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)
                    baggage.set_baggage("correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)
                    baggage.set_baggage("workflow_id", workflow_id)

                # Set baggage for cross-service propagation
                baggage.set_baggage("service", self.service_name)
                baggage.set_baggage("operation", ingestion_type)
                baggage.set_baggage("data_source", data_source)

                logger.info(
                    "Data ingestion started",
                    data_source=data_source,
                    ingestion_type=ingestion_type,
                    record_count=record_count,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "Data ingestion completed successfully",
                    data_source=data_source,
                    ingestion_type=ingestion_type,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "Data ingestion failed",
                    data_source=data_source,
                    ingestion_type=ingestion_type,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise

    @contextmanager
    def trace_llm_interaction(
        self,
        model_name: str,
        operation: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """
        Create a tracing span for a single LLM interaction and yield the active span for instrumentation.
        
        Parameters:
            model_name (str): Identifier of the LLM model used (e.g., "gpt-4").
            operation (str): LLM operation being performed (e.g., "completion", "embedding", "fine-tuning").
            prompt_tokens (Optional[int]): Number of tokens in the prompt, if available.
            completion_tokens (Optional[int]): Number of tokens produced by the model, if available.
            correlation_id (Optional[str]): ApexSigma correlation identifier to attach to the span and baggage.
            workflow_id (Optional[str]): ApexSigma workflow identifier to attach to the span and baggage.
        
        Yields:
            The active OpenTelemetry span for the LLM interaction.
        
        Notes:
            The span will have service and LLM attributes and will set baggage entries for cross-service propagation.
            On normal completion the span status is set to OK; on exception the span is marked ERROR, the exception is recorded, and the exception is re-raised.
        """
        span_name = f"ingest.llm.{operation}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", operation)
                span.set_attribute("llm.model", model_name)
                span.set_attribute("llm.operation", operation)

                if prompt_tokens is not None:
                    span.set_attribute("llm.prompt_tokens", prompt_tokens)
                if completion_tokens is not None:
                    span.set_attribute("llm.completion_tokens", completion_tokens)
                    span.set_attribute(
                        "llm.total_tokens", (prompt_tokens or 0) + completion_tokens
                    )

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)
                    baggage.set_baggage("correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)
                    baggage.set_baggage("workflow_id", workflow_id)

                # Set baggage for cross-service propagation
                baggage.set_baggage("service", self.service_name)
                baggage.set_baggage("llm_model", model_name)
                baggage.set_baggage("llm_operation", operation)

                logger.info(
                    "LLM interaction started",
                    model=model_name,
                    operation=operation,
                    prompt_tokens=prompt_tokens,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "LLM interaction completed",
                    model=model_name,
                    operation=operation,
                    completion_tokens=completion_tokens,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "LLM interaction failed",
                    model=model_name,
                    operation=operation,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise

    @contextmanager
    def trace_processing_pipeline(
        self,
        pipeline_name: str,
        stage: str,
        batch_size: Optional[int] = None,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """
        Create a tracing span for a specific data processing pipeline stage and yield the active span for instrumentation.
        
        Parameters:
            pipeline_name (str): Logical name of the processing pipeline.
            stage (str): Name of the pipeline stage or step being executed.
            batch_size (Optional[int]): Number of records in the current batch, if applicable.
            correlation_id (Optional[str]): ApexSigma correlation identifier to attach to the span and baggage.
            workflow_id (Optional[str]): ApexSigma workflow identifier to attach to the span and baggage.
        
        Yields:
            span: The active OpenTelemetry span for the pipeline stage. The span will have service, pipeline, stage,
                  optional batch size, and ApexSigma correlation/workflow attributes and baggage set. The span's status
                  is set to OK on successful completion and to ERROR with the exception recorded if an exception is raised.
        """
        span_name = f"ingest.pipeline.{pipeline_name}.{stage}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", f"pipeline_{stage}")
                span.set_attribute("pipeline.name", pipeline_name)
                span.set_attribute("pipeline.stage", stage)

                if batch_size is not None:
                    span.set_attribute("pipeline.batch_size", batch_size)

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)
                    baggage.set_baggage("correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)
                    baggage.set_baggage("workflow_id", workflow_id)

                # Set baggage for cross-service propagation
                baggage.set_baggage("service", self.service_name)
                baggage.set_baggage("pipeline", pipeline_name)
                baggage.set_baggage("stage", stage)

                logger.info(
                    "Processing pipeline stage started",
                    pipeline=pipeline_name,
                    stage=stage,
                    batch_size=batch_size,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "Processing pipeline stage completed",
                    pipeline=pipeline_name,
                    stage=stage,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "Processing pipeline stage failed",
                    pipeline=pipeline_name,
                    stage=stage,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise

    @contextmanager
    def trace_vector_operations(
        self,
        operation: str,
        vector_store: str,
        dimension: Optional[int] = None,
        vector_count: Optional[int] = None,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """
        Create a tracing span for a vector database operation (e.g., index, search, upsert) and yield it for use as a context manager.
        
        Parameters:
            operation (str): The vector operation name (e.g., "index", "search", "upsert") used in span naming and attributes.
            vector_store (str): Identifier of the vector store or index targeted by the operation.
            dimension (Optional[int]): Dimensionality of the vectors involved, if known.
            vector_count (Optional[int]): Number of vectors processed or affected by the operation, if known.
            correlation_id (Optional[str]): ApexSigma correlation identifier to attach to the span and baggage for cross-service correlation.
            workflow_id (Optional[str]): ApexSigma workflow identifier to attach to the span and baggage for workflow-level tracing.
        
        Returns:
            span: An OpenTelemetry Span object yielded for the duration of the traced operation; the caller should use it as a context manager and perform the vector operation while the span is active.
        """
        span_name = f"ingest.vector.{operation}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", operation)
                span.set_attribute("vector.store", vector_store)
                span.set_attribute("vector.operation", operation)

                if dimension is not None:
                    span.set_attribute("vector.dimension", dimension)
                if vector_count is not None:
                    span.set_attribute("vector.count", vector_count)

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)
                    baggage.set_baggage("correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)
                    baggage.set_baggage("workflow_id", workflow_id)

                # Set baggage for cross-service propagation
                baggage.set_baggage("service", self.service_name)
                baggage.set_baggage("vector_store", vector_store)
                baggage.set_baggage("vector_operation", operation)

                logger.info(
                    "Vector operation started",
                    operation=operation,
                    vector_store=vector_store,
                    dimension=dimension,
                    vector_count=vector_count,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "Vector operation completed",
                    operation=operation,
                    vector_store=vector_store,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "Vector operation failed",
                    operation=operation,
                    vector_store=vector_store,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise

    def prepare_outbound_headers(
        self,
        target_service: str,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        agent_chain: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Construct headers for an outbound HTTP request with injected OpenTelemetry context and ApexSigma correlation metadata.
        
        Parameters:
            target_service (str): Identifier of the target service (used for logging and tracing context association).
            correlation_id (Optional[str]): ApexSigma correlation identifier to propagate to the target service.
            workflow_id (Optional[str]): ApexSigma workflow identifier to propagate to the target service.
            agent_chain (Optional[str]): Agent chain string; if provided, the current service name is appended using '->', otherwise the header is set to the current service name.
        
        Returns:
            Dict[str, str]: Headers including injected OpenTelemetry propagation headers, `x-apexsigma-correlation-id` (if provided), `x-apexsigma-workflow-id` (if provided), `x-apexsigma-agent-chain`, `x-apexsigma-source-service`, and a generated `x-request-id`.
        """
        headers = {}

        # Inject OpenTelemetry context
        inject(headers)

        # Add ApexSigma correlation headers
        if correlation_id:
            headers["x-apexsigma-correlation-id"] = correlation_id
        if workflow_id:
            headers["x-apexsigma-workflow-id"] = workflow_id
        if agent_chain:
            headers["x-apexsigma-agent-chain"] = f"{agent_chain}->{self.service_name}"
        else:
            headers["x-apexsigma-agent-chain"] = self.service_name

        headers["x-apexsigma-source-service"] = self.service_name
        headers["x-request-id"] = str(uuid.uuid4())

        logger.debug(
            "Prepared outbound headers",
            target_service=target_service,
            correlation_id=correlation_id,
            headers=list(headers.keys()),
        )

        return headers

    @contextmanager
    def trace_cross_service_call(
        self,
        target_service: str,
        operation: str,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """
        Create a tracing span for an outbound call to another ApexSigma service and yield the active span for instrumentation.
        
        Parameters:
            target_service (str): Destination service name for the outbound call.
            operation (str): Logical operation being performed on the target service.
            correlation_id (Optional[str]): ApexSigma correlation identifier to attach to the span, if available.
            workflow_id (Optional[str]): ApexSigma workflow identifier to attach to the span, if available.
        
        Returns:
            span: The started OpenTelemetry span representing the outbound cross-service call.
        """
        span_name = f"ingest.outbound.{target_service}.{operation}"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", self.service_version)
                span.set_attribute("operation.name", operation)
                span.set_attribute("target.service", target_service)
                span.set_attribute("call.direction", "outbound")

                # Set ApexSigma correlation attributes
                if correlation_id:
                    span.set_attribute("apexsigma.correlation_id", correlation_id)

                if workflow_id:
                    span.set_attribute("apexsigma.workflow_id", workflow_id)

                logger.info(
                    "Cross-service call initiated",
                    target_service=target_service,
                    operation=operation,
                    correlation_id=correlation_id,
                    trace_id=format(span.get_span_context().trace_id, "032x"),
                )

                yield span

                span.set_status(Status(StatusCode.OK))
                logger.info(
                    "Cross-service call completed",
                    target_service=target_service,
                    operation=operation,
                    correlation_id=correlation_id,
                )

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    "Cross-service call failed",
                    target_service=target_service,
                    operation=operation,
                    correlation_id=correlation_id,
                    error=str(e),
                )
                raise


# Global instance
ingest_e2e_tracing = InGestE2ETracing()


def get_ingest_e2e_tracing() -> InGestE2ETracing:
    """
    Return the module-level InGestE2ETracing singleton.
    
    Returns:
        InGestE2ETracing: The shared tracing instance used by the ingest-LLM service.
    """
    return ingest_e2e_tracing