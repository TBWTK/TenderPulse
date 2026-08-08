select
    source,
    coalesce(buyer_name, 'unknown') as buyer_name,
    count(*) as current_record_count,
    count(*) filter (where kind = 'award') as award_count,
    count(*) filter (where lifecycle = 'active') as active_notice_count,
    max(observed_at) as last_observed_at
from {{ ref('stg_current_procurement_records') }}
group by source, coalesce(buyer_name, 'unknown')
