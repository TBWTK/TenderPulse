select
    source,
    count(*) as current_record_count,
    max(observed_at) as last_observed_at,
    current_timestamp - max(observed_at) as observation_lag
from {{ ref('stg_current_procurement_records') }}
group by source
