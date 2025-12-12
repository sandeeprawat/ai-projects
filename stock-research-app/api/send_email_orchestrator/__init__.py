# Simple orchestrator to send email for an existing report
import logging
import azure.durable_functions as df

logger = logging.getLogger(__name__)

def orchestrator_function(context: df.DurableOrchestrationContext):
    """
    Simple orchestrator that just calls send_email activity.
    Input: {
      "reportId": str,
      "blobPaths": {"md": str, "html": str, "pdf": str?},
      "emailTo": [str, ...],
      "title": str,
      "userId": str
    }
    """
    input_data = context.get_input() or {}
    
    # Call send_email activity
    result = yield context.call_activity("send_email", input_data)
    
    logger.info(f"Email send result for report {input_data.get('reportId')}: {result}")
    
    return result

main = df.Orchestrator.create(orchestrator_function)
