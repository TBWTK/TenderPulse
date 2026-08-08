select
    concat(records.record_id::text, ':', lot.value ->> 'source_lot_id') as outcome_key,
    records.record_id,
    records.source,
    records.source_record_id,
    lot.value ->> 'source_lot_id' as source_lot_id,
    records.title,
    records.buyer_name,
    records.supplier_names,
    nullif(lot.value ->> 'amount', '')::numeric as award_amount,
    nullif(lot.value ->> 'currency', '') as currency,
    records.observed_at,
    records.raw_sha256,
    records.ingestion_run_id
from {{ ref('stg_current_procurement_records') }} as records
cross join lateral json_array_elements(records.lots) as lot(value)
where records.kind = 'award'
