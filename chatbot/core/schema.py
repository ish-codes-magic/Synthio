"""Database schema extraction and formatting utilities."""

from chatbot.core.database import DatabaseManager

# Comprehensive schema documentation for the LLM
SCHEMA_DOCUMENTATION = """
## Database Schema Documentation

### Dimension Tables (Reference Data)

#### hcp_dim (Healthcare Professionals)
Contains a directory of doctors/healthcare providers.
- **hcp_id** (INTEGER): Unique identifier for the doctor
- **full_name** (TEXT): Name of the doctor (e.g., Dr. Blake Garcia)
- **specialty** (TEXT): Medical specialty (Rheumatology, Internal Medicine, Nephrology)
- **tier** (TEXT): Classification tier (A, B, C) - priority/value of the doctor
- **territory_id** (INTEGER): Links to territory_dim

#### account_dim (Accounts/Facilities)
Contains information about hospitals and clinics.
- **account_id** (INTEGER): Unique identifier for the facility
- **name** (TEXT): Name of the hospital or clinic
- **account_type** (TEXT): Type of facility (Hospital, Clinic)
- **address** (TEXT): City and State location
- **territory_id** (INTEGER): Links to territory_dim

#### rep_dim (Sales Representatives)
Contains details about sales representatives.
- **rep_id** (INTEGER): Unique identifier for the sales rep
- **first_name** (TEXT): First name of the representative
- **last_name** (TEXT): Last name of the representative
- **region** (TEXT): Descriptive name of the region (e.g., Territory 1)

#### territory_dim (Territory Structure)
Defines geographical/organizational hierarchies.
- **territory_id** (INTEGER): Unique ID linking to HCPs and Accounts
- **name** (TEXT): Name of the territory
- **geo_type** (TEXT): Area type description (State Cluster, Metro Area)
- **parent_territory_id** (INTEGER): Parent territory for hierarchy

#### date_dim (Calendar/Time)
Master calendar table for time-based analysis.
- **date_id** (INTEGER): Integer representation of date (e.g., 20240801)
- **quarter** (TEXT): Fiscal/calendar quarter (Q1, Q2, Q3, Q4)
- **week_num** (INTEGER): Week number of the year
- **day_of_week** (TEXT): Day name

### Fact Tables (Transactional/Metric Data)

#### fact_rx (Prescription Sales)
Tracks prescription volumes by doctors over time.
- **hcp_id** (INTEGER): Links to hcp_dim - doctor writing the script
- **date_id** (INTEGER): Links to date_dim - when prescription was recorded
- **brand_code** (TEXT): Drug being prescribed (e.g., "GAZYVA")
- **trx_cnt** (INTEGER): Total Prescriptions count
- **nrx_cnt** (INTEGER): New Prescriptions count (new-to-brand)

#### fact_rep_activity (Sales Rep Activities)
Log of interactions between sales reps and doctors/accounts.
- **rep_id** (INTEGER): Links to rep_dim - rep who performed activity
- **hcp_id** (INTEGER): Links to hcp_dim - doctor contacted
- **account_id** (INTEGER): Links to account_dim - facility visited
- **activity_type** (TEXT): Nature of interaction (call, lunch_meeting)
- **status** (TEXT): Outcome (completed, cancelled)
- **duration_min** (INTEGER): Interaction duration in minutes

#### fact_ln_metrics (Patient & Market Metrics)
Aggregated market intelligence data.
- **entity_id** (INTEGER): Links to hcp_dim (when entity_type is 'H')
- **entity_type** (TEXT): Type of entity ('H' for HCP)
- **quarter_id** (TEXT): Time period for the metric (e.g., "2024Q3")
- **ln_patient_cnt** (INTEGER): Count of patients seen by entity
- **est_market_share** (REAL): Estimated market share percentage

#### fact_payor_mix (Insurance/Payor Data)
Breakdown of payment sources for accounts.
- **account_id** (INTEGER): Links to account_dim
- **payor_type** (TEXT): Insurance category (Commercial, Medicare, Medicaid)
- **pct_of_volume** (REAL): Percentage of account's volume from payor type

### Key Relationships
- hcp_dim.territory_id → territory_dim.territory_id
- account_dim.territory_id → territory_dim.territory_id
- fact_rx.hcp_id → hcp_dim.hcp_id
- fact_rx.date_id → date_dim.date_id
- fact_rep_activity.rep_id → rep_dim.rep_id
- fact_rep_activity.hcp_id → hcp_dim.hcp_id
- fact_rep_activity.account_id → account_dim.account_id
- fact_ln_metrics.entity_id → hcp_dim.hcp_id (when entity_type='H')
- fact_payor_mix.account_id → account_dim.account_id
"""


def get_database_schema(db_manager: DatabaseManager, include_samples: bool = True) -> str:
    """
    Generate a comprehensive schema description for the LLM.
    
    Args:
        db_manager: Database manager instance
        include_samples: Whether to include sample data
        
    Returns:
        Formatted schema string for LLM context
    """
    schema_parts = [SCHEMA_DOCUMENTATION]
    
    # Add actual table info from database
    schema_parts.append("\n### Current Database Tables\n")
    
    tables = db_manager.get_table_names()
    for table_name in sorted(tables):
        row_count = db_manager.get_row_count(table_name)
        columns = db_manager.get_table_schema(table_name)
        
        schema_parts.append(f"\n**{table_name}** ({row_count} rows)")
        schema_parts.append("Columns: " + ", ".join([f"`{c['name']}`" for c in columns]))
        
        if include_samples:
            sample_df = db_manager.get_sample_data(table_name, limit=2)
            if not sample_df.empty:
                schema_parts.append("\nSample data:")
                schema_parts.append("```")
                schema_parts.append(sample_df.to_string(index=False))
                schema_parts.append("```")
    
    return "\n".join(schema_parts)


def get_table_relationships() -> dict[str, list[str]]:
    """
    Get foreign key relationships between tables.
    
    Returns:
        Dictionary mapping table names to their related tables
    """
    return {
        "hcp_dim": ["territory_dim"],
        "account_dim": ["territory_dim"],
        "fact_rx": ["hcp_dim", "date_dim"],
        "fact_rep_activity": ["rep_dim", "hcp_dim", "account_dim"],
        "fact_ln_metrics": ["hcp_dim"],
        "fact_payor_mix": ["account_dim"],
    }

