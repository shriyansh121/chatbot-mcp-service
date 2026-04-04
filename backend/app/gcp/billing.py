from google.cloud.billing import budgets_v1
from google.cloud import billing_v1
from app.lib_helper.config import settings
from app.lib_helper.logger import setup_logger

logger = setup_logger("gcp.billing")

def get_billing_info(project_id: str = None):
    """Gets information about the project's billing."""
    try:
        project = project_id or settings.project_id
        client = billing_v1.CloudBillingClient()
        project_name = f"projects/{project}"
        
        info = client.get_project_billing_info(name=project_name)
        
        return {
            "billing_enabled": info.billing_enabled,
            "billing_account_name": info.billing_account_name,
            "project_id": info.project_id,
        }
    except Exception as e:
        logger.error(f"Error getting billing info: {e}")
        return {"error": str(e)}

def list_billing_accounts():
    """Lists available billing accounts."""
    try:
        client = billing_v1.CloudBillingClient()
        accounts = client.list_billing_accounts()
        
        acc_list = []
        for account in accounts:
            acc_list.append({
                "name": account.name,
                "display_name": account.display_name,
                "open": account.open
            })
        return acc_list
    except Exception as e:
        logger.error(f"Error listing billing accounts: {e}")
        return []

def get_billing_summary():
    """Returns the budget information for the billing account."""
    try:
        budget_client = budgets_v1.BudgetServiceClient()
        billing_path = f"billingAccounts/{settings.billing_id}"
        
        budgets = budget_client.list_budgets(parent=billing_path)
        
        result = []
        for b in budgets:
            budget_amount = "N/A"
            if b.amount.specified_amount:
                budget_amount = f"{b.amount.specified_amount.units} {b.amount.specified_amount.currency_code}"
            
            result.append({
                "name": b.display_name,
                "budget_amount": budget_amount,
                "thresholds": [f"{r.threshold_percent*100}%" for r in b.threshold_rules]
            })
        
        logger.info(f"Listed {len(result)} budgets.")
        return result
    except Exception as e:
        logger.error(f"Error getting billing summary: {e}")
        return {"error": str(e)}

def get_billing_history(days: int = 30):
    """Gets budget/billing summary (actual spend requires BigQuery export)."""
    try:
        summary = get_billing_summary()
        
        return {
            "days": days,
            "period": f"Last {days} days",
            "budgets": summary,
            "note": "For detailed spend history, configure BigQuery Billing Export."
        }
    except Exception as e:
        logger.error(f"Error getting billing history: {e}")
        return {"error": str(e)}
